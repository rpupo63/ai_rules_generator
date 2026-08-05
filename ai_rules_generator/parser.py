"""
Argument parser and subcommand definitions for AI Rules Generator CLI.
"""

import argparse

from .models import get_available_languages
from .config_manager import get_config_set_keys
from .commands_config import (
    cmd_config_show,
    cmd_config_edit,
    cmd_config_set,
    cmd_config_reset,
)
from .commands_project import cmd_init, cmd_project_init, cmd_generate
from .commands_context import cmd_context, cmd_context_for, cmd_context_show
from .commands_update import cmd_update


def _add_context_flags(p: argparse.ArgumentParser) -> None:
    """Shared flags for context / project-init complementary generation."""
    p.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )
    p.add_argument(
        "--ai",
        action="store_true",
        help="Enable optional LLM enrichment (folder overviews). Default is deterministic.",
    )
    p.add_argument(
        "--no-ai",
        action="store_true",
        help="Force deterministic generation (default behavior for `context`).",
    )
    p.add_argument(
        "--no-graph",
        action="store_true",
        help="Skip Graph RAG / DKB construction.",
    )
    p.add_argument(
        "--no-ast",
        action="store_true",
        help="Skip Tree-sitter AST compression and Graph RAG.",
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
        help="Also emit glob-scoped .cursor/rules/*.mdc (default: modules only).",
    )
    p.add_argument(
        "--ai-max-folders",
        type=int,
        default=12,
        help=(
            "When --ai is set, enrich at most N importance-ranked folders "
            "(default 12)."
        ),
    )
    p.add_argument(
        "--practices",
        action="store_true",
        help="Emit `.ai-context/practices/` from bundled awesome-cursorrules (off by default).",
    )
    p.add_argument(
        "--write-graph",
        action="store_true",
        help="Write `.ai-context/graph/` sidecars (graph still built in-memory for ranking).",
    )
    p.add_argument(
        "--no-modules",
        action="store_true",
        help="Skip writing surface digests under `.ai-context/modules/`.",
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
            "AI Rules Generator — complementary codebase context provider "
            "(What / How / Why) plus optional legacy rule emitters"
        )
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Context command (primary)
    context_parser = subparsers.add_parser(
        "context",
        help=(
            "Generate lean .ai-context/ orientation map and "
            "conditional AGENTS.md pointer (does not overwrite constitution)"
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
    show_parser.add_argument(
        "folder",
        help="Relative folder path (e.g. backend/api)",
    )
    show_parser.add_argument(
        "--full",
        action="store_true",
        help="Include full skeleton + call-flow (heavier)",
    )
    show_parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )
    show_parser.add_argument(
        "--no-ast",
        action="store_true",
        help="Skip Tree-sitter AST compression",
    )
    show_parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Skip graph for --full call-flow",
    )
    show_parser.set_defaults(func=cmd_context_show)

    for_parser = context_sub.add_parser(
        "for",
        help=(
            "Print a path-scoped edit pack "
            "(ancestors + graph neighborhood + AGENTS slices)"
        ),
    )
    for_parser.add_argument(
        "paths",
        nargs="+",
        help="Relative file or folder path(s) to assemble context for",
    )
    for_parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )
    for_parser.add_argument(
        "--budget",
        type=int,
        default=2500,
        help="Token budget for the edit pack (default 2500)",
    )
    for_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON instead of markdown",
    )
    for_parser.add_argument(
        "--write",
        action="store_true",
        help="Also write under .ai-context/edits/",
    )
    for_parser.add_argument(
        "--no-ast",
        action="store_true",
        help="Skip Tree-sitter AST compression",
    )
    for_parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Skip call/used-by neighborhood",
    )
    for_parser.set_defaults(func=cmd_context_for)

    # Init command
    init_parser = subparsers.add_parser(
        'init',
        help='Initialize and configure AI provider preferences'
    )
    init_parser.set_defaults(func=cmd_init)

    # Config command with subcommands
    config_parser = subparsers.add_parser(
        'config',
        help='Manage configuration settings'
    )
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='Config actions')

    # Config show
    config_show_parser = config_subparsers.add_parser(
        'show',
        help='Show current configuration'
    )
    config_show_parser.add_argument(
        '--show-keys',
        action='store_true',
        help='Show full API keys (default: masked)'
    )
    config_show_parser.set_defaults(func=cmd_config_show, show_keys=False)

    # Config edit
    config_edit_parser = config_subparsers.add_parser(
        'edit',
        help='Edit configuration interactively'
    )
    config_edit_parser.set_defaults(func=cmd_config_edit)

    # Config set
    config_set_parser = config_subparsers.add_parser(
        'set',
        help='Set a specific configuration value'
    )
    config_set_parser.add_argument(
        'key',
        choices=get_config_set_keys(),
        help='Configuration key to set'
    )
    config_set_parser.add_argument(
        'value',
        help='Value to set'
    )
    config_set_parser.set_defaults(func=cmd_config_set)

    # Config reset
    config_reset_parser = config_subparsers.add_parser(
        'reset',
        help='Reset configuration to defaults'
    )
    config_reset_parser.set_defaults(func=cmd_config_reset)

    # Project-init command (defaults to complementary context; --legacy-rules for old path)
    project_init_parser = subparsers.add_parser(
        "project-init",
        help=(
            "Initialize complementary codebase context for the current project "
            "(use --legacy-rules for the old full AGENTS.md + skills emitter)"
        ),
    )
    _add_context_flags(project_init_parser)
    project_init_parser.add_argument(
        "--legacy-rules",
        action="store_true",
        help=(
            "Legacy: overwrite/generate full AGENTS.md, .ai-rules/skills, "
            "and tool symlinks (old behavior)."
        ),
    )
    project_init_parser.add_argument(
        "--tier",
        choices=("all", "1", "2", "3"),
        default="all",
        help="Legacy only: restrict emitted tiers.",
    )
    project_init_parser.add_argument(
        "--max-tier1-lines",
        type=int,
        default=None,
        help="Legacy only: soft Tier-1 layout hint.",
    )
    project_init_parser.add_argument(
        "--link-mode",
        choices=("symlink", "import", "copy"),
        default="symlink",
        help="Legacy only: how tool entry points reach AGENTS.md.",
    )
    project_init_parser.set_defaults(func=cmd_project_init)

    # Update command — refresh complementary context
    update_parser = subparsers.add_parser(
        "update",
        help="Refresh .ai-context pack and AGENTS.md pointer addendum",
    )
    _add_context_flags(update_parser)
    update_parser.add_argument(
        "--legacy-rules",
        action="store_true",
        help="Legacy: run the old incremental rules regenerator.",
    )
    update_parser.set_defaults(func=cmd_update)

    # Generate command
    gen_parser = subparsers.add_parser(
        'generate',
        help='Generate AI rules for your project'
    )
    gen_parser.add_argument(
        "--description",
        type=str,
        help="Project description"
    )
    gen_parser.add_argument(
        "--monorepo",
        action="store_true",
        help="Project is a monorepo"
    )
    gen_parser.add_argument(
        "--language",
        type=str,
        choices=get_available_languages(),
        help="Primary programming language"
    )
    gen_parser.add_argument(
        "--frameworks",
        type=str,
        nargs="+",
        help="Frameworks used (space-separated)"
    )
    gen_parser.add_argument(
        "--output",
        type=str,
        default=".cursorrules",
        help="Output file path (default: .cursorrules)"
    )
    gen_parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)"
    )
    gen_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (overrides other arguments)"
    )
    gen_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI generation and use template-based generation only"
    )
    gen_parser.set_defaults(func=cmd_generate, frameworks=[])

    return parser
