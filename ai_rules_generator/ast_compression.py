"""
Tree-sitter-driven AST compression ("squeezing").

This module produces a `Skeleton` for a source file: a deterministic,
language-aware extract of every top-level declaration with its signature,
docstring, and a placeholder for the body.  Per the research, this preserves
~all the architectural information the LLM needs while dropping ~70% of
tokens vs the raw file.

Design notes
------------
- All Tree-sitter imports are lazy.  A missing grammar logs once and falls
  back to the legacy regex extractor in `scanner.extract_file_signatures`.
- Parsing is best-effort.  A syntax error in a file degrades gracefully to
  whatever subtree parsed correctly.
- We avoid keeping `tree_sitter.Node` objects in the returned data class so
  callers don't accidentally hold the parser alive across many files.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LanguageRule:
    """How to compress a single language's AST."""

    name: str                          # tree-sitter language identifier
    keep_kinds: Set[str]               # node types whose signature we preserve
    body_kinds: Set[str]               # child node types treated as the body
    import_kinds: Set[str]             # node types representing imports
    comment_kinds: Set[str] = field(default_factory=lambda: {"comment", "line_comment", "block_comment"})
    body_placeholder: str = "# ... body elided ..."


# Map file extensions to LanguageRule.
LANGUAGE_RULES: Dict[str, LanguageRule] = {
    ".py": LanguageRule(
        name="python",
        keep_kinds={
            "function_definition",
            "class_definition",
            "decorated_definition",
        },
        body_kinds={"block"},
        import_kinds={"import_statement", "import_from_statement"},
        body_placeholder="    ...  # body elided",
    ),
    ".ts": LanguageRule(
        name="typescript",
        keep_kinds={
            "function_declaration",
            "method_definition",
            "class_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "enum_declaration",
            "abstract_class_declaration",
            "abstract_method_signature",
        },
        body_kinds={"statement_block", "class_body"},
        import_kinds={"import_statement"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".tsx": LanguageRule(
        name="tsx",
        keep_kinds={
            "function_declaration",
            "method_definition",
            "class_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "enum_declaration",
        },
        body_kinds={"statement_block", "class_body"},
        import_kinds={"import_statement"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".js": LanguageRule(
        name="javascript",
        keep_kinds={
            "function_declaration",
            "method_definition",
            "class_declaration",
        },
        body_kinds={"statement_block", "class_body"},
        import_kinds={"import_statement"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".jsx": LanguageRule(
        name="javascript",
        keep_kinds={
            "function_declaration",
            "method_definition",
            "class_declaration",
        },
        body_kinds={"statement_block", "class_body"},
        import_kinds={"import_statement"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".go": LanguageRule(
        name="go",
        keep_kinds={
            "function_declaration",
            "method_declaration",
            "type_declaration",
        },
        body_kinds={"block"},
        import_kinds={"import_declaration"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".rs": LanguageRule(
        name="rust",
        keep_kinds={
            "function_item",
            "impl_item",
            "struct_item",
            "enum_item",
            "trait_item",
            "type_item",
        },
        body_kinds={"block", "declaration_list"},
        import_kinds={"use_declaration"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".java": LanguageRule(
        name="java",
        keep_kinds={
            "method_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        },
        body_kinds={"block", "class_body", "interface_body", "enum_body"},
        import_kinds={"import_declaration"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".cpp": LanguageRule(
        name="cpp",
        keep_kinds={
            "function_definition",
            "class_specifier",
            "struct_specifier",
        },
        body_kinds={"compound_statement", "field_declaration_list"},
        import_kinds={"preproc_include"},
        body_placeholder="{ /* body elided */ }",
    ),
    ".hpp": LanguageRule(
        name="cpp",
        keep_kinds={
            "function_definition",
            "class_specifier",
            "struct_specifier",
        },
        body_kinds={"compound_statement", "field_declaration_list"},
        import_kinds={"preproc_include"},
        body_placeholder="{ /* body elided */ }",
    ),
}

# Identifier-node types per language, used to extract a symbol's name.
_NAME_FIELDS: Dict[str, Tuple[str, ...]] = {
    "python":     ("name",),
    "typescript": ("name",),
    "tsx":        ("name",),
    "javascript": ("name",),
    "go":         ("name",),
    "rust":       ("name",),
    "java":       ("name",),
    "cpp":        ("declarator", "name"),
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SignatureNode:
    """A single preserved top-level declaration."""

    kind: str                # tree-sitter node type, e.g. "function_definition"
    name: str                # extracted symbol name (best-effort)
    signature: str           # the textual signature (no body)
    docstring: str = ""      # first docstring/comment if available
    start_line: int = 0
    end_line: int = 0
    children: List["SignatureNode"] = field(default_factory=list)
    # Raw body text (not emitted in the rendered skeleton; used by code_graph
    # for call detection).  Empty when the node has no body.
    body_text: str = ""


@dataclass
class Skeleton:
    """Compressed representation of a single file."""

    file_path: str
    language: str
    signatures: List[SignatureNode] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    outline_markdown: str = ""
    token_estimate: int = 0
    raw_token_estimate: int = 0
    used_fallback: bool = False  # True if we couldn't load a grammar


# ---------------------------------------------------------------------------
# Lazy Tree-sitter loader
# ---------------------------------------------------------------------------

_PARSERS: Dict[str, "object"] = {}
_TREE_SITTER_OK: Optional[bool] = None
_FALLBACK_LOGGED: Set[str] = set()


# Module-level flag indicating which API surface the loaded grammar pack uses.
# - "legacy" : tree_sitter_languages (Node has .type / .children / .start_point)
# - "modern" : tree_sitter_language_pack >=1.x (Node has .kind / .child(i))
_TS_API_FLAVOR: Optional[str] = None


def _try_import_tree_sitter():
    """
    Lazily import a tree-sitter grammar pack and detect its API flavor.

    Returns the `get_parser` callable or None if no grammar pack is available.
    Memoized.
    """
    global _TREE_SITTER_OK, _TS_API_FLAVOR
    if _TREE_SITTER_OK is False:
        return None
    try:
        try:
            from tree_sitter_language_pack import get_parser  # type: ignore
            _TS_API_FLAVOR = "modern"
        except ImportError:
            from tree_sitter_languages import get_parser  # type: ignore
            _TS_API_FLAVOR = "legacy"
        _TREE_SITTER_OK = True
        return get_parser
    except Exception as exc:  # pragma: no cover - missing dep path
        if _TREE_SITTER_OK is None:
            logger.info(
                "Tree-sitter grammars unavailable (%s); ast_compression will "
                "fall back to the regex signature extractor.",
                exc,
            )
        _TREE_SITTER_OK = False
        return None


# ---------------------------------------------------------------------------
# Node adapter
# ---------------------------------------------------------------------------

def _call_or_get(obj, attr_name: str):
    """Return obj.attr() if it's a method, otherwise obj.attr."""
    value = getattr(obj, attr_name, None)
    if value is None:
        return None
    if callable(value):
        try:
            return value()
        except TypeError:
            return value
    return value


class _NodeAdapter:
    """
    Normalized view over both tree-sitter API flavors.

    Exposes the small subset of fields the rest of this module uses:
        .type, .start_byte, .end_byte, .start_point (row,col),
        .end_point, .children, .child_by_field_name(name).

    Modern (`tree_sitter_language_pack` 1.x) exposes most members as zero-arg
    methods; legacy bindings expose them as properties.  We normalize both.
    """

    __slots__ = ("_n", "_flavor", "_children_cache")

    def __init__(self, raw, flavor: str) -> None:
        self._n = raw
        self._flavor = flavor
        self._children_cache: Optional[List["_NodeAdapter"]] = None

    @property
    def type(self) -> str:
        # legacy uses .type, modern uses .kind() (or .kind on older builds)
        for name in ("kind", "type"):
            if hasattr(self._n, name):
                v = _call_or_get(self._n, name)
                if v is not None:
                    return v
        return "ERROR"

    @property
    def start_byte(self) -> int:
        return _call_or_get(self._n, "start_byte") or 0

    @property
    def end_byte(self) -> int:
        return _call_or_get(self._n, "end_byte") or 0

    @property
    def start_point(self) -> Tuple[int, int]:
        pt = _call_or_get(self._n, "start_position")
        if pt is None:
            pt = _call_or_get(self._n, "start_point")
        return _point_to_tuple(pt)

    @property
    def end_point(self) -> Tuple[int, int]:
        pt = _call_or_get(self._n, "end_position")
        if pt is None:
            pt = _call_or_get(self._n, "end_point")
        return _point_to_tuple(pt)

    @property
    def children(self) -> List["_NodeAdapter"]:
        if self._children_cache is not None:
            return self._children_cache
        items: List = []
        if hasattr(self._n, "child_count"):
            count = _call_or_get(self._n, "child_count") or 0
            try:
                items = [self._n.child(i) for i in range(count)]
            except TypeError:
                # legacy bindings: 'children' attr is a list
                items = list(getattr(self._n, "children", []) or [])
        else:
            items = list(getattr(self._n, "children", []) or [])
        wrapped = [_NodeAdapter(c, self._flavor) for c in items if c is not None]
        self._children_cache = wrapped
        return wrapped

    def child_by_field_name(self, name: str) -> Optional["_NodeAdapter"]:
        try:
            raw = self._n.child_by_field_name(name)
        except Exception:
            raw = None
        return _NodeAdapter(raw, self._flavor) if raw is not None else None


def _point_to_tuple(pt) -> Tuple[int, int]:
    if pt is None:
        return (0, 0)
    if isinstance(pt, tuple):
        return pt
    row = getattr(pt, "row", None)
    col = getattr(pt, "column", None)
    if row is not None and col is not None:
        return (row, col)
    try:
        return tuple(pt)
    except Exception:
        return (0, 0)


def _get_parser(language: str):
    if language in _PARSERS:
        return _PARSERS[language]
    get_parser = _try_import_tree_sitter()
    if get_parser is None:
        return None
    try:
        parser = get_parser(language)
    except Exception as exc:
        if language not in _FALLBACK_LOGGED:
            logger.info(
                "Could not load tree-sitter grammar for %r (%s); will fall "
                "back to regex for this language.",
                language, exc,
            )
            _FALLBACK_LOGGED.add(language)
        return None
    _PARSERS[language] = parser
    return parser


# ---------------------------------------------------------------------------
# Tree walking
# ---------------------------------------------------------------------------

def _node_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _find_child_by_field(node, field_name: str):
    """Tree-sitter Node helper - return the child registered under `field_name`."""
    try:
        return node.child_by_field_name(field_name)
    except Exception:
        return None


def _extract_name(node, language: str, source: bytes) -> str:
    """Best-effort symbol-name extraction across languages."""
    for field in _NAME_FIELDS.get(language, ("name",)):
        child = _find_child_by_field(node, field)
        if child is None:
            continue
        # C++ wraps the name in a declarator subtree.
        inner = _find_child_by_field(child, "declarator") or child
        text = _node_text(inner, source).strip()
        if text:
            return text.split("(")[0].split("<")[0].strip()
    # Fallback: first identifier child.
    for child in getattr(node, "children", []):
        if child.type in {"identifier", "type_identifier", "field_identifier"}:
            return _node_text(child, source)
    return "(anonymous)"


def _extract_signature(node, rule: LanguageRule, source: bytes) -> str:
    """
    Reconstruct the signature text by removing body-typed children.

    We walk the node's source byte range and stitch together the slices that
    are NOT covered by body subtrees, producing e.g.:
        `def foo(x: int) -> str:` (Python)
        `function foo(x: number): string` (TS)
        `func (s *Server) Foo(x int) error` (Go)
    """
    start = node.start_byte
    end = node.end_byte
    body_ranges: List[Tuple[int, int]] = []
    for child in node.children:
        if child.type in rule.body_kinds:
            body_ranges.append((child.start_byte, child.end_byte))
            break  # only excise the first / primary body

    if not body_ranges:
        sig = source[start:end].decode("utf-8", errors="ignore")
    else:
        # Keep everything before the body, then append a placeholder.
        b_start, _b_end = body_ranges[0]
        head = source[start:b_start].decode("utf-8", errors="ignore").rstrip()
        sig = f"{head} {rule.body_placeholder}"
    return sig.strip()


def _extract_docstring(node, language: str, source: bytes) -> str:
    """Pull the leading docstring/comment of a definition node, if any."""
    if language == "python":
        block = _find_child_by_field(node, "body")
        if block is None:
            return ""
        for child in block.children:
            if child.type == "expression_statement" and child.children:
                inner = child.children[0]
                if inner.type == "string":
                    return _node_text(inner, source).strip().strip('"').strip("'")[:240]
            break
        return ""
    # Other languages: first preceding /// or //! comment - skipped for now to
    # keep skeletons tight.
    return ""


def _walk_top_level(
    node,
    rule: LanguageRule,
    source: bytes,
    *,
    depth: int = 0,
) -> List[SignatureNode]:
    """Collect SignatureNodes from the top level of a tree."""
    out: List[SignatureNode] = []
    for child in node.children:
        kind = child.type
        if kind in rule.keep_kinds:
            inner = child
            # Python decorated_definition wraps the real def/class.
            if kind == "decorated_definition":
                for grand in child.children:
                    if grand.type in rule.keep_kinds:
                        inner = grand
                        break
            sig = _extract_signature(child, rule, source)
            name = _extract_name(inner, rule.name, source)
            doc = _extract_docstring(inner, rule.name, source)
            # Capture body bytes for downstream call analysis.
            body_text = ""
            body_node = None
            for grand in inner.children:
                if grand.type in rule.body_kinds:
                    body_node = grand
                    break
            if body_node is not None:
                body_text = _node_text(body_node, source)
            children: List[SignatureNode] = []
            # For class-like nodes, recurse one level to capture methods.
            if depth < 1 and body_node is not None:
                children = _walk_top_level(
                    body_node, rule, source, depth=depth + 1
                )
            out.append(SignatureNode(
                kind=kind,
                name=name,
                signature=sig,
                docstring=doc,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                children=children,
                body_text=body_text,
            ))
    return out


def _collect_imports(node, rule: LanguageRule, source: bytes) -> List[str]:
    out: List[str] = []
    for child in node.children:
        if child.type in rule.import_kinds:
            text = _node_text(child, source).strip()
            if text:
                out.append(text.splitlines()[0])
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_language_rule(file_path: Path) -> Optional[LanguageRule]:
    return LANGUAGE_RULES.get(file_path.suffix.lower())


def estimate_tokens(text: str) -> int:
    """Cheap token estimate: ~4 chars/token for English+code."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _parse_with(parser, source: bytes):
    """
    Adapter for tree-sitter API differences.

    - Legacy `tree_sitter.Parser.parse(bytes)` works as-is.
    - `tree_sitter_language_pack` 1.x wraps the parser and expects `str`.
    """
    try:
        return parser.parse(source)
    except TypeError:
        return parser.parse(source.decode("utf-8", errors="ignore"))


def _root_node(tree, flavor: str) -> "_NodeAdapter":
    """Return a normalized adapter over the tree's root node."""
    raw_root = tree.root_node() if flavor == "modern" else tree.root_node
    return _NodeAdapter(raw_root, flavor)


def extract_skeleton(file_path: Path) -> Optional[Skeleton]:
    """
    Compress one file into a Skeleton.  Returns None for unsupported
    languages; returns a fallback Skeleton (used_fallback=True) when the
    grammar is missing.
    """
    rule = get_language_rule(file_path)
    if rule is None:
        return None

    try:
        source = file_path.read_bytes()
    except OSError:
        return None
    raw_estimate = estimate_tokens(source.decode("utf-8", errors="ignore"))

    parser = _get_parser(rule.name)
    if parser is None:
        # Grammar unavailable - return a Skeleton stub so callers can still
        # display *something* deterministic for the file.
        return Skeleton(
            file_path=str(file_path),
            language=rule.name,
            signatures=[],
            imports=[],
            outline_markdown="",
            token_estimate=0,
            raw_token_estimate=raw_estimate,
            used_fallback=True,
        )

    try:
        tree = _parse_with(parser, source)
    except Exception as exc:
        logger.debug("tree-sitter parse failed for %s: %s", file_path, exc)
        return Skeleton(
            file_path=str(file_path),
            language=rule.name,
            used_fallback=True,
            raw_token_estimate=raw_estimate,
        )

    flavor = _TS_API_FLAVOR or "legacy"
    root = _root_node(tree, flavor)
    signatures = _walk_top_level(root, rule, source)
    imports = _collect_imports(root, rule, source)

    outline = render_outline_markdown(file_path, signatures, imports)
    return Skeleton(
        file_path=str(file_path),
        language=rule.name,
        signatures=signatures,
        imports=imports,
        outline_markdown=outline,
        token_estimate=estimate_tokens(outline),
        raw_token_estimate=raw_estimate,
        used_fallback=False,
    )


def render_outline_markdown(
    file_path: Path,
    signatures: List[SignatureNode],
    imports: List[str],
    *,
    include_docstrings: bool = True,
) -> str:
    """Render a Skeleton's signatures as a Markdown code block per file."""
    parts: List[str] = []
    rel_name = os.path.basename(str(file_path))
    parts.append(f"#### `{rel_name}`")
    if imports:
        parts.append("")
        parts.append("**Imports:**")
        parts.append("")
        parts.append("```")
        for imp in imports[:10]:
            parts.append(imp)
        if len(imports) > 10:
            parts.append(f"# ... +{len(imports) - 10} more")
        parts.append("```")

    if not signatures:
        parts.append("")
        parts.append("_(no top-level definitions found)_")
        return "\n".join(parts)

    parts.append("")
    parts.append("**Signatures:**")
    parts.append("")
    parts.append("```")
    for sig in signatures:
        parts.append(sig.signature)
        if include_docstrings and sig.docstring:
            parts.append(f'    """{sig.docstring}"""')
        for child in sig.children:
            parts.append(f"    {child.signature}")
    parts.append("```")
    return "\n".join(parts)


def compress_folder(
    folder_path: Path,
    file_names: List[str],
    *,
    max_total_tokens: int = 4000,
    include_docstrings: bool = True,
) -> Tuple[List[Skeleton], str]:
    """
    Compress every supported file in a folder, respecting a per-folder budget.

    Returns the list of skeletons plus a Markdown blob safe to drop into a
    `.cursor/rules/*.mdc` Tier-2 file or the `<input_code>` XML tag.

    When the cumulative budget is exceeded, later files are downgraded to
    "signatures only" (docstrings dropped); if still over, they are listed
    by name only.
    """
    skeletons: List[Skeleton] = []
    rendered: List[str] = []
    total = 0
    over_budget = False

    for name in file_names:
        path = folder_path / name
        skel = extract_skeleton(path)
        if skel is None:
            continue
        if skel.used_fallback or not skel.outline_markdown:
            continue
        if over_budget:
            rendered.append(f"#### `{name}` (omitted: budget)")
            continue
        outline = (
            skel.outline_markdown
            if include_docstrings
            else render_outline_markdown(
                path, skel.signatures, skel.imports, include_docstrings=False
            )
        )
        cost = estimate_tokens(outline)
        if total + cost > max_total_tokens and skeletons:
            # Try dropping docstrings
            outline = render_outline_markdown(
                path, skel.signatures, skel.imports, include_docstrings=False
            )
            cost = estimate_tokens(outline)
            if total + cost > max_total_tokens:
                over_budget = True
                rendered.append(f"#### `{name}` (omitted: budget)")
                continue
        skeletons.append(skel)
        rendered.append(outline)
        total += cost

    return skeletons, "\n\n".join(rendered)


__all__ = [
    "LanguageRule",
    "LANGUAGE_RULES",
    "SignatureNode",
    "Skeleton",
    "get_language_rule",
    "estimate_tokens",
    "extract_skeleton",
    "render_outline_markdown",
    "compress_folder",
]
