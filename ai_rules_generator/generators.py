"""
Rule generation functions for AI coding agent rules.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .models import ProjectConfig
from .config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from .file_utils import read_rule_file, extract_rule_content, read_general_guidelines
from .ai_generator import generate_ai_rules


@dataclass
class FolderRuleConfig:
    """Configuration for folder rule generation"""
    folder_path: Path
    folder_name: str
    language: str
    frameworks: List[str]
    base_path: Path
    project_root: Path
    use_ai: bool = True
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None


def generate_project_context(config: ProjectConfig) -> str:
    """Generate project-specific context section. Max 20 lines."""
    context = f"""
## Project Context

**Project Description:**
{config.description}

**Technology Stack:**
- Primary Language: {config.primary_language.title()}
- Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None specified'}
- Monorepo: {'Yes' if config.is_monorepo else 'No'}

"""
    return context


def generate_monorepo_section(config: ProjectConfig) -> str:
    """Generate monorepo-specific guidelines. Max 20 lines."""
    if not config.is_monorepo:
        return ""

    return """
## Monorepo Structure

This is a monorepo project. Follow these guidelines:
- Maintain clear boundaries between packages/apps
- Use workspace-aware dependency management
- Avoid circular dependencies between packages
- Use proper import paths respecting workspace structure
- Each package should be independently testable
- Document package dependencies clearly
- Use consistent naming conventions across packages

"""


def determine_glob_pattern(
    folder_path: Path,
    folder_name: str,
    language: str,
    project_root: Path
) -> str:
    """Determine glob pattern for folder. Max 25 lines."""
    try:
        rel_path = folder_path.relative_to(project_root)
        glob_base = str(rel_path).replace('\\', '/')
    except ValueError:
        glob_base = folder_name

    # Language-specific extensions
    extension_map = {
        "python": "py",
        "typescript": "{ts,tsx,js,jsx}",
        "javascript": "{js,jsx}",
        "rust": "rs",
        "go": "go",
        "java": "java",
        "cpp": "{cpp,hpp,cc,h}"
    }

    ext = extension_map.get(language, "*")
    return f"{glob_base}/**/*.{ext}"


def try_ai_generation_for_folder(config: FolderRuleConfig, glob_pattern: str) -> Optional[str]:
    """Try AI generation for folder rules. Max 25 lines."""
    general_guidelines = read_general_guidelines(config.base_path)
    project_context = f"""
**Folder:** {config.folder_name}
**Path:** {glob_pattern.split('/*')[0]}
**Language:** {config.language.title()}
**Frameworks:** {', '.join(config.frameworks) if config.frameworks else 'None'}
**Glob Pattern:** {glob_pattern}
"""

    return generate_ai_rules(
        general_guidelines=general_guidelines,
        project_context=project_context,
        language=config.language,
        frameworks=config.frameworks,
        base_path=config.base_path,
        rule_type='folder',
        format_mdc=True,
        use_ai=True,
        ai_provider=config.ai_provider,
        ai_model=config.ai_model,
        openai_key=config.openai_key,
        anthropic_key=config.anthropic_key
    )


def create_frontmatter(folder_name: str, glob_pattern: str) -> str:
    """Create MDC frontmatter. Max 15 lines."""
    return f"""---
description: {folder_name.title()} package-specific rules
globs:
  - "{glob_pattern}"
alwaysApply: false
---

"""


def update_glob_in_frontmatter(content: str, glob_pattern: str) -> str:
    """Update glob pattern in existing frontmatter. Max 25 lines."""
    lines = content.split('\n')
    if 'globs:' not in content:
        return content

    new_lines = []
    in_globs = False

    for line in lines:
        if 'globs:' in line:
            in_globs = True
            new_lines.append(line)
        elif in_globs and line.strip().startswith('-'):
            new_lines.append(f'  - "{glob_pattern}"')
            in_globs = False
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def ensure_proper_frontmatter(
    content: str,
    folder_name: str,
    glob_pattern: str
) -> str:
    """Ensure MDC content has proper frontmatter. Max 20 lines."""
    if not content.strip().startswith('---'):
        return create_frontmatter(folder_name, glob_pattern) + content

    # Update existing frontmatter with correct glob
    return update_glob_in_frontmatter(content, glob_pattern)


def build_folder_header(folder_name: str) -> str:
    """Build folder header section. Max 10 lines."""
    return f"""# {folder_name.title()} Package

This folder contains the **{folder_name}** package.

"""


def build_tech_stack_section(language: str, frameworks: List[str]) -> str:
    """Build technology stack section. Max 12 lines."""
    section = f"""## Technology Stack
- Language: {language.title()}
"""
    if frameworks:
        fw_titles = ', '.join(f.replace('-', ' ').title() for f in frameworks)
        section += f"- Frameworks: {fw_titles}\n"

    return section + "\n"


def build_language_rules_section(language: str, base_path: Path) -> str:
    """Build language-specific rules section. Max 30 lines."""
    language_key = language.lower()
    if language_key == "js":
        language_key = "javascript"
    elif language_key == "ts":
        language_key = "typescript"

    language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
    if not language_info.get("rule_file"):
        return ""

    rule_name = language_info["rule_file"].replace(".mdc", "")
    rule_content = read_rule_file(base_path, rule_name)
    if not rule_content:
        return ""

    extracted = extract_rule_content(rule_content)
    # Truncate to keep under 100 lines as per best practices
    lines = extracted.split('\n')
    if len(lines) > 100:
        extracted = '\n'.join(lines[:100]) + "\n\n[... additional rules apply from general guidelines ...]"

    return f"""## {language.title()} Best Practices

{extracted}

"""


def build_framework_rules_sections(frameworks: List[str], base_path: Path) -> str:
    """Build framework-specific rules sections. Max 35 lines."""
    sections = []

    for framework in frameworks[:2]:  # Limit to 2 frameworks to keep file size manageable
        rule_content = read_rule_file(base_path, framework.lower())
        if not rule_content:
            continue

        extracted = extract_rule_content(rule_content)
        lines = extracted.split('\n')
        if len(lines) > 80:
            extracted = '\n'.join(lines[:80]) + "\n\n[... truncated for brevity ...]"

        framework_title = framework.replace("-", " ").title()
        sections.append(f"""## {framework_title} Patterns

{extracted}

""")

    return ''.join(sections)


def build_commands_section(language: str) -> str:
    """Build commands section for language. Max 20 lines."""
    commands = {
        "python": [
            "- Run tests: `pytest` or `python -m pytest`",
            "- Install dependencies: `pip install -r requirements.txt`"
        ],
        "typescript": [
            "- Install: `npm install` or `yarn install`",
            "- Test: `npm test` or `yarn test`",
            "- Build: `npm run build` or `yarn build`"
        ],
        "javascript": [
            "- Install: `npm install`",
            "- Test: `npm test`"
        ]
    }

    section = "## Commands\n"
    for cmd in commands.get(language, []):
        section += cmd + "\n"

    return section + "\n"


def build_gotchas_section() -> str:
    """Build gotchas section. Max 10 lines."""
    return """## Gotchas
- Check existing patterns before creating new functionality
- Maintain consistency with other packages in this monorepo

"""


def generate_template_cursor_rule(
    config: FolderRuleConfig,
    glob_pattern: str
) -> str:
    """Generate template-based cursor rule. Max 30 lines."""
    sections = [
        create_frontmatter(config.folder_name, glob_pattern),
        build_folder_header(config.folder_name),
        build_tech_stack_section(config.language, config.frameworks),
        build_language_rules_section(config.language, config.base_path),
        build_framework_rules_sections(config.frameworks, config.base_path),
        build_commands_section(config.language),
        build_gotchas_section()
    ]

    content = ''.join(sections)

    # Limit to 150 lines
    lines = content.split('\n')
    if len(lines) > 150:
        content = '\n'.join(lines[:150])

    return content


def generate_folder_cursor_rule(
    folder_path: Path,
    folder_name: str,
    language: str,
    frameworks: List[str],
    base_path: Path,
    project_root: Path,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> str:
    """
    Generate a Cursor MDC rule file for a specific folder. Max 30 lines.
    Uses AI generation if available, falls back to template-based generation.
    Returns the content as a string.
    """
    config = FolderRuleConfig(
        folder_path=folder_path,
        folder_name=folder_name,
        language=language,
        frameworks=frameworks,
        base_path=base_path,
        project_root=project_root,
        use_ai=use_ai,
        ai_provider=ai_provider,
        ai_model=ai_model,
        openai_key=openai_key,
        anthropic_key=anthropic_key
    )

    glob_pattern = determine_glob_pattern(
        folder_path, folder_name, language, project_root
    )

    # Try AI generation first
    if use_ai:
        ai_content = try_ai_generation_for_folder(config, glob_pattern)
        if ai_content:
            return ensure_proper_frontmatter(ai_content, folder_name, glob_pattern)

    # Fallback to template-based generation
    return generate_template_cursor_rule(config, glob_pattern)


def generate_folder_agents_md(
    folder_path: Path,
    folder_name: str,
    language: str,
    frameworks: List[str],
    base_path: Path,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> str:
    """
    Generate an AGENTS.md file for a folder (cross-tool standard). Max 30 lines.
    Uses AI generation if available, falls back to template-based generation.
    Returns the content as a string.
    """
    # Try AI generation first
    if use_ai:
        general_guidelines = read_general_guidelines(base_path)
        project_context = f"""
**Folder:** {folder_name}
**Language:** {language.title()}
**Frameworks:** {', '.join(frameworks) if frameworks else 'None'}
"""

        ai_content = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=language,
            frameworks=frameworks,
            base_path=base_path,
            rule_type='folder',
            format_mdc=False,
            use_ai=True,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key
        )

        if ai_content:
            return ai_content

    # Fallback to template-based generation
    return generate_template_agents_md(folder_name, language, frameworks)


def generate_template_agents_md(
    folder_name: str,
    language: str,
    frameworks: List[str]
) -> str:
    """Generate template-based AGENTS.md content. Max 45 lines."""
    sections = []

    sections.append(f"# {folder_name.title()} Package")
    sections.append("")
    sections.append(f"This folder contains the **{folder_name}** package implementation.")
    sections.append("")

    # Technology stack
    sections.append("## Technology Stack")
    sections.append(f"- Language: {language.title()}")
    if frameworks:
        sections.append(f"- Frameworks: {', '.join(f.replace('-', ' ').title() for f in frameworks)}")
    sections.append("")

    # Commands
    sections.append("## Commands")
    if language == "python":
        sections.append("- Install: `pip install -r requirements.txt`")
        sections.append("- Test: `pytest`")
        sections.append("- Lint: `flake8 .` or `black --check .`")
    elif language in ["typescript", "javascript"]:
        sections.append("- Install: `npm install`")
        sections.append("- Test: `npm test`")
        sections.append("- Lint: `npm run lint`")
        sections.append("- Build: `npm run build`")
    sections.append("")

    # Patterns - concise version
    sections.append("## Patterns")
    sections.append("- Follow the established architecture patterns in this folder")
    sections.append("- Use existing utilities and helpers before creating new ones")
    sections.append("- Maintain consistency with the overall monorepo structure")
    sections.append("")

    # Language-specific notes
    if language in ["typescript", "ts"]:
        sections.append("### TypeScript Notes")
        sections.append("- Use strict type checking")
        sections.append("- Prefer interfaces over types for object shapes")
        sections.append("")
    elif language == "python":
        sections.append("### Python Notes")
        sections.append("- Follow PEP 8 style guide")
        sections.append("- Use type hints for all functions")
        sections.append("")

    content = '\n'.join(sections)

    # Keep it concise - under 80 lines
    lines = content.split('\n')
    if len(lines) > 80:
        content = '\n'.join(lines[:80])

    return content


def generate_root_monorepo_rules(
    config: ProjectConfig,
    base_path: Path,
    packages: List[Tuple[Path, str, List[str]]],
    format_mdc: bool = False,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> str:
    """
    Generate root-level rules for a monorepo. Max 45 lines.
    Uses AI generation if available, falls back to template-based generation.
    If format_mdc is True, include YAML frontmatter for Cursor MDC format.
    """
    # Try AI generation first
    if use_ai:
        general_guidelines = read_general_guidelines(base_path)
        project_context = generate_project_context(config)

        # Add package information
        packages_info = "\n**Packages:**\n"
        for folder_path, language, frameworks in packages:
            folder_name = folder_path.name
            packages_info += f"- {folder_name}: {language.title()}"
            if frameworks:
                packages_info += f" ({', '.join(frameworks)})"
            packages_info += "\n"

        full_context = project_context + packages_info

        # Collect all languages from packages for monorepo root
        all_languages = [lang for _, lang, _ in packages]

        ai_content = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=full_context,
            language=None,  # Monorepo root has no single language
            frameworks=[],
            base_path=base_path,
            rule_type='monorepo_root',
            format_mdc=format_mdc,
            use_ai=True,
            all_languages=all_languages,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key
        )

        if ai_content:
            return ensure_proper_monorepo_frontmatter(ai_content, format_mdc)

    # Fallback to template-based generation
    return generate_template_monorepo_rules(config, packages, format_mdc)


def ensure_proper_monorepo_frontmatter(content: str, format_mdc: bool) -> str:
    """Ensure proper frontmatter for monorepo MDC format. Max 30 lines."""
    if not format_mdc:
        return content

    if not content.strip().startswith('---'):
        frontmatter = """---
description: Monorepo-wide coding rules and guidelines
globs:
  - "**/*"
alwaysApply: true
---

"""
        return frontmatter + content

    # Update frontmatter to always apply
    lines = content.split('\n')
    if 'alwaysApply:' in content:
        new_lines = []
        for line in lines:
            if 'alwaysApply:' in line:
                new_lines.append('alwaysApply: true')
            else:
                new_lines.append(line)
        return '\n'.join(new_lines)

    return content


def generate_general_coding_principles() -> str:
    """Generate general coding principles section. Max 45 lines."""
    return """## General Coding Principles

The following principles should guide all code generation:

### Rule Effectiveness
- Use specific, example-driven rules rather than vague descriptions
- Include concrete code examples with ❌→✅ format showing anti-patterns and correct patterns
- Apply absolute language (ALWAYS, NEVER, MUST) for critical rules
- Keep rules concise and context-specific

### Code Quality
- Write code that passes linters with zero warnings
- Follow language-specific style guides strictly
- Maximum 50 lines per function (target < 30)
- Use meaningful variable and function names
- Document complex logic with clear comments

### Security
- NEVER commit API keys, passwords, tokens, or .env files
- Validate ALL user input using schema validation
- Never use `eval()`, `Function()`, or dynamic code execution
- Use parameterized queries only—never string concatenation for SQL
- Hash passwords with bcrypt (minimum 10 rounds)
- Apply Content-Security-Policy headers

### Error Handling
- Use Result<T> or similar patterns for error handling
- Never return null for error cases—use explicit error types
- Log errors appropriately with context
- Handle edge cases gracefully
- Provide user-friendly error messages

### Testing
- Write tests for all new functionality
- Aim for >80% code coverage
- Test error scenarios and edge cases
- Use proper test fixtures and mocking

### Workflow
- SEARCH FIRST - Use codebase_search to find similar functionality before implementing
- Investigate deeply, be 100% sure before implementing
- Before completing: run typecheck, verify imports, check linting
- Question assumptions, offer counterpoints when suggestions seem flawed

"""


def generate_package_specific_rules_section(
    packages: List[Tuple[Path, str, List[str]]]
) -> str:
    """Generate package-specific rules section. Max 25 lines."""
    if not packages:
        return ""

    sections = ["## Package-Specific Rules\n"]
    sections.append("Each package has its own rules. When working in a package, refer to:\n")

    for folder_path, language, frameworks in packages:
        folder_name = folder_path.name
        fw_str = f" with {', '.join(f.replace('-', ' ').title() for f in frameworks[:2])}" if frameworks else ""
        sections.append(f"- **{folder_name}/**: {language.title()}{fw_str}")
        sections.append(f"  - See `{folder_name}/.cursor/rules/` for Cursor rules")
        sections.append(f"  - See `{folder_name}/AGENTS.md` for cross-tool rules")

    sections.append("")
    return '\n'.join(sections)


def generate_template_monorepo_rules(
    config: ProjectConfig,
    packages: List[Tuple[Path, str, List[str]]],
    format_mdc: bool
) -> str:
    """Generate template-based monorepo rules. Max 45 lines."""
    sections = []

    # YAML frontmatter for MDC format
    if format_mdc:
        sections.append("---")
        sections.append("description: Monorepo-wide coding rules and guidelines")
        sections.append("globs:")
        sections.append('  - "**/*"')
        sections.append("alwaysApply: true")
        sections.append("---")
        sections.append("")

    # Project Context
    sections.append("# Monorepo AI Coding Rules")
    sections.append("")
    sections.append(generate_project_context(config))

    # General Guidelines
    sections.append(generate_general_coding_principles())

    # Monorepo structure
    sections.append(generate_monorepo_section(config))

    # Progressive disclosure - point to package-specific rules
    sections.append(generate_package_specific_rules_section(packages))

    # Repository Navigation
    sections.append("""## Repository Navigation & Information

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- For package-specific guidance, check the package's .cursor/rules/ or AGENTS.md file

""")

    # Critical Instructions
    sections.append("""## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Be specific**: When asked for fixes or explanations, provide actual code, not high-level descriptions
7. **Question assumptions**: Don't blindly implement - think critically about solutions

""")

    return "".join(sections)


def generate_rules_document(
    config: ProjectConfig,
    base_path: Path,
    use_ai: bool = True,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> str:
    """
    Generate the complete AI rules document. Max 45 lines.
    Combines general guidelines, project context, language/framework rules.
    Uses AI generation if available, falls back to template-based generation.
    """
    # Try AI generation first
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
            return ai_content

    # Fallback to template-based generation
    return generate_template_single_project_rules(config, base_path)


def generate_template_single_project_rules(
    config: ProjectConfig,
    base_path: Path
) -> str:
    """Generate template-based single project rules. Max 45 lines."""
    sections = []

    # Project Context
    sections.append("# AI Coding Agent Rules\n")
    sections.append(generate_project_context(config))

    # General Guidelines
    sections.append(generate_general_coding_principles())

    # Monorepo-specific guidelines
    if config.is_monorepo:
        sections.append(generate_monorepo_section(config))

    # Language-specific rules
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
            sections.append(f"## {config.primary_language.title()} Best Practices\n\n{extracted}\n\n")
        else:
            print(f"Warning: Could not load {rule_name} rules file", file=sys.stderr)

    # Framework-specific rules
    for framework in config.frameworks:
        rule_content = read_rule_file(base_path, framework.lower())
        if rule_content:
            extracted = extract_rule_content(rule_content)
            framework_title = framework.replace("-", " ").title()
            sections.append(f"## {framework_title} Best Practices\n\n{extracted}\n\n")
        else:
            print(f"Warning: Could not load {framework} rules file", file=sys.stderr)

    # Universal best practices
    for universal_rule in UNIVERSAL_RULES:
        if universal_rule not in [f.lower() for f in config.frameworks]:
            rule_content = read_rule_file(base_path, universal_rule)
            if rule_content:
                extracted = extract_rule_content(rule_content)
                rule_title = universal_rule.replace("-", " ").title()
                sections.append(f"## {rule_title}\n\n{extracted}\n\n")

    # Repository Navigation
    sections.append("""## Repository Navigation & Information

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Ask for clarification if the codebase structure is unclear

""")

    # Critical Instructions
    sections.append("""## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Be specific**: When asked for fixes or explanations, provide actual code, not high-level descriptions
7. **Question assumptions**: Don't blindly implement - think critically about solutions

""")

    return "".join(sections)
