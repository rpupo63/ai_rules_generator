"""Tests for context-manifest.yml loading and emit caps (C4-3)."""

from pathlib import Path

from ai_rules_generator import __version__
from ai_rules_generator.orchestration import (
    ContextManifest,
    _parse_simple_manifest_yaml,
    _rule_is_file_listing_only,
    generate_codebase_context,
    load_context_manifest,
)
from ai_rules_generator.token_budget import DEFAULT_GLOBAL_BUDGET, DEFAULT_MAP_BUDGET


def test_version_is_not_placeholder():
    assert __version__ != "1.0.0"
    assert __version__ == "2.0.0"


def test_default_budgets_are_aider_like():
    assert DEFAULT_GLOBAL_BUDGET == 1000
    assert DEFAULT_MAP_BUDGET == 1000


def test_parse_manifest_yaml_lists_and_ints():
    raw = _parse_simple_manifest_yaml(
        """
version: 1
budget_tokens: 1000
languages: [bash, python]
always:
  - AGENTS.md
never: [build/**, .agent-sessions/archive/**]
emit: [map, cursor-rules]
"""
    )
    assert raw["budget_tokens"] == 1000
    assert raw["languages"] == ["bash", "python"]
    assert raw["always"] == ["AGENTS.md"]
    assert raw["never"] == ["build/**", ".agent-sessions/archive/**"]
    assert raw["emit"] == ["map", "cursor-rules"]


def test_load_context_manifest_from_ai_context(tmp_path: Path):
    ctx = tmp_path / ".ai-context"
    ctx.mkdir()
    (ctx / "context-manifest.yml").write_text(
        "version: 1\nbudget_tokens: 800\nlanguages: [bash]\n"
        "always: [AGENTS.md]\nnever: [build/**]\nemit: [map, cursor-rules]\n",
        encoding="utf-8",
    )
    m = load_context_manifest(tmp_path)
    assert m is not None
    assert m.budget_tokens == 800
    assert m.languages == ["bash"]
    assert m.emit_cursor_rules is True
    assert m.emit_map is True


def test_file_listing_only_detection():
    listing = "- `a.sh`\n- `b.sh`\n"
    assert _rule_is_file_listing_only(listing, "") is True
    assert _rule_is_file_listing_only(listing, "### Used by\n- x") is False
    assert _rule_is_file_listing_only("## Signatures\n- `foo()`", "") is False


def test_generate_writes_versioned_manifest(tmp_path: Path):
    (tmp_path / "hello.py").write_text("def greet():\n    return 1\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    result = generate_codebase_context(
        tmp_path,
        emit_cursor_rules=False,
        graph_token_budget=1000,
        global_budget=1000,
    )
    man_path = tmp_path / ".ai-context" / "manifest.json"
    assert man_path.is_file()
    text = man_path.read_text(encoding="utf-8")
    assert f'"generator_version": "{__version__}"' in text
    assert result["generator_version"] == __version__
    assert result["map_tokens"] <= 1000
