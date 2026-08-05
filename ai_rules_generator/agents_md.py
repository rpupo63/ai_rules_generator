"""
Canonical AGENTS.md renderer - the single source of truth entry point.

Every supported AI coding tool "meets in the middle" here: native AGENTS.md
readers (Cursor, Codex, Windsurf, Warp, Devin, Copilot) load this file
directly; the rest (Claude Code -> CLAUDE.md, Gemini -> GEMINI.md) reach it
via symlink/import (see `linker.py`).

AGENTS.md holds the *always-on* content (identity, Stop Rules, dev commands,
off-limits, a repo-map digest, and a pointer index into `.ai-rules/` and
`.cursor/rules/`).  Deep dives live in `.ai-rules/skills/`; glob-scoped
per-folder rules live in `.cursor/rules/<folder>.mdc`.
"""

from __future__ import annotations

from typing import Any, List, Optional

from .generators import generate_project_context
from .models import ProjectConfig
from .stop_rules import render_stop_rules_block


# Canonical filename + the conventional spoke files that point back here.
AGENTS_FILENAME = "AGENTS.md"


DEFAULT_OFF_LIMITS = (
    "- `**/.env*` - environment secrets\n"
    "- `**/migrations/**` - database migrations (human review required)\n"
    "- `**/auth/**`, `**/payments/**` - security-critical code\n"
    "- `**/node_modules/**`, `**/.venv/**`, `**/dist/**`, "
    "`**/build/**` - generated / vendored"
)


def build_dev_commands(language: str) -> str:
    """Return language-aware default Dev Commands as a Markdown bullet list."""
    cmds = {
        "python": [
            "- Install: `pip install -e .` (or `pip install -r requirements.txt`)",
            "- Test: `pytest -q`",
            "- Lint: `ruff check .` (or `flake8 .`)",
            "- Format: `black .` / `ruff format .`",
            "- Type-check: `mypy .` (when configured)",
        ],
        "typescript": [
            "- Install: `npm ci` (use `npm install` only when changing deps)",
            "- Test: `npm test` (run a single test with `npm test -- <pattern>`)",
            "- Lint: `npm run lint`",
            "- Type-check: `npx tsc --noEmit`",
            "- Build: do NOT run locally; CI handles builds",
        ],
        "javascript": [
            "- Install: `npm ci`",
            "- Test: `npm test`",
            "- Lint: `npm run lint`",
        ],
        "go": [
            "- Test: `go test ./...`",
            "- Lint: `go vet ./...` and `golangci-lint run`",
            "- Build: `go build ./...`",
            "- Tidy: `go mod tidy`",
        ],
        "rust": [
            "- Test: `cargo test`",
            "- Lint: `cargo clippy -- -D warnings`",
            "- Format: `cargo fmt`",
            "- Build: `cargo build`",
        ],
        "java": [
            "- Test: `mvn test` (Maven) or `./gradlew test` (Gradle)",
            "- Build: `mvn package` / `./gradlew build`",
        ],
    }
    return "\n".join(cmds.get(language.lower(), []))


# Roles considered high-signal entry points for the Key File Index.
_HIGH_VALUE_ROLES = {
    "application entry point",
    "server entry point",
    "Go entry point",
    "Rust binary entry point",
    "Rust library entry point",
    "barrel export / entry point",
    "Node.js project configuration",
    "TypeScript compiler configuration",
    "Python project configuration",
    "Rust project configuration",
    "Go module configuration",
    "Docker Compose configuration",
    "OpenAPI specification",
    "Prisma database schema",
    "Django management script",
}


def build_key_file_index(scan_ctx: Optional[Any], limit: int = 20) -> str:
    """Build a short bullet list of high-signal entry points from a scan."""
    if scan_ctx is None or not getattr(scan_ctx, "flat", None):
        return ""

    bullets: List[str] = []
    seen: set = set()
    for folder in scan_ctx.flat:
        for f in folder.files:
            if f.role not in _HIGH_VALUE_ROLES:
                continue
            rel = f"{folder.path}/{f.name}" if folder.path else f.name
            if rel in seen:
                continue
            seen.add(rel)
            bullets.append(f"- `{rel}` - {f.role}")
            if len(bullets) >= limit:
                return "\n".join(bullets)
    return "\n".join(bullets)


def render_maintenance_block() -> str:
    """The 'keep the context current' directives injected into AGENTS.md.

    Written in the Stop-Rule `NEVER ... without ... - because ...` /
    `ALWAYS ... - because ...` schema so agents treat it as binding.
    """
    return (
        "## Keeping This Context Current\n\n"
        "This context is only useful if it stays in sync with the code. "
        "Treat the following as binding:\n\n"
        "- ALWAYS update the matching `.cursor/rules/<folder>.mdc` (or run "
        "`ai-rules-generator update`) after you add, rename, or delete a "
        "folder - because stale folder maps silently misroute every future "
        "agent.\n"
        "- ALWAYS refresh the relevant skeleton / Call Flow when you add or "
        "remove a public symbol (exported function, type, route) - because "
        "an agent that trusts an outdated signature will write code that "
        "does not compile.\n"
        "- ALWAYS update the Dev Commands above when build, test, or lint "
        "commands change - because hallucinated commands waste real time.\n"
        "- NEVER hand-edit a symlinked entry file (e.g. `CLAUDE.md`, "
        "`GEMINI.md`, `.github/copilot-instructions.md`) - because they "
        "resolve to `AGENTS.md`; edit `AGENTS.md` instead.\n"
        "- When in doubt, run `ai-rules-generator update` from the repo root "
        "to regenerate this file, the Tier-2 rules, and the repo map.\n"
        "\nSee `.ai-rules/skills/maintaining-context.md` for the full "
        "workflow."
    )


def render_pointer_index(config: ProjectConfig) -> str:
    """The 'how agents should use this repo' routing section."""
    return (
        "## How Agents Should Use This Repo\n\n"
        "This file is the always-on context. Everything else is reachable "
        "from here:\n\n"
        "- **Glob-scoped folder rules**: `.cursor/rules/<folder>.mdc` attach "
        "automatically (Cursor) or can be read on demand. They contain the "
        "per-folder skeleton, Call Flow, and Used-By context. Read the one "
        "matching the folder you are about to edit.\n"
        "- **Deep-dive skills**: `.ai-rules/skills/*.md` hold language / "
        "framework / architecture guidance. Read on demand (e.g. "
        "`@coding-principles`, or `Read` the file).\n"
        "- **Repo map**: `.ai-rules/graph/repo-map.md` is the full "
        "PageRank-ranked symbol index.\n"
        "- **Index**: `.ai-rules/README.md` lists every available rule file.\n\n"
        "### Workflow\n"
        "1. Obey the Stop Rules above without exception.\n"
        "2. SEARCH FIRST: match existing patterns before inventing new ones.\n"
        "3. Read the Tier-2 `.cursor/rules/<folder>.mdc` for the folder you "
        "are editing.\n"
        "4. Pull a Tier-3 skill when you need framework or architectural "
        "depth.\n"
        "5. VERIFY: run the Dev Commands (typecheck, lint, tests) for the "
        "touched package before finishing."
    )


def render_agents_md(
    config: ProjectConfig,
    *,
    repo_map_digest: str = "",
    key_file_index: str = "",
    dev_commands: str = "",
    off_limits: str = "",
    repo_map_inline_lines: int = 30,
    include_maintenance: bool = True,
) -> str:
    """
    Render the canonical `AGENTS.md` body (no frontmatter; AGENTS.md is plain
    Markdown, read natively by most tools).

    Section order keeps the inviolable scaffolding (identity + Stop Rules)
    first so it survives any downstream truncation.
    """
    parts: List[str] = []

    parts.append(f"# {config.description}\n")
    parts.append(
        "> Canonical AI agent context for this repository. All AI coding "
        "tools are routed here (see *How Agents Should Use This Repo*). "
        "Edit this file - not the symlinked tool entry points."
    )

    parts.append(generate_project_context(config).strip())

    parts.append(
        "## Optimization Goals\n\n"
        "- Be conservative: this is production code; prefer the smallest "
        "diff that satisfies the task.\n"
        "- Match existing patterns before introducing new ones.\n"
        "- Surface trade-offs explicitly rather than picking silently."
    )

    # Stop Rules first among the "content" blocks - inviolable.
    parts.append(render_stop_rules_block(
        language=config.primary_language,
        frameworks=config.frameworks,
    ).rstrip())

    dev = dev_commands.strip() or build_dev_commands(config.primary_language)
    if dev:
        parts.append("## Dev Commands\n\n" + dev)

    parts.append(
        "## Off-Limits Zones\n\n" + (off_limits.strip() or DEFAULT_OFF_LIMITS)
    )

    digest = _digest_repo_map(repo_map_digest, repo_map_inline_lines)
    if digest:
        parts.append("## Repo Map (top-ranked symbols)\n\n" + digest)

    if key_file_index.strip():
        parts.append("## Key File Index\n\n" + key_file_index.strip())

    parts.append(render_pointer_index(config))

    if include_maintenance:
        parts.append(render_maintenance_block())

    return "\n\n".join(parts).rstrip() + "\n"


def _digest_repo_map(digest: str, max_lines: int) -> str:
    """Pre-truncate the repo-map digest for inline embedding in AGENTS.md."""
    if not digest.strip():
        return ""
    lines = digest.strip().splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + (
        "\n_(see `.ai-rules/graph/repo-map.md` for the full ranked list)_"
    )


MAINTAINING_CONTEXT_SKILL = """# Maintaining Context

This repository ships an always-on `AGENTS.md` plus generated rule files.
Keep them fresh so every AI agent stays accurate.

## When to update

- You added, renamed, moved, or deleted a folder.
- You added or removed a public symbol (exported function, type, route,
  CLI command).
- Build, test, lint, or run commands changed.
- A dependency or framework was added or dropped.

## How to update

The fast path regenerates everything deterministically:

```bash
ai-rules-generator update
```

This re-scans the tree, rebuilds the AST skeletons + dependency graph,
rewrites `AGENTS.md`, refreshes the per-folder `.cursor/rules/<folder>.mdc`
Tier-2 files, and re-creates the tool symlinks.

## What NOT to do

- Do not hand-edit `CLAUDE.md`, `GEMINI.md`, or
  `.github/copilot-instructions.md` - they are symlinks/pointers to
  `AGENTS.md`. Edit `AGENTS.md`.
- Do not duplicate rule content into a tool-specific file; the whole point
  of the AGENTS.md hub is a single source of truth.
"""


__all__ = [
    "AGENTS_FILENAME",
    "DEFAULT_OFF_LIMITS",
    "MAINTAINING_CONTEXT_SKILL",
    "build_dev_commands",
    "build_key_file_index",
    "render_agents_md",
    "render_maintenance_block",
    "render_pointer_index",
]
