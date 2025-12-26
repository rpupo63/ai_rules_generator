"""
File reading and content extraction utilities.
"""

import sys
from pathlib import Path
from typing import Optional


def read_rule_file(base_path: Path, rule_name: str) -> Optional[str]:
    """
    Read a rule file from awesome-cursorrules/rules-new directory.
    Handles both .mdc files and falls back to rules directory if needed.
    """
    # First try rules-new directory
    rule_file_new = base_path / "awesome-cursorrules" / "rules-new" / f"{rule_name}.mdc"
    if rule_file_new.exists():
        try:
            return rule_file_new.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not read {rule_file_new}: {e}", file=sys.stderr)
            return None
    
    # If not found, try to find in rules directory
    rules_dir = base_path / "awesome-cursorrules" / "rules"
    if rules_dir.exists():
        # Search for matching directory
        pattern = f"*{rule_name}*"
        matches = list(rules_dir.glob(pattern))
        if matches:
            cursorrules_file = matches[0] / ".cursorrules"
            if cursorrules_file.exists():
                try:
                    return cursorrules_file.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"Warning: Could not read {cursorrules_file}: {e}", file=sys.stderr)
    
    return None


def read_general_guidelines(base_path: Path) -> str:
    """Read the general guidelines file"""
    guidelines_file = base_path / "ai_general_guidelines.md"
    if guidelines_file.exists():
        return guidelines_file.read_text(encoding='utf-8')
    return ""


def extract_rule_content(rule_text: str) -> str:
    """
    Extract the actual rule content from MDC files (skip YAML frontmatter)
    """
    if not rule_text:
        return ""
    
    # If it starts with YAML frontmatter, extract content after ---
    lines = rule_text.split('\n')
    if lines and lines[0].strip() == '---':
        # Find the second ---
        content_start = 1
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == '---':
                content_start = i + 1
                break
        content = '\n'.join(lines[content_start:]).strip()
    else:
        content = rule_text.strip()
    
    # Remove the first header line if it exists (to avoid duplication when we add our own header)
    content_lines = content.split('\n')
    if content_lines and content_lines[0].strip().startswith('#'):
        # Skip the first header line
        content = '\n'.join(content_lines[1:]).strip()
    
    return content

