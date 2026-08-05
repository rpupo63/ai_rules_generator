"""
Structure-only code graph: definitions, references, PageRank, repo map.

Tag queries distinguish only definitions from references. Ranking needs
"file A references a symbol defined in file B" — coarser than the old
six-edge taxonomy that fed prose generators.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .tags import Tag, extract_project_tags, language_for_path

logger = logging.getLogger(__name__)

EDGE_KINDS = ("defines", "references")


@dataclass(frozen=True)
class Symbol:
    qualified_name: str
    kind: str
    file: str
    line: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class GraphBuildResult:
    graph: "object"
    symbols_by_qname: Dict[str, Symbol]
    file_to_symbols: Dict[str, List[Symbol]]
    edges_added: int
    used_fallback: bool


class _FallbackGraph:
    """Minimal digraph when networkx is unavailable."""

    def __init__(self) -> None:
        self._nodes: Dict[str, dict] = {}
        self._edges: List[Tuple[str, str, dict]] = []
        self._in: Dict[str, int] = defaultdict(int)

    def add_node(self, n: str, **attrs) -> None:
        self._nodes[n] = attrs

    def add_edge(self, u: str, v: str, **attrs) -> None:
        self._edges.append((u, v, attrs))
        self._in[v] += 1

    def nodes(self):
        return list(self._nodes)

    def in_degree(self, n: str) -> int:
        return int(self._in.get(n, 0))

    def edges(self, data: bool = False):
        if data:
            return list(self._edges)
        return [(u, v) for u, v, _ in self._edges]

    def reverse(self, copy: bool = False):
        g = _FallbackGraph()
        for n, attrs in self._nodes.items():
            g.add_node(n, **attrs)
        for u, v, d in self._edges:
            g.add_edge(v, u, **d)
        return g

    def in_degree_ranking(
        self, symbols_by_qname: Dict[str, Symbol]
    ) -> List[Tuple[Symbol, float]]:
        ranked = [
            (sym, float(self.in_degree(q)))
            for q, sym in symbols_by_qname.items()
        ]
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked


_NX_OK: Optional[bool] = None


def _try_import_networkx():
    global _NX_OK
    if _NX_OK is False:
        return None
    try:
        import networkx  # type: ignore

        _NX_OK = True
        return networkx
    except Exception as exc:  # pragma: no cover
        if _NX_OK is None:
            logger.info("networkx unavailable (%s); using in-degree ranking", exc)
        _NX_OK = False
        return None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _qualified_name(rel_file: str, name: str) -> str:
    base = rel_file.replace("\\", "/")
    for suffix in (
        ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
        ".go", ".rs", ".java", ".gd", ".sh", ".bash",
    ):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    base = base.replace("/", ".")
    return f"{base}::{name}"


def build_graph_from_tags(
    project_root: Path,
    tags: List[Tag],
) -> GraphBuildResult:
    """Build a def/ref multigraph from structure-only tags."""
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

    # Definitions → nodes
    for tag in tags:
        if tag.kind != "def":
            continue
        qname = _qualified_name(tag.rel_path, tag.name)
        if qname in symbols_by_qname:
            continue
        sym = Symbol(
            qualified_name=qname,
            kind="definition",
            file=tag.rel_path,
            line=tag.line + 1,
        )
        symbols_by_qname[qname] = sym
        file_to_symbols.setdefault(tag.rel_path, []).append(sym)
        graph.add_node(qname, **sym.to_dict())
        # File node edges for PageRank across files
        graph.add_node(tag.rel_path, kind="file")
        graph.add_edge(tag.rel_path, qname, kind="defines")
        edges_added += 1

    name_index: Dict[str, List[str]] = defaultdict(list)
    for qname, sym in symbols_by_qname.items():
        name_index[sym.qualified_name.rsplit("::", 1)[-1]].append(qname)

    def _resolve(name: str, prefer_file: str) -> Optional[str]:
        cands = name_index.get(name) or []
        if not cands:
            return None
        same = [c for c in cands if symbols_by_qname[c].file == prefer_file]
        if same:
            return same[0]
        if len(cands) == 1:
            return cands[0]
        return None

    # References → edges from referring file to defining symbol
    for tag in tags:
        if tag.kind != "ref":
            continue
        tgt = _resolve(tag.name, tag.rel_path)
        if not tgt:
            continue
        # Skip self-refs within the same symbol name on same file when it's a def site
        src_file = tag.rel_path
        if src_file not in getattr(graph, "_nodes", {}) and not (
            hasattr(graph, "has_node") and graph.has_node(src_file)
        ):
            try:
                graph.add_node(src_file, kind="file")
            except Exception:
                pass
        graph.add_edge(src_file, tgt, kind="references")
        edges_added += 1

    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols_by_qname,
        file_to_symbols=file_to_symbols,
        edges_added=edges_added,
        used_fallback=used_fallback,
    )


def build_graph_from_project(
    project_root: Path,
    file_paths: Iterable[Path],
    *,
    should_include=None,
) -> GraphBuildResult:
    tags = extract_project_tags(
        project_root,
        file_paths,
        should_include=should_include,
    )
    return build_graph_from_tags(project_root, tags)


def rank_symbols(
    result: GraphBuildResult,
    *,
    damping: float = 0.85,
) -> List[Tuple[Symbol, float]]:
    """PageRank on the reversed graph (heavily referenced symbols rise)."""
    graph = result.graph
    if isinstance(graph, _FallbackGraph):
        return graph.in_degree_ranking(result.symbols_by_qname)

    nx = _try_import_networkx()
    if nx is None:
        return _FallbackGraph().in_degree_ranking(result.symbols_by_qname)

    try:
        reversed_g = graph.reverse(copy=False)
        scored = nx.pagerank(nx.DiGraph(reversed_g), alpha=damping)
    except Exception as exc:
        logger.info("PageRank failed (%s); falling back to in-degree", exc)
        scored = {n: graph.in_degree(n) for n in graph.nodes()}

    ranked: List[Tuple[Symbol, float]] = []
    for qname, score in scored.items():
        sym = result.symbols_by_qname.get(qname)
        if sym is None:
            continue
        ranked.append((sym, float(score)))
    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked


def rank_files(
    result: GraphBuildResult,
    *,
    damping: float = 0.85,
) -> List[Tuple[str, float]]:
    """Aggregate symbol ranks to file ranks."""
    file_scores: Dict[str, float] = defaultdict(float)
    for sym, score in rank_symbols(result, damping=damping):
        file_scores[sym.file] += score
    ranked = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked


def render_repo_map(
    result: GraphBuildResult,
    *,
    token_budget: int = 1000,
    max_symbols: int = 80,
) -> str:
    ranked = rank_symbols(result)
    if not ranked:
        return "_(no symbols extracted — install tree-sitter-language-pack)_"

    by_file: Dict[str, List[Tuple[Symbol, float]]] = {}
    for sym, score in ranked[:max_symbols]:
        by_file.setdefault(sym.file, []).append((sym, score))

    file_scores = sorted(
        by_file.items(),
        key=lambda kv: sum(s for _, s in kv[1]),
        reverse=True,
    )

    out: List[str] = ["**Top-ranked symbols** (PageRank over definitions/references)", ""]
    used = estimate_tokens("\n".join(out))
    files_shown = 0
    for rel_file, syms in file_scores:
        chunk = [f"`{rel_file}`:"]
        for sym, _score in syms:
            short = sym.qualified_name.rsplit("::", 1)[-1]
            chunk.append(f"  - `{short}`")
        chunk.append("")
        block = "\n".join(chunk)
        cost = estimate_tokens(block)
        if used + cost > token_budget:
            remaining = len(file_scores) - files_shown
            if remaining > 0:
                out.append(f"_(+{remaining} more files)_")
            break
        out.append(block)
        used += cost
        files_shown += 1

    return "\n".join(out)


def serialize(result: GraphBuildResult, out_path: Path) -> Path:
    nodes = [s.to_dict() for s in result.symbols_by_qname.values()]
    edges = []
    graph = result.graph
    if isinstance(graph, _FallbackGraph):
        for u, v, d in graph.edges(data=True):
            edges.append({"src": u, "tgt": v, "kind": d.get("kind")})
    else:
        for u, v, d in graph.edges(data=True):
            edges.append({"src": str(u), "tgt": str(v), "kind": (d or {}).get("kind")})
    doc = {
        "fallback_mode": result.used_fallback,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out_path


def deserialize(path: Path) -> GraphBuildResult:
    doc = json.loads(path.read_text(encoding="utf-8"))
    graph = _FallbackGraph()
    symbols: Dict[str, Symbol] = {}
    file_to: Dict[str, List[Symbol]] = {}
    for n in doc.get("nodes", []):
        sym = Symbol(
            qualified_name=n["qualified_name"],
            kind=n.get("kind", "definition"),
            file=n["file"],
            line=int(n.get("line", 1)),
        )
        symbols[sym.qualified_name] = sym
        file_to.setdefault(sym.file, []).append(sym)
        graph.add_node(sym.qualified_name, **sym.to_dict())
    edges_added = 0
    for e in doc.get("edges", []):
        graph.add_edge(e["src"], e["tgt"], kind=e.get("kind") or "references")
        edges_added += 1
    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols=file_to,
        edges_added=edges_added,
        used_fallback=True,
    )


# Stubs kept for callers that still import folder helpers (tier-2 emission).
def render_reverse_imports(result: GraphBuildResult, folder_or_file: str) -> str:
    folder = folder_or_file.rstrip("/")
    lines: List[str] = []
    for qname, sym in result.symbols_by_qname.items():
        if not (sym.file == folder or sym.file.startswith(folder + "/")):
            continue
        # Who references this symbol?
        graph = result.graph
        if isinstance(graph, _FallbackGraph):
            for u, v, d in graph._edges:
                if v == qname and d.get("kind") == "references":
                    lines.append(f"- `{u}` → `{sym.qualified_name.rsplit('::', 1)[-1]}`")
        else:
            for u, v, d in graph.in_edges(qname, data=True):
                if (d or {}).get("kind") == "references":
                    lines.append(f"- `{u}` → `{sym.qualified_name.rsplit('::', 1)[-1]}`")
    return "\n".join(lines[:40])


def render_folder_subgraph(
    result: GraphBuildResult, folder_rel: str, *, max_edges: int = 8
) -> str:
    return render_reverse_imports(result, folder_rel)


def file_neighborhood(*_a, **_k):
    return None


def render_file_neighborhood(*_a, **_k) -> str:
    return ""


__all__ = [
    "EDGE_KINDS",
    "GraphBuildResult",
    "Symbol",
    "build_graph_from_project",
    "build_graph_from_tags",
    "deserialize",
    "estimate_tokens",
    "file_neighborhood",
    "rank_files",
    "rank_symbols",
    "render_file_neighborhood",
    "render_folder_subgraph",
    "render_repo_map",
    "render_reverse_imports",
    "serialize",
]
