"""
Tests for the canonical AGENTS.md renderer (hub model).

Validates that AGENTS.md is the single always-on home for:
  - project identity
  - Stop Rules (NEVER ... because ... schema)
  - dev commands
  - off-limits zones
  - the repo-map digest + key file index
  - the pointer index ("How Agents Should Use This Repo")
  - the maintenance directives ("Keeping This Context Current")
"""

from pathlib import Path

from ai_rules_generator.agents_md import (
    MAINTAINING_CONTEXT_SKILL,
    build_dev_commands,
    build_key_file_index,
    render_agents_md,
    render_maintenance_block,
)
from ai_rules_generator.models import ProjectConfig


def _make_config() -> ProjectConfig:
    return ProjectConfig(
        description="Acme Service",
        is_monorepo=False,
        primary_language="python",
        frameworks=["fastapi"],
        project_root=Path("."),
    )


def test_agents_md_contains_identity_and_stop_rules():
    md = render_agents_md(_make_config())
    assert md.startswith("# Acme Service")
    assert "Stop Rules" in md
    # Stop-Rule schema.
    assert "NEVER" in md
    assert "because" in md


def test_agents_md_contains_dev_commands_and_off_limits():
    md = render_agents_md(
        _make_config(),
        dev_commands="- Test: `pytest -q`",
    )
    assert "## Dev Commands" in md
    assert "pytest" in md
    assert "## Off-Limits Zones" in md


def test_agents_md_defaults_dev_commands_from_language():
    # No explicit dev_commands -> language defaults kick in.
    md = render_agents_md(_make_config())
    assert "pytest" in md  # python default


def test_agents_md_contains_pointer_index():
    md = render_agents_md(_make_config())
    assert "How Agents Should Use This Repo" in md
    assert ".cursor/rules/" in md
    assert ".ai-rules/skills/" in md


def test_agents_md_contains_maintenance_section():
    md = render_agents_md(_make_config())
    assert "Keeping This Context Current" in md
    assert "ai-rules-generator update" in md
    # Maintenance is written as binding directives.
    assert "ALWAYS" in md


def test_agents_md_can_omit_maintenance():
    md = render_agents_md(_make_config(), include_maintenance=False)
    assert "Keeping This Context Current" not in md


def test_agents_md_embeds_repo_map_digest():
    md = render_agents_md(
        _make_config(),
        repo_map_digest="- `app.main:create_app` (rank 0.10)",
    )
    assert "Repo Map" in md
    assert "create_app" in md


def test_agents_md_repo_map_digest_truncates_long_input():
    long_digest = "\n".join(f"- sym{i}" for i in range(200))
    md = render_agents_md(
        _make_config(),
        repo_map_digest=long_digest,
        repo_map_inline_lines=20,
    )
    assert "repo-map.md" in md  # truncation pointer
    # The 100th symbol should not appear inline.
    assert "sym150" not in md


def test_build_dev_commands_per_language():
    assert "pytest" in build_dev_commands("python")
    assert "go test" in build_dev_commands("go")
    assert "cargo test" in build_dev_commands("rust")
    assert build_dev_commands("brainfuck") == ""


def test_render_maintenance_block_schema():
    block = render_maintenance_block()
    assert "NEVER" in block
    assert "ALWAYS" in block
    assert "maintaining-context.md" in block


def test_maintaining_context_skill_mentions_update():
    assert "ai-rules-generator update" in MAINTAINING_CONTEXT_SKILL
    assert "AGENTS.md" in MAINTAINING_CONTEXT_SKILL


def test_build_key_file_index_handles_missing_scan():
    assert build_key_file_index(None) == ""
