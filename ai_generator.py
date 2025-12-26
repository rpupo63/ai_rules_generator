"""
AI-powered rule generation using LLM APIs.
Generates custom rules based on general guidelines and project context.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from file_utils import read_general_guidelines, read_rule_file, extract_rule_content
from config import LANGUAGE_FRAMEWORK_MAP


def get_relevant_rule_files(language: Optional[str], frameworks: List[str], 
                           base_path: Path, is_monorepo_root: bool = False,
                           all_languages: List[str] = None) -> List[Tuple[str, str]]:
    """
    Get list of relevant rule files from awesome-cursorrules.
    Returns list of (rule_name, rule_content) tuples.
    
    For monorepo root, returns universal rules + language rules for all languages in monorepo.
    For specific folders, returns language and framework-specific rules.
    
    Args:
        language: Primary language (None for monorepo root)
        frameworks: List of frameworks
        base_path: Base path to awesome-cursorrules
        is_monorepo_root: Whether this is for monorepo root
        all_languages: List of all languages in monorepo (for monorepo root)
    """
    relevant_rules = []
    
    if is_monorepo_root:
        # For monorepo root, include universal rules
        universal_rules = ["codequality", "clean-code", "gitflow"]
        for rule_name in universal_rules:
            rule_content = read_rule_file(base_path, rule_name)
            if rule_content:
                relevant_rules.append((rule_name, rule_content))
        
        # If multiple languages in monorepo, include language-specific rules for each
        if all_languages:
            seen_languages = set()
            for lang in all_languages:
                lang_key = lang.lower()
                if lang_key == "js":
                    lang_key = "javascript"
                elif lang_key == "ts":
                    lang_key = "typescript"
                
                # Avoid duplicates
                if lang_key in seen_languages:
                    continue
                seen_languages.add(lang_key)
                
                language_info = LANGUAGE_FRAMEWORK_MAP.get(lang_key, {})
                if language_info.get("rule_file"):
                    rule_name = language_info["rule_file"].replace(".mdc", "")
                    rule_content = read_rule_file(base_path, rule_name)
                    if rule_content:
                        relevant_rules.append((rule_name, rule_content))
        
        return relevant_rules
    
    # For specific folders, include language and framework rules
    if language:
        language_key = language.lower()
        if language_key == "js":
            language_key = "javascript"
        elif language_key == "ts":
            language_key = "typescript"
        
        language_info = LANGUAGE_FRAMEWORK_MAP.get(language_key, {})
        
        # Add language-specific rule
        if language_info.get("rule_file"):
            rule_name = language_info["rule_file"].replace(".mdc", "")
            rule_content = read_rule_file(base_path, rule_name)
            if rule_content:
                relevant_rules.append((rule_name, rule_content))
        
        # Add additional universal rules for the language
        if language_info.get("additional"):
            for additional_rule in language_info["additional"]:
                rule_content = read_rule_file(base_path, additional_rule)
                if rule_content and (additional_rule, rule_content) not in relevant_rules:
                    relevant_rules.append((additional_rule, rule_content))
    
    # Add framework-specific rules
    for framework in frameworks[:3]:  # Limit to 3 frameworks
        rule_content = read_rule_file(base_path, framework.lower())
        if rule_content:
            relevant_rules.append((framework.lower(), rule_content))
    
    return relevant_rules


def build_ai_prompt(general_guidelines: str, project_context: str, 
                   relevant_rules: List[Tuple[str, str]], 
                   rule_type: str, format_mdc: bool = False) -> str:
    """
    Build the prompt for AI generation.
    rule_type: 'monorepo_root', 'folder', or 'single_project'
    """
    prompt = f"""You are an expert at creating AI coding agent rules for Cursor and Claude Code. Based on the following guidelines and context, generate a comprehensive, example-driven rules document.

## General Guidelines for Effective Rules

{general_guidelines}

## Project Context

{project_context}

## Relevant Reference Rules from awesome-cursorrules

The following rules from the awesome-cursorrules repository (https://github.com/awesome-cursorrules/awesome-cursorrules) are relevant for this context. These are community-vetted best practices for the specific language/framework combination.

**IMPORTANT:** Use these as reference and incorporate their best practices, but create a CUSTOM, PROJECT-SPECIFIC version that:
- Follows the general guidelines above
- Is tailored to the specific project context
- Includes project-specific examples and patterns
- References these files when appropriate (e.g., "Following patterns from awesome-cursorrules/python.mdc...")

"""
    
    if relevant_rules:
        for rule_name, rule_content in relevant_rules:
            extracted = extract_rule_content(rule_content)
            # Truncate long rules to keep prompt manageable
            lines = extracted.split('\n')
            if len(lines) > 100:
                extracted = '\n'.join(lines[:100]) + "\n[... truncated ...]"
            prompt += f"### Reference: awesome-cursorrules/rules-new/{rule_name}.mdc\n{extracted}\n\n"
    else:
        prompt += "(No specific language/framework rules found - generate general best practices)\n\n"
    
    prompt += f"""
## Task

Generate a custom rules document for this {rule_type} that:

1. **Follows the general guidelines** - Use specific, example-driven rules with ❌→✅ format
2. **References the relevant rules above** - Incorporate best practices from the reference rules, but make them project-specific
3. **Is concise and actionable** - Maximum 500 lines, prefer 200-300 lines
4. **Includes concrete examples** - Show anti-patterns and correct patterns with actual code
5. **Uses absolute language** - ALWAYS, NEVER, MUST for critical rules
6. **Is context-appropriate** - Tailored to the specific project context provided

"""
    
    if format_mdc:
        prompt += """## Format Requirements

Generate the content in Cursor MDC format with YAML frontmatter:
- Include appropriate `description`, `globs`, and `alwaysApply` fields
- The content after the frontmatter should be the actual rules

"""
    else:
        prompt += """## Format Requirements

Generate the content in markdown format suitable for CLAUDE.md or AGENTS.md:
- Start with a clear title
- Use proper markdown formatting
- Include sections for: Project Context, Technology Stack, Coding Standards, Testing, Common Pitfalls, Commands

"""
    
    prompt += """
Generate the rules document now. Focus on being specific, example-driven, and actionable. 

**When referencing awesome-cursorrules files:**
- You can mention them explicitly (e.g., "Following patterns from awesome-cursorrules/python.mdc...")
- Incorporate their best practices into your custom rules
- Make everything project-specific and following the general guidelines
- Don't just copy - synthesize and customize for this specific project context
"""
    
    return prompt


def call_ai_api(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Call AI API to generate rules.
    Supports OpenAI API by default. Can be extended for other providers.
    """
    try:
        import openai
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. Falling back to template-based generation.", file=sys.stderr)
            return None
        
        client = openai.OpenAI(api_key=api_key)
        
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
            temperature=0.3,  # Lower temperature for more consistent, focused output
            max_tokens=4000
        )
        
        return response.choices[0].message.content.strip()
    
    except ImportError:
        print("Warning: openai package not installed. Install with: pip install openai", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: AI API call failed: {e}. Falling back to template-based generation.", file=sys.stderr)
        return None


def generate_ai_rules(general_guidelines: str, project_context: str,
                      language: Optional[str], frameworks: List[str],
                      base_path: Path, rule_type: str, format_mdc: bool = False,
                      use_ai: bool = True, all_languages: List[str] = None) -> str:
    """
    Generate AI-powered custom rules.
    
    Args:
        general_guidelines: Content from ai_general_guidelines.md
        project_context: Project-specific context string
        language: Primary language (None for monorepo root)
        frameworks: List of frameworks
        base_path: Base path to awesome-cursorrules
        rule_type: 'monorepo_root', 'folder', or 'single_project'
        format_mdc: Whether to generate MDC format
        use_ai: Whether to use AI (if False, falls back to template)
    
    Returns:
        Generated rules content
    """
    is_monorepo_root = (rule_type == 'monorepo_root')
    
    # Get relevant rule files
    relevant_rules = get_relevant_rule_files(language, frameworks, base_path, is_monorepo_root, all_languages)
    
    # Build prompt
    prompt = build_ai_prompt(general_guidelines, project_context, relevant_rules, 
                           rule_type, format_mdc)
    
    # Call AI if enabled
    if use_ai:
        ai_content = call_ai_api(prompt)
        if ai_content:
            return ai_content
    
    # Fallback to template-based generation (return None to signal fallback needed)
    return None

