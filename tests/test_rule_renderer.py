"""
Tests for the tiered rule renderer (Phase 2).

Validates that:
  - Tier-1 files honour the line cap.
  - Stop Rules are present in every Tier-1 identity file.
  - Tier-3 files don't get truncated below their content.
  - The tier index README mentions every file.
"""

from pathlib import Path

from ai_rules_generator.models import ProjectConfig
from ai_rules_generator.rule_renderer import (
    DEFAULT_TIER_LINE_CAPS,
    Tier,
    TierFile,
    count_lines,
    detect_folder_language,
    render_tier1_baseline,
    render_tier1_identity,
    render_tier2_folder,
    render_tier3_skill,
    render_tier_index,
    truncate_with_pointer,
    write_tier_files,
)


def _make_config() -> ProjectConfig:
    return ProjectConfig(
        description="Test Project",
        is_monorepo=False,
        primary_language="python",
        frameworks=["fastapi"],
    )


def test_truncate_with_pointer_adds_pointer_on_overflow():
    body = "\n".join(f"line {i}" for i in range(50))
    out = truncate_with_pointer(body, max_lines=10, skill_link=".ai-rules/skills/foo.md")
    assert count_lines(out) <= 10
    assert "foo.md" in out


def test_truncate_with_pointer_pass_through_when_short():
    body = "one\ntwo\nthree"
    out = truncate_with_pointer(body, max_lines=10)
    assert out == body


def test_tier1_identity_respects_cap_and_contains_stop_rules():
    cfg = _make_config()
    tf = render_tier1_identity(cfg, max_lines=100)
    assert tf.tier is Tier.ALWAYS_ON
    assert tf.always_apply is True
    assert count_lines(tf.body) <= 100
    assert "Stop Rules" in tf.body
    # Must use the NEVER/without/because schema.
    assert "NEVER" in tf.body
    assert "because" in tf.body


def test_tier1_baseline_lists_dev_commands_and_off_limits():
    cfg = _make_config()
    tf = render_tier1_baseline(cfg, dev_commands="- Test: `pytest -q`", max_lines=100)
    assert "Dev Commands" in tf.body
    assert "Off-Limits Zones" in tf.body
    assert "pytest" in tf.body


def test_two_tier1_files_fit_total_budget():
    cfg = _make_config()
    tf1 = render_tier1_identity(cfg, max_lines=100)
    tf2 = render_tier1_baseline(cfg, dev_commands="- Test: pytest", max_lines=100)
    total = count_lines(tf1.body) + count_lines(tf2.body)
    assert total <= DEFAULT_TIER_LINE_CAPS[Tier.ALWAYS_ON], (
        f"Tier-1 total {total} exceeded cap {DEFAULT_TIER_LINE_CAPS[Tier.ALWAYS_ON]}"
    )


def test_tier2_folder_has_glob_and_skeleton_section():
    tf = render_tier2_folder(
        folder_name="services",
        glob_pattern="services/**/*.py",
        language="python",
        frameworks=["fastapi"],
        skeleton_markdown="#### `core.py`\n```\ndef foo(): ...\n```",
        purpose="business logic",
    )
    assert tf.tier is Tier.GLOB_SCOPED
    assert tf.glob == "services/**/*.py"
    assert "## Skeleton" in tf.body
    assert "foo" in tf.body


def test_tier3_skill_truncates_excessive_bodies():
    body = "\n".join(f"row {i}" for i in range(5000))
    tf = render_tier3_skill(slug="big", title="Big", body=body, max_lines=200)
    assert tf.tier is Tier.SKILL
    assert count_lines(tf.body) <= 200


def test_write_tier_files_creates_layout(tmp_path):
    cfg = _make_config()
    files = [
        render_tier1_identity(cfg, max_lines=80),
        render_tier1_baseline(cfg, dev_commands="- Test: pytest", max_lines=80),
        render_tier3_skill(slug="coding-principles", title="Coding Principles", body="...", max_lines=10),
    ]
    written = write_tier_files(tmp_path, files)
    paths = {p.relative_to(tmp_path).as_posix() for p in written}
    assert ".cursor/rules/00-identity.mdc" in paths
    assert ".cursor/rules/01-baseline.mdc" in paths
    assert ".ai-rules/skills/coding-principles.md" in paths
    assert ".claude/skills/coding-principles.md" in paths
    # Frontmatter sanity check
    identity = (tmp_path / ".cursor/rules/00-identity.mdc").read_text()
    assert identity.startswith("---\n")
    assert "alwaysApply: true" in identity


def test_render_tier_index_lists_every_file():
    files = [
        TierFile(tier=Tier.ALWAYS_ON, slug="00-identity", title="Identity", body="x", always_apply=True),
        TierFile(tier=Tier.GLOB_SCOPED, slug="services", title="Services", body="x", glob="services/**/*"),
        TierFile(tier=Tier.SKILL, slug="coding-principles", title="Coding Principles", body="x"),
    ]
    out = render_tier_index(files)
    assert "00-identity" in out
    assert "services" in out
    assert "coding-principles" in out
    assert "Always On" in out


# ---------------------------------------------------------------------------
# Phase 6: extended Tier-2 layout (overview / call flow / used by / per-file
# descriptions) + per-folder language detection.
# ---------------------------------------------------------------------------

def test_tier2_includes_overview_when_folder_summary_provided():
    tf = render_tier2_folder(
        folder_name="services",
        glob_pattern="services/**/*",
        language="python",
        frameworks=[],
        skeleton_markdown="#### `core.py`\n```\ndef foo(): ...\n```",
        purpose="business logic",
        folder_summary=(
            "This folder owns the domain-level business logic.  Each file "
            "implements one bounded operation; they are pure functions that "
            "the API layer composes."
        ),
    )
    assert "## Overview" in tf.body
    assert "bounded operation" in tf.body


def test_tier2_omits_overview_when_summary_blank():
    tf = render_tier2_folder(
        folder_name="services",
        glob_pattern="services/**/*",
        language="python",
        frameworks=[],
        skeleton_markdown="#### `core.py`\n```\ndef foo(): ...\n```",
    )
    assert "## Overview" not in tf.body


def test_tier2_includes_call_flow_and_used_by_when_provided():
    tf = render_tier2_folder(
        folder_name="services",
        glob_pattern="services/**/*",
        language="python",
        frameworks=[],
        skeleton_markdown="#### `core.py`\n```\ndef foo(): ...\n```",
        local_call_graph="- `services/core.py::foo` -> `services/core.py::helper`",
        reverse_imports="- `api/handler.py` -> `foo`",
    )
    assert "## Call Flow" in tf.body
    assert "## Used By" in tf.body
    assert "api/handler.py" in tf.body
    assert "helper" in tf.body


def test_tier2_interleaves_file_descriptions_into_skeleton():
    skel = (
        "#### `core.py`\n```\ndef foo(): ...\n```\n\n"
        "#### `utils.py`\n```\ndef bar(): ...\n```"
    )
    tf = render_tier2_folder(
        folder_name="services",
        glob_pattern="services/**/*",
        language="python",
        frameworks=[],
        skeleton_markdown=skel,
        file_descriptions={
            "core.py": "Owns the main pipeline; consumed by the HTTP layer.",
            "utils.py": "Small pure helpers used only inside this folder.",
        },
    )
    # The description for core.py must appear in the body *between* its
    # header and utils.py's header.
    body = tf.body
    core_pos = body.index("`core.py`")
    utils_pos = body.index("`utils.py`")
    desc_pos = body.index("Owns the main pipeline")
    assert core_pos < desc_pos < utils_pos
    # Quote prefix preserved.
    assert "> Owns the main pipeline" in body


def test_detect_folder_language_majority_vote():
    paths = ["a.go", "b.go", "c.go", "d.py"]
    assert detect_folder_language(paths) == "go"


def test_detect_folder_language_fallback_when_no_known_extensions():
    paths = ["a.md", "b.txt"]
    assert detect_folder_language(paths, fallback="typescript") == "typescript"


def test_detect_folder_language_typescript_dominant():
    paths = ["a.tsx", "b.ts", "c.go"]
    assert detect_folder_language(paths) == "typescript"


def test_tier2_no_per_file_cap_when_max_lines_none():
    """The renderer must NOT truncate when called without max_lines -
    the global TokenBudget is the authoritative limit now."""
    huge_skel = "\n\n".join(
        f"#### `f{i}.py`\n```\ndef func_{i}(): ...\n```" for i in range(500)
    )
    tf = render_tier2_folder(
        folder_name="huge",
        glob_pattern="huge/**/*",
        language="python",
        frameworks=[],
        skeleton_markdown=huge_skel,
    )
    # All 500 file headers should survive.
    assert tf.body.count("####") == 500
    assert "truncated" not in tf.body.lower()
