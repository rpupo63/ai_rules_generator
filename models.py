"""
Data models for AI rules generator.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from config import LANGUAGE_FRAMEWORK_MAP


@dataclass
class ProjectConfig:
    """Configuration for the project"""
    description: str
    is_monorepo: bool
    primary_language: str
    frameworks: List[str]
    output_file: str = ".cursorrules"
    project_root: Optional[Path] = None  # Root directory of the project


def get_available_languages() -> List[str]:
    """Get list of available languages (without aliases)"""
    # Return only primary language names, not aliases
    # Includes all languages found in awesome-cursorrules
    primary_languages = [
        "python", "typescript", "javascript", "rust", "cpp", "java", "go",
        "kotlin", "swift", "elixir", "php", "ruby", "scala", "r", "solidity",
        "html", "css"
    ]
    return [lang for lang in primary_languages if lang in LANGUAGE_FRAMEWORK_MAP]


def get_available_frameworks(language: str) -> List[str]:
    """Get list of available frameworks for a language"""
    if language not in LANGUAGE_FRAMEWORK_MAP:
        return []
    return LANGUAGE_FRAMEWORK_MAP[language]["frameworks"]

