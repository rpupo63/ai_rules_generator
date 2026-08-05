"""
Lightweight project file listing for structure-only graphing.

The old content-ingestion scanner is gone; this module only discovers paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .exclusions import get_exclusion_context, should_skip_dir, should_skip_file
from .tags import language_for_path, list_source_files


@dataclass
class FolderInfo:
    rel_path: str
    files: List[Path] = field(default_factory=list)
    language: str = ""


@dataclass
class ScanContext:
    project_root: Path
    files: List[Path]
    folders: Dict[str, FolderInfo]


def scan_project(project_root: Path) -> ScanContext:
    """List source files under project_root, honoring exclusions."""
    root = project_root.resolve()
    excl = get_exclusion_context(root)
    gitignore = excl["gitignore_patterns"]

    candidates = list_source_files(root)
    files: List[Path] = []
    folders: Dict[str, FolderInfo] = {}

    for path in candidates:
        try:
            rel = str(path.resolve().relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
        # Skip excluded path segments
        parts = Path(rel).parts
        skip = False
        for i in range(len(parts) - 1):
            d = root.joinpath(*parts[: i + 1])
            if should_skip_dir(d, root, gitignore):
                skip = True
                break
        if skip:
            continue
        if should_skip_file(path, root, gitignore):
            continue
        if language_for_path(path) is None:
            continue
        files.append(path)
        folder_rel = str(Path(rel).parent).replace("\\", "/")
        if folder_rel == ".":
            folder_rel = ""
        info = folders.setdefault(folder_rel, FolderInfo(rel_path=folder_rel))
        info.files.append(path)
        if not info.language:
            lang = language_for_path(path)
            if lang:
                info.language = lang

    return ScanContext(project_root=root, files=files, folders=folders)
