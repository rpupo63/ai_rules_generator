"""
Functions for creating shared AI rules files that can be referenced by both Cursor and Claude.
"""

from pathlib import Path
from typing import Optional

from .models import ProjectConfig
from .config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from .file_utils import read_rule_file, extract_rule_content, read_general_guidelines
from .ai_generator import generate_ai_rules
from .generators import (
    generate_project_context,
    generate_template_single_project_rules,
    generate_general_coding_principles
)


def create_shared_ai_rules_directory(
    project_root: Path,
    config: ProjectConfig,
    base_path: Path,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> Path:
    """
    Create the shared .ai-rules directory with organized rule files.
    Returns the path to the .ai-rules directory.
    """
    ai_rules_dir = project_root / ".ai-rules"
    ai_rules_dir.mkdir(parents=True, exist_ok=True)

    # Generate main project rules file
    if use_ai:
        general_guidelines = read_general_guidelines(base_path)
        project_context = generate_project_context(config)

        ai_content = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=config.primary_language,
            frameworks=config.frameworks,
            base_path=base_path,
            rule_type='single_project',
            format_mdc=False,
            use_ai=True,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key
        )

        if ai_content:
            main_rules_content = ai_content
        else:
            main_rules_content = generate_template_single_project_rules(config, base_path)
    else:
        main_rules_content = generate_template_single_project_rules(config, base_path)

    # Save main project rules
    main_rules_file = ai_rules_dir / "project-rules.md"
    main_rules_file.write_text(main_rules_content, encoding='utf-8')

    # Generate language-specific rules if applicable
    language_key = config.primary_language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"

    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if language_info.get("rule_file"):
        rule_name = language_info["rule_file"].replace(".mdc", "")
        rule_content = read_rule_file(base_path, rule_name)
        if rule_content:
            extracted = extract_rule_content(rule_content)
            language_rules_file = ai_rules_dir / f"language-{language_key}.md"
            language_rules_file.write_text(
                f"# {config.primary_language.title()} Best Practices\n\n{extracted}",
                encoding='utf-8'
            )

    # Generate framework-specific rules
    for framework in config.frameworks:
        rule_content = read_rule_file(base_path, framework.lower())
        if rule_content:
            extracted = extract_rule_content(rule_content)
            framework_title = framework.replace("-", " ").title()
            framework_rules_file = ai_rules_dir / f"framework-{framework.lower()}.md"
            framework_rules_file.write_text(
                f"# {framework_title} Best Practices\n\n{extracted}",
                encoding='utf-8'
            )

    # Generate universal rules
    for universal_rule in UNIVERSAL_RULES:
        if universal_rule not in [f.lower() for f in config.frameworks]:
            rule_content = read_rule_file(base_path, universal_rule)
            if rule_content:
                extracted = extract_rule_content(rule_content)
                rule_title = universal_rule.replace("-", " ").title()
                universal_rules_file = ai_rules_dir / f"universal-{universal_rule}.md"
                universal_rules_file.write_text(
                    f"# {rule_title}\n\n{extracted}",
                    encoding='utf-8'
                )

    # Create README for the .ai-rules directory
    readme_content = f"""# Shared AI Rules

This directory contains shared AI coding rules for this project. These rules are referenced by both Cursor (`.cursorrules`) and Claude Code (`CLAUDE.md`).

## Files

- `project-rules.md` - Main project-specific rules and guidelines
"""
    
    if language_info.get("rule_file"):
        readme_content += f"- `language-{language_key}.md` - Language-specific best practices\n"
    
    if config.frameworks:
        for framework in config.frameworks:
            readme_content += f"- `framework-{framework.lower()}.md` - {framework.replace('-', ' ').title()} framework rules\n"
    
    for universal_rule in UNIVERSAL_RULES:
        if universal_rule not in [f.lower() for f in config.frameworks]:
            readme_content += f"- `universal-{universal_rule}.md` - Universal {universal_rule.replace('-', ' ').title()} rules\n"
    
    readme_content += f"""
## Project Information

**Description:** {config.description}
**Language:** {config.primary_language.title()}
**Frameworks:** {', '.join(config.frameworks) if config.frameworks else 'None'}
**Monorepo:** {'Yes' if config.is_monorepo else 'No'}

## Usage

These rules are automatically loaded by:
- Cursor: Via `.cursorrules` or `.cursor/rules/*.mdc` files
- Claude Code: Via `CLAUDE.md` files

You can manually reference specific rule files when needed, or let the tools automatically load the appropriate rules based on context.
"""
    
    readme_file = ai_rules_dir / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')

    return ai_rules_dir




def generate_cursorrules_with_references(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate .cursorrules file that references shared AI rules."""
    sections = []
    
    # Project header
    sections.append(f"""# AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.
For detailed rules, see the files in that directory.

""")
    
    # Reference to main project rules
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.
This includes project context, general principles, and overall guidelines.

""")
    
    # Project context summary
    sections.append(generate_project_context(config))
    
    # Quick reference to language and frameworks
    language_key = config.primary_language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"
    
    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if language_info.get("rule_file"):
        sections.append(
            f"\n## Language Rules\n\n"
            f"See `.ai-rules/language-{language_key}.md` for "
            f"{config.primary_language.title()} best practices.\n\n"
        )
    
    if config.frameworks:
        sections.append("## Framework Rules\n\n")
        for framework in config.frameworks:
            sections.append(
                f"- See `.ai-rules/framework-{framework.lower()}.md` for "
                f"{framework.replace('-', ' ').title()} rules\n"
            )
        sections.append("\n")
    
    # Include critical instructions directly
    sections.append("""## Critical Instructions

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


def generate_claude_md_with_references(
    ai_rules_dir: Path,
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate CLAUDE.md file that references shared AI rules."""
    sections = []
    
    # Project header
    sections.append(f"""# AI Coding Rules for {config.description}

This file references shared AI rules located in `.ai-rules/`.
For detailed rules, see the files in that directory.

""")
    
    # Project context
    sections.append(generate_project_context(config))
    
    # Reference to main rules
    sections.append("""## Main Rules

The primary project rules are defined in `.ai-rules/project-rules.md`.

""")
    
    # Language and framework references
    language_key = config.primary_language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"
    
    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if language_info.get("rule_file"):
        sections.append(
            f"## Language Rules\n\n"
            f"See `.ai-rules/language-{language_key}.md` for "
            f"{config.primary_language.title()} best practices.\n\n"
        )
    
    if config.frameworks:
        sections.append("## Framework Rules\n\n")
        for framework in config.frameworks:
            sections.append(
                f"- `.ai-rules/framework-{framework.lower()}.md` - "
                f"{framework.replace('-', ' ').title()} rules\n"
            )
        sections.append("\n")
    
    # Critical instructions
    sections.append("""## Critical Instructions

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

