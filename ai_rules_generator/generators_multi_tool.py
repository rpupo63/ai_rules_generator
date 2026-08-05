"""
Tool entry-point emission for the AGENTS.md hub model.

Instead of generating a bespoke, content-duplicating file per tool, every
enabled tool is routed to the canonical root `AGENTS.md` (+ `.ai-rules/`)
through its native discovery path:

  - Native AGENTS.md readers (Cursor, Codex, Windsurf, Warp, Devin) need no
    file at all in symlink mode.
  - Tools with a named entry file (Claude Code -> CLAUDE.md, Gemini ->
    GEMINI.md, Copilot -> .github/copilot-instructions.md) get a symlink /
    import / copy pointing at AGENTS.md.
  - Claude Code additionally gets `.claude/skills` linked to
    `.ai-rules/skills`.
  - Cursor consumes the glob-scoped Tier-2 `.cursor/rules/<folder>.mdc`
    files (emitted separately by the orchestrator).

Capabilities come from `config_manager.get_available_tools()`.
"""

from pathlib import Path
from typing import Any, List, Optional

from .config_manager import get_available_tools
from .linker import LinkMode, LinkOutcome, claude_import_line, link_dir, link_file
from .models import ProjectConfig


DEFAULT_ENABLED_TOOLS = [
    "cursor", "claude-code", "windsurf", "copilot", "warp", "janie",
]


def generate_all_tool_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    enabled_tools: Optional[List[str]] = None,
    *,
    scan_ctx: Optional[Any] = None,
    link_mode: LinkMode = LinkMode.SYMLINK,
) -> List[Path]:
    """
    Route each enabled tool to the canonical AGENTS.md hub.

    Returns the list of files/links created (for the CLI summary). AGENTS.md
    itself is written by `generators_shared.create_shared_ai_rules_directory`;
    Tier-2 `.cursor/rules/<folder>.mdc` files are emitted by the orchestrator.
    """
    if isinstance(link_mode, str):
        link_mode = LinkMode.from_str(link_mode)

    if enabled_tools is None:
        enabled_tools = list(DEFAULT_ENABLED_TOOLS)

    canonical = project_root / "AGENTS.md"
    if not canonical.is_file():
        # Nothing to point at - the shared step should have written it.
        print("  ! AGENTS.md not found; skipping tool entry-point linking.")
        return []

    registry = get_available_tools()
    created: List[Path] = []

    for tool_key in enabled_tools:
        caps = registry.get(tool_key)
        if not caps:
            continue

        entry = caps.get("entry")
        skills_link = caps.get("skills_link")
        reads_agents_md = caps.get("reads_agents_md", False)
        glob_rules = caps.get("glob_rules", False)

        # 1. Named entry file -> point at AGENTS.md.
        if entry:
            target = project_root / entry
            import_line = None
            if link_mode is LinkMode.IMPORT:
                # Claude Code natively supports `@path` imports.
                import_line = claude_import_line(target, canonical)
            outcome = link_file(
                target, canonical, link_mode, import_line=import_line,
            )
            created.append(target)
            _report(target, project_root, outcome, points_to="AGENTS.md")
        elif reads_agents_md:
            # Native reader: nothing to emit, it auto-loads AGENTS.md.
            print(
                f"  - {caps.get('name', tool_key)}: native AGENTS.md reader "
                f"(no file needed)"
            )

        # 2. Skills directory link (e.g. .claude/skills -> .ai-rules/skills).
        if skills_link:
            target_rel, canonical_rel = skills_link
            target_dir = project_root / target_rel
            canonical_dir = project_root / canonical_rel
            if canonical_dir.exists():
                outcome = link_dir(target_dir, canonical_dir, link_mode)
                created.append(target_dir)
                _report(target_dir, project_root, outcome, points_to=canonical_rel)

        # 3. Glob-scoped Tier-2 rules are emitted by the orchestrator; we
        #    only note the dependency here.
        if glob_rules:
            print(
                f"  - {caps.get('name', tool_key)}: uses glob-scoped "
                f".cursor/rules/<folder>.mdc (Tier-2)"
            )

    return created


def _report(
    target: Path,
    project_root: Path,
    outcome: LinkOutcome,
    *,
    points_to: str,
) -> None:
    try:
        rel = target.relative_to(project_root)
    except ValueError:
        rel = target
    verb = {
        LinkOutcome.SYMLINKED: f"Symlinked {rel} -> {points_to}",
        LinkOutcome.IMPORTED: f"Wrote import stub {rel} -> {points_to}",
        LinkOutcome.COPIED: f"Copied {points_to} -> {rel}",
        LinkOutcome.SKIPPED: f"Skipped {rel}",
    }.get(outcome, f"Linked {rel}")
    print(f"  \u2713 {verb}")
