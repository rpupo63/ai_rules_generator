"""
Generators for multiple AI coding tools that all reference shared .ai-rules/ directory.
Supports: Cursor, Claude Code, Windsurf, GitHub Copilot, Warp, and Janie.
"""

from pathlib import Path
from typing import Optional, List

from .models import ProjectConfig
from .config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from .generators import generate_project_context


def _build_ai_rules_file_listing(config: ProjectConfig) -> List[str]:
    """Build the list of files that exist in the .ai-rules/ directory based on project config."""
    files = ["project-rules.md"]

    language_key = config.primary_language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"

    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if language_info.get("rule_file"):
        files.append(f"language-{language_key}.md")

    for framework in config.frameworks:
        files.append(f"framework-{framework.lower()}.md")

    for universal_rule in UNIVERSAL_RULES:
        if universal_rule not in [f.lower() for f in config.frameworks]:
            files.append(f"universal-{universal_rule}.md")

    files.append("README.md")
    return files


def _format_file_listing(files: List[str], prefix: str = ".ai-rules/") -> str:
    """Format a list of .ai-rules/ files as a bullet list."""
    lines = []
    for f in files:
        lines.append(f"- `{prefix}{f}`")
    return "\n".join(lines)


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
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files, prefix="../.ai-rules/")

    readme_content = f"""# Claude Code Rules

All project coding rules are stored in the `.ai-rules/` directory at the project root.
Use the `Read` tool to access them. Use `Glob` with pattern `.ai-rules/**/*.md` to discover all rule files.

## How to Read the Rules

1. Start with the main rules: Use `Read` on `.ai-rules/project-rules.md`
2. Read language/framework rules as needed from `.ai-rules/`
3. See `.ai-rules/README.md` for a full index

## Available Rule Files

{file_listing}

## Additional Resources

- `../CLAUDE.md` - Main Claude Code configuration (this tool's entry point)
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
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# AI Coding Rules for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Use Cursor's file reading capabilities to access the rules:

1. **Read the main rules first**: Open `.ai-rules/project-rules.md` using `@file` or read it directly
2. **Read language-specific rules**: Open the relevant `.ai-rules/language-*.md` file
3. **Read framework rules**: Open the relevant `.ai-rules/framework-*.md` files
4. **Browse all available rules**: Open `.ai-rules/README.md` for a full index

You can also use `codebase_search` to find specific rules by topic.

**Note:** Cursor also reads from `.cursor/rules/*.mdc` files which contain
more structured rules with glob patterns.

### Available Rule Files

{file_listing}

## Critical Instructions

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Use codebase_search to find existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

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

    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    frontmatter = f"""---
description: {description}
"""

    if glob_pattern:
        frontmatter += f"globs:\n  - \"{glob_pattern}\"\n"

    frontmatter += f"alwaysApply: {str(always_apply).lower()}\n---\n\n"

    content = f"""# {description}

## Quick Reference

- Project description: {config.description}
- Primary language: {config.primary_language.title()}
- Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None'}

## Project Documentation

This project's coding rules are in the `.ai-rules/` directory.
ALWAYS read `.ai-rules/project-rules.md` before starting work on this codebase.

To access the rules, use `@file` to reference them or read them directly:

### Available Rule Files

{file_listing}

Read `.ai-rules/README.md` for a complete index of all rule files.
"""

    return frontmatter + content


def _generate_claude_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Claude Code CLAUDE.md content."""
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# AI Coding Rules for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Use the `Read` tool to read files from the `.ai-rules/` directory. Start with the
project rules, then read language/framework-specific files as needed:

1. **Read the main rules first**: Use `Read` on `.ai-rules/project-rules.md`
2. **Read language-specific rules**: Use `Read` on the relevant `language-*.md` file
3. **Read framework rules**: Use `Read` on the relevant `framework-*.md` files
4. **Browse all available rules**: Use `Read` on `.ai-rules/README.md` for a full index

To discover all rule files, use the `Glob` tool with pattern `.ai-rules/**/*.md`.

### Available Rule Files

{file_listing}

## Critical Instructions

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Use Grep and Glob to find existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

""")

    return "".join(sections)


def _generate_windsurf_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Windsurf .windsurfrules content."""
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# Windsurf AI Coding Rules for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Use Windsurf's file reading capabilities to access the rules:

1. **Read the main rules first**: Read `.ai-rules/project-rules.md`
2. **Read language-specific rules**: Read the relevant `.ai-rules/language-*.md` file
3. **Read framework rules**: Read the relevant `.ai-rules/framework-*.md` files
4. **Browse all available rules**: Read `.ai-rules/README.md` for a full index

You can also search the `.ai-rules/` directory for rules on specific topics.
Windsurf can also read from `.cursor/rules/*.mdc` files if present.

### Available Rule Files

{file_listing}

## Critical Instructions

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Find existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

""")

    return "".join(sections)


def _generate_copilot_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate GitHub Copilot instructions content."""
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# GitHub Copilot Instructions for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Use the `#file:` syntax to reference rule files in Copilot Chat, or read them directly:

1. **Read the main rules first**: `#file:.ai-rules/project-rules.md`
2. **Read language-specific rules**: `#file:.ai-rules/language-*.md`
3. **Read framework rules**: `#file:.ai-rules/framework-*.md`
4. **Browse all available rules**: `#file:.ai-rules/README.md`

In Copilot Workspace or Copilot Chat, you can ask Copilot to read these files
to understand the project's coding standards before suggesting changes.

### Available Rule Files

{file_listing}

## Instructions for Copilot

When suggesting code:

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Look for existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

""")

    return "".join(sections)


def _generate_warp_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Warp AI rules content."""
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# Warp AI Coding Rules for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Use shell commands to read the rule files:

1. **Read the main rules first**: `cat .ai-rules/project-rules.md`
2. **Read language-specific rules**: `cat .ai-rules/language-*.md`
3. **Read framework rules**: `cat .ai-rules/framework-*.md`
4. **List all available rules**: `ls .ai-rules/`
5. **Browse the index**: `cat .ai-rules/README.md`

### Available Rule Files

{file_listing}

## Critical Instructions

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Find existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

""")

    return "".join(sections)


def _generate_janie_content(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate Janie AI rules content."""
    ai_rules_files = _build_ai_rules_file_listing(config)
    file_listing = _format_file_listing(ai_rules_files)

    sections = [f"""# Janie AI Coding Rules for {config.description}

"""]

    sections.append(generate_project_context(config))
    sections.append(f"""## Project Documentation

This project's coding rules and guidelines are stored in the `.ai-rules/` directory.
You MUST read these files before making changes to the codebase.

### How to Access the Rules

Read the rule files from the `.ai-rules/` directory:

1. **Read the main rules first**: `.ai-rules/project-rules.md`
2. **Read language-specific rules**: `.ai-rules/language-*.md`
3. **Read framework rules**: `.ai-rules/framework-*.md`
4. **Browse all available rules**: `.ai-rules/README.md` for a full index

### Available Rule Files

{file_listing}

## Critical Instructions

1. **Read the rules**: ALWAYS read `.ai-rules/project-rules.md` before starting work
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Search first**: Find existing patterns before creating new ones
6. **Reference framework rules**: Read the relevant `.ai-rules/framework-*.md` files when working with specific frameworks

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

