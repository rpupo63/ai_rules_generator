"""
AI-powered rule generation using LLM APIs.
Generates custom rules based on general guidelines and project context.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .file_utils import read_general_guidelines, read_rule_file, extract_rule_content
from .config import LANGUAGE_FRAMEWORK_MAP


@dataclass
class RuleSearchConfig:
    """Configuration for rule file search"""
    language: Optional[str]
    frameworks: List[str]
    base_path: Path
    is_monorepo_root: bool = False
    all_languages: Optional[List[str]] = None


@dataclass
class PromptConfig:
    """Configuration for AI prompt generation"""
    general_guidelines: str
    project_context: str
    relevant_rules: List[Tuple[str, str]]
    rule_type: str
    format_mdc: bool = False


def normalize_language_key(language: str) -> str:
    """Normalize language key (js->javascript, ts->typescript). Max 10 lines."""
    lang_key = language.lower()
    aliases = {"js": "javascript", "ts": "typescript"}
    return aliases.get(lang_key, lang_key)


def get_language_rule(base_path: Path, language: str) -> Optional[Tuple[str, str]]:
    """Get rule file for a specific language. Max 20 lines."""
    lang_key = normalize_language_key(language)
    language_info = LANGUAGE_FRAMEWORK_MAP.get(lang_key, {})

    if language_info.get("rule_file"):
        rule_name = language_info["rule_file"].replace(".mdc", "")
        rule_content = read_rule_file(base_path, rule_name)
        if rule_content:
            return (rule_name, rule_content)

    return None


def get_additional_language_rules(
    base_path: Path,
    language: str
) -> List[Tuple[str, str]]:
    """Get additional universal rules for language. Max 20 lines."""
    lang_key = normalize_language_key(language)
    language_info = LANGUAGE_FRAMEWORK_MAP.get(lang_key, {})

    additional_rules = []
    for rule_name in language_info.get("additional", []):
        rule_content = read_rule_file(base_path, rule_name)
        if rule_content:
            additional_rules.append((rule_name, rule_content))

    return additional_rules


def get_monorepo_root_rules(config: RuleSearchConfig) -> List[Tuple[str, str]]:
    """Get universal rules for monorepo root. Max 35 lines."""
    relevant_rules = []

    # Universal rules
    universal_rules = ["codequality", "clean-code", "gitflow"]
    for rule_name in universal_rules:
        rule_content = read_rule_file(config.base_path, rule_name)
        if rule_content:
            relevant_rules.append((rule_name, rule_content))

    # Language-specific rules for all languages in monorepo
    if config.all_languages:
        seen_languages = set()
        for lang in config.all_languages:
            lang_key = normalize_language_key(lang)

            # Avoid duplicates
            if lang_key in seen_languages:
                continue
            seen_languages.add(lang_key)

            lang_rule = get_language_rule(config.base_path, lang)
            if lang_rule:
                relevant_rules.append(lang_rule)

    return relevant_rules


def get_folder_specific_rules(config: RuleSearchConfig) -> List[Tuple[str, str]]:
    """Get language and framework rules for specific folder. Max 30 lines."""
    relevant_rules = []

    if config.language:
        # Add language rule
        lang_rule = get_language_rule(config.base_path, config.language)
        if lang_rule:
            relevant_rules.append(lang_rule)

        # Add additional universal rules for language
        additional = get_additional_language_rules(config.base_path, config.language)
        relevant_rules.extend(additional)

    # Add framework rules (limit to 3)
    for framework in config.frameworks[:3]:
        rule_content = read_rule_file(config.base_path, framework.lower())
        if rule_content:
            relevant_rules.append((framework.lower(), rule_content))

    return relevant_rules


def get_relevant_rule_files(config: RuleSearchConfig) -> List[Tuple[str, str]]:
    """
    Get list of relevant rule files from awesome-cursorrules. Max 15 lines.
    Returns list of (rule_name, rule_content) tuples.

    For monorepo root, returns universal rules + language rules for all languages.
    For specific folders, returns language and framework-specific rules.
    """
    if config.is_monorepo_root:
        return get_monorepo_root_rules(config)
    else:
        return get_folder_specific_rules(config)


def truncate_rule_content(content: str, max_lines: int = 100) -> str:
    """Truncate rule content to max lines. Max 10 lines."""
    lines = content.split('\n')
    if len(lines) > max_lines:
        return '\n'.join(lines[:max_lines]) + "\n[... truncated ...]"
    return content


def build_prompt_header() -> str:
    """Build prompt header. Max 10 lines."""
    return """You are an expert at creating AI coding agent rules for Cursor and Claude Code.
Based on the following guidelines and context, generate a comprehensive,
example-driven rules document."""


def build_guidelines_section(general_guidelines: str) -> str:
    """Build general guidelines section. Max 10 lines."""
    return f"""## General Guidelines for Effective Rules

{general_guidelines}"""


def build_context_section(project_context: str) -> str:
    """Build project context section. Max 10 lines."""
    return f"""## Project Context

{project_context}"""


def build_reference_rules_section(
    relevant_rules: List[Tuple[str, str]]
) -> str:
    """Build reference rules section with truncation. Max 40 lines."""
    if not relevant_rules:
        return "(No specific language/framework rules found - generate general best practices)"

    header = """## Relevant Reference Rules from awesome-cursorrules

The following rules from the awesome-cursorrules repository (https://github.com/awesome-cursorrules/awesome-cursorrules)
are relevant for this context. These are community-vetted best practices for the specific language/framework combination.

**IMPORTANT:** Use these as reference and incorporate their best practices, but create a CUSTOM, PROJECT-SPECIFIC version that:
- Follows the general guidelines above
- Is tailored to the specific project context
- Includes project-specific examples and patterns
- References these files when appropriate (e.g., "Following patterns from awesome-cursorrules/python.mdc...")

"""

    rule_sections = []
    for rule_name, rule_content in relevant_rules:
        extracted = extract_rule_content(rule_content)
        truncated = truncate_rule_content(extracted, max_lines=100)
        rule_sections.append(
            f"### Reference: awesome-cursorrules/rules-new/{rule_name}.mdc\n{truncated}"
        )

    return header + "\n\n".join(rule_sections)


def build_task_section(rule_type: str) -> str:
    """Build task instructions section. Max 30 lines."""
    return f"""## Task

Generate a custom rules document for this {rule_type} that:

1. **Follows the general guidelines** - Use specific, example-driven rules with ❌→✅ format
2. **References the relevant rules above** - Incorporate best practices from the reference rules, but make them project-specific
3. **Is concise and actionable** - Maximum 500 lines, prefer 200-300 lines
4. **Includes concrete examples** - Show anti-patterns and correct patterns with actual code
5. **Uses absolute language** - ALWAYS, NEVER, MUST for critical rules
6. **Is context-appropriate** - Tailored to the specific project context provided
"""


def build_format_requirements(format_mdc: bool) -> str:
    """Build format requirements section. Max 20 lines."""
    if format_mdc:
        return """## Format Requirements

Generate the content in Cursor MDC format with YAML frontmatter:
- Include appropriate `description`, `globs`, and `alwaysApply` fields
- The content after the frontmatter should be the actual rules
"""
    else:
        return """## Format Requirements

Generate the content in markdown format suitable for CLAUDE.md or AGENTS.md:
- Start with a clear title
- Use proper markdown formatting
- Include sections for: Project Context, Technology Stack, Coding Standards, Testing, Common Pitfalls, Commands
"""


def build_prompt_footer() -> str:
    """Build prompt footer. Max 15 lines."""
    return """
Generate the rules document now. Focus on being specific, example-driven, and actionable.

**When referencing awesome-cursorrules files:**
- You can mention them explicitly (e.g., "Following patterns from awesome-cursorrules/python.mdc...")
- Incorporate their best practices into your custom rules
- Make everything project-specific and following the general guidelines
- Don't just copy - synthesize and customize for this specific project context
"""


def build_ai_prompt(config: PromptConfig) -> str:
    """Build AI generation prompt. Max 25 lines."""
    sections = [
        build_prompt_header(),
        build_guidelines_section(config.general_guidelines),
        build_context_section(config.project_context),
        build_reference_rules_section(config.relevant_rules),
        build_task_section(config.rule_type),
        build_format_requirements(config.format_mdc),
        build_prompt_footer()
    ]

    return "\n\n".join(sections)


def call_openai_api(prompt: str, model: str, api_key: Optional[str] = None) -> Optional[str]:
    """Call OpenAI API to generate rules. Max 30 lines."""
    try:
        import openai

        # Use provided key, fall back to environment variable
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            print("Error: OPENAI_API_KEY not set. Use 'config edit' to add it or set environment variable.", file=sys.stderr)
            return None

        client = openai.OpenAI(api_key=key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at creating AI coding agent rules. You create specific, example-driven rules that follow best practices for Cursor and Claude Code."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=4000
        )

        return response.choices[0].message.content.strip()

    except ImportError:
        print("Error: openai package not installed. Install with: pip install openai", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: OpenAI API call failed: {e}", file=sys.stderr)
        return None


def call_anthropic_api(prompt: str, model: str, api_key: Optional[str] = None) -> Optional[str]:
    """Call Anthropic API to generate rules. Max 30 lines."""
    try:
        import anthropic

        # Use provided key, fall back to environment variable
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            print("Error: ANTHROPIC_API_KEY not set. Use 'config edit' to add it or set environment variable.", file=sys.stderr)
            return None

        client = anthropic.Anthropic(api_key=key)

        message = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.3,
            system="You are an expert at creating AI coding agent rules. You create specific, example-driven rules that follow best practices for Cursor and Claude Code.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return message.content[0].text.strip()

    except ImportError:
        print("Error: anthropic package not installed. Install with: pip install anthropic", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Anthropic API call failed: {e}", file=sys.stderr)
        return None


def call_ai_api(
    prompt: str,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> Optional[str]:
    """
    Call AI API to generate rules. Max 20 lines.
    Supports OpenAI and Anthropic providers.
    """
    if provider == "openai":
        return call_openai_api(prompt, model, api_key=openai_key)
    elif provider == "anthropic":
        return call_anthropic_api(prompt, model, api_key=anthropic_key)
    elif provider == "none":
        return None
    else:
        print(f"Error: Unknown AI provider: {provider}", file=sys.stderr)
        return None


def generate_ai_rules(
    general_guidelines: str,
    project_context: str,
    language: Optional[str],
    frameworks: List[str],
    base_path: Path,
    rule_type: str,
    format_mdc: bool = False,
    use_ai: bool = True,
    all_languages: Optional[List[str]] = None,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
) -> Optional[str]:
    """
    Generate AI-powered custom rules. Max 40 lines.

    Args:
        general_guidelines: Content from ai_general_guidelines.md
        project_context: Project-specific context string
        language: Primary language (None for monorepo root)
        frameworks: List of frameworks
        base_path: Base path to awesome-cursorrules
        rule_type: 'monorepo_root', 'folder', or 'single_project'
        format_mdc: Whether to generate MDC format
        use_ai: Whether to use AI (if False, falls back to template)
        all_languages: List of all languages in monorepo (for monorepo root)
        ai_provider: AI provider to use (openai, anthropic, none)
        ai_model: AI model to use
        openai_key: Optional OpenAI API key
        anthropic_key: Optional Anthropic API key

    Returns:
        Generated rules content or None for fallback
    """
    is_monorepo_root = (rule_type == 'monorepo_root')

    # Get relevant rule files
    search_config = RuleSearchConfig(
        language=language,
        frameworks=frameworks,
        base_path=base_path,
        is_monorepo_root=is_monorepo_root,
        all_languages=all_languages
    )
    relevant_rules = get_relevant_rule_files(search_config)

    # Build prompt
    prompt_config = PromptConfig(
        general_guidelines=general_guidelines,
        project_context=project_context,
        relevant_rules=relevant_rules,
        rule_type=rule_type,
        format_mdc=format_mdc
    )
    prompt = build_ai_prompt(prompt_config)

    # Call AI if enabled
    if use_ai:
        ai_content = call_ai_api(
            prompt,
            provider=ai_provider,
            model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key
        )
        if ai_content:
            return ai_content

    # Fallback to template-based generation (return None to signal fallback needed)
    return None
