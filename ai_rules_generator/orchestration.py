"""
Orchestration of rule generation: single-project, monorepo, and shared structures.
"""

from pathlib import Path
from typing import List, Tuple, Optional

from .models import ProjectConfig
from .detection import discover_monorepo_packages
from .generators import (
    generate_root_monorepo_rules,
    generate_rules_document,
    generate_folder_cursor_rule,
    generate_folder_agents_md
)
from .generators_shared import create_shared_ai_rules_directory
from .generators_multi_tool import generate_all_tool_rules
from .config import SECURITY_RULES_TEMPLATE
from .config_manager import get_available_tools, get_tool_display_name


def discover_and_print_packages(project_root: Path) -> List[Tuple[Path, str, List[str]]]:
    """Discover monorepo packages and print summary."""
    print("Discovering packages in monorepo...")
    packages = discover_monorepo_packages(project_root)
    print(f"  Found {len(packages)} packages:")

    for folder_path, language, frameworks in packages:
        fw_str = f" ({', '.join(frameworks)})" if frameworks else ""
        print(f"    - {folder_path.name}: {language}{fw_str}")

    print()
    return packages


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

    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    print(f"  ✓ Created {ai_rules_dir}")

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
    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )
    print(f"  ✓ Created {ai_rules_dir}")

    print("\nGenerating root-level rules...")
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")

    root_rules_md = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=False, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(root_rules_md, encoding='utf-8')
    print(f"  ✓ Created {claude_md}")

    security_mdc = cursor_rules_dir / "security.mdc"
    security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
    print(f"  ✓ Created {security_mdc}")

    create_package_level_rules(
        packages, base_path, project_root, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key
    )

    if enabled_tools is None:
        enabled_tools = ["cursor", "claude-code"]


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
    """Generate rules for a single project."""
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
    """Create root-level rule files."""
    print("Generating root-level rules...")

    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    root_rules_mdc = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=True, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    general_mdc = cursor_rules_dir / "general.mdc"
    general_mdc.write_text(root_rules_mdc, encoding='utf-8')
    print(f"  ✓ Created {general_mdc}")

    root_rules_md = generate_root_monorepo_rules(
        config, base_path, packages, format_mdc=False, use_ai=use_ai,
        ai_provider=ai_provider, ai_model=ai_model,
        openai_key=openai_key, anthropic_key=anthropic_key
    )
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(root_rules_md, encoding='utf-8')
    print(f"  ✓ Created {claude_md}")

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
    """Create package-level rule files."""
    for folder_path, language, frameworks in packages:
        folder_name = folder_path.name
        print(f"\nGenerating rules for {folder_name}...")

        package_cursor_dir = folder_path / ".cursor" / "rules"
        package_cursor_dir.mkdir(parents=True, exist_ok=True)

        if use_ai:
            print(f"    Using AI generation for {folder_name}...")

        cursor_rule = generate_folder_cursor_rule(
            folder_path, folder_name, language,
            frameworks, base_path, project_root, use_ai=use_ai,
            ai_provider=ai_provider, ai_model=ai_model,
            openai_key=openai_key, anthropic_key=anthropic_key
        )
        rule_file = package_cursor_dir / f"{folder_name}-patterns.mdc"
        rule_file.write_text(cursor_rule, encoding='utf-8')
        print(f"  ✓ Created {rule_file}")

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
    """Generate rules for a monorepo."""
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
