"""
Path resolution and project configuration helpers for AI Rules Generator.
"""

from pathlib import Path
from typing import Tuple

from .models import ProjectConfig
from .cli import interactive_config
from .config_manager import get_provider_display_name


def validate_and_resolve_paths(args) -> Tuple[Path, Path]:
    """Validate arguments and resolve paths."""
    package_dir = Path(__file__).resolve().parent
    base_path = package_dir
    awesome_cursorrules_path = package_dir / "awesome-cursorrules"

    if not awesome_cursorrules_path.exists():
        parent_path = package_dir.parent
        if (parent_path / "awesome-cursorrules").exists():
            base_path = parent_path
        elif (Path.cwd() / "awesome-cursorrules").exists():
            base_path = Path.cwd()

    if args.project_root:
        project_root = Path(args.project_root).resolve()
        if not project_root.exists():
            raise ValueError(f"Project root directory does not exist: {project_root}")
    else:
        project_root = Path.cwd()

    return base_path, project_root


def get_project_config(args, project_root: Path) -> ProjectConfig:
    """Get configuration from args or interactive mode."""
    if args.interactive or (not args.description and not args.language):
        config = interactive_config()
        config.project_root = project_root
        return config

    if not args.description:
        raise ValueError("--description is required in non-interactive mode")
    if not args.language:
        raise ValueError("--language is required in non-interactive mode")

    return ProjectConfig(
        description=args.description,
        is_monorepo=args.monorepo,
        primary_language=args.language.lower(),
        frameworks=args.frameworks,
        output_file=args.output,
        project_root=project_root
    )


def print_generation_info(
    config: ProjectConfig,
    project_root: Path,
    use_ai: bool,
    ai_provider: str,
    ai_model: str
) -> None:
    """Print generation configuration info."""
    print(f"\nGenerating AI rules document...")
    print(f"  Project root: {project_root}")
    print(f"  Language: {config.primary_language}")
    print(f"  Frameworks: {', '.join(config.frameworks) if config.frameworks else 'None'}")
    print(f"  Monorepo: {config.is_monorepo}")
    if use_ai:
        print(f"  AI Provider: {get_provider_display_name(ai_provider)}")
        print(f"  AI Model: {ai_model}")
    else:
        print(f"  AI generation: Disabled (using template-based generation)")
    print()
