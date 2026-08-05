"""
Load and analyze existing AGENTS.md so generated context can complement it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .agents_addendum import constitution_body


# Topics we treat as "already covered" when headings/keywords match.
TOPIC_PATTERNS: Dict[str, List[re.Pattern]] = {
    "purpose": [
        re.compile(r"\bpurpose\b", re.I),
        re.compile(r"^#\s+\S+", re.M),  # title often carries purpose
    ],
    "commands": [
        re.compile(r"^##\s*(commands|dev commands|build|test)\b", re.I | re.M),
        re.compile(r"```(?:bash|sh|shell)", re.I),
    ],
    "architecture": [
        re.compile(r"^##\s*(architecture|layout|structure)\b", re.I | re.M),
    ],
    "off_limits": [
        re.compile(r"^##\s*(off[- ]limits|do not touch|boundaries)\b", re.I | re.M),
        re.compile(r"\bnever commit\b", re.I),
        re.compile(r"\bsecrets?\b", re.I),
    ],
    "session_handoff": [
        re.compile(r"session[- ]handoff|\.agent-sessions", re.I),
    ],
    "memory": [
        re.compile(r"memory mcp|durable (facts|corrections)", re.I),
        re.compile(r"project:<", re.I),
    ],
    "permissions": [
        re.compile(r"permissions\.json|propagate-allow|always.?allow", re.I),
    ],
    "deploy": [
        re.compile(r"^##\s*deploy", re.I | re.M),
        re.compile(r"\b(racknerd|tailscale|deploy)\b", re.I),
    ],
    "access": [
        re.compile(r"\b(tailscale|ssh|magicdns)\b", re.I),
    ],
    "stack": [
        re.compile(r"\b(stack|tech stack|languages?|frameworks?)\b", re.I),
    ],
    "workflow": [
        re.compile(r"^##\s*(workflow|conventions|git|branching)\b", re.I | re.M),
        re.compile(r"\b(feature branch|commit to main|pull request|\bPR\b)\b", re.I),
    ],
    "type_safety": [
        re.compile(r"^##\s*(type.?safety|typing|static analysis)\b", re.I | re.M),
        re.compile(r"\b(typescript strict|strictNullChecks|zod|mypy|pyright)\b", re.I),
    ],
}


@dataclass
class Constitution:
    """Parsed view of the user-owned AGENTS.md constitution."""

    path: Optional[Path]
    exists: bool
    raw: str = ""
    body: str = ""  # without context addendum
    title: str = ""
    headings: List[str] = field(default_factory=list)
    covered_topics: Set[str] = field(default_factory=set)
    purpose_excerpt: str = ""
    first_paragraph: str = ""

    def covers(self, topic: str) -> bool:
        return topic in self.covered_topics


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_headings(text: str) -> List[str]:
    headings = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,3})\s+(.+)$", line)
        if m:
            headings.append(m.group(2).strip())
    return headings


def _extract_first_paragraph(text: str) -> str:
    lines = text.splitlines()
    buf: List[str] = []
    started = False
    for line in lines:
        if line.startswith("#"):
            continue
        if not line.strip():
            if started:
                break
            continue
        if line.strip().startswith("<!--"):
            continue
        started = True
        buf.append(line.strip())
        if len(" ".join(buf)) > 280:
            break
    return " ".join(buf).strip()


def _detect_topics(text: str) -> Set[str]:
    covered: Set[str] = set()
    for topic, patterns in TOPIC_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                covered.add(topic)
                break
    return covered


def load_constitution(project_root: Path) -> Constitution:
    """Load AGENTS.md from project_root if present."""
    path = project_root / "AGENTS.md"
    if not path.exists():
        return Constitution(path=path, exists=False)

    raw = path.read_text(encoding="utf-8")
    body = constitution_body(raw)
    title = _extract_title(body)
    first = _extract_first_paragraph(body)
    return Constitution(
        path=path,
        exists=True,
        raw=raw,
        body=body,
        title=title,
        headings=_extract_headings(body),
        covered_topics=_detect_topics(body),
        purpose_excerpt=first[:400],
        first_paragraph=first,
    )


def covered_topics_markdown(constitution: Constitution) -> str:
    """Human-readable index of topics already in AGENTS.md."""
    if not constitution.exists:
        return (
            "No `AGENTS.md` constitution found. "
            "Prefer Sync `install-repo-identity.sh` for purpose, commands, "
            "and boundaries."
        )
    if not constitution.covered_topics:
        return (
            "`AGENTS.md` exists but no standard topics were detected. "
            "Still prefer it for human-authored project facts."
        )
    labels = {
        "purpose": "Purpose / identity",
        "commands": "Commands / Dev Commands",
        "architecture": "Architecture / layout",
        "off_limits": "Off-limits / secrets policy",
        "session_handoff": "Session handoffs",
        "memory": "Memory MCP pointers",
        "permissions": "Permissions / always-allow",
        "deploy": "Deploy targets",
        "access": "Access model",
        "stack": "Stack mentions",
        "workflow": "Workflow / branching",
        "type_safety": "Type safety",
    }
    bullets = []
    for key in sorted(constitution.covered_topics):
        bullets.append(f"- **{labels.get(key, key)}** — already in `AGENTS.md`")
    return "\n".join(bullets)


# Heading keywords used to pull section bodies for edit packs.
_TOPIC_HEADING_HINTS: Dict[str, List[re.Pattern]] = {
    "architecture": [
        re.compile(r"^(architecture|layout|structure|entity relationships)\b", re.I),
    ],
    "commands": [
        re.compile(r"^(commands|dev commands|build|test)\b", re.I),
    ],
    "off_limits": [
        re.compile(r"^(off[- ]limits|do not touch|boundaries|gotchas)\b", re.I),
    ],
    "deploy": [
        re.compile(r"^deploy\b", re.I),
    ],
    "workflow": [
        re.compile(r"^(workflow|conventions|git|branching)\b", re.I),
    ],
    "type_safety": [
        re.compile(r"^(type.?safety|typing)\b", re.I),
    ],
    "seed": [
        re.compile(r"^(seed|seeding|seed system)\b", re.I),
    ],
    "gotchas": [
        re.compile(r"^gotchas?\b", re.I),
    ],
}


# Path segment → extra topics to pull into an edit pack.
PATH_TOPIC_HINTS: Dict[str, List[str]] = {
    "seed": ["seed", "gotchas", "architecture"],
    "api": ["architecture", "gotchas"],
    "database": ["architecture", "gotchas"],
    "services": ["architecture"],
    "models": ["architecture", "gotchas"],
    "frontend": ["architecture", "type_safety"],
    "e2e": ["commands"],
}


def _split_heading_blocks(body: str) -> List[Tuple[str, str]]:
    """Split markdown into (heading_text, section_body) pairs.

    Split only on `##` (H2) so `###` subsections stay inside the parent
    contract block (e.g. Architecture → Backend / Gotchas).
    """
    lines = body.splitlines()
    blocks: List[Tuple[str, List[str]]] = []
    current_heading = ""
    current_lines: List[str] = []
    for line in lines:
        m = re.match(r"^(#{2})\s+(.+)$", line)
        if m:
            if current_heading or any(l.strip() for l in current_lines):
                blocks.append((current_heading, current_lines))
            current_heading = m.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading or any(l.strip() for l in current_lines):
        blocks.append((current_heading, current_lines))
    return [(h, "\n".join(ls).strip()) for h, ls in blocks]


def _prefer_architecture_subsection(section: str, path_rel: str) -> str:
    """
    When Architecture has ### Backend / ### Frontend, keep the matching slice.
    """
    parts = path_rel.replace("\\", "/").strip("/").lower().split("/")
    prefer: Optional[str] = None
    if "backend" in parts or any(
        p in parts for p in ("api", "seed", "services", "database", "models", "cmd")
    ):
        prefer = "Backend"
    elif "frontend" in parts or any(
        p in parts for p in ("components", "pages", "hooks", "src")
    ):
        prefer = "Frontend"
    if not prefer:
        return section

    # Split on ### headings inside the H2 block
    lines = section.splitlines()
    chunks: List[Tuple[str, List[str]]] = []
    cur_h = ""
    cur: List[str] = []
    preamble: List[str] = []
    started = False
    for line in lines:
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            if not started and cur:
                preamble = cur
            elif cur_h or cur:
                chunks.append((cur_h, cur))
            started = True
            cur_h = m.group(1).strip()
            cur = [line]
        else:
            cur.append(line)
    if cur_h or (started and cur):
        chunks.append((cur_h, cur))
    elif not started and cur:
        return section

    for h, body_lines in chunks:
        if h.lower().startswith(prefer.lower()):
            # Keep H2 title line if present in preamble
            title = []
            for ln in preamble:
                if ln.startswith("## "):
                    title.append(ln)
                    title.append("")
                    break
            return "\n".join(title + body_lines).strip()
    return section


def extract_topic_sections(
    constitution: Constitution,
    topics: List[str],
    *,
    max_chars_per_section: int = 900,
    path_rel: str = "",
) -> List[Tuple[str, str]]:
    """
    Pull AGENTS.md heading blocks matching requested topics.

    Returns list of (topic, markdown_section) without dumping the whole file.
    When `path_rel` is set, Architecture may be trimmed to Backend/Frontend.
    """
    if not constitution.exists or not constitution.body.strip():
        return []

    wanted = [t for t in topics if t]
    if not wanted:
        return []

    blocks = _split_heading_blocks(constitution.body)
    found: List[Tuple[str, str]] = []
    seen_headings: Set[str] = set()

    for topic in wanted:
        hints = _TOPIC_HEADING_HINTS.get(topic) or [
            re.compile(rf"^{re.escape(topic)}\b", re.I)
        ]
        for heading, section in blocks:
            if not heading or heading in seen_headings:
                continue
            if any(h.search(heading) for h in hints):
                text = section.strip()
                if topic == "architecture" and path_rel:
                    text = _prefer_architecture_subsection(text, path_rel)
                if len(text) > max_chars_per_section:
                    text = text[: max_chars_per_section - 1].rstrip() + "…"
                found.append((topic, text))
                seen_headings.add(heading)
                break

    return found


def topics_for_edit_path(path_rel: str) -> List[str]:
    """Default AGENTS topics for an edit pack seeded at `path_rel`."""
    parts = path_rel.replace("\\", "/").strip("/").lower().split("/")
    topics: List[str] = ["architecture", "off_limits"]
    for part in parts:
        for extra in PATH_TOPIC_HINTS.get(part, []):
            if extra not in topics:
                topics.append(extra)
    # Always consider gotchas when present in AGENTS (cheap if missing).
    if "gotchas" not in topics:
        topics.append("gotchas")
    return topics
