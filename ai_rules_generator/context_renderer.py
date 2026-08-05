"""
Write `.ai-context/` complementary pack: CODEBASE.md, manifest.json, modules/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .context_model import CodebaseContext, ModuleRef, purpose_for_display
from .token_budget import TokenBudget


AI_CONTEXT_DIR = ".ai-context"
CODEBASE_FILENAME = "CODEBASE.md"
MANIFEST_FILENAME = "manifest.json"
MODULES_DIR = "modules"
GRAPH_DIR = "graph"

# Soft always-on budget (~800 tokens ≈ 3200 chars).
DEFAULT_CODEBASE_MAX_CHARS = 3200

# Section heading used for surface digest links (truncation target).
SURFACE_DIGESTS_MARKER = "## Surface digests"


def ai_context_root(project_root: Path) -> Path:
    return project_root / AI_CONTEXT_DIR


def _truncate_codebase(body: str, max_chars: int = DEFAULT_CODEBASE_MAX_CHARS) -> str:
    """Soft-cap CODEBASE.md: keep What/How/Why, shed Surface digests first,
    always try to keep Sidecars."""
    if len(body) <= max_chars:
        return body

    marker = SURFACE_DIGESTS_MARKER
    # Back-compat with older Module index heading
    if marker not in body and "## Module index" in body:
        marker = "## Module index"
    sidecar_marker = "## Sidecars"
    if marker not in body:
        return body[: max_chars - 80].rstrip() + (
            "\n\n_(CODEBASE.md truncated for always-on budget.)_\n"
        )

    head, _, after_index = body.partition(marker)
    sidecars = ""
    index_blob = after_index
    if sidecar_marker in after_index:
        index_blob, _, sidecar_rest = after_index.partition(sidecar_marker)
        sidecars = sidecar_marker + sidecar_rest

    index_lines = [
        ln for ln in index_blob.splitlines()
        if ln.startswith("- [") or ln.startswith("- `")
    ]
    omitted_note_lines = [
        ln for ln in index_blob.splitlines()
        if ln.strip().startswith("_(") and "more under" in ln
    ]

    footer_reserve = min(220, max(80, len(sidecars) + 60))
    keep = head.rstrip() + "\n\n" + marker + "\n\n"
    kept = 0
    for ln in index_lines:
        candidate = keep + ln + "\n"
        if len(candidate) + footer_reserve > max_chars:
            break
        keep = candidate
        kept += 1

    omitted = len(index_lines) - kept
    if omitted > 0:
        note = (
            f"\n_({omitted} more digests under `.ai-context/modules/` "
            f"— always-on budget.)_\n"
        )
        if len(keep) + len(note) + footer_reserve <= max_chars:
            keep += note
        elif kept == 0:
            stub = (
                "_(Digests truncated for always-on budget — "
                "`ai-rules-generator context show <path>`.)_\n"
            )
            keep += stub
    elif omitted_note_lines:
        for ln in omitted_note_lines[:1]:
            if len(keep) + len(ln) + footer_reserve + 2 <= max_chars:
                keep += "\n" + ln + "\n"

    if sidecars:
        if len(keep.rstrip() + "\n\n" + sidecars) <= max_chars:
            keep = keep.rstrip() + "\n\n" + sidecars.rstrip() + "\n"
        else:
            sc_lines = sidecars.strip().splitlines()
            sc_keep = sc_lines[0] + "\n"
            for ln in sc_lines[1:]:
                trial = keep.rstrip() + "\n\n" + sc_keep + ln + "\n"
                if len(trial) > max_chars:
                    break
                sc_keep += ln + "\n"
            keep = keep.rstrip() + "\n\n" + sc_keep.rstrip() + "\n"

    if len(keep) > max_chars:
        keep = keep[: max_chars - 80].rstrip() + (
            "\n\n_(CODEBASE.md truncated for always-on budget.)_\n"
        )
    return keep


def render_codebase_md(ctx: CodebaseContext) -> str:
    """Render the canonical complementary CODEBASE.md (lean always-on)."""
    parts: List[str] = []
    parts.append(f"# Codebase context: {ctx.project_name}\n")
    parts.append(
        "> Optional orientation map for any LLM. "
        "Does **not** replace `AGENTS.md` (constitution). "
        "Prefer `AGENTS.md` for purpose, commands, off-limits, and workflow. "
        "For edit-scoped context: "
        "`ai-rules-generator context for <path>`.\n"
    )

    if ctx.thin:
        # Rich AGENTS: entrypoints + conventions only
        parts.append("## How\n")
        parts.append("\n".join(ctx.how_lines) + "\n" if ctx.how_lines else "_\n")
        if ctx.workflow_lines:
            parts.append("## Conventions\n")
            parts.append("\n".join(ctx.workflow_lines) + "\n")
        if ctx.practices:
            parts.append("## Practices for this repo\n")
            parts.append(
                "Language/framework guidance from bundled awesome-cursorrules "
                "(read on demand):\n"
            )
            for pr in ctx.practices:
                parts.append(f"- [`{pr.name}`]({pr.path}) — {pr.kind}")
            parts.append("")
        sidecar_lines: List[str] = [
            "- Edit packs: `ai-rules-generator context for <path>`",
            "- Machine manifest: `.ai-context/manifest.json`",
        ]
        if ctx.graph_written:
            sidecar_lines.insert(
                1,
                "- Graph / repo map: `.ai-context/graph/repo-map.md`",
            )
        if ctx.practices:
            sidecar_lines.append("- Practices: `.ai-context/practices/`")
        parts.append("## Sidecars\n")
        parts.append("\n".join(sidecar_lines) + "\n")
        body = "\n".join(parts).rstrip() + "\n"
        return _truncate_codebase(body)

    parts.append("## What\n")
    parts.append("\n".join(ctx.what_lines) + "\n")

    parts.append("## How\n")
    parts.append("\n".join(ctx.how_lines) + "\n")

    if ctx.workflow_lines:
        parts.append("## Conventions\n")
        parts.append("\n".join(ctx.workflow_lines) + "\n")

    parts.append("## Why\n")
    parts.append("\n".join(ctx.why_lines) + "\n")

    if ctx.unknowns:
        parts.append("## Gaps\n")
        parts.append("\n".join(f"- {u}" for u in ctx.unknowns) + "\n")

    if ctx.covered_markdown:
        parts.append("## Already covered in AGENTS.md\n")
        parts.append(ctx.covered_markdown.rstrip() + "\n")

    if ctx.practices:
        parts.append("## Practices for this repo\n")
        parts.append(
            "Language/framework guidance from bundled awesome-cursorrules "
            "(read on demand):\n"
        )
        for pr in ctx.practices:
            parts.append(f"- [`{pr.name}`]({pr.path}) — {pr.kind}")
        parts.append("")

    digests = ctx.index_modules
    if digests:
        parts.append(f"{SURFACE_DIGESTS_MARKER}\n")
        for mod in digests:
            slug = mod.slug
            label = mod.rel_path or "."
            lang = mod.language or "mixed"
            purpose = purpose_for_display(mod)
            line = f"- [`{label}/`](modules/{slug}.md) — {lang}"
            if mod.frameworks:
                line += f" ({', '.join(mod.frameworks)})"
            if purpose and len(purpose) < 100:
                line += f" — {purpose}"
            parts.append(line)
        parts.append("")
        parts.append(
            "_Edit neighborhoods: `ai-rules-generator context for <path>`. "
            "Folder digests: `context show <path>`._\n"
        )

    sidecar_lines = [
        "- Edit packs: `ai-rules-generator context for <path>`",
        "- Machine manifest: `.ai-context/manifest.json`",
    ]
    if ctx.graph_written:
        sidecar_lines.insert(
            1,
            "- Graph / repo map: `.ai-context/graph/repo-map.md`",
        )
    if ctx.practices:
        sidecar_lines.append("- Practices: `.ai-context/practices/`")
    parts.append("## Sidecars\n")
    parts.append("\n".join(sidecar_lines) + "\n")

    body = "\n".join(parts).rstrip() + "\n"
    return _truncate_codebase(body)


def render_module_md(
    mod: ModuleRef,
    *,
    overview: str = "",
    skeleton: str = "",
    top_symbols: str = "",
    call_flow: str = "",
    used_by: str = "",
) -> str:
    """Render a surface digest or on-demand module map."""
    fw = ", ".join(mod.frameworks) if mod.frameworks else "(none detected for this folder)"
    display_purpose = purpose_for_display(
        ModuleRef(
            slug=mod.slug,
            rel_path=mod.rel_path,
            language=mod.language,
            frameworks=mod.frameworks,
            purpose=mod.purpose,
            overview=overview or mod.overview,
        )
    ) or mod.purpose or "(inferred)"
    parts = [
        f"# Module: `{mod.rel_path or '.'}/`\n",
        f"- Language: {mod.language or 'mixed'}",
        f"- Frameworks (folder-local): {fw}",
        f"- Purpose: {display_purpose}",
        f"- Files (approx): {mod.file_count}",
        "",
    ]
    if overview:
        parts.append("## Overview\n")
        parts.append(overview.rstrip() + "\n")
    if top_symbols:
        parts.append("## Top symbols\n")
        parts.append(top_symbols.rstrip() + "\n")
    elif skeleton:
        parts.append("## Skeleton\n")
        parts.append(skeleton.rstrip() + "\n")
    if call_flow:
        parts.append("## Call flow\n")
        parts.append(call_flow.rstrip() + "\n")
    if used_by:
        parts.append("## Used by\n")
        parts.append(used_by.rstrip() + "\n")
    parts.append(
        "\n---\nComplementary context only. Constitution: repo-root `AGENTS.md`.\n"
    )
    return "\n".join(parts)


def build_manifest(
    ctx: CodebaseContext,
    *,
    module_paths: Sequence[str],
    practice_paths: Optional[Sequence[str]] = None,
    generator_version: str = "1.0.0",
) -> Dict:
    files: Dict = {
        "codebase": f"{AI_CONTEXT_DIR}/{CODEBASE_FILENAME}",
        "modules": list(module_paths),
        "practices": list(practice_paths or [p.path for p in ctx.practices]),
    }
    if ctx.graph_written:
        files["graph"] = f"{AI_CONTEXT_DIR}/{GRAPH_DIR}/"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "ai-rules-generator",
        "generator_version": generator_version,
        "project_name": ctx.project_name,
        "languages": ctx.languages,
        "frameworks_by_language": ctx.frameworks_by_language,
        "constitution_present": ctx.constitution_exists,
        "modules": [
            {
                "slug": m.slug,
                "path": m.rel_path,
                "language": m.language,
                "frameworks": m.frameworks,
            }
            for m in ctx.index_modules
        ],
        "practices": [
            {"name": p.name, "path": p.path, "kind": p.kind}
            for p in ctx.practices
        ],
        "files": files,
    }


def write_context_pack(
    project_root: Path,
    ctx: CodebaseContext,
    *,
    module_bodies: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    budget: Optional[TokenBudget] = None,
    charge_module_budget: bool = False,
) -> Dict[str, Path]:
    """
    Write `.ai-context/CODEBASE.md`, surface digests, and manifest.json.

    Practices are written by `practices.emit_practices` beforehand when
    enabled. Only modules present in `module_bodies` (or `ctx.index_modules`
    with a fallback body) are written — not every scanned folder.
    """
    root = ai_context_root(project_root)
    modules_dir = root / MODULES_DIR
    planned: Dict[str, Path] = {
        "codebase": root / CODEBASE_FILENAME,
        "manifest": root / MANIFEST_FILENAME,
    }

    codebase_body = render_codebase_md(ctx)
    if budget is not None:
        outcome = budget.fit_or_truncate(
            codebase_body, kind="codebase_md", folder=None
        )
        if outcome is not None:
            codebase_body, _ = outcome

    module_bodies = module_bodies or {}
    module_rel_paths: List[str] = []

    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
        if module_bodies or ctx.index_modules:
            modules_dir.mkdir(parents=True, exist_ok=True)
        planned["codebase"].write_text(codebase_body, encoding="utf-8")

    # Write digests for index modules that have bodies (surface roots).
    write_slugs = set(module_bodies.keys()) | {
        m.slug for m in ctx.index_modules if m.slug in module_bodies
    }
    # Prefer explicit bodies; skip modules without a prepared digest.
    for mod in ctx.index_modules:
        if mod.slug not in module_bodies:
            continue
        path = modules_dir / f"{mod.slug}.md"
        planned[f"module:{mod.slug}"] = path
        rel = f"{AI_CONTEXT_DIR}/{MODULES_DIR}/{mod.slug}.md"
        module_rel_paths.append(rel)
        body = module_bodies[mod.slug]
        if charge_module_budget and budget is not None:
            outcome = budget.fit_or_truncate(
                body, kind="module_map", folder=mod.slug
            )
            if outcome is None:
                continue
            body, _ = outcome
        if not dry_run:
            path.write_text(body, encoding="utf-8")

    # Also write any extra bodies keyed in module_bodies (e.g. context show --write)
    for slug, body in module_bodies.items():
        if slug in write_slugs and f"module:{slug}" in planned:
            continue
        if slug not in {m.slug for m in ctx.index_modules}:
            continue

    manifest = build_manifest(
        ctx,
        module_paths=module_rel_paths,
        practice_paths=(
            [f".ai-context/{p.path}" for p in ctx.practices]
            if ctx.practices
            else []
        ),
    )
    if not dry_run:
        planned["manifest"].write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    return planned
