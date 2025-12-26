"""
Rule generation functions for AI coding agent rules.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional
from models import ProjectConfig
from config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from file_utils import read_rule_file, extract_rule_content, read_general_guidelines
from ai_generator import generate_ai_rules


def generate_project_context(config: ProjectConfig) -> str:
    """Generate project-specific context section"""
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
    """Generate monorepo-specific guidelines"""
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


def generate_folder_cursor_rule(folder_path: Path, folder_name: str, language: str, 
                                 frameworks: List[str], base_path: Path, 
                                 project_root: Path, use_ai: bool = True) -> str:
    """
    Generate a Cursor MDC rule file for a specific folder.
    Uses AI generation if available, falls back to template-based generation.
    Returns the content as a string.
    """
    # Determine glob pattern based on folder path relative to project root
    try:
        rel_path = folder_path.relative_to(project_root)
        glob_base = str(rel_path).replace('\\', '/')  # Use forward slashes for glob patterns
    except ValueError:
        # If folder_path is not relative to project_root, just use folder name
        glob_base = folder_name
    
    # Determine file extensions for glob
    if language == "python":
        glob_pattern = f"{glob_base}/**/*.py"
    elif language in ["typescript", "javascript"]:
        glob_pattern = f"{glob_base}/**/*.{{ts,tsx,js,jsx}}"
    elif language == "rust":
        glob_pattern = f"{glob_base}/**/*.rs"
    elif language == "go":
        glob_pattern = f"{glob_base}/**/*.go"
    else:
        glob_pattern = f"{glob_base}/**/*"
    
    # Try AI generation first
    if use_ai:
        general_guidelines = read_general_guidelines(base_path)
        project_context = f"""
**Folder:** {folder_name}
**Path:** {glob_base}
**Language:** {language.title()}
**Frameworks:** {', '.join(frameworks) if frameworks else 'None'}
**Glob Pattern:** {glob_pattern}
"""
        
        ai_content = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=language,
            frameworks=frameworks,
            base_path=base_path,
            rule_type='folder',
            format_mdc=True,
            use_ai=True
        )
        
        if ai_content:
            # Ensure it has proper frontmatter with glob pattern
            if not ai_content.strip().startswith('---'):
                # Add frontmatter if missing
                frontmatter = f"""---
description: {folder_name.title()} package-specific rules
globs:
  - "{glob_pattern}"
alwaysApply: false
---

"""
                return frontmatter + ai_content
            else:
                # Update glob pattern in existing frontmatter
                lines = ai_content.split('\n')
                if 'globs:' in ai_content:
                    # Find and update glob pattern
                    new_lines = []
                    in_globs = False
                    for i, line in enumerate(lines):
                        if 'globs:' in line:
                            in_globs = True
                            new_lines.append(line)
                        elif in_globs and line.strip().startswith('-'):
                            new_lines.append(f'  - "{glob_pattern}"')
                            in_globs = False
                        else:
                            new_lines.append(line)
                    return '\n'.join(new_lines)
                return ai_content
    
    # Fallback to template-based generation
    sections = []
    
    # YAML frontmatter
    sections.append("---")
    sections.append(f"description: {folder_name.title()} package-specific rules")
    sections.append(f"globs:")
    sections.append(f'  - "{glob_pattern}"')
    sections.append("alwaysApply: false")
    sections.append("---")
    sections.append("")
    
    # Folder description
    sections.append(f"# {folder_name.title()} Package")
    sections.append("")
    sections.append(f"This folder contains the **{folder_name}** package.")
    sections.append("")
    
    # Technology stack
    sections.append("## Technology Stack")
    sections.append(f"- Language: {language.title()}")
    if frameworks:
        sections.append(f"- Frameworks: {', '.join(f.replace('-', ' ').title() for f in frameworks)}")
    sections.append("")
    
    # Language-specific rules
    language_key = language.lower()
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
            # Truncate to keep under 150 lines as per best practices
            lines = extracted.split('\n')
            if len(lines) > 100:
                extracted = '\n'.join(lines[:100]) + "\n\n[... additional rules apply from general guidelines ...]"
            sections.append(f"## {language.title()} Best Practices")
            sections.append("")
            sections.append(extracted)
            sections.append("")
    
    # Framework-specific rules
    for framework in frameworks[:2]:  # Limit to 2 frameworks to keep file size manageable
        rule_content = read_rule_file(base_path, framework.lower())
        if rule_content:
            extracted = extract_rule_content(rule_content)
            lines = extracted.split('\n')
            if len(lines) > 80:
                extracted = '\n'.join(lines[:80]) + "\n\n[... truncated for brevity ...]"
            framework_title = framework.replace("-", " ").title()
            sections.append(f"## {framework_title} Patterns")
            sections.append("")
            sections.append(extracted)
            sections.append("")
    
    # Commands section
    sections.append("## Commands")
    if language == "python":
        sections.append("- Run tests: `pytest` or `python -m pytest`")
        sections.append("- Install dependencies: `pip install -r requirements.txt`")
    elif language in ["typescript", "javascript"]:
        sections.append("- Install dependencies: `npm install` or `yarn install`")
        sections.append("- Run tests: `npm test` or `yarn test`")
        sections.append("- Build: `npm run build` or `yarn build`")
    sections.append("")
    
    # Gotchas
    sections.append("## Gotchas")
    sections.append("- Check existing patterns before creating new functionality")
    sections.append("- Maintain consistency with other packages in this monorepo")
    sections.append("")
    
    content = '\n'.join(sections)
    # Ensure it's under 150 lines
    lines = content.split('\n')
    if len(lines) > 150:
        content = '\n'.join(lines[:150])
    
    return content


def generate_folder_agents_md(folder_path: Path, folder_name: str, language: str,
                               frameworks: List[str], base_path: Path, use_ai: bool = True) -> str:
    """
    Generate an AGENTS.md file for a folder (cross-tool standard).
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
            use_ai=True
        )
        
        if ai_content:
            return ai_content
    
    # Fallback to template-based generation
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
    language_key = language.lower()
    if language_key in ["typescript", "ts"]:
        sections.append("### TypeScript Notes")
        sections.append("- Use strict type checking")
        sections.append("- Prefer interfaces over types for object shapes")
        sections.append("")
    elif language_key == "python":
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


def generate_root_monorepo_rules(config: ProjectConfig, base_path: Path, 
                                  packages: List[Tuple[Path, str, List[str]]], 
                                  format_mdc: bool = False, use_ai: bool = True) -> str:
    """
    Generate root-level rules for a monorepo with progressive disclosure.
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
            all_languages=all_languages
        )
        
        if ai_content:
            # Ensure proper frontmatter for MDC format
            if format_mdc and not ai_content.strip().startswith('---'):
                frontmatter = """---
description: Monorepo-wide coding rules and guidelines
globs:
  - "**/*"
alwaysApply: true
---

"""
                return frontmatter + ai_content
            elif format_mdc:
                # Ensure frontmatter has correct values
                lines = ai_content.split('\n')
                if 'alwaysApply:' in ai_content:
                    # Update to always apply
                    new_lines = []
                    for line in lines:
                        if 'alwaysApply:' in line:
                            new_lines.append('alwaysApply: true')
                        else:
                            new_lines.append(line)
                    return '\n'.join(new_lines)
            return ai_content
    
    # Fallback to template-based generation
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
    sections.append("""## General Coding Principles

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

""")
    
    # Monorepo structure
    sections.append("""## Monorepo Structure

This is a monorepo project. Follow these guidelines:
- Maintain clear boundaries between packages/apps
- Use workspace-aware dependency management
- Avoid circular dependencies between packages
- Use proper import paths respecting workspace structure
- Each package should be independently testable
- Document package dependencies clearly
- Use consistent naming conventions across packages

""")
    
    # Progressive disclosure - point to package-specific rules
    if packages:
        sections.append("## Package-Specific Rules")
        sections.append("")
        sections.append("Each package has its own rules. When working in a package, refer to:")
        sections.append("")
        for folder_path, language, frameworks in packages:
            folder_name = folder_path.name
            sections.append(f"- **{folder_name}/**: {language.title()}" + 
                          (f" with {', '.join(f.replace('-', ' ').title() for f in frameworks[:2])}" if frameworks else ""))
            sections.append(f"  - See `{folder_name}/.cursor/rules/` for Cursor rules")
            sections.append(f"  - See `{folder_name}/AGENTS.md` for cross-tool rules")
        sections.append("")
    
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
    
    return "\n".join(sections)


def generate_rules_document(config: ProjectConfig, base_path: Path, use_ai: bool = True) -> str:
    """
    Generate the complete AI rules document by combining:
    1. General guidelines
    2. Project context
    3. Language-specific rules
    4. Framework-specific rules
    5. Universal best practices
    
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
            use_ai=True
        )
        
        if ai_content:
            return ai_content
    
    # Fallback to template-based generation
    sections = []
    
    # 1. Project Context
    sections.append("# AI Coding Agent Rules\n")
    sections.append(generate_project_context(config))
    
    # 2. General Guidelines (extract key principles)
    sections.append("""## General Coding Principles

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

""")
    
    # 3. Monorepo-specific guidelines
    if config.is_monorepo:
        sections.append(generate_monorepo_section(config))
    
    # 4. Language-specific rules
    language_key = config.primary_language.lower()
    # Handle aliases (js -> javascript, ts -> typescript)
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
    
    # 5. Framework-specific rules
    for framework in config.frameworks:
        rule_content = read_rule_file(base_path, framework.lower())
        if rule_content:
            extracted = extract_rule_content(rule_content)
            framework_title = framework.replace("-", " ").title()
            sections.append(f"## {framework_title} Best Practices\n\n{extracted}\n\n")
        else:
            print(f"Warning: Could not load {framework} rules file", file=sys.stderr)
    
    # 6. Universal best practices
    for universal_rule in UNIVERSAL_RULES:
        if universal_rule not in [f.lower() for f in config.frameworks]:
            rule_content = read_rule_file(base_path, universal_rule)
            if rule_content:
                extracted = extract_rule_content(rule_content)
                rule_title = universal_rule.replace("-", " ").title()
                sections.append(f"## {rule_title}\n\n{extracted}\n\n")
    
    # 7. Repository Navigation
    sections.append("""## Repository Navigation & Information

When working in this repository:
- Use codebase_search to find existing patterns and similar implementations
- Check existing components, utilities, and patterns before creating new ones
- Follow the established project structure and conventions
- Review related files to understand the codebase architecture
- Ask for clarification if the codebase structure is unclear

""")
    
    # 8. Critical Instructions
    sections.append("""## Critical Instructions

1. **Always verify before implementing**: Search for similar functionality first
2. **Follow project conventions**: Match existing code style and patterns
3. **Security first**: Never introduce security vulnerabilities
4. **Test your code**: Ensure new code passes all tests
5. **Document complex logic**: Add comments for non-obvious code
6. **Be specific**: When asked for fixes or explanations, provide actual code, not high-level descriptions
7. **Question assumptions**: Don't blindly implement - think critically about solutions

""")
    
    return "\n".join(sections)

