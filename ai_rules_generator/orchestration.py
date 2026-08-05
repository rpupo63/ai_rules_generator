"""
Structure-only orchestration: build repo map, optional cursor rules, AGENTS pointer.

Prose emitters and LLM enrichment paths have been removed. Generation is
deterministic: tags → graph → ranked map.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .agents_addendum import soft_addendum_body, patch_agents_md
from .code_graph import (
    build_graph_from_project,
    rank_files,
    render_repo_map,
    render_reverse_imports,
    serialize,
)
from .exclusions import get_exclusion_context, should_skip_dir, should_skip_file
from .models import ProjectConfig
from .rule_renderer import (
    TierFile,
    detect_folder_language,
    render_tier2_folder,
    write_tier_files,
)
from .scanner import FolderInfo, ScanContext, scan_project
from .tags import language_for_path
from .token_budget import DEFAULT_GLOBAL_BUDGET, TokenBudget

logger = logging.getLogger(__name__)


def _include_filter(project_root: Path):
    excl = get_exclusion_context(project_root)
    gitignore = excl["gitignore_patterns"]

    def _should(abs_path: Path, rel: str) -> bool:
        parts = Path(rel).parts
        for i in range(len(parts) - 1):
            d = project_root.joinpath(*parts[: i + 1])
            if should_skip_dir(d, project_root, gitignore):
                return False
        if should_skip_file(abs_path, project_root, gitignore):
            return False
        return language_for_path(abs_path) is not None

    return _should


def build_repo_map(
    project_root: Path,
    *,
    scan_ctx: Optional[ScanContext] = None,
    token_budget: int = 1000,
    write_graph: bool = False,
):
    """Build the structure-only graph and Markdown repo map."""
    root = project_root.resolve()
    ctx = scan_ctx or scan_project(root)
    result = build_graph_from_project(
        root,
        ctx.files,
        should_include=_include_filter(root),
    )
    md = render_repo_map(result, token_budget=token_budget)
    if write_graph:
        graph_dir = root / ".ai-context" / "graph"
        serialize(result, graph_dir / "graph.json")
        (graph_dir / "repo-map.md").write_text(md + "\n", encoding="utf-8")
    return result, md


def emit_tier2_folder_files(
    project_root: Path,
    scan_ctx: ScanContext,
    graph_result,
    *,
    config: Optional[ProjectConfig] = None,
    max_folders: int = 12,
    dry_run: bool = False,
) -> List[TierFile]:
    """Emit glob-scoped `.mdc` rules for top-ranked folders (capped)."""
    cfg = config or ProjectConfig(
        description=project_root.name,
        is_monorepo=False,
        primary_language="",
        frameworks=[],
    )
    file_ranks = {f: s for f, s in rank_files(graph_result)}
    folder_scores = []
    for rel, folder in scan_ctx.folders.items():
        if not rel:
            continue
        score = 0.0
        for path in folder.files:
            try:
                r = str(path.resolve().relative_to(project_root)).replace("\\", "/")
            except ValueError:
                continue
            score += file_ranks.get(r, 0.0)
        folder_scores.append((rel, folder, score))
    folder_scores.sort(key=lambda t: t[2], reverse=True)

    files: List[TierFile] = []
    for rel, folder, _score in folder_scores[:max_folders]:
        file_rels = []
        for p in folder.files:
            try:
                file_rels.append(
                    str(p.resolve().relative_to(project_root)).replace("\\", "/")
                )
            except ValueError:
                continue
        lang = folder.language or detect_folder_language(file_rels) or cfg.primary_language
        rev = render_reverse_imports(graph_result, rel)
        glob_pattern = f"{rel}/**/*" if rel else "**/*"
        skeleton = "\n".join(f"- `{f}`" for f in file_rels[:40])
        tf = render_tier2_folder(
            folder_name=rel or project_root.name,
            glob_pattern=glob_pattern,
            language=lang or "",
            frameworks=list(cfg.frameworks or []),
            skeleton_markdown=skeleton,
            reverse_imports=rev,
        )
        files.append(tf)

    if not dry_run and files:
        write_tier_files(project_root, files)
    return files


def generate_codebase_context(
    project_root: Path,
    *,
    enable_ast: bool = True,
    enable_graph: bool = True,
    dry_run: bool = False,
    emit_cursor_rules: bool = False,
    global_budget: int = DEFAULT_GLOBAL_BUDGET,
    graph_token_budget: int = 1000,
    write_graph: bool = False,
    write_modules: bool = False,
    emit_practices_flag: bool = False,
    **_ignored,
) -> dict:
    """
    Primary entry: structure-only `.ai-context/` map + AGENTS.md pointer.

    Keyword leftovers from the old AI/prose pipeline are accepted and ignored.
    """
    root = Path(project_root).resolve()
    budget = TokenBudget(global_budget)
    scan_ctx = scan_project(root) if enable_ast or enable_graph else ScanContext(
        project_root=root, files=[], folders={}
    )

    graph_result = None
    repo_map_md = ""
    if enable_graph or enable_ast:
        graph_result, repo_map_md = build_repo_map(
            root,
            scan_ctx=scan_ctx,
            token_budget=graph_token_budget,
            write_graph=False,
        )

    ctx_dir = root / ".ai-context"
    codebase_md = (
        f"# Codebase map\n\n"
        f"Structure-only ranked symbols (definitions / references).\n\n"
        f"{repo_map_md}\n"
    )
    budget.force_spend(codebase_md, kind="codebase")

    if not dry_run:
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "CODEBASE.md").write_text(codebase_md, encoding="utf-8")
        if write_graph and graph_result is not None:
            serialize(graph_result, ctx_dir / "graph" / "graph.json")
            (ctx_dir / "graph" / "repo-map.md").write_text(
                repo_map_md + "\n", encoding="utf-8"
            )

    cursor_files: List[TierFile] = []
    if emit_cursor_rules and graph_result is not None:
        cursor_files = emit_tier2_folder_files(
            root, scan_ctx, graph_result, dry_run=dry_run
        )

    if not dry_run:
        body = soft_addendum_body(
            has_practices=False,
            has_graph=write_graph,
            edit_pack_focused=False,
        )
        patch_agents_md(root, addendum_body=body)

    return {
        "project_root": str(root),
        "files_scanned": len(scan_ctx.files),
        "symbols": len(graph_result.symbols_by_qname) if graph_result else 0,
        "edges": graph_result.edges_added if graph_result else 0,
        "cursor_rules": len(cursor_files),
        "dry_run": dry_run,
        "budget": budget,
    }


def show_folder_context(
    project_root: Path,
    folder: str,
    *,
    full: bool = False,
    enable_ast: bool = True,
    enable_graph: bool = True,
) -> str:
    """Print a small on-demand digest for one folder."""
    root = Path(project_root).resolve()
    result, _md = build_repo_map(root, token_budget=800)
    rev = render_reverse_imports(result, folder)
    lines = [f"# Folder `{folder}`", ""]
    syms = [
        s for s in result.symbols_by_qname.values()
        if s.file == folder or s.file.startswith(folder.rstrip("/") + "/")
    ]
    lines.append(f"Symbols: {len(syms)}")
    for s in syms[:40]:
        lines.append(f"- `{s.file}` :: `{s.qualified_name.rsplit('::', 1)[-1]}`")
    if full and rev:
        lines.extend(["", "## References", rev])
    return "\n".join(lines) + "\n"


# Compatibility shims for legacy command imports (rules setup removed).
def generate_single_project_rules_setup(*_a, **_k) -> None:
    raise RuntimeError(
        "Legacy rule setup was removed. Use `ai-rules-generator context` "
        "(structure-only map) or `--emit-cursor-rules`."
    )


def generate_monorepo_project_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def generate_single_project_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def generate_monorepo_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def discover_and_print_packages(project_root: Path):
    return []
