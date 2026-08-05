"""
AI-powered rule generation using LLM APIs.
Generates custom rules based on general guidelines and project context.

Uses ai_model_picker for unified AI provider access, supporting:
OpenAI, Anthropic, Google, Mistral, Cohere, DeepSeek, xAI, Meta, Alibaba.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .file_utils import read_general_guidelines, read_rule_file, extract_rule_content
from .config import LANGUAGE_FRAMEWORK_MAP
from .prompt_xml import build_xml_prompt
from .stop_rules import render_stop_rules_block

# Import unified AI client from ai_model_picker
from ai_model_picker import (
    call_ai_simple,
    call_with_preference,
    build_preference,
    get_model_api_id,
    get_api_key_with_fallback,
    load_preference,
)

# App name for config lookup
APP_NAME = "ai-rules-generator"


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
    """Body of the <role> XML tag. No ## Markdown header."""
    return (
        "You are an expert context engineer producing AI coding agent rules "
        "for Cursor, Claude Code, Windsurf, GitHub Copilot, Warp, and Janie. "
        "You write specific, example-driven instructions and you follow the "
        "structural requirements declared in <output_format> exactly."
    )


def build_guidelines_section(general_guidelines: str) -> str:
    """Body of the <style_guide> tag - just the raw guidelines content."""
    return general_guidelines


def build_context_section(project_context: str) -> str:
    """Body of the <project_identity> tag."""
    return project_context


def build_reference_rules_section(
    relevant_rules: List[Tuple[str, str]]
) -> str:
    """Body of the <reference_rules> tag."""
    if not relevant_rules:
        return (
            "(No specific language/framework rules found - generate general "
            "best practices grounded in the project identity above.)"
        )

    header = (
        "The following rules from awesome-cursorrules "
        "(https://github.com/awesome-cursorrules/awesome-cursorrules) are "
        "community-vetted best practices for the relevant language/framework "
        "combination.\n\n"
        "IMPORTANT: Use these as reference and incorporate their best "
        "practices, but produce a CUSTOM, PROJECT-SPECIFIC version that:\n"
        "- Follows the style_guide above\n"
        "- Is tailored to the specific project_identity\n"
        "- Includes project-specific examples and patterns\n"
        "- References these files when appropriate "
        "(e.g., \"Following patterns from awesome-cursorrules/python.mdc...\")\n"
    )

    rule_sections = []
    for rule_name, rule_content in relevant_rules:
        extracted = extract_rule_content(rule_content)
        truncated = truncate_rule_content(extracted, max_lines=100)
        rule_sections.append(
            f"<reference name=\"awesome-cursorrules/rules-new/{rule_name}.mdc\">\n"
            f"{truncated}\n"
            f"</reference>"
        )

    return header + "\n\n" + "\n\n".join(rule_sections)


def build_task_section(rule_type: str) -> str:
    """Body of the <task> tag - the imperative ask for this turn."""
    return (
        f"Generate a custom rules document for this {rule_type} that:\n"
        "1. Follows the style_guide - use specific, example-driven rules "
        "with the wrong-then-right format (clearly marked).\n"
        "2. Incorporates the reference_rules above but makes them "
        "project-specific.\n"
        "3. Is concise and actionable - maximum 500 lines, prefer 200-300.\n"
        "4. Includes concrete code examples (anti-pattern then correct pattern).\n"
        "5. Uses absolute language (ALWAYS, NEVER, MUST) for critical rules.\n"
        "6. Is fully tailored to the project_identity, repo_map, and "
        "tech_stack provided.\n"
        "7. Adheres to every constraint in stop_rules - do not soften or "
        "omit any of them."
    )


def build_format_requirements(format_mdc: bool) -> str:
    """Body of the <output_format> tag - strict schema for the response."""
    if format_mdc:
        return (
            "Output Cursor MDC format with YAML frontmatter:\n"
            "- First three lines: `---`, then YAML keys "
            "(`description`, `globs`, `alwaysApply`), then `---`.\n"
            "- Content after the frontmatter is the rules body in Markdown.\n"
            "- Do not wrap the whole response in a code fence.\n"
            "- Do not echo the <task> or <reference_rules> blocks back."
        )
    return (
        "Output Markdown suitable for CLAUDE.md / AGENTS.md:\n"
        "- Start with a clear `# Title` line.\n"
        "- Use the following H2 sections in this order: "
        "Project Context, Technology Stack, Architecture Snapshot, "
        "Dev Commands, Coding Standards, Testing, Stop Rules, "
        "Common Pitfalls.\n"
        "- Do not wrap the whole response in a code fence.\n"
        "- Do not echo the <task> or <reference_rules> blocks back."
    )


def build_prompt_footer() -> str:
    """Kept for backwards-compatible callers; returned as part of <task>."""
    return (
        "When referencing awesome-cursorrules files: mention them explicitly, "
        "incorporate their best practices, but customize for this specific "
        "project. Do not copy verbatim - synthesize."
    )


def build_ai_prompt(config: PromptConfig) -> str:
    """
    Build the AI generation prompt as XML-tagged sections.

    The structure follows `prompt_xml.CANONICAL_SECTION_ORDER` so all callers
    in the codebase (rule generators, summary generators, future agents) speak
    a single, model-friendly vocabulary.
    """
    sections = {
        "role": build_prompt_header(),
        "project_identity": build_context_section(config.project_context),
        "style_guide": build_guidelines_section(config.general_guidelines),
        "reference_rules": build_reference_rules_section(config.relevant_rules),
        "stop_rules": render_stop_rules_block().strip(),
        "task": build_task_section(config.rule_type)
                + "\n\n"
                + build_prompt_footer(),
        "output_format": build_format_requirements(config.format_mdc),
    }
    return build_xml_prompt(sections)


# System prompt for rule generation
RULE_GENERATION_SYSTEM_PROMPT = (
    "You are an expert at creating AI coding agent rules. "
    "You create specific, example-driven rules that follow best practices "
    "for Cursor and Claude Code."
)


def call_ai_api(
    prompt: str,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
    mistral_key: Optional[str] = None,
    cohere_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **extra_keys,
) -> Optional[str]:
    """
    Call AI API to generate rules using unified ai_model_picker client.

    Uses ModelPreference instructions (when set) as an addendum to the
    default rule-generation system prompt. API keys resolve locally via
    explicit args, config, or env — never from the preference handoff.
    """
    if provider == "none":
        return None

    # Map legacy key parameters to provider (plus any ``{provider}_key`` extras)
    key_map = {
        "openai": openai_key,
        "anthropic": anthropic_key,
        "google": google_key,
        "mistral": mistral_key,
        "cohere": cohere_key,
    }
    for key_name, key_value in extra_keys.items():
        if key_name.endswith("_key") and key_value:
            key_map[key_name[: -len("_key")]] = key_value

    api_key = key_map.get(provider)
    if not api_key:
        api_key = get_api_key_with_fallback(provider, APP_NAME)

    pref = load_preference(APP_NAME)
    # Prefer caller provider/model when generating; keep saved instructions
    runtime_pref = build_preference(
        provider=provider,
        model=model,
        instructions=pref.instructions,
        temperature=pref.temperature,
        max_tokens=pref.max_tokens,
        app_name=APP_NAME,
    )

    base_system = system_prompt or RULE_GENERATION_SYSTEM_PROMPT
    if runtime_pref.instructions:
        effective_system = f"{base_system}\n\nAdditional instructions:\n{runtime_pref.instructions}"
    else:
        effective_system = base_system

    result = call_with_preference(
        prompt=prompt,
        preference=runtime_pref,
        app_name=APP_NAME,
        api_key=api_key,
        system_prompt=effective_system,
    )
    if result is None:
        # Fallback for environments without preference wiring
        return call_ai_simple(
            prompt=prompt,
            provider=provider,
            model=model,
            api_key=api_key,
            app_name=APP_NAME,
            system_prompt=effective_system,
        )
    return result.content


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
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
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
        ai_provider: AI provider to use (openai, anthropic, google, none)
        ai_model: AI model to use
        openai_key: Optional OpenAI API key
        anthropic_key: Optional Anthropic API key
        google_key: Optional Google API key

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
            anthropic_key=anthropic_key,
            google_key=google_key,
        )
        if ai_content:
            return ai_content

    # Fallback to template-based generation (return None to signal fallback needed)
    return None
