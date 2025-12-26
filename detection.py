"""
Technology detection and monorepo package discovery.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from config import TECHNOLOGY_INDICATORS, MONOREPO_PACKAGE_DIRS


def detect_folder_technology(folder_path: Path) -> Tuple[Optional[str], List[str]]:
    """
    Detect the technology stack of a folder by examining files.
    Returns (language, frameworks) tuple.
    """
    if not folder_path.exists() or not folder_path.is_dir():
        return None, []
    
    # Check for technology indicators
    detected_language = None
    detected_frameworks = []
    
    # Check Python
    for indicator in TECHNOLOGY_INDICATORS["python"]:
        if (folder_path / indicator).exists():
            detected_language = "python"
            break
    
    # Check JavaScript/TypeScript
    package_json = folder_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                # Check for TypeScript
                if (folder_path / "tsconfig.json").exists() or "typescript" in deps:
                    detected_language = "typescript"
                else:
                    detected_language = "javascript"
                
                # Detect frameworks
                if "next" in deps:
                    detected_frameworks.append("nextjs")
                if "react" in deps:
                    detected_frameworks.append("react")
                if "vue" in deps:
                    detected_frameworks.append("vue")
                if "svelte" in deps or "sveltekit" in deps:
                    detected_frameworks.append("svelte")
                if "tailwindcss" in deps:
                    detected_frameworks.append("tailwind")
                if "express" in deps:
                    detected_frameworks.append("node-express")
        except (json.JSONDecodeError, Exception):
            pass
    
    # Check Rust
    if (folder_path / "Cargo.toml").exists():
        detected_language = "rust"
    
    # Check Go
    if (folder_path / "go.mod").exists():
        detected_language = "go"
    
    # Check Java
    for indicator in TECHNOLOGY_INDICATORS["java"]:
        if (folder_path / indicator).exists():
            detected_language = "java"
            break
    
    # Check Python frameworks
    if detected_language == "python":
        requirements_file = folder_path / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text(encoding='utf-8').lower()
                if "fastapi" in content:
                    detected_frameworks.append("fastapi")
                if "django" in content:
                    detected_frameworks.append("django")
                if "flask" in content:
                    detected_frameworks.append("flask")
            except Exception:
                pass
        # Also check pyproject.toml
        pyproject = folder_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding='utf-8').lower()
                if "fastapi" in content:
                    detected_frameworks.append("fastapi")
                if "django" in content:
                    detected_frameworks.append("django")
                if "flask" in content:
                    detected_frameworks.append("flask")
            except Exception:
                pass
    
    return detected_language, list(set(detected_frameworks))  # Remove duplicates


def discover_monorepo_packages(root_path: Path) -> List[Tuple[Path, str, List[str]]]:
    """
    Discover packages/subfolders in a monorepo.
    Returns list of (folder_path, language, frameworks) tuples.
    """
    packages = []
    
    # Common patterns: packages/, apps/, services/, libs/
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
    skip_dirs = {".git", ".cursor", "node_modules", ".venv", "venv", "env", "__pycache__", 
                 "dist", "build", ".next", ".nuxt", ".svelte-kit", "target", "bin", "obj"}
    
    # Only check direct children if no standard package dirs were found
    if not packages:
        for item in root_path.iterdir():
            if item.is_dir() and item.name not in skip_dirs and not item.name.startswith('.'):
                language, frameworks = detect_folder_technology(item)
                if language:
                    packages.append((item, language, frameworks))
    
    return packages

