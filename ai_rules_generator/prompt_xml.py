"""
XML-tagged prompt builder for AI rule generation.

Per the context-engineering research (Anthropic / OpenAI / Google guidelines),
XML-style delimiters create unambiguous semantic boundaries that:
  - Prevent passive context from being interpreted as executable instructions
  - Align with the pre-training distribution of frontier LLMs (HTML/XML markup)
  - Provide injection resistance vs flat text
  - Naturally express hierarchical / multi-step workflows

This module is the single source of truth for prompt structure.  All callers
should build a `dict[str, str]` of canonical section names and pass it to
`build_xml_prompt`.  Unknown sections are accepted (rendered last) but log a
debug warning so we keep a fixed vocabulary over time.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Mapping, Optional

logger = logging.getLogger(__name__)

# Canonical section order.  Sections are emitted in this order regardless of
# the order they appear in the input dict, so callers don't have to think about
# ordering.  Sections not in this list are appended at the end (and logged).
CANONICAL_SECTION_ORDER: List[str] = [
    "role",
    "project_identity",
    "tech_stack",
    "architecture_snapshot",
    "repo_map",
    "key_file_index",
    "reference_rules",
    "input_code",
    "stop_rules",
    "off_limits",
    "external_services",
    "dev_commands",
    "style_guide",
    "task",
    "output_format",
]

# A short description of each canonical tag, used both for documentation and
# for emitting an inline comment when DEBUG logging is enabled.
SECTION_DESCRIPTIONS: Dict[str, str] = {
    "role":               "Persona / capabilities of the assistant",
    "project_identity":   "Brand, product, optimization goals (always-on)",
    "tech_stack":         "Languages, frameworks, versions",
    "architecture_snapshot": "Non-obvious architectural choices",
    "repo_map":           "Ranked symbols + key edges (DKB / Graph RAG)",
    "key_file_index":     "Pointers to critical files",
    "reference_rules":    "Vetted external rules to incorporate",
    "input_code":         "Source code skeletons supplied as context",
    "stop_rules":         "NEVER [action] without [condition] - because [reason]",
    "off_limits":         "Read-only or human-review-required paths",
    "external_services":  "Third-party API caveats, rate limits, staging hints",
    "dev_commands":       "Explicit test / lint / build invocations",
    "style_guide":        "Naming, formatting, idiom conventions",
    "task":               "The actual ask / instruction for this turn",
    "output_format":      "Strict schema the response must follow",
}


def _normalize_tag(name: str) -> str:
    """Coerce arbitrary section keys to lowercase snake_case tag names."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _render_section(tag: str, body: str) -> str:
    """Render a single <tag>...</tag> block.  Empty bodies render as <tag/>."""
    body = body.strip("\n")
    if not body:
        return f"<{tag}/>"
    return f"<{tag}>\n{body}\n</{tag}>"


def build_xml_prompt(
    sections: Mapping[str, str],
    *,
    extra_order: Optional[Iterable[str]] = None,
    omit_empty: bool = True,
) -> str:
    """
    Build a single XML-tagged prompt string from a mapping of section bodies.

    Parameters
    ----------
    sections : Mapping[str, str]
        Section name -> body text.  Keys are normalized to snake_case and used
        as XML tag names.  Bodies are emitted verbatim (no escaping); callers
        are responsible for not embedding their own conflicting tags.
    extra_order : Iterable[str] | None
        Optional override that prepends additional tag names to the canonical
        order (useful when a caller introduces a new vocabulary item that has
        not yet been promoted to CANONICAL_SECTION_ORDER).
    omit_empty : bool
        When True (default), sections whose body is empty/whitespace are
        skipped entirely rather than rendered as <tag/>.

    Returns
    -------
    str
        The fully assembled prompt.  Caller passes this directly to call_ai_api.
    """
    normalized: Dict[str, str] = {
        _normalize_tag(k): v for k, v in sections.items()
    }

    if omit_empty:
        normalized = {k: v for k, v in normalized.items() if v and v.strip()}

    order: List[str] = []
    if extra_order:
        order.extend(_normalize_tag(t) for t in extra_order)
    for tag in CANONICAL_SECTION_ORDER:
        if tag not in order:
            order.append(tag)

    seen: set = set()
    out: List[str] = []
    for tag in order:
        if tag in normalized and tag not in seen:
            out.append(_render_section(tag, normalized[tag]))
            seen.add(tag)

    # Append any extra sections the caller passed in that we don't yet know
    # about so nothing is silently dropped.
    for tag, body in normalized.items():
        if tag in seen:
            continue
        logger.debug(
            "build_xml_prompt: unknown section %r appended at end; consider "
            "adding it to CANONICAL_SECTION_ORDER.",
            tag,
        )
        out.append(_render_section(tag, body))

    return "\n\n".join(out)


__all__ = [
    "CANONICAL_SECTION_ORDER",
    "SECTION_DESCRIPTIONS",
    "build_xml_prompt",
]
