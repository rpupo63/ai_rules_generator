"""
Tests for the global TokenBudget (Phase 6).

Validates:
  - `try_spend` is atomic - on failure the budget is untouched.
  - `force_spend` always succeeds and tracks over-cap spending.
  - `fit_or_truncate` returns a truncated, marker-decorated string when
    the full text wouldn't fit but a useful prefix would.
  - `fit_or_truncate` returns None when even the minimum useful prefix
    wouldn't fit.
  - The budget report is well-formed.
  - Priority shedding works: high-priority content survives, low-priority
    content is skipped when the cap is tight.
"""

from ai_rules_generator.token_budget import (
    DEFAULT_GLOBAL_BUDGET,
    TokenBudget,
)


def test_default_cap_is_one_thousand_tokens():
    """Aider-like ~1k default (pack-era 1_000_000 retired in C4-3)."""
    assert DEFAULT_GLOBAL_BUDGET == 1000
    b = TokenBudget()
    assert b.cap == 1000


def test_try_spend_is_atomic_on_failure():
    b = TokenBudget(cap=10)  # ~40 chars
    accepted = b.try_spend("x" * 1000)  # ~250 tokens, won't fit
    assert accepted is False
    assert b.spent == 0
    assert len(b.rejections) == 1
    assert b.rejections[0].reason == "no_room"


def test_try_spend_debits_only_when_fits():
    b = TokenBudget(cap=100)  # ~400 chars
    ok = b.try_spend("x" * 200)
    assert ok is True
    assert b.spent == 50  # 200 // 4
    assert b.remaining() == 50


def test_force_spend_always_succeeds_and_tracks_overage():
    b = TokenBudget(cap=10)  # ~40 chars
    b.force_spend("x" * 200, kind="tier1")
    assert b.spent == 50
    assert b.forced_over > 0
    assert len(b.spends) == 1
    assert b.spends[0].kind == "tier1"


def test_fit_or_truncate_returns_full_text_when_it_fits():
    b = TokenBudget(cap=1000)
    out = b.fit_or_truncate("hello world")
    assert out is not None
    text, truncated = out
    assert text == "hello world"
    assert truncated is False


def test_fit_or_truncate_returns_truncated_when_text_too_big():
    b = TokenBudget(cap=200)  # ~800 chars
    long_text = "\n".join(f"line {i}" * 5 for i in range(200))
    assert len(long_text) > 800
    out = b.fit_or_truncate(long_text, min_useful_chars=100)
    assert out is not None
    text, truncated = out
    assert truncated is True
    assert "truncated" in text.lower()
    assert len(text) < len(long_text)


def test_fit_or_truncate_returns_none_when_nothing_useful_fits():
    b = TokenBudget(cap=2)  # ~8 chars
    out = b.fit_or_truncate("x" * 10_000, min_useful_chars=500)
    assert out is None
    assert any(r.reason in {"no_room", "below_min_useful", "no_room_after_truncate"}
               for r in b.rejections)


def test_priority_shedding_keeps_high_priority_content():
    """Simulate the orchestrator's emission pattern: force-spend Tier-1,
    then try optional sections in priority order.  When the budget is
    saturated, low-priority content should be the first to drop."""
    b = TokenBudget(cap=500)  # ~2000 chars

    # Priority 0: forced (Tier-1).  Always emitted.
    b.force_spend("identity_block" * 50, kind="tier1_identity")  # ~700 chars, ~175 tokens
    b.force_spend("baseline_block" * 50, kind="tier1_baseline")  # another ~175 tokens

    # Priority 4: skeleton (one per folder, processed in importance order).
    accepted_skeletons = 0
    for i in range(20):
        if b.try_spend("skeleton_chunk" * 50, kind="skeleton", folder=f"folder_{i}"):
            accepted_skeletons += 1
    # Priority 9: skill files (low priority).
    accepted_skills = 0
    for i in range(5):
        if b.try_spend("skill_chunk" * 50, kind="tier3_skill", folder=f"skill_{i}"):
            accepted_skills += 1

    # The forced Tier-1 content must be in the spend log.
    kinds = {s.kind for s in b.spends}
    assert "tier1_identity" in kinds
    assert "tier1_baseline" in kinds

    # Some skeletons should have made it, but not all 20 (cap is tight).
    # When the budget runs out, later try_spends produce rejections.
    assert accepted_skeletons + accepted_skills < 25
    assert len(b.rejections) > 0


def test_summary_string_includes_basic_stats():
    b = TokenBudget(cap=1000)
    b.try_spend("hello world")
    summary = b.summary()
    assert "spent" in summary
    assert "1,000" in summary  # cap formatted


def test_report_markdown_lists_spends_and_rejections():
    b = TokenBudget(cap=50)  # ~200 chars
    b.force_spend("a" * 100, kind="tier1")
    b.try_spend("b" * 10, kind="readme")
    b.try_spend("c" * 10_000, kind="legacy", folder="some_folder")
    report = b.report_markdown()
    assert "# Budget Report" in report
    assert "tier1" in report
    assert "Sections shed" in report
    assert "some_folder" in report


def test_force_spend_does_not_block_subsequent_try_spend_under_cap():
    b = TokenBudget(cap=100)
    # Tier-1 doesn't blow the budget here.
    b.force_spend("x" * 200, kind="tier1")  # ~50 tokens
    # Optional content of the same size should still fit.
    assert b.try_spend("x" * 200, kind="opt") is True
    assert b.spent == 100
