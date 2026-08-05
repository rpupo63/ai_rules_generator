"""
Tool entry-point linker.

Routes each AI tool's conventional discovery path to the canonical
`AGENTS.md` / `.ai-rules/` source without duplicating content.  Three modes:

  SYMLINK : create a relative symlink (e.g. CLAUDE.md -> AGENTS.md).  Zero
            drift, git-tracked.  Falls back to COPY on OSError (Windows
            without privilege / filesystems that forbid symlinks).
  IMPORT  : write a tiny pointer stub.  For Claude Code this is the native
            `@AGENTS.md` import directive; for others a short "see AGENTS.md"
            note.  Portable (Windows-safe), explicit.
  COPY    : write the full content (legacy behaviour / maximal portability).
"""

from __future__ import annotations

import enum
import os
from pathlib import Path
from typing import List, Optional


class LinkMode(enum.Enum):
    SYMLINK = "symlink"
    IMPORT = "import"
    COPY = "copy"

    @classmethod
    def from_str(cls, value: str) -> "LinkMode":
        try:
            return cls(value)
        except ValueError:
            return cls.SYMLINK


@enum.unique
class LinkOutcome(enum.Enum):
    SYMLINKED = "symlinked"
    IMPORTED = "imported"
    COPIED = "copied"
    SKIPPED = "skipped"


def _relative_to(target: Path, canonical: Path) -> str:
    """Compute a relative path from `target`'s directory to `canonical`."""
    return os.path.relpath(canonical, target.parent)


def _remove_existing(path: Path) -> None:
    """Remove an existing file/symlink/dir so we can re-create it cleanly."""
    if path.is_symlink() or path.exists():
        if path.is_dir() and not path.is_symlink():
            import shutil

            shutil.rmtree(path)
        else:
            path.unlink()


def link_file(
    target: Path,
    canonical: Path,
    mode: LinkMode,
    *,
    import_line: Optional[str] = None,
    copy_text: Optional[str] = None,
) -> LinkOutcome:
    """
    Point `target` at `canonical` using `mode`.

    Parameters
    ----------
    target : Path
        The tool-specific entry path to create (e.g. `<root>/CLAUDE.md`).
    canonical : Path
        The source of truth (e.g. `<root>/AGENTS.md`).
    import_line : str | None
        Override for IMPORT mode.  Defaults to a relative `@<path>` import.
    copy_text : str | None
        Content to write in COPY mode (or symlink fallback).  When None,
        the canonical file's current text is copied.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    rel = _relative_to(target, canonical)

    if mode is LinkMode.SYMLINK:
        try:
            _remove_existing(target)
            os.symlink(rel, target)
            return LinkOutcome.SYMLINKED
        except OSError:
            # Windows without developer mode, or a filesystem that rejects
            # symlinks - degrade gracefully to a copy.
            pass  # fall through to COPY

    if mode is LinkMode.IMPORT:
        _remove_existing(target)
        if import_line is None:
            import_line = f"@{rel}"
        body = (
            f"{import_line}\n\n"
            f"<!-- This file points at the canonical {canonical.name}. "
            f"Edit {canonical.name}, not this file. -->\n"
        )
        target.write_text(body, encoding="utf-8")
        return LinkOutcome.IMPORTED

    # COPY (explicit, or symlink fallback).
    _remove_existing(target)
    if copy_text is None:
        copy_text = (
            canonical.read_text(encoding="utf-8")
            if canonical.is_file()
            else ""
        )
    target.write_text(copy_text, encoding="utf-8")
    return LinkOutcome.COPIED


def link_dir(
    target_dir: Path,
    canonical_dir: Path,
    mode: LinkMode,
) -> LinkOutcome:
    """
    Point a directory (e.g. `.claude/skills`) at a canonical directory
    (e.g. `.ai-rules/skills`).

    SYMLINK creates a directory symlink; IMPORT/COPY mirror the files (a
    directory cannot be `@import`ed, so IMPORT behaves like COPY here).
    """
    canonical_dir = canonical_dir.resolve() if canonical_dir.exists() else canonical_dir
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    rel = _relative_to(target_dir, canonical_dir)

    if mode is LinkMode.SYMLINK:
        try:
            _remove_existing(target_dir)
            os.symlink(rel, target_dir, target_is_directory=True)
            return LinkOutcome.SYMLINKED
        except OSError:
            pass  # fall through to copy-mirror

    # COPY / IMPORT: mirror the directory contents.
    import shutil

    _remove_existing(target_dir)
    if canonical_dir.is_dir():
        shutil.copytree(canonical_dir, target_dir)
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
    return LinkOutcome.COPIED


# Claude Code natively supports `@path` imports inside CLAUDE.md.
def claude_import_line(target: Path, canonical: Path) -> str:
    rel = _relative_to(target, canonical)
    return f"@{rel}"


__all__ = [
    "LinkMode",
    "LinkOutcome",
    "link_file",
    "link_dir",
    "claude_import_line",
]
