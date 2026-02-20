"""
Update command handler for incremental regeneration of AI rules.
Scans for new/changed folders and only regenerates affected files.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import ProjectConfig
from .config_manager import load_user_config, UserConfig, get_available_tools, get_tool_display_name
from .paths import validate_and_resolve_paths
from .scanner import scan_project, FolderInfo, ScanContext
from .generators_shared import create_shared_ai_rules_directory
from .generators_multi_tool import generate_all_tool_rules
from .detection import detect_folder_technology


# Snapshot file storing last scan state
SNAPSHOT_FILE = ".ai-rules/.scan-snapshot.json"


def _load_snapshot(project_root: Path) -> Dict:
    """Load the previous scan snapshot."""
    snapshot_path = project_root / SNAPSHOT_FILE
    if not snapshot_path.exists():
        return {}

    try:
        return json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_snapshot(project_root: Path, folders: List[FolderInfo]) -> None:
    """Save current scan state as snapshot for future diffing."""
    snapshot_path = project_root / SNAPSHOT_FILE
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "timestamp": time.time(),
        "folders": {}
    }

    for folder in folders:
        snapshot["folders"][folder.path or "(root)"] = {
            "name": folder.name,
            "file_count": folder.file_count,
            "subfolders": folder.subfolders,
            "files": [f.name for f in folder.files],
        }

    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def _diff_snapshots(
    old_snapshot: Dict,
    new_folders: List[FolderInfo],
) -> Tuple[List[FolderInfo], List[FolderInfo], List[str]]:
    """
    Compare old snapshot with new scan results.
    Returns: (new_folders, changed_folders, removed_folder_paths)
    """
    old_folders = old_snapshot.get("folders", {})
    old_paths = set(old_folders.keys())

    new_folder_map = {}
    for f in new_folders:
        key = f.path or "(root)"
        new_folder_map[key] = f
    new_paths = set(new_folder_map.keys())

    # New folders
    added_paths = new_paths - old_paths
    added = [new_folder_map[p] for p in added_paths]

    # Removed folders
    removed = list(old_paths - new_paths)

    # Changed folders (different file count or different files)
    changed = []
    for path in new_paths & old_paths:
        old_data = old_folders[path]
        new_data = new_folder_map[path]

        if (
            old_data.get("file_count") != new_data.file_count
            or set(old_data.get("subfolders", [])) != set(new_data.subfolders)
            or set(old_data.get("files", [])) != {f.name for f in new_data.files}
        ):
            changed.append(new_data)

    return added, changed, removed


def cmd_update(args) -> None:
    """Handle the update command - incrementally update AI rules."""
    print("=" * 60)
    print("AI Rules Generator - Incremental Update")
    print("=" * 60)
    print()

    user_config = load_user_config()
    if not user_config:
        user_config = UserConfig()

    ai_provider = user_config.ai_provider
    ai_model = user_config.ai_model
    openai_key = user_config.openai_api_key or os.getenv("OPENAI_API_KEY")
    anthropic_key = user_config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

    base_path, project_root = validate_and_resolve_paths(args)

    ai_rules_dir = project_root / ".ai-rules"
    if not ai_rules_dir.exists():
        print("No .ai-rules/ directory found.")
        print("Run 'ai-rules-generator project-init' first to initialize the project.")
        sys.exit(1)

    use_ai = not getattr(args, "no_ai", False)
    if getattr(args, "no_ai", False):
        ai_provider = "none"
        ai_model = "template"

    # Load previous snapshot
    old_snapshot = _load_snapshot(project_root)

    # Scan current project (once)
    print("Scanning project structure...")
    scan_ctx = scan_project(project_root, max_depth=4)
    print(f"  Found {len(scan_ctx.flat)} significant folders")

    if not old_snapshot:
        print("\n  No previous snapshot found - performing full regeneration.")
        _full_regenerate(
            project_root, base_path, scan_ctx,
            use_ai, ai_provider, ai_model, openai_key, anthropic_key,
            user_config,
        )
        _save_snapshot(project_root, scan_ctx.flat)
        return

    # Diff against snapshot
    added, changed, removed = _diff_snapshots(old_snapshot, scan_ctx.flat)

    if not added and not changed and not removed:
        print("\n  No changes detected since last generation.")
        print("  Use 'project-init' to force a full regeneration.")
        return

    print(f"\nChanges detected:")
    if added:
        print(f"  + {len(added)} new folder(s):")
        for f in added:
            print(f"    + {f.path or '(root)'}/")
    if changed:
        print(f"  ~ {len(changed)} changed folder(s):")
        for f in changed:
            print(f"    ~ {f.path or '(root)'}/")
    if removed:
        print(f"  - {len(removed)} removed folder(s):")
        for p in removed:
            print(f"    - {p}/")

    print("\nRegenerating rules with updated structure...")
    _full_regenerate(
        project_root, base_path, scan_ctx,
        use_ai, ai_provider, ai_model, openai_key, anthropic_key,
        user_config,
    )

    # Save new snapshot
    _save_snapshot(project_root, scan_ctx.flat)

    print()
    print("=" * 60)
    print("Update complete!")
    print("=" * 60)


def _full_regenerate(
    project_root: Path,
    base_path: Path,
    scan_ctx: ScanContext,
    use_ai: bool,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    user_config: UserConfig,
) -> None:
    """Perform a full regeneration of all rules."""
    from .detection import detect_folder_technology
    language, frameworks = detect_folder_technology(project_root)

    if not language:
        language = "python"  # fallback

    config = ProjectConfig(
        description="(auto-detected project)",
        is_monorepo=False,
        primary_language=language,
        frameworks=frameworks,
        project_root=project_root,
    )

    # Try to load description from existing project-rules.md
    project_rules_file = project_root / ".ai-rules" / "project-rules.md"
    if project_rules_file.exists():
        try:
            content = project_rules_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("**Project Description:**"):
                    desc = line.replace("**Project Description:**", "").strip()
                    if desc:
                        config.description = desc
                    break
        except OSError:
            pass

    ai_rules_dir = create_shared_ai_rules_directory(
        project_root, config, base_path, use_ai, ai_provider, ai_model,
        openai_key, anthropic_key, scan_ctx=scan_ctx
    )
    print(f"  Updated {ai_rules_dir}")

    enabled_tools = user_config.enabled_tools if user_config.enabled_tools else ["cursor", "claude-code"]
    generate_all_tool_rules(ai_rules_dir, config, base_path, project_root,
                           enabled_tools, scan_ctx=scan_ctx)
