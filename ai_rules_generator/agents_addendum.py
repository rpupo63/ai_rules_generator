"""
Idempotent AGENTS.md pointer addendum for complementary codebase context.

Never rewrites user constitution content outside the delimited markers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

BEGIN_MARKER = "<!-- codebase-context:begin -->"
END_MARKER = "<!-- codebase-context:end -->"

DEFAULT_ADDENDUM_BODY = """## Additional codebase context

Optional orientation map (complements this file; do not treat as constitution):
- `.ai-context/CODEBASE.md` — What / How / Why surfaces + entrypoints
- Surface digests: `.ai-context/modules/` (or `ai-rules-generator context show <path>`)
"""


def soft_addendum_body(
    *,
    has_practices: bool = False,
    has_graph: bool = False,
    edit_pack_focused: bool = True,
) -> str:
    """Softer AGENTS pointer used by the lean context pipeline."""
    if edit_pack_focused:
        lines = [
            "## Additional codebase context",
            "",
            "Structural context for agents (complements this file; do not treat as constitution):",
            "- Before editing deep paths: "
            "`ai-rules-generator context for <path>` "
            "(ancestor roles + blast-radius neighborhood + matched AGENTS slices)",
            "- Optional orientation: `.ai-context/CODEBASE.md` "
            "(entrypoints + evidenced conventions)",
            "- Folder digests: `ai-rules-generator context show <path>`",
        ]
    else:
        lines = [
            "## Additional codebase context",
            "",
            "Optional orientation map (complements this file; do not treat as constitution):",
            "- `.ai-context/CODEBASE.md` — What / How / Why surfaces + entrypoints",
            "- Deeper folders: `ai-rules-generator context show <path>` "
            "(or `.ai-context/modules/` digests when present)",
        ]
    if has_practices:
        lines.append("- Language/framework practices: `.ai-context/practices/`")
    if has_graph:
        lines.append("- Graph / repo map: `.ai-context/graph/`")
    return "\n".join(lines) + "\n"


def render_addendum_block(body: Optional[str] = None) -> str:
    """Return the full delimited addendum block (no trailing newline after end)."""
    inner = (body if body is not None else DEFAULT_ADDENDUM_BODY).rstrip() + "\n"
    return f"{BEGIN_MARKER}\n{inner}{END_MARKER}"


def strip_addendum(text: str) -> str:
    """Return AGENTS.md text with any existing context addendum removed."""
    start = text.find(BEGIN_MARKER)
    if start < 0:
        return text
    end = text.find(END_MARKER, start)
    if end < 0:
        # Malformed: drop from begin marker to EOF
        return text[:start].rstrip() + ("\n" if text[:start].strip() else "")
    end_inclusive = end + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end_inclusive:].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return (before or after).rstrip() + ("\n" if (before or after) else "")


def constitution_body(text: str) -> str:
    """User-owned AGENTS.md content excluding the context addendum."""
    return strip_addendum(text).rstrip() + ("\n" if text.strip() else "")


def apply_addendum(
    text: str,
    *,
    body: Optional[str] = None,
) -> str:
    """
    Ensure exactly one delimited addendum at EOF.

    Preserves all content outside markers. Replaces an existing block in place
    when markers are present; otherwise appends at end.
    """
    block = render_addendum_block(body)
    start = text.find(BEGIN_MARKER)
    if start >= 0:
        end = text.find(END_MARKER, start)
        if end >= 0:
            end_inclusive = end + len(END_MARKER)
            before = text[:start].rstrip()
            after = text[end_inclusive:].lstrip("\n")
            parts = [p for p in (before, block, after) if p]
            result = "\n\n".join(parts) if before or after else block
            return result.rstrip() + "\n"
        # Begin without end: truncate from begin and append fresh block
        before = text[:start].rstrip()
        return (before + "\n\n" + block if before else block).rstrip() + "\n"

    base = text.rstrip()
    if not base:
        return block.rstrip() + "\n"
    return base + "\n\n" + block.rstrip() + "\n"


def minimal_agents_stub(project_name: str) -> str:
    """Minimal AGENTS.md when none exists (title + addendum only)."""
    title = f"# {project_name}\n\n"
    note = (
        "Constitution not found. Prefer Sync "
        "`install-repo-identity.sh` (or hand-write purpose, commands, "
        "and boundaries here). Structural context is generated separately.\n\n"
    )
    return apply_addendum(title + note)


def patch_agents_md(
    project_root: Path,
    *,
    dry_run: bool = False,
    addendum_body: Optional[str] = None,
) -> Tuple[str, bool, Optional[str]]:
    """
    Patch or create AGENTS.md with the context pointer addendum.

    Returns (new_text, created_stub, previous_constitution_body).
    When dry_run is True, does not write to disk.
    """
    agents_path = project_root / "AGENTS.md"
    created_stub = False
    previous_constitution: Optional[str] = None

    if agents_path.exists():
        original = agents_path.read_text(encoding="utf-8")
        previous_constitution = constitution_body(original)
        new_text = apply_addendum(original, body=addendum_body)
    else:
        created_stub = True
        previous_constitution = ""
        new_text = minimal_agents_stub(project_root.name)

    if not dry_run:
        agents_path.write_text(new_text, encoding="utf-8")

    return new_text, created_stub, previous_constitution
