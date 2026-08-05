"""
Functions for creating shared AI rules around the AGENTS.md hub model.

This module is the *orchestrator* for shared-rule emission.  It:

  - Writes the canonical always-on `AGENTS.md` (identity, Stop Rules, dev
    commands, off-limits, repo-map digest, pointer index, maintenance).
  - Drops large coding-principles / framework deep dives into Tier-3
    `.ai-rules/skills/` so they don't pollute every prompt.
  - Keeps a legacy `project-rules.md` index for tools that still read it.

The AGENTS.md rendering logic lives in `agents_md.py`; per-tool entry points
(symlinks/imports) are emitted by `generators_multi_tool.py` via `linker.py`.
"""

from pathlib import Path
from typing import Any, List, Optional

from .agents_md import (
    MAINTAINING_CONTEXT_SKILL,
    build_dev_commands,
    build_key_file_index,
    render_agents_md,
)
from .ai_generator import generate_ai_rules
from .config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from .file_utils import extract_rule_content, read_general_guidelines, read_rule_file
from .generators import (
    generate_general_coding_principles,
    generate_project_context,
    generate_template_single_project_rules,
)
from .models import ProjectConfig
from .rule_renderer import (
    Tier,
    TierFile,
    render_tier3_skill,
    render_tier_index,
    write_tier_files,
)
from .token_budget import TokenBudget


# ---------------------------------------------------------------------------
# AGENTS.md composition
# ---------------------------------------------------------------------------

def _build_agents_md(
    config: ProjectConfig,
    scan_ctx: Optional[Any],
    *,
    repo_map_digest: str = "",
) -> str:
    """Render the canonical AGENTS.md body for this project."""
    return render_agents_md(
        config,
        repo_map_digest=repo_map_digest,
        key_file_index=build_key_file_index(scan_ctx),
        dev_commands=build_dev_commands(config.primary_language),
    )


def _build_tier3_skill_files(
    config: ProjectConfig,
    base_path: Path,
    *,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    google_key: Optional[str] = None,
) -> List[TierFile]:
    """
    Build Tier-3 (skill) files - the lazy-loaded deep dives.

    - `coding-principles.md`   : the historically-large general principles block
    - `language-<lang>.md`     : full language rules (read_rule_file output)
    - `framework-<fw>.md`      : per framework
    - `universal-<rule>.md`    : universal extras (codequality, gitflow, ...)
    - `architecture.md`        : AI-generated rich rules (when AI is available)
    """
    skills: List[TierFile] = []

    skills.append(render_tier3_skill(
        slug="coding-principles",
        title="Coding Principles",
        body=generate_general_coding_principles(),
    ))

    skills.append(render_tier3_skill(
        slug="maintaining-context",
        title="Maintaining Context",
        body=MAINTAINING_CONTEXT_SKILL,
    ))

    lang_key = config.primary_language.lower()
    if lang_key == "js":
        lang_key = "javascript"
    elif lang_key == "ts":
        lang_key = "typescript"

    language_info = LANGUAGE_FRAMEWORK_MAP.get(lang_key, {})
    if language_info.get("rule_file"):
        rule_name = language_info["rule_file"].replace(".mdc", "")
        rule_content = read_rule_file(base_path, rule_name)
        if rule_content:
            skills.append(render_tier3_skill(
                slug=f"language-{lang_key}",
                title=f"{config.primary_language.title()} Deep Dive",
                body=(
                    f"# {config.primary_language.title()} Best Practices\n\n"
                    + extract_rule_content(rule_content)
                ),
            ))

    for fw in config.frameworks:
        rule_content = read_rule_file(base_path, fw.lower())
        if not rule_content:
            continue
        skills.append(render_tier3_skill(
            slug=f"framework-{fw.lower()}",
            title=f"{fw.replace('-', ' ').title()} Deep Dive",
            body=(
                f"# {fw.replace('-', ' ').title()} Best Practices\n\n"
                + extract_rule_content(rule_content)
            ),
        ))

    for u_rule in UNIVERSAL_RULES:
        if u_rule in [f.lower() for f in config.frameworks]:
            continue
        rule_content = read_rule_file(base_path, u_rule)
        if not rule_content:
            continue
        skills.append(render_tier3_skill(
            slug=f"universal-{u_rule}",
            title=f"Universal: {u_rule.replace('-', ' ').title()}",
            body=(
                f"# {u_rule.replace('-', ' ').title()}\n\n"
                + extract_rule_content(rule_content)
            ),
        ))

    if use_ai and ai_provider != "none":
        general_guidelines = read_general_guidelines(base_path)
        project_context = generate_project_context(config)
        ai_body = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=config.primary_language,
            frameworks=config.frameworks,
            base_path=base_path,
            rule_type="single_project",
            format_mdc=False,
            use_ai=True,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
        )
        if ai_body:
            skills.append(render_tier3_skill(
                slug="architecture",
                title="Architecture & AI-Generated Patterns",
                body=ai_body,
            ))

    return skills


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def create_shared_ai_rules_directory(
    project_root: Path,
    config: ProjectConfig,
    base_path: Path,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    *,
    google_key: Optional[str] = None,
    scan_ctx: Optional[Any] = None,
    repo_map_digest: str = "",
    max_tier1_lines: Optional[int] = None,
    budget: Optional[TokenBudget] = None,
) -> Path:
    """
    Create the shared `.ai-rules/` directory and the Tier-1 / Tier-3 files.

    Returns the path to `.ai-rules/`.  Tier-2 (per-folder, glob-scoped) files
    are emitted by the orchestrator after the AST/Graph phases run, since
    they depend on the scanner's FolderInfo + skeletons.

    Parameters
    ----------
    repo_map_digest : str
        Truncated Markdown repo map (from `code_graph.render_repo_map`).
        Passed in by the orchestrator after Phase 4 runs.
    max_tier1_lines : int | None
        Backward-compat per-file Tier-1 cap.  When `budget` is supplied the
        global TokenBudget is the authoritative limit; `max_tier1_lines` is
        only used as a soft layout hint.
    budget : TokenBudget | None
        Shared global token budget.  Tier-1 files are force-spent (they
        always survive).  Tier-3 skills + legacy artifacts are emitted via
        priority shedding.
    """
    ai_rules_dir = project_root / ".ai-rules"
    ai_rules_dir.mkdir(parents=True, exist_ok=True)

    budget = budget or TokenBudget()

    # --- Tier 1: canonical AGENTS.md (priority 0; never shed) -----------
    agents_md_body = _build_agents_md(
        config, scan_ctx, repo_map_digest=repo_map_digest,
    )
    budget.force_spend(agents_md_body, kind="agents_md", folder=None)
    (project_root / "AGENTS.md").write_text(agents_md_body, encoding="utf-8")

    # --- Tier 3: build candidates; emit each via try_spend (priority 9) -
    tier3_all = _build_tier3_skill_files(
        config,
        base_path,
        use_ai=use_ai,
        ai_provider=ai_provider,
        ai_model=ai_model,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
        google_key=google_key,
    )
    accepted_tier3: List[TierFile] = []
    for tf in tier3_all:
        if budget.try_spend(tf.body, kind="tier3_skill", folder=tf.slug):
            accepted_tier3.append(tf)

    write_tier_files(
        project_root, accepted_tier3, ai_rules_dir=ai_rules_dir,
    )

    # --- Legacy compat: project-rules.md (priority 10) ------------------
    if use_ai:
        general_guidelines = read_general_guidelines(base_path)
        project_context = generate_project_context(config)
        ai_content = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=config.primary_language,
            frameworks=config.frameworks,
            base_path=base_path,
            rule_type="single_project",
            format_mdc=False,
            use_ai=True,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
        )
        main_rules_content = ai_content or generate_template_single_project_rules(
            config, base_path
        )
    else:
        main_rules_content = generate_template_single_project_rules(config, base_path)

    outcome = budget.fit_or_truncate(
        main_rules_content, kind="legacy_project_rules", folder=None,
    )
    if outcome is not None:
        final_body, _ = outcome
        (ai_rules_dir / "project-rules.md").write_text(
            final_body, encoding="utf-8",
        )

    # README - tier index (small; usually fits)
    readme_body = render_tier_index(accepted_tier3)
    readme_body += (
        "\n\n## Entry points\n"
        "- `AGENTS.md` (repo root) - canonical always-on context. All AI "
        "tools are routed here.\n"
        "- `project-rules.md` - back-compat single-file dump for older tools.\n"
        "- See per-folder `.mdc` files under `.cursor/rules/` for Tier-2 "
        "(glob-scoped) rules.\n"
        "- `budget-report.md` - emission diagnostics (what was kept, "
        "truncated, or shed by the global TokenBudget).\n"
    )
    if budget.try_spend(readme_body, kind="readme", folder=None):
        (ai_rules_dir / "README.md").write_text(readme_body, encoding="utf-8")

    return ai_rules_dir


# ---------------------------------------------------------------------------
# Backwards-compatible reference generators
# ---------------------------------------------------------------------------

def generate_cursorrules_with_references(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
) -> str:
    """Generate a thin `.cursorrules` that points at the AGENTS.md hub."""
    return (
        f"# AI Coding Rules for {config.description}\n\n"
        "This project routes all AI tools through a canonical `AGENTS.md` "
        "hub. The authoritative context lives in:\n\n"
        "- `AGENTS.md` (repo root) - always-on identity, Stop Rules, dev "
        "commands, off-limits, repo map\n"
        "- `.cursor/rules/<folder>.mdc` - glob-scoped per-folder Tier-2 rules\n"
        "- `.ai-rules/skills/<topic>.md` - lazy-loaded deep dives\n\n"
        + generate_project_context(config)
        + "\n## How to read these rules\n"
        "1. Read `AGENTS.md` first - it loads automatically for most tools.\n"
        "2. Tier-2 .mdc files attach automatically when matching files are open.\n"
        "3. Invoke a Tier-3 skill via `@skill-name` (e.g. `@coding-principles`).\n"
    )


def generate_claude_md_with_references(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
) -> str:
    """Generate a thin `CLAUDE.md` that points at the AGENTS.md hub."""
    return (
        "@AGENTS.md\n\n"
        f"# AI Coding Rules for {config.description}\n\n"
        "This file points at the canonical `AGENTS.md` (imported above). "
        "Authoritative always-on context (identity, Stop Rules, dev "
        "commands, off-limits, repo map) lives there.\n\n"
        "Tier-3 deep-dive skills live in `.ai-rules/skills/`; glob-scoped "
        "Tier-2 rules live in `.cursor/rules/<folder>.mdc`.\n\n"
        + generate_project_context(config)
        + "\n## Critical Instructions\n"
        "1. Read `AGENTS.md` first - it contains Stop Rules and dev commands.\n"
        "2. When working on a specific folder, also consult its matching "
        "Tier-2 `.cursor/rules/<folder>.mdc`.\n"
        "3. Pull a Tier-3 skill (`.ai-rules/skills/*.md`) on demand.\n"
        "4. NEVER violate a Stop Rule; if a condition cannot be met, stop "
        "and ask the user.\n"
    )
