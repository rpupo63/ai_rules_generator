"""Project / generate commands — redirected to structure-only context."""

from __future__ import annotations

from .commands_context import cmd_context
from .paths import validate_and_resolve_paths


def cmd_init(args) -> None:
    print("Use `ai-rules-generator context` for structure-only maps.")
    cmd_context(args)


def cmd_project_init(args) -> None:
    cmd_init(args)


def cmd_generate(args) -> None:
    print(
        "Legacy rule generation was removed. "
        "Running structure-only `context` instead."
    )
    cmd_context(args)
