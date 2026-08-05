"""
Stop Rules: inviolable boundaries for AI coding agents.

Per the research, LLMs treat capitalized absolute constraints
(NEVER / ALWAYS / MUST) very differently from soft preferences.  The optimal
syntax is:

    NEVER [action] without [condition] - because [reason]

The "because" clause is essential: it gives the model a semantic anchor so the
rule generalizes correctly to unforeseen edge cases instead of being treated
as an arbitrary prohibition the agent will try to circumvent.

This module is the single source of truth for generated Stop Rules and is
consumed by the tier renderer (Phase 2) and the XML prompt builder (Phase 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StopRule:
    """A single inviolable boundary."""

    action: str   # imperative verb phrase that is forbidden absent a condition
    condition: str  # the gate that, if satisfied, makes the action allowed
    reason: str   # the underlying "why" - critical for generalization

    def render(self) -> str:
        return f"- NEVER {self.action} without {self.condition} - because {self.reason}."


# ---------------------------------------------------------------------------
# Project-agnostic defaults
# ---------------------------------------------------------------------------

UNIVERSAL_STOP_RULES: List[StopRule] = [
    StopRule(
        action="commit secrets, API keys, tokens, or .env files",
        condition="running `git secrets --scan` (or equivalent) first",
        reason="leaked credentials persist in git history forever and cost real money to rotate",
    ),
    StopRule(
        action="run destructive shell commands (`rm -rf`, `DROP TABLE`, force-push)",
        condition="echoing the exact command for the user and waiting for confirmation",
        reason="agents have no undo for filesystem or database mutations",
    ),
    StopRule(
        action="use `git add .` or `git commit -A`",
        condition="staging files one by one with explicit paths",
        reason="bulk staging silently captures secrets, build artifacts, and unrelated work",
    ),
    StopRule(
        action="modify authentication, authorization, or payment code paths",
        condition="writing a failing test that reproduces the desired behaviour first",
        reason="security regressions are extremely expensive and rarely caught in code review",
    ),
    StopRule(
        action="run `eval`, `exec`, `Function(...)`, or any dynamic-code primitive on user input",
        condition="proving the input is constrained to a fixed whitelist",
        reason="dynamic execution is the most common remote-code-execution vector",
    ),
    StopRule(
        action="concatenate strings into SQL, shell, or HTML",
        condition="using parameterized queries, `shlex`, or a templating engine with auto-escape",
        reason="string concatenation is the canonical injection vulnerability",
    ),
    StopRule(
        action="invent APIs, library functions, or CLI flags",
        condition="verifying them in the actual source / docs (search the codebase first)",
        reason="hallucinated symbols compile-fail and waste reviewer time",
    ),
]


# ---------------------------------------------------------------------------
# Language- and toolchain-specific defaults
# ---------------------------------------------------------------------------

LANGUAGE_STOP_RULES: Dict[str, List[StopRule]] = {
    "python": [
        StopRule(
            action="merge code that fails `pytest -q`",
            condition="all tests in the touched package pass locally",
            reason="CI is slow and broken main blocks every other contributor",
        ),
        StopRule(
            action="add a runtime dependency",
            condition="declaring it in `pyproject.toml` / `requirements.txt`",
            reason="undeclared deps work on the author's machine and break in CI/prod",
        ),
        StopRule(
            action="catch bare `Exception` or `BaseException`",
            condition="re-raising with `raise` or logging the exception with `exc_info=True`",
            reason="silent except blocks hide real bugs",
        ),
    ],
    "typescript": [
        StopRule(
            action="use `any` or `@ts-ignore`",
            condition="adding a comment explaining why the type system can't express the invariant",
            reason="`any` poisons the type checker for every downstream call site",
        ),
        StopRule(
            action="ship code that fails `tsc --noEmit`",
            condition="all type errors in the touched files are resolved",
            reason="type errors compound; one ignored error hides ten more",
        ),
        StopRule(
            action="run `npm run build`",
            condition="the user explicitly asks - CI handles builds",
            reason="local builds kill watch processes and rarely match CI",
        ),
    ],
    "javascript": [
        StopRule(
            action="use `var`",
            condition="targeting an environment older than ES2015",
            reason="`var` has confusing hoisting and function-scoped semantics",
        ),
        StopRule(
            action="run `npm install <pkg>`",
            condition="the package is added to `package.json` with a pinned range",
            reason="floating versions cause non-reproducible builds",
        ),
    ],
    "go": [
        StopRule(
            action="ignore returned errors",
            condition="explicitly assigning to `_` with a comment explaining why",
            reason="ignored errors are Go's #1 production-incident source",
        ),
        StopRule(
            action="call `panic`",
            condition="the program literally cannot continue (unrecoverable invariant violation)",
            reason="panics propagate across goroutines and crash the whole binary",
        ),
    ],
    "rust": [
        StopRule(
            action="call `.unwrap()` or `.expect()`",
            condition="proving the `Option`/`Result` cannot be `None`/`Err`",
            reason="unwrap panics in production; use `?` or pattern-match instead",
        ),
        StopRule(
            action="use `unsafe`",
            condition="documenting every invariant the block relies on in a `// SAFETY:` comment",
            reason="unsafe blocks bypass the borrow checker - bugs become memory corruption",
        ),
    ],
    "java": [
        StopRule(
            action="catch generic `Exception`",
            condition="re-throwing as a more specific runtime exception",
            reason="broad catches hide bugs and obscure the failure surface",
        ),
    ],
    "kotlin": [
        StopRule(
            action="use `!!` (non-null assertion)",
            condition="using `?.let`, `requireNotNull`, or an explicit null check instead",
            reason="`!!` throws NullPointerException at runtime",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Framework-specific defaults
# ---------------------------------------------------------------------------

FRAMEWORK_STOP_RULES: Dict[str, List[StopRule]] = {
    "django": [
        StopRule(
            action="run `python manage.py migrate` against production",
            condition="reviewing the generated SQL with `sqlmigrate` and getting a +1",
            reason="migrations are not transactional on all backends and can lock tables",
        ),
    ],
    "fastapi": [
        StopRule(
            action="return raw ORM objects from an endpoint",
            condition="wrapping them in a Pydantic response model",
            reason="leaking ORM internals exposes columns that should never be public",
        ),
    ],
    "react": [
        StopRule(
            action="call hooks conditionally or inside loops",
            condition="they're at the top level of a component or custom hook",
            reason="React relies on call order to associate state with hooks",
        ),
    ],
    "nextjs": [
        StopRule(
            action="import server-only modules into client components",
            condition="guarding the import with `'server-only'`",
            reason="bundling server secrets into the client is a critical leak",
        ),
    ],
    "prisma": [
        StopRule(
            action="run `prisma db push`",
            condition="showing the generated migration plan and getting confirmation",
            reason="`db push` skips migration history and can drop columns",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Selection / rendering helpers
# ---------------------------------------------------------------------------

def collect_stop_rules(
    language: Optional[str] = None,
    frameworks: Optional[List[str]] = None,
    *,
    include_universal: bool = True,
) -> List[StopRule]:
    """
    Collect the relevant set of Stop Rules for a project.

    Order: universal first, then language-specific, then per-framework.
    Duplicates (same action+condition) are de-duplicated.
    """
    out: List[StopRule] = []
    seen: set = set()

    def _add(rule: StopRule) -> None:
        key = (rule.action, rule.condition)
        if key in seen:
            return
        seen.add(key)
        out.append(rule)

    if include_universal:
        for r in UNIVERSAL_STOP_RULES:
            _add(r)

    if language:
        for r in LANGUAGE_STOP_RULES.get(language.lower(), []):
            _add(r)

    for fw in frameworks or []:
        for r in FRAMEWORK_STOP_RULES.get(fw.lower(), []):
            _add(r)

    return out


def render_stop_rules_block(
    language: Optional[str] = None,
    frameworks: Optional[List[str]] = None,
    *,
    title: str = "Stop Rules",
    include_universal: bool = True,
) -> str:
    """
    Render a complete Markdown ## section ready to embed in a rule file or in
    the <stop_rules> tag of an XML prompt.
    """
    rules = collect_stop_rules(
        language=language,
        frameworks=frameworks,
        include_universal=include_universal,
    )
    lines = [f"## {title}", ""]
    lines.append(
        "These are inviolable. Each rule follows the form "
        "`NEVER [action] without [condition] - because [reason]`. "
        "The 'because' clause is the source of truth; if the condition cannot "
        "be met, stop and ask the user."
    )
    lines.append("")
    for r in rules:
        lines.append(r.render())
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "StopRule",
    "UNIVERSAL_STOP_RULES",
    "LANGUAGE_STOP_RULES",
    "FRAMEWORK_STOP_RULES",
    "collect_stop_rules",
    "render_stop_rules_block",
]
