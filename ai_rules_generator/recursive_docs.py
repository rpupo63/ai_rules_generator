"""
Recursive per-folder documentation generator.
Generates one .md file per significant folder in .ai-rules/structure/.
Combines Tier 1 (deterministic) + optional Tier 2 (LLM insights).
"""

from pathlib import Path
from typing import List, Optional

from .scanner import (
    FolderInfo,
    ScanContext,
    generate_deterministic_folder_doc,
)
from .ai_summary import generate_ai_folder_summary
from .ai_generator import generate_ai_rules
from .file_utils import read_general_guidelines
from .generators import generate_project_context
from .models import ProjectConfig, get_all_languages


def _folder_path_to_filename(rel_path: str) -> str:
    """Convert a relative folder path to a flat filename using -- as separator.
    e.g., 'src/components' -> 'src--components.md', '' -> 'root.md'
    """
    if not rel_path:
        return "root.md"
    return rel_path.replace("/", "--").replace("\\", "--") + ".md"


def _extract_folder_context(scan_ctx: ScanContext, folder: FolderInfo) -> str:
    """Build focused context for a specific folder's Tier 2 generation.

    Instead of passing the entire project tree, provides:
    - Current folder path and purpose
    - Current folder's children (names + purposes)
    - Truncated broader project tree for high-level context
    """
    lines = []

    # Current folder info
    folder_display = folder.path if folder.path else "(root)"
    lines.append(f"## Current Folder: `{folder_display}/`")
    lines.append(f"**Purpose:** {folder.purpose}")
    lines.append("")

    # Children of this folder
    if folder.children:
        lines.append("### Child Folders:")
        for child in folder.children:
            lines.append(f"- **`{child.name}/`** - {child.purpose} ({child.file_count} files)")
        lines.append("")

    # File listing for this folder
    if folder.files:
        lines.append("### Files in this folder:")
        for f in folder.files[:30]:
            lines.append(f"- `{f.name}` ({f.role}, {f.size_lines} lines)")
        lines.append("")

    # Broader project tree (truncated) for context
    if scan_ctx.prompt_text:
        lines.append("### Broader Project Context (summary):")
        lines.append(scan_ctx.prompt_text[:1500])
        lines.append("")

    return "\n".join(lines)


def _is_significant_for_docs(folder: FolderInfo) -> bool:
    """Determine if a folder warrants its own documentation file."""
    return folder.file_count >= 1 or len(folder.subfolders) >= 1


def generate_folder_docs_tree(
    scan_ctx: ScanContext,
    config: ProjectConfig,
    project_root: Path,
    ai_rules_dir: Path,
    base_path: Path,
    use_ai: bool = False,
    ai_provider: str = "none",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
) -> List[Path]:
    """
    Walk the FolderInfo tree and generate per-folder documentation files.

    Each file is written to .ai-rules/structure/<relative-path>.md and
    contains Tier 1 (deterministic) content + optional Tier 2 (LLM insights).

    Returns list of created file paths.
    """
    structure_dir = ai_rules_dir / "structure"
    structure_dir.mkdir(parents=True, exist_ok=True)

    created_files: List[Path] = []

    def _walk_and_generate(folder: FolderInfo) -> None:
        if not _is_significant_for_docs(folder):
            return

        if use_ai and ai_provider != "none":
            generate_ai_folder_summary(
                folder=folder,
                project_root=project_root,
                project_config=config,
                ai_provider=ai_provider,
                ai_model=ai_model,
                openai_key=openai_key,
                anthropic_key=anthropic_key,
                google_key=google_key,
            )

        # Tier 1: deterministic structural content (now includes AI summaries if generated)
        tier1_content = generate_deterministic_folder_doc(folder)
        
        # Combine and write
        full_content = tier1_content # No need to add tier2_content as it's already in tier1
        filename = _folder_path_to_filename(folder.path)
        file_path = structure_dir / filename
        file_path.write_text(full_content, encoding='utf-8')
        created_files.append(file_path)

        # Recurse into children
        for child in folder.children:
            _walk_and_generate(child)

    _walk_and_generate(scan_ctx.root)
    return created_files


def generate_project_overview(
    scan_ctx: ScanContext,
    config: ProjectConfig,
    base_path: Path,
    use_ai: bool = False,
    ai_provider: str = "none",
    ai_model: str = "gpt-4o-mini",
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
) -> str:
    """
    Generate the high-level project-rules.md content.
    Tier 1: project overview + folder tree with purposes.
    Tier 2 (optional): architectural insights from LLM.
    """
    sections: List[str] = []

    sections.append(f"# {config.description}")
    sections.append("")

    # Project context
    sections.append(generate_project_context(config))

    # Folder tree overview (from scanner)
    sections.append(scan_ctx.prompt_text)
    sections.append("")

    # Reference to per-folder docs
    sections.append("## Detailed Structure")
    sections.append("")
    sections.append("Per-folder documentation is available in `.ai-rules/structure/`:")
    sections.append("")
    for folder in scan_ctx.flat:
        filename = _folder_path_to_filename(folder.path)
        folder_display = folder.path if folder.path else "(root)"
        sections.append(f"- [`{filename}`](.ai-rules/structure/{filename}) - {folder_display}/ ({folder.purpose})")
    sections.append("")

    tier1_content = "\n".join(sections)

    # Tier 2: optional LLM insights
    if use_ai and ai_provider != "none":
        general_guidelines = read_general_guidelines(base_path)
        project_context = generate_project_context(config)

        tier2 = generate_ai_rules(
            general_guidelines=general_guidelines,
            project_context=project_context,
            language=config.primary_language,
            frameworks=config.frameworks,
            base_path=base_path,
            rule_type='single_project',
            format_mdc=False,
            use_ai=True,
            ai_provider=ai_provider,
            ai_model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
            all_languages=get_all_languages(config),
        )
        if tier2:
            tier1_content += f"\n---\n\n{tier2}"

    return tier1_content
