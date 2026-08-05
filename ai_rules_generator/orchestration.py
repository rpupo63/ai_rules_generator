"""
Orchestration of rule generation: single-project, monorepo, and shared structures.

Per the context-engineering plan, the pipeline is:

    scan -> ast_compress -> code_graph.build -> rule_renderer.emit_tiers -> multi_tool.write

The scanner already runs the AST compression in-line (Phase 3); this module
adds the Graph RAG step (Phase 4) and passes the resulting repo-map digest
into the Tier-1 always-on files emitted by `create_shared_ai_rules_directory`.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ast_compression import extract_skeleton, get_language_rule
from .code_graph import (
    GraphBuildResult,
    build_graph,
    render_folder_subgraph,
    render_repo_map,
    render_reverse_imports,
    serialize as serialize_graph,
)
from .config import SECURITY_RULES_TEMPLATE
from .config_manager import get_available_tools, get_tool_display_name
from .detection import discover_monorepo_packages
from .generators import (
    generate_folder_agents_md,
    generate_folder_cursor_rule,
    generate_root_monorepo_rules,
    generate_rules_document,
)
from .generators_multi_tool import generate_all_tool_rules
from .generators_shared import create_shared_ai_rules_directory
from .linker import LinkMode
from .models import ProjectConfig
from .rule_renderer import (
    Tier,
    TierFile,
    detect_folder_language,
    render_tier2_folder,
    write_tier_files,
)
from .scanner import FolderInfo, ScanContext
from .token_budget import DEFAULT_GLOBAL_BUDGET, TokenBudget

logger = logging.getLogger(__name__)


def discover_and_print_packages(project_root: Path) -> List[Tuple[Path, str, List[str]]]:
    """Discover monorepo packages and print summary."""
    print("Discovering packages in monorepo...")
    packages = discover_monorepo_packages(project_root)
    print(f"  Found {len(packages)} packages:")

    for folder_path, language, frameworks in packages:
        fw_str = f" ({', '.join(frameworks)})" if frameworks else ""
        print(f"    - {folder_path.name}: {language}{fw_str}")

    print()
    return packages


# ---------------------------------------------------------------------------
# Phase 3+4 helpers: AST + Graph RAG
# ---------------------------------------------------------------------------

def _collect_skeletons_from_scan(scan_ctx: Optional[ScanContext]) -> list:
    """Walk a ScanContext and gather every AST Skeleton produced by the scanner."""
    if scan_ctx is None or not getattr(scan_ctx, "flat", None):
        return []
    out = []
    seen_files: set = set()
    for folder in scan_ctx.flat:
        for skel in getattr(folder, "skeletons", []):
            if skel.file_path in seen_files:
                continue
            seen_files.add(skel.file_path)
            out.append(skel)
    return out


def _collect_skeletons_from_walk(project_root: Path) -> list:
    """
    Fallback path used when no ScanContext is supplied.  Walks the project
    tree once, extracts skeletons for supported files, and returns the list.
    """
    out = []
    SKIP = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if get_language_rule(path) is None:
            continue
        try:
            skel = extract_skeleton(path)
        except Exception as exc:
            logger.debug("skeleton extraction failed for %s: %s", path, exc)
            continue
        if skel is None or skel.used_fallback or not skel.signatures:
            continue
        out.append(skel)
    return out


def build_repo_map(
    project_root: Path,
    scan_ctx: Optional[ScanContext],
    *,
    token_budget: int = 1000,
    write_artifacts: bool = True,
    budget: Optional[TokenBudget] = None,
) -> Tuple[str, Optional[GraphBuildResult]]:
    """
    Build the DKB and return `(digest, graph_result)`.

    `token_budget` controls the size of the *inline* digest emitted into
    the Tier-1 file.  `budget`, if provided, is the global artifact
    `TokenBudget` and is used to bound the on-disk `repo-map.md` sidecar
    via priority shedding (the full ranked list is sized to the remaining
    global budget rather than always written in full).

    Side effects (when `write_artifacts` is True):
      - `.ai-context/graph/graph.json` - full DKB serialization (NOT counted
        against the artifact budget; it is a machine-readable sidecar that
        no AI tool ingests directly).
      - `.ai-context/graph/repo-map.md` - the same digest persisted for the
        agent to read on demand.  Budget-aware.
    """
    skeletons = _collect_skeletons_from_scan(scan_ctx)
    if not skeletons:
        skeletons = _collect_skeletons_from_walk(project_root)

    if not skeletons:
        return "", None

    result = build_graph(project_root, skeletons)
    digest = render_repo_map(result, token_budget=token_budget)

    if write_artifacts:
        graph_dir = project_root / ".ai-context" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        serialize_graph(result, graph_dir / "graph.json")

        # The on-disk repo-map.md is a low-priority sidecar.  We size it
        # against the *remaining* global budget so big repos don't dump
        # a 200K-token file when the agent's context is already saturated.
        if budget is not None:
            remaining_token_budget = max(2_000, budget.remaining() // 8)
            sidecar_digest = render_repo_map(
                result, token_budget=remaining_token_budget
            )
        else:
            sidecar_digest = digest

        body = (
            f"# Repository Map (DKB / Graph RAG)\n\n"
            f"Auto-generated from {len(skeletons)} parsed files. "
            f"Edges: {result.edges_added}.\n\n"
            f"{sidecar_digest}\n"
        )
        if budget is not None:
            outcome = budget.fit_or_truncate(
                body, kind="repo_map_sidecar", folder=None,
            )
            if outcome is not None:
                final_body, _ = outcome
                (graph_dir / "repo-map.md").write_text(final_body, encoding="utf-8")
        else:
            (graph_dir / "repo-map.md").write_text(body, encoding="utf-8")

    return digest, result


_CONVENTIONS_BLOCK = (
    "## Conventions\n\n"
    "- Match existing exports listed above before adding new ones.\n"
    "- Co-locate tests with the file under test where the folder "
    "already does so."
)


def _compose_folder_header(
    *,
    slug: str,
    glob: str,
    language: str,
    frameworks: List[str],
    purpose: str,
) -> str:
    fw_str = ", ".join(frameworks) if frameworks else "(none)"
    title = f"{slug} - Domain Rules"
    return (
        f"# {title}\n\n"
        f"- Folder: `{slug}/`\n"
        f"- Glob: `{glob}`\n"
        f"- Language: {language.title() if language else '(mixed)'}\n"
        f"- Frameworks: {fw_str}\n"
        f"- Purpose: {purpose or '(inferred from contents)'}"
    )


def _compose_folder_skeleton(folder: FolderInfo) -> str:
    """Concatenate per-file outline_markdown for every skeleton in the
    folder.  Used by `context show --full`; digests use top-symbols instead."""
    blocks = []
    for skel in folder.skeletons:
        block = (skel.outline_markdown or "").strip()
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


def _compose_top_symbols(folder: FolderInfo, *, limit: int = 15) -> str:
    """Lean digest: up to `limit` signature lines across files in the folder."""
    lines: List[str] = []
    for skel in folder.skeletons:
        if len(lines) >= limit:
            break
        name = Path(skel.file_path).name if skel.file_path else "?"
        sigs = list(getattr(skel, "signatures", None) or [])
        if not sigs:
            continue
        for sig in sigs:
            if len(lines) >= limit:
                break
            text = (getattr(sig, "signature", None) or "").strip()
            if not text:
                continue
            # One line per symbol; keep first line of multi-line signatures
            first = text.splitlines()[0].strip()
            lines.append(f"- `{name}`: `{first}`")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _build_folder_importance_index(
    graph_result: Optional[GraphBuildResult],
) -> Dict[str, float]:
    """Pre-compute, for every file in the DKB, the sum of its symbols'
    PageRank scores.  Tier-2 emission then sums file scores per folder
    in O(folders + files) instead of running PageRank per folder."""
    if graph_result is None:
        return {}
    from .code_graph import rank_symbols
    ranked = rank_symbols(graph_result)
    per_file: Dict[str, float] = {}
    for sym, score in ranked:
        f = sym.file.replace("\\", "/")
        per_file[f] = per_file.get(f, 0.0) + float(score)
    return per_file


def _folder_importance(
    folder: FolderInfo,
    per_file_scores: Dict[str, float],
) -> float:
    """Heuristic: how much priority a folder should get when the global
    budget is tight.  Sums per-file PageRank totals for files under this
    folder; falls back to skeleton/file count when no graph is available."""
    rel = (folder.path or "").rstrip("/")
    if not per_file_scores:
        return float(folder.file_count or len(folder.skeletons))
    score = 0.0
    prefix = (rel + "/") if rel else ""
    for f, s in per_file_scores.items():
        if not rel or f.startswith(prefix) or f == rel:
            score += s
    return score or float(folder.file_count or len(folder.skeletons))


def select_ai_folders(
    candidates: List[FolderInfo],
    surfaces: List[str],
    *,
    limit: int,
    per_file_scores: Optional[Dict[str, float]] = None,
) -> List[FolderInfo]:
    """Pick folders for AI enrichment: ≥1 per surface, then fill by importance.

    Candidates should already be importance-sortable; this function re-ranks
    and surface-balances so backend-heavy graphs do not starve frontend/etc.
    """
    from .context_model import _surface_of

    if limit <= 0 or not candidates:
        return []
    scores = per_file_scores or {}
    ranked = sorted(
        candidates,
        key=lambda f: -_folder_importance(f, scores),
    )
    chosen: List[FolderInfo] = []
    seen: set = set()

    def _key(f: FolderInfo) -> str:
        return (f.path or "").rstrip("/")

    ordered_surfaces = list(surfaces) if surfaces else []
    # Also cover top-level segments present in candidates
    for f in ranked:
        surf = _surface_of(f.path or "", ordered_surfaces or [])
        if surf and surf not in ordered_surfaces:
            ordered_surfaces.append(surf)

    for surf in ordered_surfaces:
        if len(chosen) >= limit:
            break
        for f in ranked:
            if _key(f) in seen:
                continue
            if _surface_of(f.path or "", ordered_surfaces) != surf:
                continue
            chosen.append(f)
            seen.add(_key(f))
            break

    for f in ranked:
        if len(chosen) >= limit:
            break
        if _key(f) in seen:
            continue
        chosen.append(f)
        seen.add(_key(f))
    return chosen


def emit_tier2_folder_files(
    project_root: Path,
    scan_ctx: ScanContext,
    config: ProjectConfig,
    *,
    budget: Optional[TokenBudget] = None,
    graph_result: Optional[GraphBuildResult] = None,
    use_ai: bool = False,
    ai_provider: str = "none",
    ai_model: str = "template",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
    folder_frameworks: Optional[Dict[str, List[str]]] = None,
) -> List[Path]:
    """
    Emit one Tier-2 `.cursor/rules/<folder>.mdc` per significant folder.

    The per-folder body is composed in canonical section order
    (header -> overview -> skeleton -> call flow -> used by -> conventions).
    A shared `TokenBudget` drives priority shedding: headers are force-spent
    so every folder always gets a stub; optional sections compete in
    priority order across folders, with the more "central" folders (by
    PageRank, when available) getting first dibs.
    """
    if not getattr(scan_ctx, "flat", None):
        return []

    budget = budget or TokenBudget()

    # ----- 1. Build per-folder specs (one per significant folder) ----------
    per_file_scores = _build_folder_importance_index(graph_result)
    specs: List[Dict[str, Any]] = []
    seen_slugs: set = set()
    for folder in scan_ctx.flat:
        if not folder.skeletons:
            continue
        rel_path = folder.path or folder.name
        slug = (rel_path.replace("/", "--").replace("\\", "--")) or "root"
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        glob = f"{rel_path}/**/*" if rel_path else "**/*"
        file_paths = [s.file_path for s in folder.skeletons]
        language = detect_folder_language(
            file_paths, fallback=config.primary_language
        )

        specs.append({
            "folder": folder,
            "slug": slug,
            "rel_path": rel_path,
            "glob": glob,
            "language": language,
            "importance": _folder_importance(folder, per_file_scores),
            "fragments": {},   # slot -> rendered text
        })

    if not specs:
        return []

    # ----- 2. (Optional) AI folder + file summarization --------------------
    if use_ai and ai_provider != "none":
        try:
            from .ai_summary import generate_ai_folder_summary
        except Exception as exc:
            logger.warning("AI summary module unavailable: %s", exc)
            generate_ai_folder_summary = None  # type: ignore

        if generate_ai_folder_summary is not None:
            for spec in specs:
                try:
                    generate_ai_folder_summary(
                        spec["folder"],
                        project_root,
                        config,
                        ai_provider=ai_provider,
                        ai_model=ai_model,
                        openai_key=openai_key,
                        anthropic_key=anthropic_key,
                        google_key=google_key,
                    )
                except Exception as exc:
                    logger.warning(
                        "AI folder summary failed for %s: %s",
                        spec["slug"], exc,
                    )

    # ----- 3. Force-emit folder headers (priority 1, never shed) -----------
    for spec in specs:
        # Prefer folder-local frameworks (polyglot-safe); never stamp the
        # whole project's framework list onto every folder.
        fws: List[str] = []
        if folder_frameworks and spec["rel_path"] in folder_frameworks:
            fws = folder_frameworks[spec["rel_path"]]
        elif folder_frameworks and spec["slug"] in folder_frameworks:
            fws = folder_frameworks[spec["slug"]]
        header = _compose_folder_header(
            slug=spec["slug"],
            glob=spec["glob"],
            language=spec["language"],
            frameworks=fws,
            purpose=spec["folder"].purpose,
        )
        budget.force_spend(header, kind="tier2_header", folder=spec["slug"])
        spec["fragments"]["header"] = header

    # ----- 4. Optional sections in priority order across folders ----------
    by_importance = sorted(specs, key=lambda s: -s["importance"])

    # Priority 3: per-folder overview
    for spec in by_importance:
        summary = (spec["folder"].ai_folder_summary or "").strip()
        if not summary:
            continue
        block = "## Overview\n\n" + summary
        outcome = budget.fit_or_truncate(
            block, kind="folder_summary", folder=spec["slug"],
        )
        if outcome is not None:
            text, _ = outcome
            spec["fragments"]["overview"] = text

    # Priority 4: AST skeleton (with file descriptions interleaved)
    from .rule_renderer import _interleave_descriptions
    for spec in by_importance:
        skeleton_md = _compose_folder_skeleton(spec["folder"])
        if not skeleton_md.strip():
            continue
        descs: Dict[str, str] = {}
        for f in spec["folder"].files:
            if f.description:
                descs[f.name] = f.description
        skeleton_block = (
            "## Skeleton\n\n"
            + _interleave_descriptions(skeleton_md, descs).strip()
        )
        outcome = budget.fit_or_truncate(
            skeleton_block, kind="skeleton", folder=spec["slug"],
        )
        if outcome is not None:
            text, _ = outcome
            spec["fragments"]["skeleton"] = text

    # Priority 5: folder-local call subgraph (deterministic)
    if graph_result is not None:
        for spec in by_importance:
            local = render_folder_subgraph(graph_result, spec["rel_path"])
            if not local:
                continue
            block = "## Call Flow\n\n" + local
            outcome = budget.fit_or_truncate(
                block, kind="local_call_graph", folder=spec["slug"],
            )
            if outcome is not None:
                text, _ = outcome
                spec["fragments"]["call_flow"] = text

    # Priority 6: reverse imports (deterministic)
    if graph_result is not None:
        for spec in by_importance:
            rev = render_reverse_imports(graph_result, spec["rel_path"])
            if not rev:
                continue
            block = "## Used By\n\n" + rev
            outcome = budget.fit_or_truncate(
                block, kind="reverse_imports", folder=spec["slug"],
            )
            if outcome is not None:
                text, _ = outcome
                spec["fragments"]["used_by"] = text

    # Priority 7: conventions (small; usually fits)
    for spec in by_importance:
        outcome = budget.fit_or_truncate(
            _CONVENTIONS_BLOCK, kind="conventions", folder=spec["slug"],
        )
        if outcome is not None:
            text, _ = outcome
            spec["fragments"]["conventions"] = text

    # ----- 5. Assemble + write -------------------------------------------
    tier_files: List[TierFile] = []
    slot_order = (
        "header", "overview", "skeleton",
        "call_flow", "used_by", "conventions",
    )
    for spec in specs:
        parts: List[str] = []
        for slot in slot_order:
            text = spec["fragments"].get(slot)
            if text:
                parts.append(text)
        body = "\n\n".join(parts).rstrip() + "\n"
        tier_files.append(TierFile(
            tier=Tier.GLOB_SCOPED,
            slug=spec["slug"],
            title=f"{spec['slug']} - Domain Rules",
            body=body,
            glob=spec["glob"],
        ))

    return write_tier_files(project_root, tier_files)


def _write_budget_report(project_root: Path, budget: TokenBudget) -> None:
    """Persist the budget report to `.ai-rules/budget-report.md` so the
    user can see exactly which sections were emitted, truncated, or shed."""
    ai_rules_dir = project_root / ".ai-rules"
    ai_rules_dir.mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "budget-report.md").write_text(
        budget.report_markdown(), encoding="utf-8",
    )


def generate_single_project_rules_setup(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    enabled_tools: Optional[List[str]] = None,
    *,
    google_key: Optional[str] = None,
    scan_ctx: Optional[ScanContext] = None,
    enable_graph: bool = True,
    enable_ast: bool = True,
    graph_token_budget: int = 1000,
    max_tier1_lines: Optional[int] = None,
    global_budget: int = DEFAULT_GLOBAL_BUDGET,
    link_mode: LinkMode = LinkMode.SYMLINK,
) -> TokenBudget:
    """
    Generate rules for a single project using the 2-4-2 tiered layout
    under a single global `TokenBudget`.

    Pipeline:
        1. (Optional) Build the DKB / Graph RAG and persist the digest.
        2. Emit Tier-1 always-on + Tier-3 skill files (budget-aware).
        3. Emit Tier-2 glob-scoped per-folder files (budget-aware, priority shedding).
        4. Emit tool-specific entry files (`generate_all_tool_rules`).
        5. Write `.ai-rules/budget-report.md`.

    Returns the `TokenBudget` so callers can inspect spending / rejections.
    """
    budget = TokenBudget(cap=global_budget)

    repo_map_digest = ""
    graph_result: Optional[GraphBuildResult] = None
    if enable_ast and enable_graph:
        print("Building DKB / Graph RAG repo map...")
        repo_map_digest, graph_result = build_repo_map(
            project_root, scan_ctx,
            token_budget=graph_token_budget,
            budget=budget,
        )
        if repo_map_digest:
            print(f"  Wrote .ai-context/graph/graph.json + repo-map.md")

    print("Creating shared AI rules directory (Tier 1 + Tier 3)...")
    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key,
        google_key=google_key,
        scan_ctx=scan_ctx,
        repo_map_digest=repo_map_digest,
        max_tier1_lines=max_tier1_lines,
        budget=budget,
    )
    print(f"  ✓ Created {ai_rules_dir}")

    if scan_ctx is not None:
        print("Emitting Tier-2 glob-scoped per-folder files...")
        tier2_paths = emit_tier2_folder_files(
            project_root, scan_ctx, config,
            budget=budget,
            graph_result=graph_result,
            use_ai=use_ai,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
        )
        for p in tier2_paths:
            print(f"  ✓ Created {p.relative_to(project_root)}")

    if enabled_tools is None:
        enabled_tools = ["cursor", "claude-code"]
    tool_names = [get_tool_display_name(tool) for tool in enabled_tools]
    print(f"\nGenerating rule files for enabled AI coding tools...")
    print(f"  Tools: {', '.join(tool_names)}")
    generate_all_tool_rules(
        ai_rules_dir, config, base_path, project_root, enabled_tools,
        scan_ctx=scan_ctx,
        link_mode=link_mode,
    )

    _write_budget_report(project_root, budget)
    print(f"\n{budget.summary()}")
    print(f"  Report: .ai-rules/budget-report.md")
    return budget


def generate_monorepo_project_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    enabled_tools: Optional[List[str]] = None,
    *,
    google_key: Optional[str] = None,
    scan_ctx: Optional[ScanContext] = None,
    enable_graph: bool = True,
    enable_ast: bool = True,
    graph_token_budget: int = 1000,
    max_tier1_lines: Optional[int] = None,
    global_budget: int = DEFAULT_GLOBAL_BUDGET,
    link_mode: LinkMode = LinkMode.SYMLINK,
) -> TokenBudget:
    """Generate rules for a monorepo with shared AI rules structure under
    a single global TokenBudget."""
    budget = TokenBudget(cap=global_budget)

    packages = discover_and_print_packages(project_root)

    repo_map_digest = ""
    graph_result: Optional[GraphBuildResult] = None
    if enable_ast and enable_graph:
        print("Building DKB / Graph RAG repo map for monorepo...")
        repo_map_digest, graph_result = build_repo_map(
            project_root, scan_ctx,
            token_budget=graph_token_budget,
            budget=budget,
        )

    print("\nCreating shared AI rules directory (Tier 1 + Tier 3)...")
    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key,
        google_key=google_key,
        scan_ctx=scan_ctx,
        repo_map_digest=repo_map_digest,
        max_tier1_lines=max_tier1_lines,
        budget=budget,
    )
    print(f"  ✓ Created {ai_rules_dir}")

    if scan_ctx is not None:
        print("Emitting Tier-2 glob-scoped per-folder files...")
        tier2_paths = emit_tier2_folder_files(
            project_root, scan_ctx, config,
            budget=budget,
            graph_result=graph_result,
            use_ai=use_ai,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
        )
        for p in tier2_paths:
            print(f"  ✓ Created {p.relative_to(project_root)}")

    print("\nGenerating root-level rules...")
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")

    security_mdc = cursor_rules_dir / "security.mdc"
    security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
    print(f"  ✓ Created {security_mdc}")

    create_package_level_rules(
        packages, base_path, project_root, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )

    if enabled_tools is None:
        enabled_tools = ["cursor", "claude-code"]

    print(f"\nLinking tool entry points to AGENTS.md...")
    generate_all_tool_rules(
        ai_rules_dir, config, base_path, project_root, enabled_tools,
        scan_ctx=scan_ctx,
        link_mode=link_mode,
    )

    _write_budget_report(project_root, budget)
    print(f"\n{budget.summary()}")
    print(f"  Report: .ai-rules/budget-report.md")
    return budget


def generate_single_project_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Generate rules for a single project."""
    print(f"  Output: {config.output_file}")
    print()

    rules_doc = generate_rules_document(
        config, base_path, use_ai=use_ai, ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )

    output_path = project_root / config.output_file
    output_path.write_text(rules_doc, encoding='utf-8')

    print(f"✓ Successfully generated rules document: {output_path}")
    print(f"  File size: {len(rules_doc)} characters, {len(rules_doc.splitlines())} lines")


def create_root_level_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    packages: List[Tuple[Path, str, List[str]]],
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Create root-level rule files."""
    print("Generating root-level rules...")

    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")

    root_rules_md = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=False, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(root_rules_md, encoding='utf-8')
    print(f"  ✓ Created {claude_md}")

    security_mdc = cursor_rules_dir / "security.mdc"
    security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
    print(f"  ✓ Created {security_mdc}")


def create_package_level_rules(
    packages: List[Tuple[Path, str, List[str]]],
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Create package-level rule files."""
    for folder_path, language, frameworks in packages:
        folder_name = folder_path.name
        print(f"\nGenerating rules for {folder_name}...")

        package_cursor_dir = folder_path / ".cursor" / "rules"
        package_cursor_dir.mkdir(parents=True, exist_ok=True)

        if use_ai:
            print(f"    Using AI generation for {folder_name}...")

        cursor_rule = generate_folder_cursor_rule(
            folder_path, folder_name, language,
            frameworks, base_path, project_root, use_ai=use_ai,
            ai_provider=ai_provider, ai_model=ai_model,
            openai_key=openai_key, anthropic_key=anthropic_key
        )
        rule_file = package_cursor_dir / f"{folder_name}-patterns.mdc"
        rule_file.write_text(cursor_rule, encoding='utf-8')
        print(f"  ✓ Created {rule_file}")

        agents_content = generate_folder_agents_md(
            folder_path, folder_name, language,
            frameworks, base_path, use_ai=use_ai,
            ai_provider=ai_provider, ai_model=ai_model,
            openai_key=openai_key, anthropic_key=anthropic_key
        )

        agents_md = folder_path / "AGENTS.md"
        agents_md.write_text(agents_content, encoding='utf-8')
        print(f"  ✓ Created {agents_md}")

        package_claude_md = folder_path / "CLAUDE.md"
        package_claude_md.write_text(agents_content, encoding='utf-8')
        print(f"  ✓ Created {package_claude_md}")


def generate_monorepo_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Generate rules for a monorepo."""
    packages = discover_and_print_packages(project_root)
    create_root_level_rules(
        config, base_path, project_root, packages, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    create_package_level_rules(
        packages, base_path, project_root, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )

    print(f"\n✓ Successfully generated monorepo rules structure")
    cursor_dir = project_root / ".cursor" / "rules" / "general.mdc"
    print(f"  Root rules: {cursor_dir}")
    print(f"  Package rules: {len(packages)} packages configured")


def _slug_for_folder(rel_path: str) -> str:
    return (rel_path.replace("/", "--").replace("\\", "--")) or "root"


def collect_module_refs(
    scan_ctx: Optional[ScanContext],
    evidence: "EvidenceBundle",
    *,
    primary_language_fallback: str = "",
    graph_result: Optional[GraphBuildResult] = None,
) -> Tuple[List["ModuleRef"], Dict[str, List[str]]]:
    """Build ModuleRef list + per-folder framework map (no project-wide bleed)."""
    from .context_model import ModuleRef
    from .evidence import frameworks_for_path

    per_file_scores = _build_folder_importance_index(graph_result)
    modules: List[ModuleRef] = []
    folder_fws: Dict[str, List[str]] = {}
    if scan_ctx is None or not getattr(scan_ctx, "flat", None):
        for pkg in evidence.top_packages[:30]:
            lang = ""
            for s in evidence.stacks:
                if s.source.rstrip("/") == pkg or s.source.startswith(pkg + "/"):
                    lang = s.language
                    break
            fws = frameworks_for_path(evidence, pkg, lang or None)
            slug = _slug_for_folder(pkg)
            modules.append(ModuleRef(
                slug=slug,
                rel_path=pkg,
                language=lang or "mixed",
                frameworks=fws,
                purpose="",
                file_count=0,
                importance=1.0,
            ))
            folder_fws[pkg] = fws
        return modules, folder_fws

    seen: set = set()
    for folder in scan_ctx.flat:
        if not folder.skeletons and folder.file_count < 2:
            continue
        rel_path = folder.path or folder.name or ""
        slug = _slug_for_folder(rel_path)
        if slug in seen:
            continue
        seen.add(slug)
        file_paths = [s.file_path for s in folder.skeletons] if folder.skeletons else []
        language = detect_folder_language(
            file_paths,
            fallback=primary_language_fallback or (
                evidence.languages[0] if evidence.languages else ""
            ),
        )
        fws = frameworks_for_path(evidence, rel_path, language or None)
        folder_fws[rel_path] = fws
        overview = (getattr(folder, "ai_folder_summary", None) or "").strip()
        from .edit_pack import recursive_code_file_count
        code_count = recursive_code_file_count(scan_ctx, rel_path)
        modules.append(ModuleRef(
            slug=slug,
            rel_path=rel_path,
            language=language or "mixed",
            frameworks=fws,
            purpose=folder.purpose or "",
            file_count=code_count or folder.file_count or len(folder.skeletons),
            importance=_folder_importance(folder, per_file_scores),
            overview=overview,
        ))
    return modules, folder_fws


def emit_module_context_files(
    project_root: Path,
    scan_ctx: Optional[ScanContext],
    modules: List["ModuleRef"],
    *,
    budget: Optional[TokenBudget] = None,
    graph_result: Optional[GraphBuildResult] = None,
    full: bool = False,
    charge_budget: bool = True,
) -> Dict[str, str]:
    """
    Build module markdown bodies for `.ai-context/modules/`.

    Default digests: overview + top symbols (no call-flow / full skeleton).
    `full=True` adds skeleton + call flow + used-by (for `context show --full`).
    """
    from .context_renderer import render_module_md

    budget = budget or TokenBudget()
    bodies: Dict[str, str] = {}
    folder_by_slug = {}
    if scan_ctx and getattr(scan_ctx, "flat", None):
        for folder in scan_ctx.flat:
            rel = folder.path or folder.name or ""
            folder_by_slug[_slug_for_folder(rel)] = folder

    for mod in modules:
        overview = mod.overview or ""
        top_symbols = ""
        skeleton = ""
        call_flow = ""
        used_by = ""
        folder = folder_by_slug.get(mod.slug)
        if folder is not None:
            if not overview:
                overview = (getattr(folder, "ai_folder_summary", None) or "").strip()
            if full:
                skeleton = _compose_folder_skeleton(folder)
                if graph_result is not None:
                    call_flow = render_folder_subgraph(graph_result, mod.rel_path) or ""
                    used_by = render_reverse_imports(graph_result, mod.rel_path) or ""
            else:
                top_symbols = _compose_top_symbols(folder, limit=15)
        body = render_module_md(
            mod,
            overview=overview,
            top_symbols=top_symbols,
            skeleton=skeleton,
            call_flow=call_flow,
            used_by=used_by,
        )
        if charge_budget:
            outcome = budget.fit_or_truncate(
                body, kind="module_map", folder=mod.slug,
            )
            if outcome is not None:
                bodies[mod.slug], _ = outcome
        else:
            bodies[mod.slug] = body
    return bodies


def generate_codebase_context(
    project_root: Path,
    *,
    enable_ast: bool = True,
    enable_graph: bool = True,
    write_graph: bool = False,
    write_modules: bool = True,
    emit_practices_flag: bool = False,
    use_ai: bool = False,
    ai_provider: str = "none",
    ai_model: str = "template",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
    graph_token_budget: int = 1000,
    global_budget: int = DEFAULT_GLOBAL_BUDGET,
    emit_cursor_rules: bool = False,
    dry_run: bool = False,
    base_path: Optional[Path] = None,
    ai_max_folders: int = 12,
) -> Dict[str, Any]:
    """
    Complementary context pipeline (default product path):

        evidence + constitution -> scan/graph(rank) -> lean What/How/Why pack
        -> optional practices + surface digests -> conditional AGENTS pointer

    Does not overwrite user AGENTS.md constitution. Legacy full-rules emission
    remains in generate_single_project_rules_setup / --legacy-rules.
    """
    from .agents_addendum import (
        constitution_body,
        patch_agents_md,
        soft_addendum_body,
    )
    from .constitution import load_constitution
    from .context_model import build_context_model, select_surface_digest_modules
    from .context_renderer import write_context_pack
    from .evidence import EvidenceBundle, collect_evidence
    from .models import ProjectConfig
    from .practices import emit_practices
    from .workflow import collect_workflow

    project_root = project_root.resolve()
    package_base = base_path or Path(__file__).resolve().parent
    budget = TokenBudget(cap=global_budget)

    print("Collecting multi-stack evidence...")
    evidence: EvidenceBundle = collect_evidence(project_root)
    langs = ", ".join(evidence.languages) if evidence.languages else "(none)"
    print(f"  Languages: {langs}")
    print(f"  Surfaces: {', '.join(evidence.surfaces) or '(none)'}")

    constitution = load_constitution(project_root)
    if constitution.exists:
        print(f"  Constitution: AGENTS.md ({len(constitution.covered_topics)} topics covered)")
    else:
        print("  Constitution: missing (will create minimal AGENTS.md stub + addendum)")

    pre_constitution = constitution.body if constitution.exists else ""

    primary = evidence.languages[0] if evidence.languages else "unknown"
    all_fws: List[str] = []
    for fws in evidence.frameworks_by_language.values():
        for fw in fws:
            if fw not in all_fws:
                all_fws.append(fw)

    config = ProjectConfig(
        description=constitution.title or project_root.name,
        is_monorepo=len(evidence.languages) > 1 or len(evidence.top_packages) > 3,
        primary_language=primary,
        frameworks=all_fws,
        project_root=project_root,
    )

    scan_ctx: Optional[ScanContext] = None
    if enable_ast:
        try:
            from .scanner import scan_project
            print("Scanning project (AST skeletons)...")
            scan_ctx = scan_project(
                project_root, config, extract_signatures=True
            )
        except Exception as exc:
            print(f"  (scan skipped: {exc})")

    repo_map_digest = ""
    graph_result: Optional[GraphBuildResult] = None
    graph_written = False
    if enable_ast and enable_graph:
        print("Building DKB / Graph RAG (ranking)...")
        if write_graph and not dry_run:
            repo_map_digest, graph_result = build_repo_map(
                project_root, scan_ctx,
                token_budget=graph_token_budget,
                budget=budget,
                write_artifacts=True,
            )
            graph_written = bool(repo_map_digest) or (
                project_root / ".ai-context" / "graph" / "graph.json"
            ).is_file()
            if graph_written:
                print("  Wrote .ai-context/graph/graph.json + repo-map.md")
        else:
            skeletons = _collect_skeletons_from_scan(scan_ctx)
            if not skeletons:
                skeletons = _collect_skeletons_from_walk(project_root)
            if skeletons:
                graph_result = build_graph(project_root, skeletons)
                repo_map_digest = render_repo_map(
                    graph_result, token_budget=graph_token_budget
                )
            if write_graph and dry_run:
                print("  (dry-run) would write .ai-context/graph/")
            else:
                print("  Graph sidecars skipped (pass --write-graph to emit)")

    # Optional AI folder summaries — importance-ranked, capped for speed
    if use_ai and ai_provider != "none" and scan_ctx is not None:
        try:
            from .ai_summary import generate_ai_folder_summary
            per_file = _build_folder_importance_index(graph_result)
            candidates = [
                f for f in scan_ctx.flat
                if getattr(f, "skeletons", None)
            ]
            limit = max(0, int(ai_max_folders))
            chosen = select_ai_folders(
                candidates,
                list(evidence.surfaces or []),
                limit=limit,
                per_file_scores=per_file,
            )
            print(
                f"Enriching folder overviews with AI "
                f"({len(chosen)}/{len(candidates)} folders, "
                f"--ai-max-folders={limit}, surface-balanced)..."
            )
            for folder in chosen:
                try:
                    generate_ai_folder_summary(
                        folder, project_root, config,
                        ai_provider=ai_provider,
                        ai_model=ai_model,
                        openai_key=openai_key,
                        anthropic_key=anthropic_key,
                        google_key=google_key,
                    )
                except Exception as exc:
                    logger.warning("AI summary failed for %s: %s", folder.path, exc)
        except Exception as exc:
            logger.warning("AI summary unavailable: %s", exc)

    all_modules, folder_fws = collect_module_refs(
        scan_ctx, evidence,
        primary_language_fallback=primary,
        graph_result=graph_result,
    )
    digest_modules = select_surface_digest_modules(
        all_modules, evidence.surfaces, limit=12
    )

    practice_refs: List = []
    if emit_practices_flag:
        print("Emitting language/framework practices...")
        practice_refs = emit_practices(
            project_root,
            evidence,
            base_path=package_base,
            dry_run=dry_run,
            budget=budget,
        )
        print(f"  Practices: {len(practice_refs)}")
    else:
        print("Practices skipped (pass --practices to emit)")

    print("Gleaning workflow / conventions from git + configs...")
    workflow = collect_workflow(
        project_root,
        constitution=constitution,
        languages=evidence.languages,
    )
    print(f"  Workflow facts: {len(workflow.facts)}")

    ctx = build_context_model(
        project_name=project_root.name,
        evidence=evidence,
        constitution=constitution,
        modules=all_modules,
        repo_map_digest=repo_map_digest,
        practices=practice_refs,
        graph_written=graph_written,
        workflow=workflow,
    )

    module_bodies: Dict[str, str] = {}
    if write_modules and digest_modules:
        module_bodies = emit_module_context_files(
            project_root, scan_ctx, digest_modules,
            budget=budget,
            graph_result=None,  # digests omit call-flow
            full=False,
            charge_budget=True,
        )
    elif not write_modules:
        print("Surface digests skipped (--no-modules)")

    print("Writing .ai-context pack...")
    planned = write_context_pack(
        project_root, ctx,
        module_bodies=module_bodies,
        dry_run=dry_run,
        budget=budget,
        charge_module_budget=False,  # already charged in emit
    )
    for key, path in planned.items():
        if key.startswith("module:"):
            continue
        print(f"  {'Would write' if dry_run else 'Wrote'} {path.relative_to(project_root)}")
    mod_count = sum(1 for k in planned if k.startswith("module:"))
    print(f"  Surface digests: {mod_count}")

    if emit_cursor_rules and scan_ctx is not None and not dry_run:
        print("Emitting optional Cursor Tier-2 .mdc rules...")
        paths = emit_tier2_folder_files(
            project_root, scan_ctx, config,
            budget=budget,
            graph_result=graph_result,
            use_ai=False,
            folder_frameworks=folder_fws,
        )
        for p in paths:
            print(f"  ✓ {p.relative_to(project_root)}")

    agents_patched = False
    new_agents = constitution.raw if constitution.exists else ""
    created_stub = False
    if ctx.additive or not constitution.exists:
        print("Patching AGENTS.md addendum (constitution preserved)...")
        addendum = soft_addendum_body(
            has_practices=bool(practice_refs),
            has_graph=graph_written,
        )
        new_agents, created_stub, _ = patch_agents_md(
            project_root,
            dry_run=dry_run,
            addendum_body=addendum,
        )
        agents_patched = True
        if dry_run:
            print("  (dry-run) addendum:")
            print(new_agents[new_agents.find("<!-- codebase-context:begin -->"):][:500])
        elif created_stub:
            print("  Created minimal AGENTS.md stub + context pointer")
            print("  Tip: run Sync install-repo-identity.sh for a full constitution")
        else:
            print("  Updated context pointer addendum only")
    else:
        # Rich AGENTS: rewrite stale What/How/Why pointer to edit-pack affordance
        # (still only touches the delimited addendum block).
        print(
            "AGENTS.md pointer: rewriting to edit-pack affordance "
            "(constitution already covers purpose/architecture/commands)"
        )
        addendum = soft_addendum_body(
            has_practices=bool(practice_refs),
            has_graph=graph_written,
            edit_pack_focused=True,
        )
        if constitution.exists:
            agents_path = project_root / "AGENTS.md"
            original = agents_path.read_text(encoding="utf-8")
            # Only rewrite if an addendum already exists or we want a thin pointer
            from .agents_addendum import BEGIN_MARKER
            if BEGIN_MARKER in original:
                new_agents, created_stub, _ = patch_agents_md(
                    project_root,
                    dry_run=dry_run,
                    addendum_body=addendum,
                )
                agents_patched = True
                if dry_run:
                    print("  (dry-run) would rewrite addendum to edit-pack pointer")
                else:
                    print("  Updated context pointer to `context for` affordance")
            else:
                new_agents = original
                print("  No existing addendum; left AGENTS.md untouched")
        else:
            new_agents = ""

    post_constitution = constitution_body(new_agents) if new_agents else ""
    if pre_constitution and agents_patched and not created_stub and not dry_run:
        if post_constitution.rstrip() != pre_constitution.rstrip():
            logger.warning(
                "AGENTS.md constitution body changed unexpectedly; "
                "please report this as a bug"
            )

    if not dry_run:
        report_dir = project_root / ".ai-context"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "budget-report.md").write_text(
            budget.report_markdown(), encoding="utf-8"
        )

    print(f"\n{budget.summary()}")
    return {
        "project_root": project_root,
        "languages": evidence.languages,
        "modules": mod_count,
        "modules_scanned": len(all_modules),
        "practices": len(practice_refs),
        "planned": planned,
        "created_agents_stub": created_stub,
        "agents_patched": agents_patched,
        "additive": ctx.additive,
        "pre_constitution": pre_constitution,
        "post_constitution": post_constitution if not dry_run else constitution_body(new_agents),
        "agents_text": new_agents,
        "budget": budget,
        "context": ctx,
        "dry_run": dry_run,
        "graph_written": graph_written,
        "workflow_facts": len(workflow.facts),
    }


def show_folder_context(
    project_root: Path,
    folder_rel: str,
    *,
    full: bool = False,
    enable_ast: bool = True,
    enable_graph: bool = True,
) -> str:
    """
    On-demand digest for a folder (prints; does not rewrite the pack).

    `full=True` includes skeleton + call-flow when graph/AST available.
    """
    from .context_model import ModuleRef
    from .evidence import collect_evidence, frameworks_for_path
    from .models import ProjectConfig

    project_root = project_root.resolve()
    rel = folder_rel.replace("\\", "/").strip().strip("/")
    evidence = collect_evidence(project_root)
    primary = evidence.languages[0] if evidence.languages else "unknown"
    config = ProjectConfig(
        description=project_root.name,
        is_monorepo=len(evidence.languages) > 1,
        primary_language=primary,
        frameworks=[],
        project_root=project_root,
    )

    scan_ctx: Optional[ScanContext] = None
    if enable_ast:
        try:
            from .scanner import scan_project
            scan_ctx = scan_project(project_root, config, extract_signatures=True)
        except Exception as exc:
            logger.warning("scan failed: %s", exc)

    graph_result: Optional[GraphBuildResult] = None
    if enable_ast and enable_graph and full and scan_ctx is not None:
        skeletons = _collect_skeletons_from_scan(scan_ctx)
        if skeletons:
            graph_result = build_graph(project_root, skeletons)

    folder = None
    if scan_ctx and getattr(scan_ctx, "flat", None):
        for f in scan_ctx.flat:
            frel = (f.path or f.name or "").replace("\\", "/").strip("/")
            if frel == rel:
                folder = f
                break

    lang = primary
    purpose = ""
    overview = ""
    file_count = 0
    if folder is not None:
        purpose = folder.purpose or ""
        overview = (getattr(folder, "ai_folder_summary", None) or "").strip()
        file_count = folder.file_count or len(folder.skeletons or [])
        file_paths = [s.file_path for s in folder.skeletons] if folder.skeletons else []
        lang = detect_folder_language(file_paths, fallback=primary) or primary

    fws = frameworks_for_path(evidence, rel, lang or None)
    mod = ModuleRef(
        slug=_slug_for_folder(rel),
        rel_path=rel,
        language=lang or "mixed",
        frameworks=fws,
        purpose=purpose,
        file_count=file_count,
        overview=overview,
    )
    bodies = emit_module_context_files(
        project_root,
        scan_ctx,
        [mod],
        budget=None,
        graph_result=graph_result if full else None,
        full=full,
        charge_budget=False,
    )
    return bodies.get(mod.slug) or f"# Module: `{rel}/`\n\n_(no scan data for this path)_\n"
