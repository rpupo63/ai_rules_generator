"""
Tests for the XML-tagged prompt builder (Phase 1).

Validates that every prompt the codebase emits contains the canonical XML
sections required by the context-engineering architecture, and that the
builder is robust to ordering and empty-section input.
"""

import re

import pytest

from ai_rules_generator.prompt_xml import (
    CANONICAL_SECTION_ORDER,
    build_xml_prompt,
)
from ai_rules_generator.ai_generator import (
    PromptConfig,
    build_ai_prompt,
)


REQUIRED_TAGS = ("role", "task", "output_format", "stop_rules")


def _has_tag(prompt: str, tag: str) -> bool:
    return f"<{tag}>" in prompt and f"</{tag}>" in prompt


def test_build_xml_prompt_emits_known_tags():
    out = build_xml_prompt({
        "role": "you are a helper",
        "task": "do the thing",
        "output_format": "return JSON",
    })
    for tag in ("role", "task", "output_format"):
        assert _has_tag(out, tag), f"missing <{tag}> in: {out}"


def test_build_xml_prompt_respects_canonical_order():
    out = build_xml_prompt({
        "output_format": "json",
        "role": "expert",
        "task": "summarize",
        "project_identity": "test project",
    })
    role_pos = out.index("<role>")
    identity_pos = out.index("<project_identity>")
    task_pos = out.index("<task>")
    of_pos = out.index("<output_format>")
    assert role_pos < identity_pos < task_pos < of_pos, (
        "sections must appear in canonical order: " + out
    )


def test_build_xml_prompt_omits_empty_sections_by_default():
    out = build_xml_prompt({"role": "ok", "task": "", "output_format": "x"})
    assert "<task>" not in out
    assert "<task/>" not in out


def test_build_xml_prompt_emits_unknown_sections_at_end():
    out = build_xml_prompt({"role": "r", "task": "t", "novel_tag": "value"})
    assert _has_tag(out, "novel_tag")
    assert out.rfind("<novel_tag>") > out.rfind("<task>")


def test_ai_generator_prompt_contains_required_tags():
    """The high-level builder used by every AI rule call must emit the
    full schema, not just whatever sections happened to be supplied."""
    cfg = PromptConfig(
        general_guidelines="some guidelines",
        project_context="some context",
        relevant_rules=[("python", "# Python rules\n- foo")],
        rule_type="single_project",
        format_mdc=False,
    )
    out = build_ai_prompt(cfg)
    for tag in REQUIRED_TAGS + ("project_identity", "reference_rules", "style_guide"):
        assert _has_tag(out, tag), f"missing <{tag}> in build_ai_prompt output"


def test_ai_generator_stop_rules_use_never_format():
    cfg = PromptConfig(
        general_guidelines="g",
        project_context="c",
        relevant_rules=[],
        rule_type="single_project",
        format_mdc=False,
    )
    out = build_ai_prompt(cfg)
    # At least one NEVER ... without ... because ... rule must appear.
    pattern = re.compile(r"NEVER .+ without .+ - because", re.IGNORECASE)
    assert pattern.search(out), "stop_rules must use the NEVER/without/because schema"


def test_canonical_order_is_stable():
    """Guard against accidental reordering that would break downstream regex tests."""
    assert CANONICAL_SECTION_ORDER[0] == "role"
    assert "stop_rules" in CANONICAL_SECTION_ORDER
    assert "output_format" in CANONICAL_SECTION_ORDER
    assert "task" in CANONICAL_SECTION_ORDER
