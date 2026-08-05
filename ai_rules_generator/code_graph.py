"""
Deterministic AST-Derived Knowledge Base (DKB) and Graph RAG support.

Builds a typed directed multigraph from the AST skeletons produced by
`ast_compression`:

    nodes  : Symbol(qualified_name, kind, file, line)
    edges  : "defines", "imports", "calls", "extends", "implements",
             "references"

Then runs `networkx.pagerank` on the reversed graph (heavily-referenced
symbols bubble to the top - matching Aider's "importance" heuristic) and
renders an Aider-style repo map sized to fit a token budget.

This module is the *deterministic* path: per the research, an AST-derived
knowledge base (DKB) is strictly superior to an LLM-extracted one
(LLM-KB) on cost, latency, hallucination, and coverage.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .ast_compression import (
    LANGUAGE_RULES,
    SignatureNode,
    Skeleton,
    estimate_tokens,
    extract_skeleton,
    get_language_rule,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

EDGE_KINDS = ("defines", "imports", "calls", "extends", "implements", "references")


@dataclass(frozen=True)
class Symbol:
    qualified_name: str
    kind: str       # node kind from the AST, e.g. "function_definition"
    file: str       # path relative to the project root
    line: int       # 1-based start line

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class GraphBuildResult:
    """Output of `build_graph`: the graph itself plus a Symbol index."""

    graph: "object"                       # networkx.MultiDiGraph
    symbols_by_qname: Dict[str, Symbol]   # canonical lookup
    file_to_symbols: Dict[str, List[Symbol]]
    edges_added: int
    used_fallback: bool                   # True when networkx is missing


# ---------------------------------------------------------------------------
# Lazy networkx loader
# ---------------------------------------------------------------------------

_NX_OK: Optional[bool] = None


def _try_import_networkx():
    global _NX_OK
    if _NX_OK is False:
        return None
    try:
        import networkx  # type: ignore
        _NX_OK = True
        return networkx
    except Exception as exc:  # pragma: no cover - missing dep path
        if _NX_OK is None:
            logger.info(
                "networkx not available (%s); Graph RAG will emit only the "
                "raw symbol JSON without ranking.",
                exc,
            )
        _NX_OK = False
        return None


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

# Per-language regex for `calls` and `extends`/`implements`.  Cheap & lossy by
# design - Tree-sitter would give us perfect data but we'd pay an order of
# magnitude more bytes per file.  For ranking purposes, recall matters more
# than precision.
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_EXTENDS_RE = re.compile(r"\bextends\s+([A-Za-z_][A-Za-z0-9_.]*)")
_IMPLEMENTS_RE = re.compile(r"\bimplements\s+([A-Za-z_][A-Za-z0-9_., ]*)")
_PY_BASE_RE = re.compile(r"^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*\(([^)]+)\)")
_GO_INTERFACE_RE = re.compile(r"^\s*type\s+[A-Za-z_][A-Za-z0-9_]*\s+interface")


def _qualified_name(rel_file: str, sig: SignatureNode) -> str:
    base = rel_file.replace("/", ".").replace("\\", ".")
    if base.endswith(".py") or base.endswith(".ts") or base.endswith(".tsx") \
            or base.endswith(".js") or base.endswith(".jsx") or base.endswith(".go") \
            or base.endswith(".rs") or base.endswith(".java"):
        base = base.rsplit(".", 1)[0]
    return f"{base}::{sig.name}"


def _iter_signatures(sig: SignatureNode) -> Iterable[SignatureNode]:
    yield sig
    for child in sig.children:
        yield child


def build_graph(
    project_root: Path,
    skeletons: List[Skeleton],
) -> GraphBuildResult:
    """
    Build the DKB MultiDiGraph from a list of AST Skeletons.

    Falls back to a lightweight namespace stand-in when `networkx` is missing
    so callers can still serialize the symbol set.
    """
    nx = _try_import_networkx()

    if nx is None:
        graph = _FallbackGraph()
        used_fallback = True
    else:
        graph = nx.MultiDiGraph()
        used_fallback = False

    symbols_by_qname: Dict[str, Symbol] = {}
    file_to_symbols: Dict[str, List[Symbol]] = {}
    edges_added = 0

    # ---------- 1. Add nodes (defines) ----------
    for skel in skeletons:
        try:
            rel_file = str(Path(skel.file_path).relative_to(project_root)).replace("\\", "/")
        except ValueError:
            rel_file = skel.file_path
        file_to_symbols.setdefault(rel_file, [])
        for sig in skel.signatures:
            for s in _iter_signatures(sig):
                if not s.name or s.name == "(anonymous)":
                    continue
                qname = _qualified_name(rel_file, s)
                sym = Symbol(
                    qualified_name=qname,
                    kind=s.kind,
                    file=rel_file,
                    line=s.start_line,
                )
                symbols_by_qname[qname] = sym
                file_to_symbols[rel_file].append(sym)
                graph.add_node(qname, **sym.to_dict())

    # Helper: resolve a bare name to its qualified counterpart.
    # Precision over recall: never guess across unrelated packages.
    name_index: Dict[str, List[str]] = {}
    for qname, sym in symbols_by_qname.items():
        name_index.setdefault(sym.qualified_name.rsplit("::", 1)[-1], []).append(qname)

    def _package_dir(file_rel: str) -> str:
        """Parent folder of the file (Go package / module folder)."""
        parts = file_rel.replace("\\", "/").strip("/").split("/")
        return "/".join(parts[:-1]) if len(parts) > 1 else ""

    def _resolve(name: str, *, prefer_file: str) -> Optional[str]:
        candidates = name_index.get(name)
        if not candidates:
            return None
        same_file = [c for c in candidates if symbols_by_qname[c].file == prefer_file]
        if same_file:
            return same_file[0]
        prefer_pkg = _package_dir(prefer_file)
        if prefer_pkg:
            same_pkg = [
                c for c in candidates
                if _package_dir(symbols_by_qname[c].file) == prefer_pkg
            ]
            if len(same_pkg) == 1:
                return same_pkg[0]
            if len(same_pkg) > 1:
                # Ambiguous within package — still prefer first same-pkg over global
                return same_pkg[0]
        if len(candidates) == 1:
            return candidates[0]
        # Multiple packages define this name — omit rather than guess
        return None

    # ---------- 2. imports ----------
    for skel in skeletons:
        try:
            rel_file = str(Path(skel.file_path).relative_to(project_root)).replace("\\", "/")
        except ValueError:
            rel_file = skel.file_path
        for imp in skel.imports:
            target = imp.split("import")[-1].strip().split(" as ")[0].split(",")[0].strip()
            target = target.strip("\"'`;").replace("from", "").strip()
            if not target:
                continue
            graph.add_edge(rel_file, target, kind="imports")
            edges_added += 1

    # ---------- 3. calls + extends + implements ----------
    for skel in skeletons:
        try:
            rel_file = str(Path(skel.file_path).relative_to(project_root)).replace("\\", "/")
        except ValueError:
            rel_file = skel.file_path

        for sig in skel.signatures:
            for s in _iter_signatures(sig):
                if not s.name or s.name == "(anonymous)":
                    continue
                src_qname = _qualified_name(rel_file, s)

                # Calls: scan both the signature AND the body text for call
                # expressions.  Body text is captured by ast_compression but
                # never emitted in the rendered skeleton.
                search_text = " ".join((s.signature, s.body_text))
                seen_calls: Set[str] = set()
                for m in _CALL_RE.finditer(search_text):
                    callee = m.group(1)
                    if callee == s.name or callee in seen_calls:
                        continue
                    seen_calls.add(callee)
                    tgt = _resolve(callee, prefer_file=rel_file)
                    if not tgt:
                        continue
                    graph.add_edge(src_qname, tgt, kind="calls")
                    edges_added += 1

                # extends (TS/JS/Java/Kotlin)
                for m in _EXTENDS_RE.finditer(s.signature):
                    parent = m.group(1).split(".")[-1]
                    tgt = _resolve(parent, prefer_file=rel_file)
                    if tgt:
                        graph.add_edge(src_qname, tgt, kind="extends")
                        edges_added += 1

                # implements (TS/Java)
                for m in _IMPLEMENTS_RE.finditer(s.signature):
                    for iface in m.group(1).split(","):
                        iface = iface.strip().split(".")[-1]
                        if not iface:
                            continue
                        tgt = _resolve(iface, prefer_file=rel_file)
                        if tgt:
                            graph.add_edge(src_qname, tgt, kind="implements")
                            edges_added += 1

                # Python class bases via the signature `(Base1, Base2):` prefix
                for m in _PY_BASE_RE.finditer(s.signature):
                    for base in m.group(1).split(","):
                        base = base.strip().split(".")[-1]
                        if not base:
                            continue
                        tgt = _resolve(base, prefer_file=rel_file)
                        if tgt:
                            graph.add_edge(src_qname, tgt, kind="extends")
                            edges_added += 1

    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols_by_qname,
        file_to_symbols=file_to_symbols,
        edges_added=edges_added,
        used_fallback=used_fallback,
    )


# ---------------------------------------------------------------------------
# Convenience: build from a project directory
# ---------------------------------------------------------------------------

def build_graph_from_project(
    project_root: Path,
    file_paths: Iterable[Path],
) -> GraphBuildResult:
    """One-shot helper: skeletonize every supported file under file_paths."""
    skeletons: List[Skeleton] = []
    for p in file_paths:
        if get_language_rule(p) is None:
            continue
        skel = extract_skeleton(p)
        if skel is None or skel.used_fallback or not skel.signatures:
            continue
        skeletons.append(skel)
    return build_graph(project_root, skeletons)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_symbols(
    result: GraphBuildResult,
    *,
    damping: float = 0.85,
) -> List[Tuple[Symbol, float]]:
    """
    Rank symbols by Aider-style importance using PageRank on the reversed
    graph (so symbols heavily *referenced* by others bubble up).

    When networkx isn't installed, falls back to a simple in-degree ranking
    using the FallbackGraph.
    """
    graph = result.graph
    if isinstance(graph, _FallbackGraph):
        return graph.in_degree_ranking(result.symbols_by_qname)

    nx = _try_import_networkx()
    if nx is None:  # belt and suspenders
        return _FallbackGraph().in_degree_ranking(result.symbols_by_qname)

    try:
        reversed_g = graph.reverse(copy=False)
        # PageRank wants a non-multi-graph view; convert in-place.
        scored = nx.pagerank(nx.DiGraph(reversed_g), alpha=damping)
    except Exception as exc:
        logger.info("PageRank failed (%s); falling back to in-degree.", exc)
        scored = {n: graph.in_degree(n) for n in graph.nodes()}

    ranked: List[Tuple[Symbol, float]] = []
    for qname, score in scored.items():
        sym = result.symbols_by_qname.get(qname)
        if sym is None:
            continue
        ranked.append((sym, float(score)))
    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked


# ---------------------------------------------------------------------------
# Repo map rendering
# ---------------------------------------------------------------------------

def render_repo_map(
    result: GraphBuildResult,
    *,
    token_budget: int = 1000,
    max_symbols: int = 80,
) -> str:
    """
    Render a Markdown repo map - top-ranked symbols grouped by file - sized
    to fit the requested token budget.
    """
    ranked = rank_symbols(result)
    if not ranked:
        return "_(no symbols extracted - is Tree-sitter installed?)_"

    by_file: Dict[str, List[Tuple[Symbol, float]]] = {}
    for sym, score in ranked[:max_symbols]:
        by_file.setdefault(sym.file, []).append((sym, score))

    # Sort files by total importance.
    file_scores = sorted(
        by_file.items(),
        key=lambda kv: sum(s for _, s in kv[1]),
        reverse=True,
    )

    out: List[str] = ["**Top-ranked symbols** (PageRank over the DKB)"]
    out.append("")
    used = estimate_tokens("\n".join(out))
    for rel_file, syms in file_scores:
        chunk = [f"`{rel_file}`:"]
        for sym, _score in syms:
            short = sym.qualified_name.rsplit("::", 1)[-1]
            chunk.append(f"  - {sym.kind.split('_')[0]} `{short}`")
        chunk.append("")
        block = "\n".join(chunk)
        cost = estimate_tokens(block)
        if used + cost > token_budget:
            out.append(f"_(+{len(file_scores) - len(out) + 1} more files - "
                       f"open `.ai-rules/graph/graph.json` for the full DKB)_")
            break
        out.append(block)
        used += cost

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Folder-scoped subgraph helpers (used by Tier-2 emission)
# ---------------------------------------------------------------------------

def _file_in_folder(file_rel: str, folder_rel: str) -> bool:
    """True iff `file_rel` is at or under `folder_rel` (both POSIX-relative)."""
    if not folder_rel:
        return True  # root folder owns everything
    folder_norm = folder_rel.rstrip("/") + "/"
    file_norm = file_rel.replace("\\", "/")
    return file_norm.startswith(folder_norm) or file_norm == folder_rel


def _qname_file(qname: str, symbols_by_qname: Dict[str, Symbol]) -> Optional[str]:
    sym = symbols_by_qname.get(qname)
    return sym.file if sym else None


def _semantic_edges(result: GraphBuildResult):
    """Yield (src_qname, tgt_qname, kind) for `calls`/`extends`/`implements`
    edges only.  Skips raw `imports` edges (which have a module-string
    target, not a Symbol target).  Works for both real networkx graphs and
    the fallback."""
    graph = result.graph
    if isinstance(graph, _FallbackGraph):
        for s, t, d in graph._edges:
            kind = d.get("kind") if isinstance(d, dict) else None
            if kind in {"calls", "extends", "implements"}:
                yield s, t, kind
        return

    for u, v, data in graph.edges(data=True):
        kind = data.get("kind") if isinstance(data, dict) else None
        if kind in {"calls", "extends", "implements"}:
            yield str(u), str(v), kind


@dataclass
class NeighborhoodEdge:
    """One semantic edge touching a seed file or folder."""

    src_qname: str
    tgt_qname: str
    kind: str
    src_file: str
    tgt_file: str


@dataclass
class FileNeighborhood:
    """Ego-neighborhood for a seed file (cross-folder edges included)."""

    file_rel: str
    outbound: List[NeighborhoodEdge] = field(default_factory=list)
    inbound: List[NeighborhoodEdge] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    local_symbols: List[str] = field(default_factory=list)


# Ultra-common helpers that dilute blast-radius signal in Go/TS handlers.
BOILERPLATE_SYMBOLS: frozenset = frozenset({
    "respondjson", "responderror", "respond", "error", "string", "new",
    "ctxgetuserid", "ctxget", "parsepaginationparams", "abilitymod",
    "tostring", "valueof", "printf", "println", "sprintf", "len",
    "make", "append", "close", "lock", "unlock", "done", "wait",
})


def _norm_rel(path: str) -> str:
    return path.replace("\\", "/").strip().strip("/")


def _symbol_short(qname: str) -> str:
    return qname.rsplit("::", 1)[-1]


def _is_boilerplate_symbol(name: str) -> bool:
    return name.lower() in BOILERPLATE_SYMBOLS


def _parent_folder(file_rel: str) -> str:
    parts = _norm_rel(file_rel).split("/")
    return "/".join(parts[:-1]) if len(parts) > 1 else ""


HIGH_FANIN_THRESHOLD = 5


def _callee_fanin(result: GraphBuildResult) -> Dict[str, int]:
    """Distinct source-file count calling each target qname."""
    fanin: Dict[str, Set[str]] = {}
    for src, tgt, kind in _semantic_edges(result):
        if kind != "calls":
            continue
        src_file = _qname_file(src, result.symbols_by_qname)
        if src_file is None:
            continue
        fanin.setdefault(tgt, set()).add(_norm_rel(src_file))
    return {q: len(files) for q, files in fanin.items()}


def _rank_outbound_key(
    edge: NeighborhoodEdge,
    seed: str,
    fanin: Dict[str, int],
    *,
    high_fanin_threshold: int = HIGH_FANIN_THRESHOLD,
) -> Tuple[int, int, int, str]:
    """Sort: non-boilerplate, low-fanin, cross-folder, then name."""
    tgt_short = _symbol_short(edge.tgt_qname)
    boilerplate = 1 if _is_boilerplate_symbol(tgt_short) else 0
    fi = fanin.get(edge.tgt_qname, 0)
    high_fanin = 1 if fi >= high_fanin_threshold else 0
    same_file = 1 if edge.tgt_file == seed else 0
    same_folder = 0
    if not same_file:
        same_folder = (
            1 if _parent_folder(edge.tgt_file) == _parent_folder(seed) else 0
        )
    locality = same_file * 2 + same_folder
    return (boilerplate, high_fanin, locality, tgt_short.lower())


def file_neighborhood(
    result: GraphBuildResult,
    file_rel: str,
    *,
    max_edges: int = 40,
    max_consumers: int = 15,
    high_fanin_threshold: int = HIGH_FANIN_THRESHOLD,
) -> FileNeighborhood:
    """
    Collect calls/extends/implements edges where either end is `file_rel`.

    Outbound: deduped by target qname, ranked by rarity (inverse fan-in) and
    locality; high-fan-in helpers sink.
    """
    seed = _norm_rel(file_rel)
    inbound: List[NeighborhoodEdge] = []
    seen_out: Set[Tuple[str, str, str]] = set()
    seen_in: Set[Tuple[str, str, str]] = set()
    related: Set[str] = set()
    out_by_tgt: Dict[str, List[NeighborhoodEdge]] = {}

    for src, tgt, kind in _semantic_edges(result):
        src_file = _qname_file(src, result.symbols_by_qname)
        tgt_file = _qname_file(tgt, result.symbols_by_qname)
        if src_file is None or tgt_file is None:
            continue
        src_n = _norm_rel(src_file)
        tgt_n = _norm_rel(tgt_file)
        edge = NeighborhoodEdge(src, tgt, kind, src_n, tgt_n)
        key = (src, tgt, kind)
        if src_n == seed and tgt_n != seed:
            if key not in seen_out:
                seen_out.add(key)
                out_by_tgt.setdefault(tgt, []).append(edge)
                related.add(tgt_n)
        elif tgt_n == seed and src_n != seed:
            if key not in seen_in:
                seen_in.add(key)
                inbound.append(edge)
                related.add(src_n)
        elif src_n == seed and tgt_n == seed:
            if key not in seen_out:
                seen_out.add(key)
                out_by_tgt.setdefault(tgt, []).append(edge)

    fanin = _callee_fanin(result)
    deduped: List[Tuple[NeighborhoodEdge, int]] = [
        (edges[0], len(edges)) for edges in out_by_tgt.values()
    ]
    deduped.sort(
        key=lambda pair: _rank_outbound_key(
            pair[0], seed, fanin, high_fanin_threshold=high_fanin_threshold
        )
    )

    non_boiler = [
        (e, n) for e, n in deduped
        if not _is_boilerplate_symbol(_symbol_short(e.tgt_qname))
    ]
    if len(non_boiler) >= 2:
        deduped = non_boiler

    rare = [
        (e, n) for e, n in deduped
        if fanin.get(e.tgt_qname, 0) < high_fanin_threshold
    ]
    if len(rare) >= 2:
        high = [
            (e, n) for e, n in deduped
            if fanin.get(e.tgt_qname, 0) >= high_fanin_threshold
        ]
        deduped = rare + high[:1]

    outbound = [e for e, _n in deduped[:max_edges]]
    multiplicity = {e.tgt_qname: n for e, n in deduped}

    inbound.sort(
        key=lambda e: (
            1 if _is_boilerplate_symbol(_symbol_short(e.tgt_qname)) else 0,
            e.src_file,
        )
    )
    inbound = inbound[:max_consumers]

    local_syms: List[str] = []
    for sym in result.file_to_symbols.get(seed, []) or []:
        local_syms.append(sym.qualified_name.rsplit("::", 1)[-1])
    if not local_syms:
        for q, sym in result.symbols_by_qname.items():
            if _norm_rel(sym.file) == seed:
                local_syms.append(q.rsplit("::", 1)[-1])

    neigh = FileNeighborhood(
        file_rel=seed,
        outbound=outbound,
        inbound=inbound,
        related_files=sorted(related),
        local_symbols=local_syms[:30],
    )
    neigh._outbound_multiplicity = multiplicity  # type: ignore[attr-defined]
    return neigh


def _format_edge_bullet(edge: NeighborhoodEdge, *, multiplicity: int = 1) -> str:
    src_short = edge.src_qname.rsplit("::", 1)[-1]
    tgt_short = edge.tgt_qname.rsplit("::", 1)[-1]
    arrow = {
        "calls": "->",
        "extends": "extends",
        "implements": "implements",
    }.get(edge.kind, edge.kind)
    suffix = f" ×{multiplicity}" if multiplicity > 1 else ""
    return (
        f"- `{edge.src_file}::{src_short}` {arrow} "
        f"`{edge.tgt_file}::{tgt_short}`{suffix}"
    )


_WEAK_GRAPH_EXTS = {".ts", ".tsx", ".js", ".jsx"}


def render_file_neighborhood(
    result: GraphBuildResult,
    file_rel: str,
    *,
    max_edges: int = 15,
    max_consumers: int = 15,
) -> str:
    """Markdown for a file ego-neighborhood (Calls + Used by)."""
    neigh = file_neighborhood(
        result, file_rel, max_edges=max_edges, max_consumers=max_consumers
    )
    multiplicity: Dict[str, int] = getattr(neigh, "_outbound_multiplicity", {}) or {}
    parts: List[str] = []
    if neigh.outbound:
        parts.append("### Calls / deps")
        for edge in neigh.outbound:
            parts.append(
                _format_edge_bullet(
                    edge, multiplicity=multiplicity.get(edge.tgt_qname, 1)
                )
            )
        if len(neigh.outbound) >= max_edges:
            parts.append(f"- _(outbound capped at {max_edges})_")
    if neigh.inbound:
        parts.append("### Used by")
        by_file: Dict[str, Set[str]] = {}
        for edge in neigh.inbound:
            tgt = edge.tgt_qname.rsplit("::", 1)[-1]
            if _is_boilerplate_symbol(tgt) and len(neigh.inbound) > 3:
                continue
            by_file.setdefault(edge.src_file, set()).add(tgt)
        if not by_file:
            for edge in neigh.inbound:
                by_file.setdefault(edge.src_file, set()).add(
                    edge.tgt_qname.rsplit("::", 1)[-1]
                )
        for src_file, targets in sorted(
            by_file.items(), key=lambda kv: (-len(kv[1]), kv[0])
        ):
            targets_str = ", ".join(f"`{t}`" for t in sorted(targets)[:5])
            if len(targets) > 5:
                targets_str += f", +{len(targets) - 5} more"
            parts.append(f"- `{src_file}` -> {targets_str}")

    ext = Path(file_rel).suffix.lower()
    edge_count = len(neigh.outbound) + len(neigh.inbound)
    if ext in _WEAK_GRAPH_EXTS and edge_count < 2:
        parts.append(
            "_(call graph weak for this language — verify with search)_"
        )

    return "\n".join(parts)

def render_folder_subgraph(
    result: GraphBuildResult,
    folder_rel: str,
    *,
    max_edges: int = 40,
) -> str:
    """
    Render the `calls`/`extends`/`implements` edges that live entirely
    inside `folder_rel` as a Markdown bullet list.  Returns "" when no
    intra-folder edges exist (caller can then omit the section).
    """
    edges: List[Tuple[str, str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for src, tgt, kind in _semantic_edges(result):
        src_file = _qname_file(src, result.symbols_by_qname)
        tgt_file = _qname_file(tgt, result.symbols_by_qname)
        if src_file is None or tgt_file is None:
            continue
        if not (_file_in_folder(src_file, folder_rel)
                and _file_in_folder(tgt_file, folder_rel)):
            continue
        key = (src, tgt, kind)
        if key in seen:
            continue
        seen.add(key)
        edges.append((src, tgt, kind))

    if not edges:
        return ""

    lines: List[str] = []
    for src, tgt, kind in edges[:max_edges]:
        src_short = src.rsplit("::", 1)[-1]
        tgt_short = tgt.rsplit("::", 1)[-1]
        src_file = _qname_file(src, result.symbols_by_qname) or "?"
        tgt_file = _qname_file(tgt, result.symbols_by_qname) or "?"
        arrow = {"calls": "->", "extends": "extends", "implements": "implements"}[kind]
        lines.append(
            f"- `{src_file}::{src_short}` {arrow} `{tgt_file}::{tgt_short}`"
        )
    if len(edges) > max_edges:
        lines.append(f"- _(+{len(edges) - max_edges} more edges suppressed)_")
    return "\n".join(lines)


def render_reverse_imports(
    result: GraphBuildResult,
    folder_rel: str,
    *,
    max_consumers: int = 10,
) -> str:
    """
    Render the set of *external* files that semantically reference (call,
    extend, implement) symbols defined inside `folder_rel`.  Provides the
    "Used By" context an AI tool needs to avoid breaking consumers when
    editing inside the folder.
    """
    consumers: Dict[str, Set[str]] = {}   # external_file -> {target_symbol}
    for src, tgt, _kind in _semantic_edges(result):
        src_file = _qname_file(src, result.symbols_by_qname)
        tgt_file = _qname_file(tgt, result.symbols_by_qname)
        if src_file is None or tgt_file is None:
            continue
        if (_file_in_folder(tgt_file, folder_rel)
                and not _file_in_folder(src_file, folder_rel)):
            consumers.setdefault(src_file, set()).add(
                tgt.rsplit("::", 1)[-1]
            )

    if not consumers:
        return ""

    ranked = sorted(
        consumers.items(), key=lambda kv: (-len(kv[1]), kv[0])
    )
    lines: List[str] = []
    for src_file, targets in ranked[:max_consumers]:
        targets_str = ", ".join(f"`{t}`" for t in sorted(targets)[:5])
        if len(targets) > 5:
            targets_str += f", +{len(targets) - 5} more"
        lines.append(f"- `{src_file}` -> {targets_str}")
    if len(ranked) > max_consumers:
        lines.append(
            f"- _(+{len(ranked) - max_consumers} more consumers suppressed)_"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize(result: GraphBuildResult, path: Path) -> Path:
    """Write the DKB (nodes + edges) as a JSON document."""
    graph = result.graph
    nodes_payload = [sym.to_dict() for sym in result.symbols_by_qname.values()]

    if isinstance(graph, _FallbackGraph):
        edges_payload = graph.serialize_edges()
    else:
        edges_payload = []
        for u, v, data in graph.edges(data=True):
            edges_payload.append({"source": str(u), "target": str(v), **data})

    doc = {
        "nodes": nodes_payload,
        "edges": edges_payload,
        "fallback_mode": result.used_fallback,
        "stats": {
            "node_count": len(nodes_payload),
            "edge_count": len(edges_payload),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def deserialize(path: Path) -> Optional[GraphBuildResult]:
    """Load a GraphBuildResult previously written by `serialize`."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to load graph cache %s: %s", path, exc)
        return None

    symbols: Dict[str, Symbol] = {}
    file_to_symbols: Dict[str, List[Symbol]] = {}
    for node in doc.get("nodes") or []:
        try:
            sym = Symbol(
                qualified_name=str(node["qualified_name"]),
                kind=str(node.get("kind") or "unknown"),
                file=_norm_rel(str(node.get("file") or "")),
                line=int(node.get("line") or 0),
            )
        except (KeyError, TypeError, ValueError):
            continue
        symbols[sym.qualified_name] = sym
        file_to_symbols.setdefault(sym.file, []).append(sym)

    graph = _FallbackGraph()
    for q, sym in symbols.items():
        graph.add_node(q, **sym.to_dict())
    edges_added = 0
    for edge in doc.get("edges") or []:
        src = edge.get("source")
        tgt = edge.get("target")
        if not src or not tgt:
            continue
        kind = edge.get("kind") or "references"
        attrs = {k: v for k, v in edge.items() if k not in {"source", "target"}}
        attrs["kind"] = kind
        graph.add_edge(str(src), str(tgt), **attrs)
        edges_added += 1

    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols=file_to_symbols,
        edges_added=edges_added,
        used_fallback=True,
    )


# ---------------------------------------------------------------------------
# Fallback graph used when networkx is unavailable
# ---------------------------------------------------------------------------

class _FallbackGraph:
    """Tiny stand-in that supports the subset of the API we need."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict] = {}
        self._edges: List[Tuple[str, str, Dict]] = []

    # API parity (subset) -----------------------------------------------
    def add_node(self, qname, **attrs) -> None:
        self._nodes[qname] = dict(attrs)

    def add_edge(self, src, tgt, **attrs) -> None:
        self._edges.append((str(src), str(tgt), dict(attrs)))

    def nodes(self):
        return list(self._nodes.keys())

    def edges(self, data: bool = False):
        if data:
            return [(s, t, d) for s, t, d in self._edges]
        return [(s, t) for s, t, _ in self._edges]

    def in_degree(self, node: str) -> int:
        return sum(1 for _, t, _ in self._edges if t == node)

    # Helpers -----------------------------------------------------------
    def in_degree_ranking(
        self, symbols_by_qname: Dict[str, Symbol]
    ) -> List[Tuple[Symbol, float]]:
        counts: Dict[str, int] = {q: 0 for q in symbols_by_qname}
        for _, tgt, _ in self._edges:
            if tgt in counts:
                counts[tgt] += 1
        ranked = [
            (symbols_by_qname[q], float(c))
            for q, c in counts.items()
        ]
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked

    def serialize_edges(self) -> List[Dict]:
        return [{"source": s, "target": t, **d} for s, t, d in self._edges]


__all__ = [
    "EDGE_KINDS",
    "Symbol",
    "GraphBuildResult",
    "NeighborhoodEdge",
    "FileNeighborhood",
    "build_graph",
    "build_graph_from_project",
    "rank_symbols",
    "render_repo_map",
    "file_neighborhood",
    "render_file_neighborhood",
    "render_folder_subgraph",
    "render_reverse_imports",
    "serialize",
    "deserialize",
]
