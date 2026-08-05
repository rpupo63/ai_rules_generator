"""
Global token budget for generated rule artifacts.

A single `TokenBudget` instance is constructed in the orchestrator and
threaded through every emission path (Tier-1, Tier-2, Tier-3, repo-map,
CLAUDE.md).  Each emit attempt either:

  * `force_spend`s text that *must* be written (Stop Rules, identity,
    folder headers); this can exceed the cap but is logged.
  * `try_spend`s optional text; this is atomic - the budget is only
    debited if the text fits.
  * `fit_or_truncate`s text that should fit if at all possible - it
    returns a truncated string when the full text would not fit but a
    useful prefix would.

The budget counts characters' worth of tokens (4 chars ~= 1 token, same
heuristic the rest of the codebase uses via
`ast_compression.estimate_tokens`).  Only LLM-consumable artifacts are
counted - sidecar JSON like `.ai-rules/graph/graph.json` is excluded
because no AI tool ingests it directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ast_compression import estimate_tokens


DEFAULT_GLOBAL_BUDGET = 1_000_000


@dataclass
class Rejection:
    """One record of content that did not make it into the artifacts."""

    kind: str            # candidate.kind ("folder_summary", "skeleton", ...)
    folder: Optional[str]
    requested_tokens: int
    remaining_tokens: int
    reason: str          # "no_room", "truncated", "forced_over"


@dataclass
class Spend:
    """One record of content that DID make it in."""

    kind: str
    folder: Optional[str]
    tokens: int
    truncated: bool = False


@dataclass
class TokenBudget:
    """
    A single-bucket token meter.

    The cap is advisory for `force_spend` (which always succeeds and just
    accumulates over-budget) and strict for `try_spend` /
    `fit_or_truncate`.  Optional content is rejected before any over-budget
    state is reached.
    """

    cap: int = DEFAULT_GLOBAL_BUDGET
    spent: int = 0
    forced_over: int = 0
    rejections: List[Rejection] = field(default_factory=list)
    spends: List[Spend] = field(default_factory=list)

    # ------------------------------------------------------------------ core

    def remaining(self) -> int:
        return max(0, self.cap - self.spent)

    def would_fit(self, text: str) -> bool:
        return estimate_tokens(text) <= self.remaining()

    # ------------------------------------------------------------ accounting

    def force_spend(
        self,
        text: str,
        *,
        kind: str = "forced",
        folder: Optional[str] = None,
    ) -> str:
        """
        Always count the text and return it unchanged.  Used for content
        the renderer has decided is non-negotiable (Stop Rules, identity,
        folder headers).  If this overflows the cap, the excess is tracked
        in `forced_over` for the budget report - we never block emission of
        a Stop Rule because of a budget knob.
        """
        cost = estimate_tokens(text)
        self.spent += cost
        if self.spent > self.cap:
            self.forced_over = self.spent - self.cap
        self.spends.append(Spend(kind=kind, folder=folder, tokens=cost))
        return text

    def try_spend(
        self,
        text: str,
        *,
        kind: str = "optional",
        folder: Optional[str] = None,
    ) -> bool:
        """
        Spend `text`'s tokens iff they fit.  Returns True on success,
        False on rejection (in which case the budget is untouched).
        """
        cost = estimate_tokens(text)
        if cost > self.remaining():
            self.rejections.append(Rejection(
                kind=kind,
                folder=folder,
                requested_tokens=cost,
                remaining_tokens=self.remaining(),
                reason="no_room",
            ))
            return False
        self.spent += cost
        self.spends.append(Spend(kind=kind, folder=folder, tokens=cost))
        return True

    def fit_or_truncate(
        self,
        text: str,
        *,
        kind: str = "optional",
        folder: Optional[str] = None,
        min_useful_chars: int = 200,
        truncation_marker: str = "\n\n_[... truncated to fit the global token budget ...]_\n",
    ) -> Optional[Tuple[str, bool]]:
        """
        Try to emit `text`.  If it fits whole, return `(text, False)` and
        debit the cost.  If it does not fit but at least `min_useful_chars`
        characters could be emitted, return the truncated string with a
        clear pointer and a `truncated=True` flag.  If even that does not
        fit, return None and log a rejection.
        """
        # Fast path: it fits whole.
        if self.try_spend(text, kind=kind, folder=folder):
            return text, False

        # The text didn't fit.  See how much we can fit while leaving room
        # for the truncation marker itself.
        marker_cost = estimate_tokens(truncation_marker)
        room = self.remaining() - marker_cost
        if room <= 0:
            # already logged by try_spend above
            return None

        # estimate_tokens uses chars // 4, so chars budget ~= room * 4.
        char_budget = max(0, room * 4)
        if char_budget < min_useful_chars:
            self.rejections.append(Rejection(
                kind=kind,
                folder=folder,
                requested_tokens=estimate_tokens(text),
                remaining_tokens=self.remaining(),
                reason="below_min_useful",
            ))
            return None

        # Truncate at a line boundary if possible to avoid breaking
        # mid-signature.  Pick the largest prefix whose char count is
        # <= char_budget.
        truncated = _truncate_at_line(text, char_budget)
        candidate = truncated + truncation_marker
        cost = estimate_tokens(candidate)

        # Edge case: rounding might push us over by one token; trim more.
        while cost > self.remaining() and truncated:
            # drop the last line and retry
            if "\n" in truncated:
                truncated = truncated.rsplit("\n", 1)[0]
            else:
                truncated = truncated[: max(0, len(truncated) - 200)]
            candidate = truncated + truncation_marker
            cost = estimate_tokens(candidate)
            if not truncated:
                break

        if not truncated or cost > self.remaining():
            self.rejections.append(Rejection(
                kind=kind,
                folder=folder,
                requested_tokens=estimate_tokens(text),
                remaining_tokens=self.remaining(),
                reason="no_room_after_truncate",
            ))
            return None

        self.spent += cost
        self.spends.append(Spend(
            kind=kind, folder=folder, tokens=cost, truncated=True,
        ))
        return candidate, True

    # ----------------------------------------------------------- diagnostics

    def summary(self) -> str:
        pct = 100.0 * self.spent / max(1, self.cap)
        bits = [
            f"spent {self.spent:,} / {self.cap:,} tokens ({pct:.1f}%)",
        ]
        if self.forced_over > 0:
            bits.append(f"forced {self.forced_over:,} over cap")
        if self.rejections:
            bits.append(f"{len(self.rejections)} sections shed")
        return "TokenBudget: " + ", ".join(bits)

    def report_markdown(self) -> str:
        lines = [
            "# Budget Report",
            "",
            f"- Cap: {self.cap:,} tokens",
            f"- Spent: {self.spent:,} tokens "
            f"({100.0 * self.spent / max(1, self.cap):.1f}%)",
            f"- Forced over cap: {self.forced_over:,} tokens",
            f"- Sections written: {len(self.spends):,}",
            f"- Sections shed: {len(self.rejections):,}",
            "",
        ]
        if self.spends:
            lines.append("## Spending by kind")
            lines.append("")
            by_kind: dict = {}
            for s in self.spends:
                by_kind.setdefault(s.kind, [0, 0])
                by_kind[s.kind][0] += 1
                by_kind[s.kind][1] += s.tokens
            for k in sorted(by_kind, key=lambda x: -by_kind[x][1]):
                count, tokens = by_kind[k]
                lines.append(f"- `{k}`: {count} section(s), {tokens:,} tokens")
            lines.append("")

        if self.rejections:
            lines.append("## Sections shed (priority shedding)")
            lines.append("")
            for r in self.rejections[:200]:
                folder_tag = f" [{r.folder}]" if r.folder else ""
                lines.append(
                    f"- `{r.kind}`{folder_tag}: requested {r.requested_tokens:,} "
                    f"tokens, {r.remaining_tokens:,} remaining at the time "
                    f"({r.reason})"
                )
            if len(self.rejections) > 200:
                lines.append(
                    f"- ... and {len(self.rejections) - 200:,} more"
                )
            lines.append("")
        return "\n".join(lines)


def _truncate_at_line(text: str, char_budget: int) -> str:
    """Return the largest prefix of `text` not exceeding char_budget chars,
    cut on a newline boundary if one exists in the prefix range."""
    if len(text) <= char_budget:
        return text
    prefix = text[:char_budget]
    if "\n" in prefix:
        return prefix.rsplit("\n", 1)[0]
    return prefix


__all__ = [
    "DEFAULT_GLOBAL_BUDGET",
    "Rejection",
    "Spend",
    "TokenBudget",
]
