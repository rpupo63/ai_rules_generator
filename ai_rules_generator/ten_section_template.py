"""
The Universal 10-Section Template for global AI rule files (CLAUDE.md and
equivalents).

Per the research, a well-structured global context file pre-emptively answers
every logistical question an AI might encounter when navigating a proprietary
codebase.  The ten sections below are derived directly from that recommended
template.

Each section is declared as a `Section` dataclass with:

    - `name`              : human-readable title (used as the ## heading)
    - `xml_tag`           : matching tag for the XML prompt vocabulary
    - `max_lines`         : per-section token budget (hard cap)
    - `description`       : 1-line explainer (for docs)
    - `required`          : whether to always emit the section, even if empty
    - `default_source`    : function name (string) the renderer should call to
                            populate the section if no body is supplied

The renderer (Phase 2) iterates over `SECTIONS` in order, truncating each body
to `max_lines` lines and emitting a `[... continues in <skill> ...]` pointer
when overflow occurs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Section:
    name: str
    xml_tag: str
    max_lines: int
    description: str
    required: bool = True
    default_source: Optional[str] = None


# The canonical 10-section ordering.  Total budget at default caps: ~340 lines,
# which leaves headroom under the recommended 500-line ceiling for global
# rule files.
SECTIONS: List[Section] = [
    Section(
        name="Project Overview",
        xml_tag="project_identity",
        max_lines=30,
        description=(
            "What the product does, who it's for, and what it optimizes for "
            "(speed vs security vs cost)."
        ),
        default_source="render_project_overview",
    ),
    Section(
        name="Tech Stack",
        xml_tag="tech_stack",
        max_lines=25,
        description=(
            "Primary language, frameworks, runtime / interpreter versions, "
            "key SaaS dependencies."
        ),
        default_source="render_tech_stack",
    ),
    Section(
        name="Architecture Snapshot",
        xml_tag="architecture_snapshot",
        max_lines=40,
        description=(
            "Non-obvious architectural choices and the layering rules the AI "
            "must not silently refactor away."
        ),
        default_source="render_architecture_snapshot",
    ),
    Section(
        name="Dev Commands",
        xml_tag="dev_commands",
        max_lines=20,
        description=(
            "Exact invocations for test, lint, build, and local server start."
        ),
        default_source="render_dev_commands",
    ),
    Section(
        name="Key File Index",
        xml_tag="key_file_index",
        max_lines=30,
        description=(
            "Pointers to critical entry points so the agent doesn't waste "
            "tokens on exploratory directory walks."
        ),
        default_source="render_key_file_index",
    ),
    Section(
        name="Repo Map",
        xml_tag="repo_map",
        max_lines=40,
        description=(
            "Top-N PageRank-ranked symbols from the Graph RAG layer, plus "
            "their most important edges."
        ),
        required=False,
        default_source="render_repo_map_placeholder",
    ),
    Section(
        name="Off-Limits Zones",
        xml_tag="off_limits",
        max_lines=20,
        description=(
            "Read-only paths (auth, payments, migrations) requiring human "
            "review before modification."
        ),
        default_source="render_off_limits",
    ),
    Section(
        name="External Service Notes",
        xml_tag="external_services",
        max_lines=25,
        description=(
            "Third-party APIs: rate limits, staging URLs, test-key conventions."
        ),
        required=False,
        default_source="render_external_services",
    ),
    Section(
        name="Style Guide",
        xml_tag="style_guide",
        max_lines=30,
        description=(
            "Naming conventions, formatting tools, idiomatic patterns "
            "specific to this codebase."
        ),
        default_source="render_style_guide",
    ),
    Section(
        name="Stop Rules",
        xml_tag="stop_rules",
        max_lines=40,
        description=(
            "Inviolable boundaries in `NEVER [action] without [condition] - "
            "because [reason]` form."
        ),
        default_source="render_stop_rules",
    ),
]


# Lookup helpers --------------------------------------------------------------

_BY_NAME = {s.name: s for s in SECTIONS}
_BY_TAG = {s.xml_tag: s for s in SECTIONS}


def get_section_by_name(name: str) -> Optional[Section]:
    return _BY_NAME.get(name)


def get_section_by_tag(tag: str) -> Optional[Section]:
    return _BY_TAG.get(tag)


def total_max_lines() -> int:
    """Sum of all per-section caps - a hard upper bound on a global file."""
    return sum(s.max_lines for s in SECTIONS)


__all__ = [
    "Section",
    "SECTIONS",
    "get_section_by_name",
    "get_section_by_tag",
    "total_max_lines",
]
