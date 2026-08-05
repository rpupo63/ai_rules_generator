"""Tests for idempotent AGENTS.md context pointer addendum."""

from pathlib import Path

from ai_rules_generator.agents_addendum import (
    BEGIN_MARKER,
    END_MARKER,
    apply_addendum,
    constitution_body,
    patch_agents_md,
    strip_addendum,
)


CONSTITUTION = """# My App

Purpose line about doing useful things.

## Commands

```bash
make test
```

## Off-Limits

- secrets
"""


def test_apply_addendum_appends_when_missing():
    out = apply_addendum(CONSTITUTION)
    assert BEGIN_MARKER in out
    assert END_MARKER in out
    assert out.index(BEGIN_MARKER) > out.index("## Off-Limits")
    assert constitution_body(out).rstrip() == CONSTITUTION.rstrip()


def test_apply_addendum_is_idempotent():
    once = apply_addendum(CONSTITUTION)
    twice = apply_addendum(once)
    assert once.count(BEGIN_MARKER) == 1
    assert twice.count(BEGIN_MARKER) == 1
    assert constitution_body(twice).rstrip() == CONSTITUTION.rstrip()


def test_strip_addendum_removes_block():
    with_add = apply_addendum(CONSTITUTION)
    assert BEGIN_MARKER not in strip_addendum(with_add)
    assert "## Commands" in strip_addendum(with_add)


def test_patch_agents_md_preserves_body(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(CONSTITUTION, encoding="utf-8")
    before = agents.read_text(encoding="utf-8")
    new_text, created, prev = patch_agents_md(tmp_path)
    assert not created
    assert prev.rstrip() == CONSTITUTION.rstrip()
    assert constitution_body(new_text).rstrip() == CONSTITUTION.rstrip()
    # Re-run
    patch_agents_md(tmp_path)
    after = agents.read_text(encoding="utf-8")
    assert constitution_body(after).rstrip() == constitution_body(before).rstrip()
    assert after.count(BEGIN_MARKER) == 1


def test_patch_creates_minimal_stub(tmp_path: Path):
    new_text, created, prev = patch_agents_md(tmp_path)
    assert created
    assert prev == ""
    assert (tmp_path / "AGENTS.md").exists()
    assert BEGIN_MARKER in new_text
    assert "install-repo-identity" in new_text
