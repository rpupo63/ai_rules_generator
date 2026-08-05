"""
Structure-only tag extraction via vendored tree-sitter tag queries.

Inputs are symbol names, paths, and reference edges — never string literals,
comments, or doc text. Queries live in `queries/` (Aider Apache-2.0 + local
GDScript).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

QUERIES_DIR = Path(__file__).resolve().parent / "queries"

# Extension → tree-sitter language name (must match `{lang}-tags.scm`).
EXT_TO_LANG: Dict[str, str] = {
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".lua": "lua",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".jl": "julia",
    ".ex": "elixir",
    ".exs": "elixir",
    ".elm": "elm",
    ".dart": "dart",
    ".gd": "gdscript",
    ".sol": "solidity",
    ".zig": "zig",
    ".d": "d",
    ".ml": "ocaml",
    ".mli": "ocaml_interface",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".lisp": "commonlisp",
    ".el": "elisp",
    ".rkt": "racket",
    ".m": "matlab",
    ".mat": "matlab",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".ino": "arduino",
    ".properties": "properties",
    ".rules": "udev",
}

_LANG_CACHE: Dict[str, object] = {}
_SCM_CACHE: Dict[str, str] = {}


@dataclass(frozen=True)
class Tag:
    """One definition or reference symbol name at a path/line."""

    rel_path: str
    name: str
    kind: str  # "def" | "ref"
    line: int  # 0-based


def language_for_path(path: Path) -> Optional[str]:
    return EXT_TO_LANG.get(path.suffix.lower())


def scm_path_for_lang(lang: str) -> Path:
    return QUERIES_DIR / f"{lang}-tags.scm"


def _load_scm(lang: str) -> Optional[str]:
    if lang in _SCM_CACHE:
        return _SCM_CACHE[lang]
    path = scm_path_for_lang(lang)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    _SCM_CACHE[lang] = text
    return text


def _get_language(lang: str):
    if lang in _LANG_CACHE:
        return _LANG_CACHE[lang]
    try:
        from tree_sitter_language_pack import get_language
    except ImportError:
        logger.info("tree_sitter_language_pack not installed; no tags for %s", lang)
        _LANG_CACHE[lang] = None
        return None
    try:
        language = get_language(lang)
    except Exception as exc:  # pragma: no cover - missing grammar
        logger.debug("grammar unavailable for %s: %s", lang, exc)
        language = None
    _LANG_CACHE[lang] = language
    return language


def _node_text(node) -> str:
    raw = node.text
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore")
    return str(raw)


def _run_captures(query, root_node):
    """Support tree-sitter Query.captures and QueryCursor.captures."""
    if hasattr(query, "captures"):
        return query.captures(root_node)
    from tree_sitter import QueryCursor

    return QueryCursor(query).captures(root_node)


def extract_tags(abs_path: Path, rel_path: str) -> List[Tag]:
    """
    Run the language tag query on one file. Returns def/ref tags only
    (captures named `name.definition.*` / `name.reference.*`).
    """
    lang = language_for_path(abs_path)
    if not lang:
        return []
    scm = _load_scm(lang)
    language = _get_language(lang)
    if not scm or language is None:
        return []

    try:
        source = abs_path.read_bytes()
    except OSError:
        return []
    if not source.strip():
        return []

    try:
        from tree_sitter import Parser, Query
    except ImportError:
        return []

    try:
        tree = Parser(language).parse(source)
        root = tree.root_node
        query = Query(language, scm)
        captures = _run_captures(query, root)
    except Exception as exc:
        logger.debug("tag extract failed for %s: %s", rel_path, exc)
        return []

    # Normalize to list of (node, tag_name)
    pairs: List[Tuple[object, str]] = []
    if isinstance(captures, dict):
        for tag_name, nodes in captures.items():
            for node in nodes:
                pairs.append((node, tag_name))
    else:
        for item in captures:
            if isinstance(item, tuple) and len(item) == 2:
                a, b = item
                if isinstance(a, str):
                    pairs.append((b, a))
                else:
                    pairs.append((a, b))

    out: List[Tag] = []
    seen: Set[Tuple[str, str, int]] = set()
    for node, tag_name in pairs:
        if tag_name.startswith("name.definition."):
            kind = "def"
        elif tag_name.startswith("name.reference."):
            kind = "ref"
        else:
            continue
        name = _node_text(node).strip()
        if not name or "\n" in name:
            # Skip multi-line / empty — never ingest string/doc bodies.
            continue
        line = int(node.start_point[0])
        key = (name, kind, line)
        if key in seen:
            continue
        seen.add(key)
        out.append(Tag(rel_path=rel_path, name=name, kind=kind, line=line))
    return out


def list_source_files(project_root: Path) -> List[Path]:
    """Prefer `git ls-files`; fall back to a recursive walk of known suffixes."""
    root = project_root.resolve()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=False,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            rels = [p for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]
            return [root / r for r in rels]
    except OSError:
        pass

    out: List[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and language_for_path(path):
            out.append(path)
    return out


def extract_project_tags(
    project_root: Path,
    file_paths: Optional[Iterable[Path]] = None,
    *,
    should_include=None,
) -> List[Tag]:
    """Extract tags for many files under project_root."""
    root = project_root.resolve()
    paths = list(file_paths) if file_paths is not None else list_source_files(root)
    tags: List[Tag] = []
    for abs_path in paths:
        if not abs_path.is_file():
            continue
        if language_for_path(abs_path) is None:
            continue
        try:
            rel = str(abs_path.resolve().relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = abs_path.name
        if should_include is not None and not should_include(abs_path, rel):
            continue
        tags.extend(extract_tags(abs_path, rel))
    return tags


__all__ = [
    "EXT_TO_LANG",
    "QUERIES_DIR",
    "Tag",
    "extract_project_tags",
    "extract_tags",
    "language_for_path",
    "list_source_files",
    "scm_path_for_lang",
]
