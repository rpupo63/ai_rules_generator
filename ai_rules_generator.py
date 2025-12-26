#!/usr/bin/env python3
"""
AI Rules Generator CLI
Generates comprehensive AI coding agent rules based on project configuration
and best practices from general guidelines and language/framework-specific rules.
"""

import sys
import argparse
from pathlib import Path

from models import ProjectConfig, get_available_languages
from detection import discover_monorepo_packages
from generators import (
    generate_root_monorepo_rules,
    generate_rules_document,
    generate_folder_cursor_rule,
    generate_folder_agents_md
)
from cli import interactive_config
from config import SECURITY_RULES_TEMPLATE


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate AI coding agent rules based on project configuration"
    )
    parser.add_argument(
        "--description",
        type=str,
        help="Project description"
    )
    parser.add_argument(
        "--monorepo",
        action="store_true",
        help="Project is a monorepo"
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=get_available_languages(),
        help="Primary programming language"
    )
    parser.add_argument(
        "--frameworks",
        type=str,
        nargs="+",
        help="Frameworks used (space-separated)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".cursorrules",
        help="Output file path (default: .cursorrules)"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (overrides other arguments)"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI generation and use template-based generation only"
    )
    
    args = parser.parse_args()
    
    # Get base path (directory containing this script - where awesome-cursorrules is)
    base_path = Path(__file__).parent.absolute()
    
    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
        if not project_root.exists():
            print(f"Error: Project root directory does not exist: {project_root}", file=sys.stderr)
            sys.exit(1)
    else:
        project_root = Path.cwd()
    
    # Collect configuration
    if args.interactive or (not args.description and not args.language):
        config = interactive_config()
        config.project_root = project_root
    else:
        if not args.description:
            print("Error: --description is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)
        if not args.language:
            print("Error: --language is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)
        
        config = ProjectConfig(
            description=args.description,
            is_monorepo=args.monorepo,
            primary_language=args.language.lower(),
            frameworks=args.frameworks or [],
            output_file=args.output,
            project_root=project_root
        )
    
    # Determine if AI should be used
    use_ai = not args.no_ai
    
    # Generate rules document
    print(f"\nGenerating AI rules document...")
    print(f"  Project root: {project_root}")
    print(f"  Language: {config.primary_language}")
    print(f"  Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None'}")
    print(f"  Monorepo: {config.is_monorepo}")
    if use_ai:
        print(f"  AI generation: Enabled (set --no-ai to disable)")
    else:
        print(f"  AI generation: Disabled (using template-based generation)")
    print()
    
    if config.is_monorepo:
        # Discover packages
        print("Discovering packages in monorepo...")
        packages = discover_monorepo_packages(project_root)
        print(f"  Found {len(packages)} packages:")
        for folder_path, language, frameworks in packages:
            print(f"    - {folder_path.name}: {language}" + 
                  (f" ({', '.join(frameworks)})" if frameworks else ""))
        print()
        
        # Generate root-level rules
        print("Generating root-level rules...")
        
        # Create .cursor/rules/ directory at root
        cursor_rules_dir = project_root / ".cursor" / "rules"
        cursor_rules_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and write MDC format for Cursor
        root_rules_mdc = generate_root_monorepo_rules(config, base_path, packages, format_mdc=True, use_ai=use_ai)
        general_mdc = cursor_rules_dir / "general.mdc"
        general_mdc.write_text(root_rules_mdc, encoding='utf-8')
        print(f"  ✓ Created {general_mdc}")
        
        # Generate and write markdown format for Claude Code
        root_rules_md = generate_root_monorepo_rules(config, base_path, packages, format_mdc=False, use_ai=use_ai)
        claude_md = project_root / "CLAUDE.md"
        claude_md.write_text(root_rules_md, encoding='utf-8')
        print(f"  ✓ Created {claude_md}")
        
        # Create always-applied security rules
        security_mdc = cursor_rules_dir / "security.mdc"
        security_mdc.write_text(SECURITY_RULES_TEMPLATE, encoding='utf-8')
        print(f"  ✓ Created {security_mdc}")
        
        # Generate package-specific rules
        for folder_path, language, frameworks in packages:
            folder_name = folder_path.name
            print(f"\nGenerating rules for {folder_name}...")
            
            # Create .cursor/rules/ directory for package
            package_cursor_dir = folder_path / ".cursor" / "rules"
            package_cursor_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate Cursor MDC rule
            if use_ai:
                print(f"    Using AI generation for {folder_name}...")
            cursor_rule = generate_folder_cursor_rule(folder_path, folder_name, language, 
                                                      frameworks, base_path, project_root, use_ai=use_ai)
            rule_file = package_cursor_dir / f"{folder_name}-patterns.mdc"
            rule_file.write_text(cursor_rule, encoding='utf-8')
            print(f"  ✓ Created {rule_file}")
            
            # Generate AGENTS.md
            agents_md_content = generate_folder_agents_md(folder_path, folder_name, language,
                                                          frameworks, base_path, use_ai=use_ai)
            agents_md = folder_path / "AGENTS.md"
            agents_md.write_text(agents_md_content, encoding='utf-8')
            print(f"  ✓ Created {agents_md}")
            
            # Also create CLAUDE.md for Claude Code
            claude_md_content = generate_folder_agents_md(folder_path, folder_name, language,
                                                          frameworks, base_path, use_ai=use_ai)
            package_claude_md = folder_path / "CLAUDE.md"
            package_claude_md.write_text(claude_md_content, encoding='utf-8')
            print(f"  ✓ Created {package_claude_md}")
        
        print(f"\n✓ Successfully generated monorepo rules structure")
        print(f"  Root rules: {general_mdc}")
        print(f"  Package rules: {len(packages)} packages configured")
        
    else:
        # Single-project mode - generate single rules file
        print(f"  Output: {config.output_file}")
        print()
        
        rules_doc = generate_rules_document(config, base_path, use_ai=use_ai)
        
        # Write output file
        output_path = project_root / config.output_file
        output_path.write_text(rules_doc, encoding='utf-8')
        
        print(f"✓ Successfully generated rules document: {output_path}")
        print(f"  File size: {len(rules_doc)} characters, {len(rules_doc.splitlines())} lines")


if __name__ == "__main__":
    main()
