"""
Technology detection and monorepo package discovery.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .config import MONOREPO_PACKAGE_DIRS


def detect_python(folder_path: Path) -> Optional[str]:
    """Detect Python project. Max 10 lines."""
    python_indicators = ["requirements.txt", "pyproject.toml", "setup.py",
                         "Pipfile", "poetry.lock"]

    for indicator in python_indicators:
        if (folder_path / indicator).exists():
            return "python"

    return None


def detect_javascript_typescript(folder_path: Path) -> Optional[str]:
    """Detect JavaScript/TypeScript project. Max 20 lines."""
    package_json = folder_path / "package.json"
    if not package_json.exists():
        return None

    try:
        with open(package_json, 'r', encoding='utf-8') as f:
            pkg_data = json.load(f)
            deps = {**pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {})}

        # Check for TypeScript
        has_tsconfig = (folder_path / "tsconfig.json").exists()
        has_typescript = "typescript" in deps

        return "typescript" if (has_tsconfig or has_typescript) else "javascript"

    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Could not parse {package_json}: {e}", file=sys.stderr)
        return "javascript"  # Fallback to JavaScript


def detect_rust(folder_path: Path) -> Optional[str]:
    """Detect Rust project. Max 5 lines."""
    return "rust" if (folder_path / "Cargo.toml").exists() else None


def detect_go(folder_path: Path) -> Optional[str]:
    """Detect Go project. Max 5 lines."""
    return "go" if (folder_path / "go.mod").exists() else None


def detect_java(folder_path: Path) -> Optional[str]:
    """Detect Java project. Max 12 lines."""
    java_indicators = ["pom.xml", "build.gradle", "build.gradle.kts"]

    for indicator in java_indicators:
        if (folder_path / indicator).exists():
            return "java"

    return None


def detect_cpp(folder_path: Path) -> Optional[str]:
    """Detect C++ project. Max 10 lines."""
    cpp_indicators = ["CMakeLists.txt", "Makefile"]

    for indicator in cpp_indicators:
        if (folder_path / indicator).exists():
            return "cpp"

    return None


def scan_file_for_frameworks(
    file_path: Path,
    framework_keywords: List[str]
) -> List[str]:
    """Scan file content for framework keywords. Max 15 lines."""
    try:
        content = file_path.read_text(encoding='utf-8').lower()
        return [fw for fw in framework_keywords if fw in content]
    except OSError as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []


def detect_python_frameworks(folder_path: Path) -> List[str]:
    """Detect Python frameworks. Max 25 lines."""
    frameworks = []
    framework_keywords = ["fastapi", "django", "flask"]

    # Check requirements.txt
    requirements = folder_path / "requirements.txt"
    if requirements.exists():
        frameworks.extend(scan_file_for_frameworks(
            requirements, framework_keywords
        ))

    # Check pyproject.toml
    pyproject = folder_path / "pyproject.toml"
    if pyproject.exists():
        frameworks.extend(scan_file_for_frameworks(
            pyproject, framework_keywords
        ))

    return list(set(frameworks))  # Remove duplicates


def detect_js_frameworks(folder_path: Path) -> List[str]:
    """Detect JavaScript/TypeScript frameworks. Max 30 lines."""
    package_json = folder_path / "package.json"
    if not package_json.exists():
        return []

    try:
        with open(package_json, 'r', encoding='utf-8') as f:
            pkg_data = json.load(f)
            deps = {**pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {})}

        framework_map = {
            "next": "nextjs",
            "react": "react",
            "vue": "vue",
            "svelte": "svelte",
            "sveltekit": "svelte",
            "tailwindcss": "tailwind",
            "express": "node-express"
        }

        detected = []
        for dep, fw in framework_map.items():
            if dep in deps and fw not in detected:
                detected.append(fw)

        return detected

    except (json.JSONDecodeError, OSError):
        return []


def detect_frameworks(folder_path: Path, language: Optional[str]) -> List[str]:
    """Detect frameworks for language. Max 15 lines."""
    if language == "python":
        return detect_python_frameworks(folder_path)
    elif language in ["typescript", "javascript"]:
        return detect_js_frameworks(folder_path)
    else:
        return []


def detect_folder_technology(folder_path: Path) -> Tuple[Optional[str], List[str]]:
    """Detect technology stack of a folder. Max 25 lines."""
    if not folder_path.exists() or not folder_path.is_dir():
        return None, []

    # Check languages in priority order
    language = (
        detect_python(folder_path) or
        detect_javascript_typescript(folder_path) or
        detect_rust(folder_path) or
        detect_go(folder_path) or
        detect_java(folder_path) or
        detect_cpp(folder_path)
    )

    # Detect frameworks for the language
    frameworks = detect_frameworks(folder_path, language) if language else []

    return language, frameworks


def discover_monorepo_packages(root_path: Path) -> List[Tuple[Path, str, List[str]]]:
    """
    Discover packages/subfolders in a monorepo. Max 40 lines.
    Returns list of (folder_path, language, frameworks) tuples.
    """
    packages = []

    # Common patterns: packages/, apps/, services/, libs/, modules/
    for package_dir_name in MONOREPO_PACKAGE_DIRS:
        package_dir = root_path / package_dir_name
        if package_dir.exists() and package_dir.is_dir():
            for item in package_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    language, frameworks = detect_folder_technology(item)
                    if language:  # Only include if we detected a technology
                        packages.append((item, language, frameworks))

    # Also check for direct subfolders (if not using standard structure)
    # Skip common non-package directories
    skip_dirs = {
        ".git", ".cursor", "node_modules", ".venv", "venv", "env",
        "__pycache__", "dist", "build", ".next", ".nuxt",
        ".svelte-kit", "target", "bin", "obj"
    }

    # Only check direct children if no standard package dirs were found
    if not packages:
        for item in root_path.iterdir():
            if item.is_dir() and item.name not in skip_dirs and not item.name.startswith('.'):
                language, frameworks = detect_folder_technology(item)
                if language:
                    packages.append((item, language, frameworks))

    return packages
