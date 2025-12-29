#!/usr/bin/env python3
"""
AI Rules Generator CLI
Generates comprehensive AI coding agent rules based on project configuration
and best practices from general guidelines and language/framework-specific rules.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

from .models import ProjectConfig, get_available_languages
from .detection import discover_monorepo_packages
from .generators import (
    generate_root_monorepo_rules,
    generate_rules_document,
    generate_folder_cursor_rule,
    generate_folder_agents_md
)
from .generators_shared import (
    create_shared_ai_rules_directory,
    generate_cursorrules_with_references,
    generate_claude_md_with_references
)
from .generators_multi_tool import generate_all_tool_rules
from .cli import interactive_config, select_ai_provider, select_ai_model, _select_multiple_from_options
from .config import SECURITY_RULES_TEMPLATE
from .config_manager import (
    load_user_config,
    save_user_config,
    UserConfig,
    get_available_providers,
    get_provider_display_name,
    get_provider_models,
    display_config,
    reset_config,
    get_config_path,
    get_available_tools,
    get_tool_display_name
)
import os


def cmd_config_show(args) -> None:
    """Handle the config show command. Max 20 lines."""
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
    """Handle the config edit command. Max 40 lines."""
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

    # AI Provider
    current_provider = config.ai_provider
    provider = select_ai_provider()
    if provider:
        config.ai_provider = provider

        # Select model for the provider
        model = select_ai_model(config.ai_provider)
        if model:
            config.ai_model = model

    # API Keys
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
    
    # Update enabled tools
    print()
    print("=" * 60)
    print("AI Coding Tool Selection")
    print("=" * 60)
    print()
    available_tools = get_available_tools()
    tool_options = list(available_tools.keys())
    current_tools = config.enabled_tools if config.enabled_tools else ["cursor", "claude-code"]
    
    from .cli import _select_multiple_from_options
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
    """Handle the config set command. Max 30 lines."""
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
        # Parse comma-separated list of tools
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
        print("Valid keys: provider, model, openai-key, anthropic-key, enabled-tools")
        sys.exit(1)

    save_user_config(config)


def cmd_config_reset(args) -> None:
    """Handle the config reset command. Max 10 lines."""
    print()
    confirm = input("Are you sure you want to reset all configuration? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        reset_config()
        print("Configuration reset successfully.")
    else:
        print("Reset cancelled.")


def cmd_project_init(args) -> None:
    """Handle the project-init command - Sets up rules for a specific project."""
    print("=" * 60)
    print("AI Rules Generator - Project Initialization")
    print("=" * 60)
    print()
    print("This will set up AI rules for this project.")
    print("Rules will be generated and saved in the project directory.")
    print()

    # Check if global config exists
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

    # Load configuration
    ai_provider = user_config.ai_provider
    ai_model = user_config.ai_model
    openai_key = user_config.openai_api_key or os.getenv('OPENAI_API_KEY')
    anthropic_key = user_config.anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')

    # Resolve paths
    base_path, project_root = validate_and_resolve_paths(args)
    
    # Check if already initialized
    ai_rules_dir = project_root / ".ai-rules"
    if ai_rules_dir.exists():
        print(f"⚠️  Project already initialized (found {ai_rules_dir})")
        response = input("Re-initialize? This will overwrite existing rules. (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)

    # Get project configuration interactively
    config = interactive_config()
    config.project_root = project_root

    # Override AI settings if --no-ai is specified
    use_ai = not args.no_ai
    if args.no_ai:
        ai_provider = "none"
        ai_model = "template"

    print()
    print("=" * 60)
    print("Generating Project Rules")
    print("=" * 60)
    print()

    # Get enabled tools from user config
    enabled_tools = user_config.enabled_tools if user_config.enabled_tools else ["cursor", "claude-code"]
    
    # Generate rules
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

    # Load existing config if available
    existing_config = load_user_config()
    config = existing_config if existing_config else UserConfig()

    # Select AI provider
    provider = select_ai_provider()
    print(f"\n  Selected provider: {get_provider_display_name(provider)}")
    config.ai_provider = provider

    # Select AI model
    model = select_ai_model(provider)
    print(f"  Selected model: {model}")
    config.ai_model = model

    # Handle API keys
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

    # OpenAI API key
    if provider == "openai" or provider == "none":
        openai_display = config.openai_api_key[:10] + '...' if config.openai_api_key and len(config.openai_api_key) > 10 else (config.openai_api_key if config.openai_api_key else 'Not set')
        print(f"Current OpenAI API key: {openai_display}")
        openai_input = input("OpenAI API key (press Enter to skip): ").strip()
        if openai_input:
            config.openai_api_key = openai_input
            print("  ✓ OpenAI API key saved to config file")
        else:
            print("  ℹ  Skipped - will use environment variable if set (OPENAI_API_KEY)")

    # Anthropic API key
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

    # Select AI coding tools
    print()
    print("=" * 60)
    print("AI Coding Tool Selection")
    print("=" * 60)
    print()
    print("Which AI coding tools do you use? Rules will be generated for selected tools.")
    print()
    
    available_tools = get_available_tools()
    tool_options = list(available_tools.keys())
    
    # Get current selection or defaults
    current_tools = config.enabled_tools if config.enabled_tools else ["cursor", "claude-code"]
    
    from .cli import _select_multiple_from_options
    selected_tools = _select_multiple_from_options(
        tool_options,
        "Select AI Coding Tools",
        default_selected=current_tools
    )
    
    config.enabled_tools = selected_tools if selected_tools else current_tools
    
    # Show summary
    tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
    print(f"\n  ✓ Selected tools: {', '.join(tool_names)}")

    # Save configuration
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
    """Handle the generate command. Max 60 lines."""
    # Load user config (or use defaults)
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

    # Override if --no-ai is specified
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


def validate_and_resolve_paths(args) -> Tuple[Path, Path]:
    """Validate arguments and resolve paths. Max 30 lines."""
    # Find base_path - look in multiple locations for awesome-cursorrules
    # 1. Package directory (where this module is located)
    package_dir = Path(__file__).parent.absolute()
    
    # 2. Check if awesome-cursorrules exists in package directory
    base_path = package_dir
    awesome_cursorrules_path = package_dir / "awesome-cursorrules"
    
    # 3. If not found, try looking in common installation locations
    if not awesome_cursorrules_path.exists():
        # Try parent directory (for package installations)
        parent_path = package_dir.parent
        if (parent_path / "awesome-cursorrules").exists():
            base_path = parent_path
        # Try current working directory (for development)
        elif (Path.cwd() / "awesome-cursorrules").exists():
            base_path = Path.cwd()
    
    if args.project_root:
        project_root = Path(args.project_root).resolve()
        if not project_root.exists():
            raise ValueError(f"Project root directory does not exist: {project_root}")
    else:
        project_root = Path.cwd()

    return base_path, project_root


def get_project_config(args, project_root: Path) -> ProjectConfig:
    """Get configuration from args or interactive mode. Max 25 lines."""
    if args.interactive or (not args.description and not args.language):
        config = interactive_config()
        config.project_root = project_root
        return config

    if not args.description:
        raise ValueError("--description is required in non-interactive mode")
    if not args.language:
        raise ValueError("--language is required in non-interactive mode")

    return ProjectConfig(
        description=args.description,
        is_monorepo=args.monorepo,
        primary_language=args.language.lower(),
        frameworks=args.frameworks,
        output_file=args.output,
        project_root=project_root
    )


def print_generation_info(
    config: ProjectConfig,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str
) -> None:
    """Print generation configuration info. Max 20 lines."""
    print(f"\nGenerating AI rules document...")
    print(f"  Project root: {project_root}")
    print(f"  Language: {config.primary_language}")
    print(f"  Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None'}")
    print(f"  Monorepo: {config.is_monorepo}")
    if use_ai:
        print(f"  AI Provider: {get_provider_display_name(ai_provider)}")
        print(f"  AI Model: {ai_model}")
    else:
        print(f"  AI generation: Disabled (using template-based generation)")
    print()


def generate_single_project_rules_setup(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    enabled_tools: Optional[List[str]] = None
) -> None:
    """Generate rules for a single project with shared AI rules structure."""
    print("Creating shared AI rules directory...")
    
    # Create shared AI rules directory
    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    print(f"  ✓ Created {ai_rules_dir}")
    
    # Generate rule files for enabled AI coding tools
    if enabled_tools is None:
        enabled_tools = ["cursor", "claude-code"]
    tool_names = [get_tool_display_name(tool) for tool in enabled_tools]
    print(f"\nGenerating rule files for enabled AI coding tools...")
    print(f"  Tools: {', '.join(tool_names)}")
    generate_all_tool_rules(ai_rules_dir, config, base_path, project_root, enabled_tools)


def generate_monorepo_project_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    enabled_tools: Optional[List[str]] = None
) -> None:
    """Generate rules for a monorepo with shared AI rules structure."""
    packages = discover_and_print_packages(project_root)
    
    print("\nCreating shared AI rules directory...")
    # Create root-level shared AI rules
    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    print(f"  ✓ Created {ai_rules_dir}")
    
    # Generate root-level .cursorrules and CLAUDE.md
    print("\nGenerating root-level rules...")
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate Cursor MDC format
    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")
    
    # Generate CLAUDE.md
    root_rules_md = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=False, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(root_rules_md, encoding='utf-8')
    print(f"  ✓ Created {claude_md}")
    
    # Create security rules
    from .config import SECURITY_RULES_TEMPLATE
    security_mdc = cursor_rules_dir / "security.mdc"
    security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
    print(f"  ✓ Created {security_mdc}")
    
    # Generate package-level rules
    create_package_level_rules(
        packages, base_path, project_root, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    
    # Generate rule files for enabled tools (only for root, packages use default structure)
    if enabled_tools is None:
        enabled_tools = ["cursor", "claude-code"]
    # Note: For monorepos, we still generate the standard structure
    # but could filter based on enabled_tools in the future


def generate_single_project_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Generate rules for a single project. Max 30 lines."""
    print(f"  Output: {config.output_file}")
    print()

    rules_doc = generate_rules_document(
        config, base_path, use_ai=use_ai, ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )

    output_path = project_root / config.output_file
    output_path.write_text(rules_doc, encoding='utf-8')

    print(f"✓ Successfully generated rules document: {output_path}")
    print(f"  File size: {len(rules_doc)} characters, {len(rules_doc.splitlines())} lines")


def discover_and_print_packages(project_root: Path) -> List[Tuple[Path, str, List[str]]]:
    """Discover monorepo packages and print summary. Max 15 lines."""
    print("Discovering packages in monorepo...")
    packages = discover_monorepo_packages(project_root)
    print(f"  Found {len(packages)} packages:")

    for folder_path, language, frameworks in packages:
        fw_str = f" ({', '.join(frameworks)})" if frameworks else ""
        print(f"    - {folder_path.name}: {language}{fw_str}")

    print()
    return packages


def create_root_level_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    packages: List[Tuple[Path, str, List[str]]],
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Create root-level rule files. Max 40 lines."""
    print("Generating root-level rules...")

    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    # Generate MDC format for Cursor
    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")

    # Generate markdown for Claude Code
    root_rules_md = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=False, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(root_rules_md, encoding='utf-8')
    print(f"  ✓ Created {claude_md}")

    # Create always-applied security rules
    security_mdc = cursor_rules_dir / "security.mdc"
    security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
    print(f"  ✓ Created {security_mdc}")


def create_package_level_rules(
    packages: List[Tuple[Path, str, List[str]]],
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Create package-level rule files. Max 50 lines."""
    for folder_path, language, frameworks in packages:
        folder_name = folder_path.name
        print(f"\nGenerating rules for {folder_name}...")

        package_cursor_dir = folder_path / ".cursor" / "rules"
        package_cursor_dir.mkdir(parents=True, exist_ok=True)

        if use_ai:
            print(f"    Using AI generation for {folder_name}...")

        # Generate Cursor MDC rule
        cursor_rule = generate_folder_cursor_rule(
            folder_path, folder_name, language,
            frameworks, base_path, project_root, use_ai=use_ai,
            ai_provider=ai_provider, ai_model=ai_model,
            openai_key=openai_key, anthropic_key=anthropic_key
        )
        rule_file = package_cursor_dir / f"{folder_name}-patterns.mdc"
        rule_file.write_text(cursor_rule, encoding='utf-8')
        print(f"  ✓ Created {rule_file}")

        # Generate AGENTS.md and CLAUDE.md
        agents_content = generate_folder_agents_md(
            folder_path, folder_name, language,
            frameworks, base_path, use_ai=use_ai,
            ai_provider=ai_provider, ai_model=ai_model,
            openai_key=openai_key, anthropic_key=anthropic_key
        )

        agents_md = folder_path / "AGENTS.md"
        agents_md.write_text(agents_content, encoding='utf-8')
        print(f"  ✓ Created {agents_md}")

        package_claude_md = folder_path / "CLAUDE.md"
        package_claude_md.write_text(agents_content, encoding='utf-8')
        print(f"  ✓ Created {package_claude_md}")


def generate_monorepo_rules(
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str]
) -> None:
    """Generate rules for a monorepo. Max 25 lines."""
    packages = discover_and_print_packages(project_root)
    create_root_level_rules(
        config, base_path, project_root, packages, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    create_package_level_rules(
        packages, base_path, project_root, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )

    print(f"\n✓ Successfully generated monorepo rules structure")
    cursor_dir = project_root / ".cursor" / "rules" / "general.mdc"
    print(f"  Root rules: {cursor_dir}")
    print(f"  Package rules: {len(packages)} packages configured")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands. Max 150 lines."""
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
        choices=['provider', 'model', 'openai-key', 'anthropic-key', 'enabled-tools'],
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


def main() -> None:
    """Main entry point. Max 30 lines."""
    try:
        parser = create_parser()
        args = parser.parse_args()

        # If no command is specified, show help
        if not args.command:
            parser.print_help()
            sys.exit(0)

        # Execute the command
        args.func(args)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
