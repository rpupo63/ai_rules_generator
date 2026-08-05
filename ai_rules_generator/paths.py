"""
Path resolution helpers for AI Rules Generator.
"""

from pathlib import Path
from typing import Tuple


def validate_and_resolve_paths(args) -> Tuple[Path, Path]:
    """Validate arguments and resolve paths.

    Returns (package_dir, project_root).
    """
    package_dir = Path(__file__).resolve().parent

    if getattr(args, "project_root", None):
        project_root = Path(args.project_root).resolve()
        if not project_root.exists():
            raise ValueError(f"Project root directory does not exist: {project_root}")
    else:
        project_root = Path.cwd()

    return package_dir, project_root
