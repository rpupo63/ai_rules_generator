"""Update command — regenerates the structure-only context map."""

from __future__ import annotations

from .commands_context import cmd_context


def cmd_update(args) -> None:
    print("Regenerating structure-only context…")
    cmd_context(args)
