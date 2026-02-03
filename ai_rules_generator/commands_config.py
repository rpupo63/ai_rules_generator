"""
Config subcommand handlers for AI Rules Generator CLI.
"""

import sys

from .config_manager import (
    load_user_config,
    save_user_config,
    UserConfig,
    get_available_providers,
    get_provider_display_name,
    get_config_set_keys,
    get_available_tools,
    get_tool_display_name,
    display_config,
    reset_config,
)
from .cli import select_ai_provider, select_ai_model, _select_multiple_from_options


def cmd_config_show(args) -> None:
    """Handle the config show command."""
    config = load_user_config()
    if config:
        display_config(config, show_keys=args.show_keys)
    else:
        print()
        print("=" * 60)
        print("No configuration found")
        print("=" * 60)
        print()
        print("Run 'python ai_rules_generator.py init' to create a configuration.")
        print()


def cmd_config_edit(args) -> None:
    """Handle the config edit command."""
    config = load_user_config()
    if not config:
        config = UserConfig()

    print()
    print("=" * 60)
    print("Edit Configuration")
    print("=" * 60)
    print()
    print("Leave blank to keep current value.")
    print()

    current_provider = config.ai_provider
    provider = select_ai_provider()
    if provider:
        config.ai_provider = provider
        model = select_ai_model(config.ai_provider)
        if model:
            config.ai_model = model

    print()
    print("=" * 60)
    print("API Keys (optional - leave blank to use environment variables)")
    print("=" * 60)
    print()

    if config.ai_provider == "openai" or config.ai_provider == "none":
        print(f"Current OpenAI API key: {config.openai_api_key if config.openai_api_key else 'Not set'}")
        openai_input = input("OpenAI API key (leave blank to keep current): ").strip()
        if openai_input:
            config.openai_api_key = openai_input

    if config.ai_provider == "anthropic" or config.ai_provider == "none":
        print(f"\nCurrent Anthropic API key: {config.anthropic_api_key if config.anthropic_api_key else 'Not set'}")
        anthropic_input = input("Anthropic API key (leave blank to keep current): ").strip()
        if anthropic_input:
            config.anthropic_api_key = anthropic_input

    print()
    print("=" * 60)
    print("AI Coding Tool Selection")
    print("=" * 60)
    print()
    available_tools = get_available_tools()
    tool_options = list(available_tools.keys())
    current_tools = config.enabled_tools if config.enabled_tools else ["cursor", "claude-code"]

    selected_tools = _select_multiple_from_options(
        tool_options,
        "Select AI Coding Tools",
        default_selected=current_tools
    )
    if selected_tools:
        config.enabled_tools = selected_tools
        tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
        print(f"\n  ✓ Selected tools: {', '.join(tool_names)}")

    save_user_config(config)
    print()
    print("Configuration updated successfully!")


def cmd_config_set(args) -> None:
    """Handle the config set command."""
    config = load_user_config()
    if not config:
        config = UserConfig()

    if args.key == "provider":
        if args.value not in get_available_providers():
            print(f"Error: Invalid provider '{args.value}'")
            print(f"Valid providers: {', '.join(get_available_providers().keys())}")
            sys.exit(1)
        config.ai_provider = args.value
        print(f"Set provider to: {get_provider_display_name(args.value)}")

    elif args.key == "model":
        config.ai_model = args.value
        print(f"Set model to: {args.value}")

    elif args.key == "openai-key":
        config.openai_api_key = args.value
        print("Set OpenAI API key")

    elif args.key == "anthropic-key":
        config.anthropic_api_key = args.value
        print("Set Anthropic API key")

    elif args.key == "enabled-tools":
        tools = [t.strip() for t in args.value.split(',')]
        available_tools = get_available_tools()
        invalid_tools = [t for t in tools if t not in available_tools]
        if invalid_tools:
            print(f"Error: Invalid tools: {', '.join(invalid_tools)}")
            print(f"Valid tools: {', '.join(available_tools.keys())}")
            sys.exit(1)
        config.enabled_tools = tools
        tool_names = [get_tool_display_name(tool) for tool in tools]
        print(f"Set enabled tools to: {', '.join(tool_names)}")

    else:
        print(f"Error: Unknown config key '{args.key}'")
        print(f"Valid keys: {', '.join(get_config_set_keys())}")
        sys.exit(1)

    save_user_config(config)


def cmd_config_reset(args) -> None:
    """Handle the config reset command."""
    print()
    confirm = input("Are you sure you want to reset all configuration? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        reset_config()
        print("Configuration reset successfully.")
    else:
        print("Reset cancelled.")
