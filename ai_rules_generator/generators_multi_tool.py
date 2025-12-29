"""
Generators for multiple AI coding tools that all reference shared .ai-rules/ directory.
Supports: Cursor, Claude Code, Windsurf, GitHub Copilot, Warp, and Janie.
"""

from pathlib import Path
from typing import Optional, List

from .models import ProjectConfig
from .config import LANGUAGE_FRAMEWORK_MAP
from .generators import generate_project_context


def generate_all_tool_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path,
    enabled_tools: Optional[List[str]] = None
) -> None:
    """Generate rule files for enabled AI coding tools."""
    if enabled_tools is None:
        # Default to all tools if not specified
        enabled_tools = ["cursor", "claude-code", "windsurf", "copilot", "warp", "janie"]
    
    files_created = []
    
    # Generate Cursor rules
    if "cursor" in enabled_tools:
        cursor_files = generate_cursor_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(cursor_files)
    
    # Generate Claude Code rules
    if "claude-code" in enabled_tools:
        claude_files = generate_claude_code_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(claude_files)
    
    # Generate Windsurf rules
    if "windsurf" in enabled_tools:
        windsurf_files = generate_windsurf_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(windsurf_files)
    
    # Generate GitHub Copilot rules
    if "copilot" in enabled_tools:
        copilot_files = generate_copilot_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(copilot_files)
    
    # Generate Warp rules
    if "warp" in enabled_tools:
        warp_files = generate_warp_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(warp_files)
    
    # Generate Janie rules
    if "janie" in enabled_tools:
        janie_files = generate_janie_rules(ai_rules_dir, config, base_path, project_root)
        files_created.extend(janie_files)
    
    # Print created files
    for file_path in files_created:
        rel_path = file_path.relative_to(project_root)
        print(f"  ✓ Created {rel_path}")


def generate_cursor_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate Cursor .cursorrules file and .cursor/rules/*.mdc files."""
    # Generate .cursorrules file that references shared rules
    cursorrules_content = _generate_cursorrules_content(ai_rules_dir, config, base_path)
    cursorrules_file = project_root / ".cursorrules"
    cursorrules_file.write_text(cursorrules_content, encoding='utf-8')
    
    # Generate .cursor/rules/ directory structure
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    
    # Main rules file
    main_mdc_content = _generate_cursor_mdc_content(ai_rules_dir, config, always_apply=True)
    main_mdc = cursor_rules_dir / "main.mdc"
    main_mdc.write_text(main_mdc_content, encoding='utf-8')
    
    # Language-specific rules if applicable
    language_key = config.primary_language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"
    
    files_created = [cursorrules_file, main_mdc]
    
    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if language_info.get("rule_file"):
        lang_mdc_content = _generate_cursor_mdc_content(
            ai_rules_dir, config, 
            glob_pattern=f"**/*.{_get_language_ext(language_key)}",
            description=f"{config.primary_language.title()} coding standards",
            always_apply=False
        )
        lang_mdc = cursor_rules_dir / f"{language_key}.mdc"
        lang_mdc.write_text(lang_mdc_content, encoding='utf-8')
        files_created.append(lang_mdc)
    
    return files_created


def generate_claude_code_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate Claude Code CLAUDE.md file and .claude/rules/ directory."""
    # Main CLAUDE.md
    claude_content = _generate_claude_content(ai_rules_dir, config, base_path)
    claude_file = project_root / "CLAUDE.md"
    claude_file.write_text(claude_content, encoding='utf-8')
    
    # Create .claude/rules/ directory
    claude_rules_dir = project_root / ".claude" / "rules"
    claude_rules_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy references to shared rules
    readme_content = f"""# Claude Code Rules

This directory contains Claude Code-specific rule references.
All actual rules are stored in `.ai-rules/` directory.

## Project Rules

See `.ai-rules/project-rules.md` for main project rules.

## Additional Resources

- `.ai-rules/README.md` - Index of all rule files
- `../CLAUDE.md` - Main Claude Code configuration
"""
    readme_file = claude_rules_dir / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')
    
    return [claude_file, readme_file]


def generate_windsurf_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate Windsurf .windsurfrules file."""
    windsurf_content = _generate_windsurf_content(ai_rules_dir, config, base_path)
    windsurf_file = project_root / ".windsurfrules"
    windsurf_file.write_text(windsurf_content, encoding='utf-8')
    return [windsurf_file]


def generate_copilot_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate GitHub Copilot instructions file."""
    copilot_content = _generate_copilot_content(ai_rules_dir, config, base_path)

    # GitHub Copilot uses .github/copilot-instructions.md or .copilot/instructions.md
    # Create both locations for better support
    github_dir = project_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    copilot_file_github = github_dir / "copilot-instructions.md"
    copilot_file_github.write_text(copilot_content, encoding='utf-8')
    
    # Also create in .copilot directory
    copilot_dir = project_root / ".copilot"
    copilot_dir.mkdir(parents=True, exist_ok=True)
    copilot_file = copilot_dir / "instructions.md"
    copilot_file.write_text(copilot_content, encoding='utf-8')
    
    return [copilot_file_github, copilot_file]


def generate_warp_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate Warp AI rules file."""
    warp_content = _generate_warp_content(ai_rules_dir, config, base_path)
    warp_file = project_root / ".warp" / "rules.md"
    warp_file.parent.mkdir(parents=True, exist_ok=True)
    warp_file.write_text(warp_content, encoding='utf-8')
    return [warp_file]


def generate_janie_rules(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path,
    project_root: Path
) -> list:
    """Generate Janie AI rules file."""
    janie_content = _generate_janie_content(ai_rules_dir, config, base_path)
    janie_file = project_root / ".janie" / "rules.md"
    janie_file.parent.mkdir(parents=True, exist_ok=True)
    janie_file.write_text(janie_content, encoding='utf-8')
    return [janie_file]


def _generate_cursorrules_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate .cursorrules content."""
    sections = [f"""# AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.
For detailed rules, see the files in that directory.

**Note:** Cursor also reads from `.cursor/rules/*.mdc` files which contain
more structured rules with glob patterns.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.
This includes project context, general principles, and overall guidelines.

For Cursor's modern rule system, see `.cursor/rules/*.mdc` files.

## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files
- `.cursor/rules/*.mdc` - Cursor-specific structured rules

""")
    
    return "".join(sections)


def _generate_cursor_mdc_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    glob_pattern: Optional[str] = None,
    description: Optional[str] = None,
    always_apply: bool = True
) -> str:
    """Generate Cursor MDC format content."""
    if description is None:
        description = "Project coding rules and guidelines"
    
    frontmatter = f"""---
description: {description}
"""
    
    if glob_pattern:
        frontmatter += f"globs:\n  - \"{glob_pattern}\"\n"
    
    frontmatter += f"alwaysApply: {str(always_apply).lower()}\n---\n\n"
    
    content = f"""# {description}

This rule file references shared AI rules in `.ai-rules/` directory.

## Main Rules

See `.ai-rules/project-rules.md` for comprehensive project rules.

## Quick Reference

- Project description: {config.description}
- Primary language: {config.primary_language.title()}
- Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None'}

## Rules Location

All detailed rules are maintained in `.ai-rules/`:
- `.ai-rules/project-rules.md` - Main project rules
- `.ai-rules/README.md` - Complete index

This keeps rules DRY and maintainable across all AI coding tools.
"""
    
    return frontmatter + content


def _generate_claude_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Claude Code CLAUDE.md content."""
    sections = [f"""# AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.
For detailed rules, see the files in that directory.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files

""")
    
    return "".join(sections)


def _generate_windsurf_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Windsurf .windsurfrules content."""
    sections = [f"""# Windsurf AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.
Windsurf can also read from `.cursor` directory if present.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files

Note: Windsurf also supports reading from `.cursor/rules/*.mdc` files if available.

""")
    
    return "".join(sections)


def _generate_copilot_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate GitHub Copilot instructions content."""
    sections = [f"""# GitHub Copilot Instructions for {config.description}

This file provides instructions for GitHub Copilot.
It references shared AI rules located in `.ai-rules/`.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

## Instructions for Copilot

When suggesting code:

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

- Look for existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files

""")
    
    return "".join(sections)


def _generate_warp_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Warp AI rules content."""
    sections = [f"""# Warp AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files

""")
    
    return "".join(sections)


def _generate_janie_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Janie AI rules content."""
    sections = [f"""# Janie AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.

"""]
    
    sections.append(generate_project_context(config))
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Reference shared rules**: Check `.ai-rules/` directory for detailed guidelines

## Repository Navigation

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Reference `.ai-rules/` directory for comprehensive guidelines

For complete rules, see:
- `.ai-rules/project-rules.md` - Full project rules
- `.ai-rules/README.md` - Index of all rule files

""")
    
    return "".join(sections)


def _get_language_ext(language: str) -> str:
    """Get file extension for a language."""
    ext_map = {
        "python": "py",
        "typescript": "{ts,tsx}",
        "javascript": "{js,jsx}",
        "rust": "rs",
        "go": "go",
        "java": "java",
        "cpp": "{cpp,hpp,cc,h}",
    }
    return ext_map.get(language, "*")

