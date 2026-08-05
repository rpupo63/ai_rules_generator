"""
Path-scoped edit packs for agents.

Assembles ancestor roles, AGENTS contract slices, local symbols, and
graph neighborhoods under a hard token budget — without AI enrichment.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .ast_compression import estimate_tokens
from .cache_store import (
    fingerprint_project,
    purposes_from_scan,
    try_load_warm_cache,
    write_cache,
)
from .code_graph import (
    FileNeighborhood,
    GraphBuildResult,
    build_graph,
    deserialize,
    file_neighborhood,
    render_file_neighborhood,
    serialize,
)
from .constitution import (
    Constitution,
    extract_topic_sections,
    load_constitution,
    topics_for_edit_path,
)
from .scanner import ScanContext
from .token_budget import TokenBudget

logger = logging.getLogger(__name__)

DEFAULT_EDIT_BUDGET = 2500
MAX_ANCESTOR_DEPTH = 6
GRAPH_CACHE_REL = ".ai-context/graph/graph.json"
EDIT_PACK_MAX_EDGES = 15
EDIT_PACK_MAX_CONSUMERS = 15


@dataclass
class EditPackSection:
    """One budgeted section of an edit pack."""

    kind: str
    title: str
    body: str
    priority: int  # lower = keep longer (1 = highest)


@dataclass
class EditPackResult:
    """Structured edit pack for markdown or JSON emission."""

    paths: List[str]
    sections: List[EditPackSection] = field(default_factory=list)
    tokens_spent: int = 0
    tokens_cap: int = DEFAULT_EDIT_BUDGET
    shed: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        parts = [
            "# Edit pack",
            "",
            f"Paths: {', '.join(f'`{p}`' for p in self.paths)}",
            "",
        ]
        for sec in self.sections:
            parts.append(f"## {sec.title}")
            parts.append("")
            parts.append(sec.body.rstrip())
            parts.append("")
        if self.shed:
            parts.append("## Shed (budget)")
            parts.append("")
            for kind in self.shed:
                parts.append(f"- _{kind}_")
            parts.append("")
        parts.append(
            f"_Budget: {self.tokens_spent} / {self.tokens_cap} tokens._\n"
        )
        return "\n".join(parts).rstrip() + "\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paths": self.paths,
            "tokens_spent": self.tokens_spent,
            "tokens_cap": self.tokens_cap,
            "shed": self.shed,
            "sections": [asdict(s) for s in self.sections],
        }


def ancestor_purpose_chain(
    scan_ctx: Optional[ScanContext],
    path_rel: str,
    *,
    max_depth: int = MAX_ANCESTOR_DEPTH,
    purposes: Optional[Dict[str, str]] = None,
) -> List[Tuple[str, str]]:
    """
    Walk parent folders of `path_rel` → (folder_rel, purpose) one-liners.

    For a file `a/b/c.go` yields `a`, `a/b` (not the file itself).
    Cap at `max_depth` ancestors from the root outward.
    Prefer `purposes` cache, then scan_ctx, then heuristics.
    """
    rel = path_rel.replace("\\", "/").strip().strip("/")
    if not rel:
        return []

    purposes = purposes or {}
    parts = rel.split("/")
    # If last segment looks like a file, drop it for ancestor walk.
    if "." in parts[-1] and not (
        (scan_ctx and rel in (scan_ctx.by_path or {})) or rel in purposes
    ):
        dir_parts = parts[:-1]
    else:
        # Folder path: include self as last ancestor
        dir_parts = parts

    if not dir_parts:
        return []

    chain: List[Tuple[str, str]] = []
    for i in range(1, len(dir_parts) + 1):
        folder_rel = "/".join(dir_parts[:i])
        purpose = (purposes.get(folder_rel) or "").strip()
        if not purpose and scan_ctx and scan_ctx.by_path:
            info = scan_ctx.by_path.get(folder_rel)
            if info is not None:
                purpose = (info.purpose or "").strip()
        if not purpose:
            purpose = _heuristic_purpose(folder_rel)
        chain.append((folder_rel, purpose))

    if len(chain) > max_depth:
        chain = chain[-max_depth:]
    return chain


def _heuristic_purpose(folder_rel: str) -> str:
    leaf = folder_rel.rstrip("/").split("/")[-1].lower()
    hints = {
        "api": "HTTP API endpoints and handlers",
        "seed": "Database seeding and test data generation",
        "services": "Core business logic services",
        "models": "Data models / schemas",
        "database": "Data access / repositories",
        "frontend": "UI application",
        "backend": "Server / API application",
        "e2e": "End-to-end tests",
        "cmd": "CLI / binary entrypoints",
        "internal": "Internal packages",
        "components": "UI components",
        "pages": "UI pages / routes",
        "hooks": "UI hooks",
    }
    return hints.get(leaf, "project files")


def recursive_code_file_count(
    scan_ctx: Optional[ScanContext],
    rel_path: str,
) -> int:
    """Count AST skeletons under `rel_path` (recursive via by_path)."""
    if scan_ctx is None or not scan_ctx.by_path:
        return 0
    rel = (rel_path or "").replace("\\", "/").strip("/")
    prefix = rel + "/" if rel else ""
    total = 0
    for path, folder in scan_ctx.by_path.items():
        p = (path or "").replace("\\", "/").strip("/")
        if rel:
            if p != rel and not p.startswith(prefix):
                continue
        total += len(folder.skeletons or [])
    return total


def _graph_cache_path(project_root: Path) -> Path:
    return project_root / GRAPH_CACHE_REL


def load_or_build_graph(
    project_root: Path,
    scan_ctx: Optional[ScanContext],
    *,
    enable_graph: bool = True,
    write_cache: bool = True,
) -> Optional[GraphBuildResult]:
    """Build graph from scan (or return None). Prefer warm path via try_load_warm_cache."""
    if not enable_graph or scan_ctx is None:
        return None

    skeletons = []
    for folder in scan_ctx.flat or []:
        skeletons.extend(folder.skeletons or [])
    if not skeletons:
        return None

    result = build_graph(project_root, skeletons)
    if write_cache and result.symbols_by_qname:
        try:
            serialize(result, _graph_cache_path(project_root))
        except OSError as exc:
            logger.warning("could not write graph cache: %s", exc)
    return result


def _file_symbols_markdown(
    scan_ctx: Optional[ScanContext],
    graph_result: Optional[GraphBuildResult],
    file_rel: str,
    *,
    limit: int = 20,
) -> str:
    rel = file_rel.replace("\\", "/").strip("/")
    names: List[str] = []
    if graph_result:
        neigh = file_neighborhood(graph_result, rel, max_edges=0, max_consumers=0)
        names = list(neigh.local_symbols)
    if not names and scan_ctx:
        # Find skeleton for this file in containing folder
        parent = "/".join(rel.split("/")[:-1])
        folder = (scan_ctx.by_path or {}).get(parent) or (scan_ctx.by_path or {}).get(rel)
        if folder:
            for skel in folder.skeletons or []:
                skel_rel = getattr(skel, "file_path", None) or ""
                # file_path may be absolute
                skel_s = str(skel_rel).replace("\\", "/")
                if skel_s.endswith("/" + rel) or skel_s.endswith(rel) or Path(skel_s).name == Path(rel).name:
                    for sig in (skel.signatures or [])[:limit]:
                        names.append(getattr(sig, "name", str(sig)))
                    break
    if not names:
        return ""
    return "\n".join(f"- `{n}`" for n in names[:limit])


def _path_looks_like_dir(
    path: str,
    scan_ctx: Optional[ScanContext],
    purposes: Optional[Dict[str, str]],
) -> bool:
    rel = path.rstrip("/")
    if scan_ctx and scan_ctx.by_path and rel in scan_ctx.by_path:
        return True
    if purposes and rel in purposes:
        return True
    # No extension → treat as folder
    leaf = rel.split("/")[-1]
    return "." not in leaf


def _build_candidate_sections(
    *,
    paths: Sequence[str],
    constitution: Constitution,
    scan_ctx: Optional[ScanContext],
    graph_result: Optional[GraphBuildResult],
    workflow_lines: Sequence[str],
    purposes: Optional[Dict[str, str]] = None,
) -> List[EditPackSection]:
    sections: List[EditPackSection] = []
    purposes = purposes or {}

    # 1. AGENTS slices (priority 1)
    topics: List[str] = []
    for p in paths:
        for t in topics_for_edit_path(p):
            if t not in topics:
                topics.append(t)
    # Prefer path of first seed for Architecture subsection trimming
    slices = extract_topic_sections(
        constitution, topics, path_rel=paths[0] if paths else ""
    )
    if slices:
        body_parts = []
        for topic, md in slices:
            body_parts.append(md)
            body_parts.append("")
        sections.append(EditPackSection(
            kind="agents_slices",
            title="AGENTS contracts (matched)",
            body="\n".join(body_parts).strip(),
            priority=1,
        ))

    # 2. Ancestors (priority 2)
    anc_lines: List[str] = []
    seen_anc: set = set()
    for p in paths:
        for folder_rel, purpose in ancestor_purpose_chain(
            scan_ctx, p, purposes=purposes
        ):
            if folder_rel in seen_anc:
                continue
            seen_anc.add(folder_rel)
            anc_lines.append(f"- `{folder_rel}/` — {purpose}")
    if anc_lines:
        sections.append(EditPackSection(
            kind="ancestors",
            title="Ancestor folders",
            body="\n".join(anc_lines),
            priority=2,
        ))

    # 3–4. Per-path neighborhood + symbols
    for p in paths:
        is_dir = _path_looks_like_dir(p, scan_ctx, purposes)

        if graph_result and not is_dir:
            neigh_md = render_file_neighborhood(
                graph_result,
                p,
                max_edges=EDIT_PACK_MAX_EDGES,
                max_consumers=EDIT_PACK_MAX_CONSUMERS,
            )
            # Split used-by vs calls for priority
            if "### Used by" in neigh_md:
                before, _, after = neigh_md.partition("### Used by")
                calls = before.replace("### Calls / deps", "").strip()
                used = after.strip()
                if used:
                    sections.append(EditPackSection(
                        kind="used_by",
                        title=f"Used by (`{p}`)",
                        body=used if used.startswith("-") else f"### Used by\n{used}",
                        priority=3,
                    ))
                if calls:
                    sections.append(EditPackSection(
                        kind="outbound",
                        title=f"Calls / deps (`{p}`)",
                        body=calls,
                        priority=4,
                    ))
            elif neigh_md.strip():
                sections.append(EditPackSection(
                    kind="outbound",
                    title=f"Neighborhood (`{p}`)",
                    body=neigh_md,
                    priority=4,
                ))

            sym_md = _file_symbols_markdown(scan_ctx, graph_result, p)
            if sym_md:
                sections.append(EditPackSection(
                    kind="symbols",
                    title=f"Local symbols (`{p}`)",
                    body=sym_md,
                    priority=4,
                ))
        elif graph_result and is_dir:
            from .code_graph import render_folder_subgraph, render_reverse_imports
            used = render_reverse_imports(graph_result, p)
            used_bullets = sum(
                1 for ln in (used or "").splitlines() if ln.startswith("- `")
            )
            if used:
                sections.append(EditPackSection(
                    kind="used_by",
                    title=f"Used by (`{p}/`)",
                    body=used,
                    priority=3,
                ))
            # Prefer Used-by for blast radius; skip noisy Call flow when
            # enough consumers already listed; otherwise cap at 8 edges.
            if used_bullets < 3:
                calls = render_folder_subgraph(graph_result, p, max_edges=8)
                if calls:
                    sections.append(EditPackSection(
                        kind="outbound",
                        title=f"Call flow (`{p}/`)",
                        body=calls,
                        priority=4,
                    ))
            # else: Call flow omitted — Used-by already covers consumers

    # 5. Workflow conventions
    if workflow_lines:
        sections.append(EditPackSection(
            kind="conventions",
            title="Conventions (evidenced)",
            body="\n".join(workflow_lines),
            priority=5,
        ))

    # 6. Containing-folder purpose / cached overview
    overview_lines: List[str] = []
    for p in paths:
        parts = p.replace("\\", "/").strip("/").split("/")
        parent = "/".join(parts[:-1]) if len(parts) > 1 else parts[0]
        line = ""
        folder_label = parent
        if scan_ctx and scan_ctx.by_path:
            info = scan_ctx.by_path.get(parent) or scan_ctx.by_path.get(p.rstrip("/"))
            if info is not None:
                ai = (getattr(info, "ai_folder_summary", None) or "").strip()
                purpose = (info.purpose or "").strip()
                line = ai.split("\n")[0].strip() if ai else purpose
                folder_label = info.path or parent
        if not line:
            line = (purposes.get(parent) or purposes.get(p.rstrip("/")) or "").strip()
        if line:
            overview_lines.append(f"- `{folder_label}/` — {line}")
    if overview_lines:
        # Dedupe
        seen = set()
        uniq = []
        for ln in overview_lines:
            if ln not in seen:
                seen.add(ln)
                uniq.append(ln)
        sections.append(EditPackSection(
            kind="folder_overview",
            title="Containing folder",
            body="\n".join(uniq),
            priority=6,
        ))

    sections.sort(key=lambda s: s.priority)
    return sections


def _constitution_is_rich(constitution: Constitution) -> bool:
    return bool(
        constitution.exists
        and all(
            constitution.covers(t)
            for t in ("purpose", "architecture", "commands")
        )
    )


def assemble_edit_pack(
    project_root: Path,
    paths: Sequence[str],
    *,
    token_budget: int = DEFAULT_EDIT_BUDGET,
    enable_graph: bool = True,
    enable_ast: bool = True,
    write_graph_cache: bool = True,
    scan_ctx: Optional[ScanContext] = None,
    graph_result: Optional[GraphBuildResult] = None,
    constitution: Optional[Constitution] = None,
    workflow_lines: Optional[Sequence[str]] = None,
    purposes: Optional[Dict[str, str]] = None,
    use_cache: bool = True,
) -> EditPackResult:
    """
    Build a budgeted edit pack for one or more relative paths.

    Warm path: fingerprint match → load graph + purposes (skip AST scan).
    Priority (keep first): agents_slices → ancestors → used_by →
    outbound/symbols → conventions → folder_overview.
    """
    from .evidence import collect_evidence
    from .models import ProjectConfig
    from .workflow import collect_workflow, workflow_lines_for_codebase

    project_root = project_root.resolve()
    norm_paths = [
        p.replace("\\", "/").strip().strip("/")
        for p in paths
        if p and p.strip()
    ]
    if not norm_paths:
        return EditPackResult(
            paths=[],
            sections=[EditPackSection(
                kind="error",
                title="Error",
                body="No paths provided.",
                priority=1,
            )],
            tokens_cap=token_budget,
        )

    if constitution is None:
        constitution = load_constitution(project_root)

    warm = False
    purposes = dict(purposes) if purposes else {}

    # Warm path: skip evidence/scan when cache fingerprint matches
    if (
        use_cache
        and enable_graph
        and enable_ast
        and scan_ctx is None
        and graph_result is None
    ):
        hit = try_load_warm_cache(project_root)
        if hit is not None:
            loaded = deserialize(hit.graph_path)
            if loaded is not None and loaded.symbols_by_qname:
                graph_result = loaded
                purposes = hit.purposes
                warm = True
                logger.info("edit-pack warm cache hit fp=%s…", hit.fingerprint[:12])

    if not warm and scan_ctx is None and enable_ast:
        evidence = collect_evidence(project_root)
        primary = evidence.languages[0] if evidence.languages else "unknown"
        config = ProjectConfig(
            description=project_root.name,
            is_monorepo=len(evidence.languages) > 1,
            primary_language=primary,
            frameworks=[],
            project_root=project_root,
        )
        try:
            from .scanner import scan_project
            scan_ctx = scan_project(project_root, config, extract_signatures=True)
        except Exception as exc:
            logger.warning("scan failed for edit pack: %s", exc)
            scan_ctx = None

    if not warm and graph_result is None and enable_graph:
        graph_result = load_or_build_graph(
            project_root,
            scan_ctx,
            enable_graph=True,
            write_cache=write_graph_cache,
        )

    # Persist cache after cold scan
    if (
        not warm
        and use_cache
        and write_graph_cache
        and scan_ctx is not None
        and graph_result is not None
        and graph_result.symbols_by_qname
    ):
        try:
            fp, nfiles = fingerprint_project(project_root)
            purposes = purposes_from_scan(scan_ctx)
            write_cache(
                project_root,
                fingerprint=fp,
                file_count=nfiles,
                purposes=purposes,
            )
            # Ensure graph.json exists (load_or_build may have written it)
            if write_graph_cache:
                serialize(graph_result, _graph_cache_path(project_root))
        except OSError as exc:
            logger.warning("could not write edit-pack cache: %s", exc)

    if purposes is None:
        purposes = {}
    if not purposes and scan_ctx is not None:
        purposes = purposes_from_scan(scan_ctx)

    if workflow_lines is None:
        rich = _constitution_is_rich(constitution)
        if rich or constitution.covers("workflow") or warm:
            # Warm path skips evidence glean; rich AGENTS needs no conventions dump
            workflow_lines = []
        else:
            try:
                evidence = collect_evidence(project_root)
                langs = evidence.languages or None
                wf = collect_workflow(
                    project_root,
                    constitution=constitution,
                    languages=langs,
                )
                workflow_lines = workflow_lines_for_codebase(wf, max_bullets=6)
            except Exception:
                workflow_lines = []

    candidates = _build_candidate_sections(
        paths=norm_paths,
        constitution=constitution,
        scan_ctx=scan_ctx,
        graph_result=graph_result,
        workflow_lines=workflow_lines or [],
        purposes=purposes,
    )

    budget = TokenBudget(cap=token_budget)
    kept: List[EditPackSection] = []
    shed: List[str] = []

    # Header is free / forced
    header = f"Paths: {', '.join(norm_paths)}\n"
    budget.force_spend(header, kind="edit_pack_header")

    for sec in candidates:
        block = f"## {sec.title}\n\n{sec.body}\n"
        # Higher priority (lower number) uses fit_or_truncate; lower uses try_spend
        if sec.priority <= 2:
            fitted = budget.fit_or_truncate(
                block,
                kind=sec.kind,
                folder=norm_paths[0],
                min_useful_chars=80,
            )
            if fitted is None:
                shed.append(sec.kind)
                continue
            text, truncated = fitted
            # Re-parse body from fitted block roughly
            body = text
            if body.startswith(f"## {sec.title}"):
                body = body.split("\n", 2)[-1].strip()
            kept.append(EditPackSection(
                kind=sec.kind,
                title=sec.title,
                body=body,
                priority=sec.priority,
            ))
            if truncated:
                shed.append(f"{sec.kind}:truncated")
        else:
            if budget.try_spend(block, kind=sec.kind, folder=norm_paths[0]):
                kept.append(sec)
            else:
                # Try truncated fit for used_by (priority 3)
                if sec.priority == 3:
                    fitted = budget.fit_or_truncate(
                        block,
                        kind=sec.kind,
                        folder=norm_paths[0],
                        min_useful_chars=60,
                    )
                    if fitted is not None:
                        text, _ = fitted
                        body = text.split("\n", 2)[-1].strip() if text.startswith("##") else text
                        kept.append(EditPackSection(
                            kind=sec.kind,
                            title=sec.title,
                            body=body,
                            priority=sec.priority,
                        ))
                        continue
                shed.append(sec.kind)

    return EditPackResult(
        paths=list(norm_paths),
        sections=kept,
        tokens_spent=budget.spent,
        tokens_cap=token_budget,
        shed=shed,
    )


def write_edit_pack(
    project_root: Path,
    result: EditPackResult,
    *,
    as_json: bool = False,
) -> Path:
    """Write pack under `.ai-context/edits/`."""
    edits = project_root / ".ai-context" / "edits"
    edits.mkdir(parents=True, exist_ok=True)
    slug = "--".join(
        p.replace("/", "-") for p in result.paths[:3]
    ) or "pack"
    if len(slug) > 80:
        slug = slug[:80]
    ext = "json" if as_json else "md"
    out = edits / f"{slug}.{ext}"
    if as_json:
        out.write_text(
            json.dumps(result.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        out.write_text(result.to_markdown(), encoding="utf-8")
    return out
