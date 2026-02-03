"""
Init, project-init, and generate command handlers for AI Rules Generator CLI.
"""

import os
import sys

from .models import ProjectConfig
from .config_manager import (
    load_user_config,
    save_user_config,
    UserConfig,
    get_provider_display_name,
    get_available_tools,
    get_tool_display_name,
    get_config_path,
)
from .cli import interactive_config, _select_multiple_from_options, select_ai_provider, select_ai_model
from .paths import validate_and_resolve_paths, get_project_config, print_generation_info
from .orchestration import (
    generate_monorepo_project_rules,
    generate_single_project_rules_setup,
    generate_monorepo_rules,
    generate_single_project_rules,
)


def cmd_project_init(args) -> None:
    """Handle the project-init command - Sets up rules for a specific project."""
    print("=" * 60)
    print("AI Rules Generator - Project Initialization")
    print("=" * 60)
    print()
    print("This will set up AI rules for this project.")
    print("Rules will be generated and saved in the project directory.")
    print()

    user_config = load_user_config()
    if not user_config:
        print("⚠️  No global configuration found.")
        print("Please run 'ai-rules-generator init' first to configure your AI provider.")
        print()
        response = input("Continue anyway with defaults? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)
        user_config = UserConfig()

    ai_provider = user_config.ai_provider
    ai_model = user_config.ai_model
    openai_key = user_config.openai_api_key or os.getenv('OPENAI_API_KEY')
    anthropic_key = user_config.anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')

    base_path, project_root = validate_and_resolve_paths(args)

    ai_rules_dir = project_root / ".ai-rules"
    if ai_rules_dir.exists():
        print(f"⚠️  Project already initialized (found {ai_rules_dir})")
        response = input("Re-initialize? This will overwrite existing rules. (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)

    config = interactive_config()
    config.project_root = project_root

    use_ai = not args.no_ai
    if args.no_ai:
        ai_provider = "none"
        ai_model = "template"

    print()
    print("=" * 60)
    print("Generating Project Rules")
    print("=" * 60)
    print()

    enabled_tools = user_config.enabled_tools if user_config.enabled_tools else ["cursor", "claude-code"]

    if config.is_monorepo:
        generate_monorepo_project_rules(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key, enabled_tools
        )
    else:
        generate_single_project_rules_setup(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key, enabled_tools
        )

    print()
    print("=" * 60)
    print("✓ Project initialization complete!")
    print("=" * 60)
    print()
    print("Files created:")
    print(f"  - {project_root / '.ai-rules'}/ (shared AI rules - single source of truth)")
    print(f"  - Rule files for enabled AI coding tools:")
    available_tools = get_available_tools()
    for tool in enabled_tools:
        tool_info = available_tools[tool]
        file_list = ', '.join(tool_info['files'])
        print(f"    • {tool_info['name']}: {file_list}")
    print()
    print("All rule files reference the shared .ai-rules/ directory.")
    print("You can now use your selected AI coding tools with consistent rules!")
    print()
    print("To change which tools are enabled, run:")
    print("  ai-rules-generator config edit")
    print("=" * 60)


def cmd_init(args) -> None:
    """Handle the init command - Global configuration for token/API key management."""
    print("=" * 60)
    print("AI Rules Generator - Global Configuration")
    print("=" * 60)
    print()
    print("This will set up your global AI provider preferences and API keys.")
    print("All settings will be saved to a config file - no need to modify")
    print("your shell configuration (.bashrc, .zshrc, etc.)!")
    print()
    print("This configuration applies to all projects on this computer.")
    print("You can change this later by running 'init' again.")
    print()

    existing_config = load_user_config()
    config = existing_config if existing_config else UserConfig()

    provider = select_ai_provider()
    print(f"\n  Selected provider: {get_provider_display_name(provider)}")
    config.ai_provider = provider

    model = select_ai_model(provider)
    print(f"  Selected model: {model}")
    config.ai_model = model

    print()
    print("=" * 60)
    print("API Key Configuration")
    print("=" * 60)
    print()
    print("API keys will be securely stored in your config file.")
    print("No need to set environment variables in .bashrc or .zshrc!")
    print()
    print("You can also use environment variables if preferred.")
    print("Environment variables take precedence if set.")
    print()

    if provider == "openai" or provider == "none":
        openai_display = config.openai_api_key[:10] + '...' if config.openai_api_key and len(config.openai_api_key) > 10 else (config.openai_api_key if config.openai_api_key else 'Not set')
        print(f"Current OpenAI API key: {openai_display}")
        openai_input = input("OpenAI API key (press Enter to skip): ").strip()
        if openai_input:
            config.openai_api_key = openai_input
            print("  ✓ OpenAI API key saved to config file")
        else:
            print("  ℹ  Skipped - will use environment variable if set (OPENAI_API_KEY)")

    if provider == "anthropic" or provider == "none":
        print()
        anthropic_display = config.anthropic_api_key[:10] + '...' if config.anthropic_api_key and len(config.anthropic_api_key) > 10 else (config.anthropic_api_key if config.anthropic_api_key else 'Not set')
        print(f"Current Anthropic API key: {anthropic_display}")
        anthropic_input = input("Anthropic API key (press Enter to skip): ").strip()
        if anthropic_input:
            config.anthropic_api_key = anthropic_input
            print("  ✓ Anthropic API key saved to config file")
        else:
            print("  ℹ  Skipped - will use environment variable if set (ANTHROPIC_API_KEY)")

    print()
    print("=" * 60)
    print("AI Coding Tool Selection")
    print("=" * 60)
    print()
    print("Which AI coding tools do you use? Rules will be generated for selected tools.")
    print()

    available_tools = get_available_tools()
    tool_options = list(available_tools.keys())
    current_tools = config.enabled_tools if config.enabled_tools else ["cursor", "claude-code"]

    selected_tools = _select_multiple_from_options(
        tool_options,
        "Select AI Coding Tools",
        default_selected=current_tools
    )

    config.enabled_tools = selected_tools if selected_tools else current_tools

    tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
    print(f"\n  ✓ Selected tools: {', '.join(tool_names)}")

    save_user_config(config)

    print()
    print("=" * 60)
    print("✓ Global configuration saved successfully!")
    print("=" * 60)
    print()
    print(f"📁 Config file: {get_config_path()}")
    print("   (Your API keys are securely stored here)")
    print()
    print("✓ No need to modify .bashrc, .zshrc, or other shell configs!")
    print()
    print("Enabled AI coding tools:")
    for tool in config.enabled_tools:
        tool_info = available_tools[tool]
        print(f"  • {tool_info['name']} - {', '.join(tool_info['files'])}")
    print()
    print("Next steps:")
    print("  1. Navigate to your project directory")
    print("  2. Run: ai-rules-generator project-init")
    print("     This will set up rules for that specific project")
    print()
    print("To view or edit your config later:")
    print("  ai-rules-generator config show")
    print("  ai-rules-generator config edit")
    print("=" * 60)


def cmd_generate(args) -> None:
    """Handle the generate command."""
    user_config = load_user_config()
    if user_config:
        ai_provider = user_config.ai_provider
        ai_model = user_config.ai_model
        openai_key = user_config.openai_api_key
        anthropic_key = user_config.anthropic_api_key
        print(f"Using saved configuration: {get_provider_display_name(ai_provider)} ({ai_model})")
    else:
        print("No saved configuration found. Using default: OpenAI (gpt-4o-mini)")
        print("Run 'init' to configure your preferred AI provider and model.")
        ai_provider = "openai"
        ai_model = "gpt-4o-mini"
        openai_key = None
        anthropic_key = None

    use_ai = not args.no_ai
    if args.no_ai:
        ai_provider = "none"
        ai_model = "template"

    base_path, project_root = validate_and_resolve_paths(args)
    config = get_project_config(args, project_root)

    print_generation_info(config, project_root, use_ai, ai_provider, ai_model)

    if config.is_monorepo:
        generate_monorepo_rules(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key
        )
    else:
        generate_single_project_rules(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key
        )
