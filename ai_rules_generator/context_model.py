"""
Typed What / How / Why model for complementary codebase context.

CODEBASE.md is intentionally lean: surfaces + entrypoints + pointers.
Surface digests live in `.ai-context/modules/` (roots only by default).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from .constitution import Constitution, covered_topics_markdown
from .evidence import EvidenceBundle
from .workflow import WorkflowBundle, workflow_lines_for_codebase


# Heuristic labels that must not appear in always-on CODEBASE How.
GENERIC_PURPOSES: Set[str] = {
    "project files",
    "scripts",
    "batch database operations",
    "configuration management",
    "parsing utilities",
    "test files",
    "inferred from contents",
    "source file",
    "Go executable entry point",
    "Go application",
    "typescript project",
    "javascript project",
}

# Soft cap for How / digest one-liners (~800-token CODEBASE budget).
DISPLAY_PURPOSE_MAX = 120


@dataclass
class ModuleRef:
    slug: str
    rel_path: str
    language: str
    frameworks: List[str]
    purpose: str
    file_count: int = 0
    importance: float = 0.0
    overview: str = ""


@dataclass
class PracticeRef:
    name: str
    path: str  # relative e.g. practices/typescript.md
    kind: str  # language | framework | universal


@dataclass
class CodebaseContext:
    """Delta-aware complementary context for a repository."""

    project_name: str
    what_lines: List[str] = field(default_factory=list)
    how_lines: List[str] = field(default_factory=list)
    why_lines: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    covered_markdown: str = ""
    modules: List[ModuleRef] = field(default_factory=list)
    index_modules: List[ModuleRef] = field(default_factory=list)
    practices: List[PracticeRef] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    frameworks_by_language: Dict[str, List[str]] = field(default_factory=dict)
    repo_map_digest: str = ""
    constitution_exists: bool = False
    graph_written: bool = False
    additive: bool = True
    thin: bool = False  # rich AGENTS: skip What/Why essays
    workflow_lines: List[str] = field(default_factory=list)


def _truncate_one_liner(text: str, max_chars: int = DISPLAY_PURPOSE_MAX) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Prefer sentence boundary
    cut = text[:max_chars]
    for sep in (". ", "; ", " — ", " - "):
        idx = cut.rfind(sep)
        if idx >= max_chars // 2:
            return cut[: idx + 1].rstrip()
    # Prefer word boundary
    idx = cut.rfind(" ")
    if idx >= max_chars // 2:
        return cut[:idx].rstrip() + "…"
    return cut.rstrip() + "…"


def purpose_for_display(mod: ModuleRef, *, max_chars: int = DISPLAY_PURPOSE_MAX) -> str:
    """Prefer AI overview sentence; suppress generic heuristic labels."""
    if mod.overview:
        first = mod.overview.strip().split("\n")[0].strip()
        return _truncate_one_liner(first, max_chars)
    p = (mod.purpose or "").strip()
    if not p or p.lower() in GENERIC_PURPOSES:
        return ""
    if p.lower() in {g.lower() for g in GENERIC_PURPOSES}:
        return ""
    return _truncate_one_liner(p, max_chars)


def _surface_of(rel_path: str, surfaces: Sequence[str]) -> str:
    rel = (rel_path or "").replace("\\", "/").strip("/")
    if not rel:
        return "root"
    top = rel.split("/")[0]
    if top in surfaces:
        return top
    return top or "root"


def select_surface_digest_modules(
    modules: Sequence[ModuleRef],
    surfaces: Sequence[str],
    *,
    limit: int = 12,
) -> List[ModuleRef]:
    """One module per surface root (e.g. backend/, frontend/); skip root/."""
    by_path = {(m.rel_path or "").strip("/"): m for m in modules}
    selected: List[ModuleRef] = []
    seen: Set[str] = set()
    for surf in surfaces:
        if not surf or surf == "root":
            continue
        mod = by_path.get(surf)
        if mod is None:
            # Fallback: shallowest module under this surface
            candidates = [
                m for m in modules
                if _surface_of(m.rel_path, surfaces) == surf
            ]
            if not candidates:
                continue
            candidates.sort(
                key=lambda m: (
                    (m.rel_path or "").count("/"),
                    -m.importance,
                    m.rel_path,
                )
            )
            mod = candidates[0]
        if mod.slug in seen:
            continue
        seen.add(mod.slug)
        selected.append(mod)
        if len(selected) >= limit:
            break
    return selected


def context_is_additive(
    constitution: Constitution,
    ctx: CodebaseContext,
    evidence: EvidenceBundle,
) -> bool:
    """
    Whether CODEBASE adds orientation worth an AGENTS.md pointer.

    Rich constitutions (purpose + architecture + commands) with no gaps
    skip a new pointer. Thin AGENTS or missing constitution still get one.
    """
    if not constitution.exists:
        return True
    if ctx.unknowns:
        return True
    rich = all(
        constitution.covers(t)
        for t in ("purpose", "architecture", "commands")
    )
    if rich:
        return False
    if evidence.surfaces or any(
        ep.kind != "ci" for ep in evidence.primary_entrypoints
    ):
        return True
    return bool(ctx.how_lines or ctx.what_lines)


def build_context_model(
    *,
    project_name: str,
    evidence: EvidenceBundle,
    constitution: Constitution,
    modules: List[ModuleRef],
    repo_map_digest: str = "",
    practices: Optional[List[PracticeRef]] = None,
    graph_written: bool = False,
    workflow: Optional[WorkflowBundle] = None,
) -> CodebaseContext:
    """Assemble lean What/How/Why lines with delta filtering against AGENTS.md."""
    practices = practices or []
    surfaces = evidence.surfaces
    # How + digests: surface roots only (not nested api/database spam)
    surface_modules = select_surface_digest_modules(modules, surfaces, limit=12)

    ctx = CodebaseContext(
        project_name=project_name,
        languages=evidence.languages,
        frameworks_by_language=evidence.frameworks_by_language,
        modules=modules,
        index_modules=surface_modules,
        practices=practices,
        repo_map_digest=repo_map_digest,
        constitution_exists=constitution.exists,
        covered_markdown=covered_topics_markdown(constitution),
        unknowns=list(evidence.unknowns),
        graph_written=graph_written,
    )

    covers_purpose = constitution.covers("purpose")
    covers_arch = constitution.covers("architecture")
    covers_stack = constitution.covers("stack")
    covers_deploy = constitution.covers("deploy")
    covers_access = constitution.covers("access")
    covers_commands = constitution.covers("commands")
    covers_workflow = constitution.covers("workflow")
    covers_type_safety = constitution.covers("type_safety")

    # ----- WHAT -----
    if constitution.exists and constitution.purpose_excerpt and covers_purpose:
        ctx.what_lines.append(
            f"Purpose is defined in `AGENTS.md` "
            f"(excerpt: {constitution.purpose_excerpt[:200]}"
            f"{'…' if len(constitution.purpose_excerpt) > 200 else ''})."
        )
    elif evidence.readme_excerpt:
        ctx.what_lines.append(
            f"From `{evidence.readme_path}`: {evidence.readme_excerpt}"
        )
    elif constitution.exists and constitution.purpose_excerpt:
        ctx.what_lines.append(constitution.purpose_excerpt[:400])
    else:
        ctx.what_lines.append(
            f"Repository `{project_name}` — purpose not found in README or "
            f"`AGENTS.md`; see Gaps."
        )
        ctx.unknowns.append("Human purpose statement missing (README / AGENTS.md).")

    if evidence.languages:
        stack_bits = []
        for lang in evidence.languages:
            fws = evidence.frameworks_by_language.get(lang) or []
            if fws:
                stack_bits.append(f"{lang} ({', '.join(fws)})")
            else:
                stack_bits.append(lang)
        line = "Detected stacks: " + ", ".join(stack_bits) + "."
        if covers_stack:
            ctx.what_lines.append("Stack details complement `AGENTS.md`: " + line)
        else:
            ctx.what_lines.append(line)

    if surfaces:
        pkgs = ", ".join(f"`{p}/`" for p in surfaces[:12])
        ctx.what_lines.append(f"Top-level surfaces: {pkgs}.")
    elif evidence.top_packages:
        pkgs = ", ".join(f"`{p}/`" for p in evidence.top_packages[:12])
        ctx.what_lines.append(f"Top-level packages / dirs: {pkgs}.")

    if evidence.godot_version:
        ctx.what_lines.append(
            f"Godot project (version feature: {evidence.godot_version})."
        )

    # ----- HOW (lean) -----
    # Prefer product/control entrypoints; hide demoted util mains from How
    # unless they would leave the list empty.
    non_ci = [ep for ep in evidence.primary_entrypoints if ep.kind != "ci"]
    primary = [
        ep for ep in non_ci
        if not (ep.kind == "go_main" and "util" in (ep.note or "").lower())
    ][:5]
    if not primary:
        primary = non_ci[:5]
    ci_eps = [ep for ep in evidence.primary_entrypoints if ep.kind == "ci"][:1]
    show_eps = primary + (ci_eps if not primary else [])

    if show_eps:
        ctx.how_lines.append("Entrypoints / control surfaces:")
        for ep in show_eps:
            note = f" — {ep.note}" if ep.note else ""
            ctx.how_lines.append(f"- `{ep.path}` ({ep.kind}){note}")
    elif not covers_arch:
        ctx.how_lines.append(
            "No strong entrypoints detected from manifests; "
            "inspect top-level surfaces or run "
            "`ai-rules-generator context show <path>`."
        )

    if surface_modules:
        ctx.how_lines.append("Surfaces:")
        for mod in surface_modules:
            if (mod.rel_path or "") in ("", "."):
                continue
            fw = f" / {', '.join(mod.frameworks)}" if mod.frameworks else ""
            purpose = purpose_for_display(mod)
            if purpose:
                ctx.how_lines.append(
                    f"- `{mod.rel_path}/` — {mod.language or 'mixed'}{fw}; "
                    f"{purpose}"
                )
            else:
                ctx.how_lines.append(
                    f"- `{mod.rel_path}/` — {mod.language or 'mixed'}{fw}"
                )
        ctx.how_lines.append(
            "Deeper folders: `ai-rules-generator context show <path>` "
            "(optional digests under `.ai-context/modules/`)."
        )

    if covers_commands:
        ctx.how_lines.append(
            "Build/test/run commands: use `AGENTS.md` (not duplicated here)."
        )

    # ----- CONVENTIONS / WORKFLOW (evidenced) -----
    if workflow is not None:
        # If AGENTS already documents workflow + type safety heavily, still
        # keep git/config gleanings that AGENTS may not restate — but skip
        # AGENTS-sourced duplicates when those topics are covered.
        facts = list(workflow.facts)
        if covers_workflow:
            facts = [f for f in facts if f.source != "AGENTS.md" or f.category not in (
                "branches", "commits", "style",
            )]
        if covers_type_safety:
            facts = [f for f in facts if f.category != "type_safety" or f.source != "AGENTS.md"]
        slim = WorkflowBundle(facts=facts, unknowns=[])
        # Workflow "unknowns" are observational (e.g. no git) — do not treat
        # them as Gaps that force an AGENTS.md pointer.
        ctx.workflow_lines = workflow_lines_for_codebase(slim, max_bullets=10)

    if not ctx.how_lines:
        ctx.how_lines.append(
            "How this codebase works could not be inferred automatically."
        )
        ctx.unknowns.append("Need human architecture notes in AGENTS.md.")

    # ----- WHY -----
    for fact, source in evidence.why_facts:
        low = fact.lower()
        if covers_access and any(
            k in low for k in ("tailscale", "ssh", "magicdns")
        ):
            continue
        if covers_deploy and "deploy" in low and "compose" not in low:
            continue
        # Skip README purpose echo when constitution already has purpose
        if covers_purpose and "readme describes project purpose" in low:
            continue
        ctx.why_lines.append(f"- {fact} _(source: `{source}`)_")

    for path, label in evidence.constraint_docs:
        ctx.why_lines.append(
            f"- {label}: see `{path}` (do not restate; follow the doc)."
        )

    if constitution.exists and covers_access:
        ctx.why_lines.append(
            "- Access / networking constraints: see `AGENTS.md` (not restated)."
        )
    if constitution.exists and covers_deploy:
        ctx.why_lines.append(
            "- Deploy targets: see `AGENTS.md` (not restated)."
        )

    if not ctx.why_lines:
        ctx.why_lines.append(
            "- No evidenced constraints beyond stack detection; "
            "record trade-offs in `AGENTS.md` when known."
        )
        ctx.unknowns.append(
            "Why/constraints mostly undocumented — add to AGENTS.md when sure."
        )

    # Cap Why noise
    if len(ctx.why_lines) > 10:
        ctx.why_lines = ctx.why_lines[:10]

    seen_u: set = set()
    uniq = []
    for u in ctx.unknowns:
        if u not in seen_u:
            seen_u.add(u)
            uniq.append(u)
    ctx.unknowns = uniq
    ctx.additive = context_is_additive(constitution, ctx, evidence)

    # Thin pack when AGENTS already covers purpose/architecture/commands:
    # keep entrypoints + conventions; drop What paraphrase, Why trivia,
    # and "Already covered" laundry lists from always-on CODEBASE.
    rich = all(
        constitution.covers(t)
        for t in ("purpose", "architecture", "commands")
    ) if constitution.exists else False
    if rich and not ctx.additive:
        ctx.thin = True
        ctx.what_lines = []
        if evidence.languages:
            stack_bits = []
            for lang in evidence.languages[:6]:
                fws = evidence.frameworks_by_language.get(lang) or []
                stack_bits.append(
                    f"{lang} ({', '.join(fws)})" if fws else lang
                )
            ctx.how_lines.insert(
                0,
                "Stacks: " + ", ".join(stack_bits) + ". "
                "Purpose/architecture/commands: see `AGENTS.md`.",
            )
        # Keep only entrypoints + surface names + edit-pack pointer
        slim_how: List[str] = []
        for line in ctx.how_lines:
            if line.startswith("Build/test/run"):
                continue
            slim_how.append(line)
        # Ensure edit-pack affordance
        edit_hint = (
            "Edit neighborhoods: `ai-rules-generator context for <path>` "
            "(ancestors + blast radius + matched AGENTS slices)."
        )
        if not any("context for" in ln for ln in slim_how):
            slim_how.append(edit_hint)
        # Soften show-only deeper-folder line to mention `for`
        slim_how = [
            ln.replace(
                "`ai-rules-generator context show <path>`",
                "`ai-rules-generator context for <path>` "
                "(or `context show <folder>`)",
            )
            if "Deeper folders:" in ln
            else ln
            for ln in slim_how
        ]
        ctx.how_lines = slim_how
        ctx.why_lines = []
        ctx.unknowns = []
        ctx.covered_markdown = ""
        ctx.index_modules = []  # no truncated digests section

    return ctx
