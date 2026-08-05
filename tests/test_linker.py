"""
Tests for the tool entry-point linker.

Covers all three link modes plus the symlink->copy fallback that keeps the
generator usable on filesystems / platforms that forbid symlinks.
"""

import os
from pathlib import Path

import pytest

from ai_rules_generator.linker import (
    LinkMode,
    LinkOutcome,
    link_dir,
    link_file,
)


def _write_canonical(root: Path, text: str = "# AGENTS\n\nbody\n") -> Path:
    canonical = root / "AGENTS.md"
    canonical.write_text(text, encoding="utf-8")
    return canonical


def test_link_mode_from_str_defaults_to_symlink():
    assert LinkMode.from_str("symlink") is LinkMode.SYMLINK
    assert LinkMode.from_str("import") is LinkMode.IMPORT
    assert LinkMode.from_str("copy") is LinkMode.COPY
    assert LinkMode.from_str("nonsense") is LinkMode.SYMLINK


def test_symlink_mode_creates_symlink(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"
    outcome = link_file(target, canonical, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.SYMLINKED
    assert target.is_symlink()
    # Resolves to the canonical content.
    assert target.read_text() == canonical.read_text()
    # Relative link (not absolute).
    assert not os.path.isabs(os.readlink(target))


def test_symlink_into_subdir_is_relative(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / ".github" / "copilot-instructions.md"
    outcome = link_file(target, canonical, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.SYMLINKED
    assert target.is_symlink()
    link = os.readlink(target)
    assert link == os.path.join("..", "AGENTS.md")
    assert target.read_text() == canonical.read_text()


def test_import_mode_writes_pointer_stub(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"
    outcome = link_file(
        target, canonical, LinkMode.IMPORT, import_line="@AGENTS.md",
    )
    assert outcome is LinkOutcome.IMPORTED
    assert not target.is_symlink()
    body = target.read_text()
    assert body.splitlines()[0] == "@AGENTS.md"


def test_import_mode_default_import_line_is_relative(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "sub" / "GEMINI.md"
    link_file(target, canonical, LinkMode.IMPORT)
    body = target.read_text()
    assert body.startswith("@")
    assert "AGENTS.md" in body


def test_copy_mode_writes_full_content(tmp_path):
    canonical = _write_canonical(tmp_path, text="# FULL\n\nlots of content\n")
    target = tmp_path / "CLAUDE.md"
    outcome = link_file(target, canonical, LinkMode.COPY)
    assert outcome is LinkOutcome.COPIED
    assert not target.is_symlink()
    assert target.read_text() == canonical.read_text()


def test_copy_mode_uses_explicit_text(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"
    link_file(target, canonical, LinkMode.COPY, copy_text="custom body")
    assert target.read_text() == "custom body"


def test_symlink_falls_back_to_copy_on_oserror(tmp_path, monkeypatch):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"

    def boom(*args, **kwargs):
        raise OSError("symlinks not permitted")

    monkeypatch.setattr(os, "symlink", boom)
    outcome = link_file(target, canonical, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.COPIED
    assert not target.is_symlink()
    assert target.read_text() == canonical.read_text()


def test_link_file_is_idempotent(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"
    link_file(target, canonical, LinkMode.SYMLINK)
    # Re-run: should replace cleanly, not raise.
    outcome = link_file(target, canonical, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.SYMLINKED
    assert target.is_symlink()


def test_link_file_replaces_existing_regular_file(tmp_path):
    canonical = _write_canonical(tmp_path)
    target = tmp_path / "CLAUDE.md"
    target.write_text("stale hand-written content")
    outcome = link_file(target, canonical, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.SYMLINKED
    assert target.read_text() == canonical.read_text()


def test_link_dir_symlinks_directory(tmp_path):
    skills = tmp_path / ".ai-rules" / "skills"
    skills.mkdir(parents=True)
    (skills / "a.md").write_text("skill a")
    target = tmp_path / ".claude" / "skills"
    outcome = link_dir(target, skills, LinkMode.SYMLINK)
    assert outcome is LinkOutcome.SYMLINKED
    assert (target / "a.md").read_text() == "skill a"


def test_link_dir_copy_mode_mirrors_files(tmp_path):
    skills = tmp_path / ".ai-rules" / "skills"
    skills.mkdir(parents=True)
    (skills / "a.md").write_text("skill a")
    target = tmp_path / ".claude" / "skills"
    outcome = link_dir(target, skills, LinkMode.COPY)
    assert outcome is LinkOutcome.COPIED
    assert not target.is_symlink()
    assert (target / "a.md").read_text() == "skill a"
