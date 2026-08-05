"""
Argument parser and subcommand definitions for AI Rules Generator CLI.
"""

import argparse

from .commands_config import (
    cmd_config_edit,
    cmd_config_reset,
    cmd_config_set,
    cmd_config_show,
)
from .commands_context import cmd_context, cmd_context_for, cmd_context_show
from .commands_project import cmd_generate, cmd_init, cmd_project_init
from .commands_update import cmd_update
from .config_manager import get_config_set_keys


def _add_context_flags(p: argparse.ArgumentParser) -> None:
    """Shared flags for structure-only context generation."""
    p.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )
    p.add_argument(
        "--no-graph",
        action="store_true",
        help="Skip graph construction.",
    )
    p.add_argument(
        "--no-ast",
        action="store_true",
        help="Skip tag extraction / graph.",
    )
    p.add_argument(
        "--token-budget",
        type=int,
        default=1_000_000,
        help="Global artifact token budget (default 1,000,000).",
    )
    p.add_argument(
        "--graph-budget",
        type=int,
        default=1000,
        help="Token budget for inline repo-map digest (default 1000).",
    )
    p.add_argument(
        "--emit-cursor-rules",
        action="store_true",
        help="Also emit glob-scoped .cursor/rules/*.mdc for top folders.",
    )
    p.add_argument(
        "--write-graph",
        action="store_true",
        help="Write `.ai-context/graph/` sidecars.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned outputs without writing files.",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description=(
            "AI Rules Generator — structure-only codebase context "
            "(ranked definition/reference map) plus optional Cursor rules"
        )
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    context_parser = subparsers.add_parser(
        "context",
        help=(
            "Generate lean .ai-context/ orientation map and "
            "conditional AGENTS.md pointer"
        ),
    )
    _add_context_flags(context_parser)
    context_parser.set_defaults(func=cmd_context, context_cmd=None)

    context_sub = context_parser.add_subparsers(
        dest="context_cmd", required=False
    )
    show_parser = context_sub.add_parser(
        "show",
        help="Print an on-demand digest for a folder path",
    )
    show_parser.add_argument("folder", help="Relative folder path")
    show_parser.add_argument(
        "--full",
        action="store_true",
        help="Include reference edges",
    )
    show_parser.add_argument("--project-root", type=str)
    show_parser.add_argument("--no-ast", action="store_true")
    show_parser.add_argument("--no-graph", action="store_true")
    show_parser.set_defaults(func=cmd_context_show)

    for_parser = context_sub.add_parser(
        "for",
        help="Show structure digest for a path",
    )
    for_parser.add_argument("path", help="Relative file or folder path")
    for_parser.add_argument("--project-root", type=str)
    for_parser.add_argument("--no-ast", action="store_true")
    for_parser.add_argument("--no-graph", action="store_true")
    for_parser.set_defaults(func=cmd_context_for)

    init_parser = subparsers.add_parser(
        "init",
        help="Alias for structure-only context generation",
    )
    _add_context_flags(init_parser)
    init_parser.set_defaults(func=cmd_init, context_cmd=None)

    project_parser = subparsers.add_parser(
        "project-init",
        help="Alias for structure-only context generation",
    )
    _add_context_flags(project_parser)
    project_parser.set_defaults(func=cmd_project_init, context_cmd=None)

    gen_parser = subparsers.add_parser(
        "generate",
        help="Alias for structure-only context generation",
    )
    _add_context_flags(gen_parser)
    gen_parser.set_defaults(func=cmd_generate, context_cmd=None)

    update_parser = subparsers.add_parser(
        "update",
        help="Regenerate the structure-only context map",
    )
    _add_context_flags(update_parser)
    update_parser.set_defaults(func=cmd_update, context_cmd=None)

    config_parser = subparsers.add_parser(
        "config",
        help="Tool preference config (no model settings)",
    )
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    config_sub.add_parser("show").set_defaults(func=cmd_config_show)
    config_sub.add_parser("edit").set_defaults(func=cmd_config_edit)
    config_sub.add_parser("reset").set_defaults(func=cmd_config_reset)
    set_p = config_sub.add_parser("set")
    set_p.add_argument("key", choices=get_config_set_keys())
    set_p.add_argument("value")
    set_p.set_defaults(func=cmd_config_set)

    return parser
