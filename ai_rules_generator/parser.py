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


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="AI Rules Generator - Generate AI coding agent rules"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

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

    # Project-init command
    project_init_parser = subparsers.add_parser(
        'project-init',
        help='Initialize AI rules for the current project (generates rules automatically)'
    )
    project_init_parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)"
    )
    project_init_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI generation and use template-based generation only"
    )
    project_init_parser.set_defaults(func=cmd_project_init)

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
