"""
Tiered rule renderer implementing the 2-4-2 architecture from the research.

Three tiers:

    Tier 1 - ALWAYS_ON     Loaded on every prompt.  Hard cap: 200 lines total
                           (split across at most two files).  Must contain
                           project identity + Stop Rules + repo map digest.

    Tier 2 - GLOB_SCOPED   Auto-attached when matching files are touched.
                           Per-folder `.mdc` with `applyTo: <glob>`.

    Tier 3 - SKILL         Lazy / agent-requested.  Larger files invoked via
                           `@skill-name` from Tier 1 or by the agent itself.

The renderer is intentionally provider-agnostic: it produces canonical
Markdown blobs.  The multi-tool emitters in `generators_multi_tool.py` then
adapt those blobs to each AI tool's native file format.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from .stop_rules import render_stop_rules_block
from .ten_section_template import SECTIONS, Section
from .models import ProjectConfig


class Tier(enum.Enum):
    ALWAYS_ON = "always_on"
    GLOB_SCOPED = "glob_scoped"
    SKILL = "skill"


# Hard caps per tier.  Tier 1 has the tightest budget because every token
# counts against every single prompt.
DEFAULT_TIER_LINE_CAPS: Dict[Tier, int] = {
    Tier.ALWAYS_ON: 200,
    Tier.GLOB_SCOPED: 350,
    Tier.SKILL: 1200,
}


@dataclass
class TierFile:
    """One rendered file ready to be written by a tool-specific emitter."""

    tier: Tier
    slug: str                       # filename stem
    title: str                      # used as `# Title` heading
    body: str                       # final Markdown body (already truncated)
    glob: Optional[str] = None      # only for Tier 2
    always_apply: bool = False      # only for Tier 1
    skill_links: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

def truncate_with_pointer(
    body: str,
    max_lines: int,
    *,
    skill_link: Optional[str] = None,
) -> str:
    """
    Hard-truncate `body` to `max_lines` lines.  On overflow, append a pointer
    to the skill file that continues the content - giving the LLM a clear
    handle to invoke when it needs more depth.
    """
    lines = body.splitlines()
    if len(lines) <= max_lines:
        return body
    truncated = "\n".join(lines[: max(0, max_lines - 1)])
    pointer = (
        f"\n[... continues in `{skill_link}` - invoke via @skill ...]"
        if skill_link
        else "\n[... truncated to fit tier-1 budget ...]"
    )
    return truncated + pointer


def count_lines(body: str) -> int:
    return len(body.splitlines())


# ---------------------------------------------------------------------------
# Tier 1 - always-on identity + baseline
# ---------------------------------------------------------------------------

def _digest_repo_map(digest: str, max_lines: int) -> str:
    """
    Pre-truncate a repo-map digest for embedding in Tier-1.

    The full ranked map already lives in `.ai-rules/graph/repo-map.md`; we
    only inject the top-N lines into the always-on file so the budget is
    spent on Stop Rules + identity, not a long node list.
    """
    if not digest.strip():
        return ""
    lines = digest.strip().splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + (
        "\n_(see `.ai-rules/graph/repo-map.md` for the full ranked list)_"
    )


def render_tier1_identity(
    config: ProjectConfig,
    *,
    repo_map_digest: str = "",
    key_file_index: str = "",
    max_lines: int = 100,
    repo_map_inline_lines: int = 25,
) -> TierFile:
    """
    Render the `00-identity.mdc` file.

    Section order is chosen so that the *inviolable* content (Identity +
    Stop Rules) is rendered before optional context blocks (Repo Map +
    Key File Index).  That way, even if the body overflows `max_lines` and
    gets truncated, the must-have safety scaffolding survives.

    The Repo Map digest is pre-truncated to `repo_map_inline_lines` so the
    long version stays in `.ai-rules/graph/repo-map.md` and only the top
    symbols ride along in the always-on prompt context.
    """
    lines: List[str] = [
        f"# {config.description}",
        "",
        "## Project Identity",
        f"- Description: {config.description}",
        f"- Primary language: {config.primary_language.title()}",
        (
            f"- Frameworks: {', '.join(config.frameworks)}"
            if config.frameworks
            else "- Frameworks: (none declared)"
        ),
        f"- Monorepo: {'yes' if config.is_monorepo else 'no'}",
        "",
        "## Optimization Goals",
        "- Be conservative: this is production code; prefer the smallest "
        "diff that satisfies the task.",
        "- Match existing patterns before introducing new ones.",
        "- Surface trade-offs explicitly rather than picking silently.",
        "",
    ]

    # Stop Rules FIRST -- inviolable scaffolding must not be truncated away.
    lines.append(render_stop_rules_block(
        language=config.primary_language,
        frameworks=config.frameworks,
    ).rstrip())
    lines.append("")

    # Then the optional context blocks.  Repo Map digest is capped because
    # the full version lives in `.ai-rules/graph/repo-map.md`.
    inline_map = _digest_repo_map(repo_map_digest, repo_map_inline_lines)
    if inline_map:
        lines.append("## Repo Map (top-ranked symbols)")
        lines.append("")
        lines.append(inline_map)
        lines.append("")

    if key_file_index.strip():
        lines.append("## Key File Index")
        lines.append("")
        lines.append(key_file_index.strip())
        lines.append("")

    lines.append("## Deeper Context")
    lines.append("")
    lines.append("For framework specifics, architecture rationale, or full "
                 "coding standards, invoke a skill from `.ai-rules/skills/` "
                 "(e.g. `@coding-principles`, `@architecture`).")

    body = "\n".join(lines)
    body = truncate_with_pointer(
        body, max_lines, skill_link=".ai-rules/skills/identity-extended.md"
    )
    return TierFile(
        tier=Tier.ALWAYS_ON,
        slug="00-identity",
        title=f"{config.description} - Identity",
        body=body,
        always_apply=True,
        skill_links=[
            ".ai-rules/skills/coding-principles.md",
            ".ai-rules/skills/architecture.md",
        ],
    )


def render_tier1_baseline(
    config: ProjectConfig,
    *,
    dev_commands: str = "",
    off_limits: str = "",
    max_lines: int = 100,
) -> TierFile:
    """
    Render the `01-baseline.mdc` file: dev commands + off-limits + workflow
    guardrails.  Companion to the identity file - both always-on.
    """
    lines: List[str] = [
        "# Baseline Workflow",
        "",
        "## Dev Commands",
        "",
    ]
    if dev_commands.strip():
        lines.append(dev_commands.strip())
    else:
        lines.append("- (none declared - the agent should ask before "
                     "inventing commands)")
    lines.append("")

    lines.append("## Off-Limits Zones")
    lines.append("")
    if off_limits.strip():
        lines.append(off_limits.strip())
    else:
        lines.append(
            "- `**/.env*` - environment secrets\n"
            "- `**/migrations/**` - database migrations (human review required)\n"
            "- `**/auth/**`, `**/payments/**` - security-critical code\n"
            "- `**/node_modules/**`, `**/.venv/**`, `**/dist/**`, "
            "`**/build/**` - generated / vendored"
        )
    lines.append("")

    lines.append("## Workflow Discipline")
    lines.append(
        "- SEARCH FIRST: use codebase search before writing new code; "
        "match existing patterns.\n"
        "- VERIFY BEFORE FINISHING: run typecheck, lint, and tests for the "
        "touched package.\n"
        "- ASK ON AMBIGUITY: when requirements are unclear, ask one "
        "specific clarifying question rather than guess.\n"
        "- CITE WHEN YOU CHANGE: in code review, point at the file/line of "
        "the pattern you matched."
    )

    body = "\n".join(lines)
    body = truncate_with_pointer(
        body, max_lines, skill_link=".ai-rules/skills/workflow.md"
    )
    return TierFile(
        tier=Tier.ALWAYS_ON,
        slug="01-baseline",
        title="Baseline Workflow",
        body=body,
        always_apply=True,
    )


# ---------------------------------------------------------------------------
# Tier 2 - glob-scoped per-folder rules
# ---------------------------------------------------------------------------

def render_tier2_folder(
    *,
    folder_name: str,
    glob_pattern: str,
    language: str,
    frameworks: Sequence[str],
    skeleton_markdown: str = "",
    purpose: str = "",
    folder_summary: str = "",
    file_descriptions: Optional[Mapping[str, str]] = None,
    local_call_graph: str = "",
    reverse_imports: str = "",
    max_lines: Optional[int] = None,
) -> TierFile:
    """
    Render a Tier-2 `.mdc` for a single folder.

    The body is composed in canonical section order so it stays readable
    even when the budget-aware emitter sheds individual sections:

        1. Header (folder / glob / language / frameworks / purpose)
        2. Overview (AI folder summary, if available)
        3. Skeleton (signatures, with per-file AI descriptions inline)
        4. Call Flow (intra-folder DKB edges, deterministic)
        5. Used By (external consumers, deterministic)
        6. Conventions (boilerplate)

    `max_lines` is kept for backward compatibility but defaults to None
    (no per-file cap).  The global `TokenBudget` enforced by the
    orchestrator is what bounds emission now; this renderer just
    assembles the canonical layout.
    """
    title = f"{folder_name} - Domain Rules"
    fw_str = ", ".join(frameworks) if frameworks else "(none)"
    parts: List[str] = []
    parts.append(
        f"# {title}\n\n"
        f"- Folder: `{folder_name}/`\n"
        f"- Glob: `{glob_pattern}`\n"
        f"- Language: {language.title() if language else '(mixed)'}\n"
        f"- Frameworks: {fw_str}\n"
        f"- Purpose: {purpose or '(inferred from contents)'}"
    )

    if folder_summary.strip():
        parts.append("## Overview\n\n" + folder_summary.strip())

    skeleton_block = _interleave_descriptions(
        skeleton_markdown, file_descriptions or {}
    )
    if skeleton_block.strip():
        parts.append("## Skeleton\n\n" + skeleton_block.strip())
    else:
        parts.append(
            "## Skeleton\n\n"
            "(no AST skeleton available - agent should read files directly)"
        )

    if local_call_graph.strip():
        parts.append("## Call Flow\n\n" + local_call_graph.strip())

    if reverse_imports.strip():
        parts.append("## Used By\n\n" + reverse_imports.strip())

    parts.append(
        "## Conventions\n\n"
        "- Match existing exports listed above before adding new ones.\n"
        "- Co-locate tests with the file under test where the folder "
        "already does so."
    )

    body = "\n\n".join(parts).rstrip() + "\n"

    if max_lines is not None:
        body = truncate_with_pointer(
            body,
            max_lines,
            skill_link=f".ai-rules/skills/{folder_name}-deep-dive.md",
        )
    slug = folder_name.replace("/", "--").replace("\\", "--").replace(".", "")
    return TierFile(
        tier=Tier.GLOB_SCOPED,
        slug=slug or "folder",
        title=title,
        body=body,
        glob=glob_pattern,
    )


def _interleave_descriptions(
    skeleton_markdown: str,
    file_descriptions: Mapping[str, str],
) -> str:
    r"""Insert each file's AI description right under its `#### `name``
    header.  If we don't have a description for a file we leave its block
    unchanged."""
    if not file_descriptions:
        return skeleton_markdown

    out_lines: List[str] = []
    for line in skeleton_markdown.splitlines():
        out_lines.append(line)
        # Match `#### \`filename.ext\``
        stripped = line.strip()
        if stripped.startswith("#### `") and stripped.endswith("`"):
            filename = stripped[6:-1]  # strip "#### `" and trailing "`"
            desc = file_descriptions.get(filename) \
                or file_descriptions.get(Path(filename).name)
            if desc:
                out_lines.append("")
                for desc_line in desc.strip().splitlines():
                    out_lines.append(f"> {desc_line}")
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# Tier 3 - skill files (lazy / agent-requested)
# ---------------------------------------------------------------------------

def render_tier3_skill(
    *,
    slug: str,
    title: str,
    body: str,
    max_lines: Optional[int] = None,
) -> TierFile:
    """Render a Tier-3 skill file.

    When ``max_lines`` is None (the default), the body is emitted whole and
    the global ``TokenBudget`` enforced by the orchestrator is what bounds
    emission.  Pass an explicit ``max_lines`` only for tests or legacy caps.
    """
    if max_lines is not None:
        body = truncate_with_pointer(body, max_lines)
    return TierFile(
        tier=Tier.SKILL,
        slug=slug,
        title=title,
        body=body,
    )


# ---------------------------------------------------------------------------
# Filesystem emission
# ---------------------------------------------------------------------------

def write_tier_files(
    project_root: Path,
    files: Sequence[TierFile],
    *,
    ai_rules_dir: Optional[Path] = None,
    cursor_rules_dir: Optional[Path] = None,
    skills_subdir: str = "skills",
) -> List[Path]:
    """
    Persist a batch of TierFile objects to disk.  Returns absolute paths of
    the files actually written.

    Layout (per the plan):

        <project_root>/.cursor/rules/<slug>.mdc          (Tier 1 + Tier 2)
        <project_root>/.ai-rules/skills/<slug>.md         (Tier 3)
        <project_root>/.claude/skills/<slug>.md           (Tier 3 mirror)
    """
    ai_rules_dir = ai_rules_dir or (project_root / ".ai-rules")
    cursor_rules_dir = cursor_rules_dir or (project_root / ".cursor" / "rules")
    skills_dir = ai_rules_dir / skills_subdir
    claude_skills_dir = project_root / ".claude" / "skills"

    ai_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for tf in files:
        if tf.tier in (Tier.ALWAYS_ON, Tier.GLOB_SCOPED):
            cursor_rules_dir.mkdir(parents=True, exist_ok=True)
            path = cursor_rules_dir / f"{tf.slug}.mdc"
            path.write_text(_mdc_with_frontmatter(tf), encoding="utf-8")
            written.append(path)
        else:  # SKILL
            skills_dir.mkdir(parents=True, exist_ok=True)
            claude_skills_dir.mkdir(parents=True, exist_ok=True)
            ai_path = skills_dir / f"{tf.slug}.md"
            claude_path = claude_skills_dir / f"{tf.slug}.md"
            ai_path.write_text(tf.body, encoding="utf-8")
            claude_path.write_text(tf.body, encoding="utf-8")
            written.extend([ai_path, claude_path])

    return written


def _mdc_with_frontmatter(tf: TierFile) -> str:
    """Build a Cursor MDC file (YAML frontmatter + body)."""
    lines = ["---"]
    lines.append(f"description: {tf.title}")
    if tf.glob:
        lines.append("globs:")
        lines.append(f"  - \"{tf.glob}\"")
    lines.append(f"alwaysApply: {str(tf.always_apply).lower()}")
    lines.append("---")
    lines.append("")
    lines.append(tf.body)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tier file index (for emitting the 'see also' README in .ai-rules/)
# ---------------------------------------------------------------------------

def render_tier_index(files: Sequence[TierFile]) -> str:
    """Produce a `.ai-rules/README.md` body describing the tier layout."""
    by_tier: Dict[Tier, List[TierFile]] = {t: [] for t in Tier}
    for tf in files:
        by_tier[tf.tier].append(tf)

    lines = [
        "# Shared AI Rules (AGENTS.md hub)",
        "",
        "All AI tools are routed to the canonical `AGENTS.md` at the repo root.",
        "Supporting content is organized as:",
        "",
        "- **Always On** - `AGENTS.md` (identity, Stop Rules, dev commands, "
        "off-limits, repo map). Tool entry points (CLAUDE.md, GEMINI.md, "
        "`.github/copilot-instructions.md`) symlink to it.",
        "- **Tier 2 - Glob Scoped** - `.cursor/rules/<folder>.mdc`, "
        "auto-attached when matching files are touched.",
        "- **Tier 3 - Skills** - `.ai-rules/skills/*.md`, lazy-loaded via "
        "`@skill-name` or by the agent.",
        "",
    ]

    for tier in Tier:
        bucket = by_tier[tier]
        if not bucket:
            continue
        lines.append(f"## {tier.value.replace('_', ' ').title()}")
        lines.append("")
        for tf in bucket:
            location = (
                f".cursor/rules/{tf.slug}.mdc"
                if tier in (Tier.ALWAYS_ON, Tier.GLOB_SCOPED)
                else f".ai-rules/skills/{tf.slug}.md"
            )
            extras = []
            if tf.glob:
                extras.append(f"glob `{tf.glob}`")
            if tf.always_apply:
                extras.append("always-apply")
            tail = f" - {', '.join(extras)}" if extras else ""
            lines.append(f"- [`{location}`]({location}) - {tf.title}{tail}")
        lines.append("")

    return "\n".join(lines)


_EXT_TO_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".m": "objective-c",
    ".mm": "objective-cpp",
}


def detect_folder_language(file_paths: Sequence[str], fallback: str = "") -> str:
    """
    Majority-vote a language for a folder from the extensions of the
    skeletonized files inside it.  Returns `fallback` when no recognized
    extensions are present.  Fixes the bug where a `.go` folder is
    labelled with the project's `primary_language=typescript`.
    """
    counts: Dict[str, int] = {}
    for path in file_paths:
        ext = Path(path).suffix.lower()
        lang = _EXT_TO_LANGUAGE.get(ext)
        if not lang:
            continue
        counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return fallback
    return max(counts.items(), key=lambda kv: kv[1])[0]


__all__ = [
    "Tier",
    "TierFile",
    "DEFAULT_TIER_LINE_CAPS",
    "truncate_with_pointer",
    "count_lines",
    "render_tier1_identity",
    "render_tier1_baseline",
    "render_tier2_folder",
    "render_tier3_skill",
    "render_tier_index",
    "write_tier_files",
    "detect_folder_language",
]
