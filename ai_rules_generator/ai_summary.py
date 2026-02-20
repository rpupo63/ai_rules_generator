"""
AI-powered summary generation for folders and files.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from .ai_generator import call_ai_api
from .models import ProjectConfig
from .scanner import FolderInfo


def generate_ai_folder_summary(
    folder: FolderInfo,
    project_root: Path,
    project_config: ProjectConfig,
    ai_provider: str,
    ai_model: str,
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    google_key: Optional[str] = None,
):
    """
    Generate a folder-level summary and individual file summaries using a
    single, batched AI call.
    """
    if not folder.files:
        return

    # Helper to get file content snippet
    def _get_file_snippet(file_path: Path, max_lines_limit: int) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [f.readline() for _ in range(max_lines_limit)]
                content = "".join(lines)
                if len(lines) == max_lines_limit and f.readline(): # Check if more lines exist
                    content += "\n... (file truncated)\n"
                return content
        except OSError:
            return ""

    file_map = {f.name: f for f in folder.files}
    files_to_process = folder.files[:]
    batch_size = 10  # Process up to 10 files at a time for each AI call
    is_first_batch = True

    for i in range(0, len(files_to_process), batch_size):
        batch = files_to_process[i:i + batch_size]
        
        # Construct the file content section of the prompt
        file_contents_prompt = []
        for file_info in batch:
            file_path = project_root / folder.path / file_info.name
            max_lines_for_file = 50 if file_info.size_lines > 75 else 75 # Adjust based on original size
            content = _get_file_snippet(file_path, max_lines_for_file)
            
            if not content.strip():
                continue

            file_contents_prompt.append(f"### File: {file_info.name} (Role: {file_info.role}, Lines: {file_info.size_lines})")
            file_contents_prompt.append(f"```{{{Path(file_info.name).suffix.lstrip('.')}}}")
            file_contents_prompt.append(content)
            file_contents_prompt.append("```")

        if not file_contents_prompt:
            continue

        project_languages = list(project_config.language_stacks.keys()) if project_config.is_monorepo and project_config.language_stacks else [project_config.primary_language]
        language_info = f"Project Languages: {', '.join(project_languages)}"
        frameworks_info = f"Frameworks: {', '.join(project_config.frameworks)}" if project_config.frameworks else ""

        # Construct the main prompt
        prompt = [
            f"**Folder Context:**",
            f"- Path: `{folder.path}/`",
            f"- Purpose: {folder.purpose}",
            f"- {language_info}",
            f"- {frameworks_info}" if frameworks_info else "",
            f"- Child Subfolders: {', '.join([f'`{s.name}/`' for s in folder.children[:5]]) or '(none)'}",
            f"\n**Task:**",
        ]

        if is_first_batch:
            prompt.extend([
                "1. Write a concise **folder summary** (4-6 sentences) explaining the folder's overall role, how its files collaborate, and its importance to the project.",
                "2. For each file below, provide a **technical summary** (3-5 sentences) detailing its specific responsibility, key functions/classes, and its relationship with other files in this folder.",
                "\n**Output Format:**",
                "Your response MUST strictly follow this Markdown structure:",
                "## Overview",
                "Your summary of the folder's purpose and how the files work together. (4-6 sentences)",
                "",
                "## File: <filename>",
                "(Your file summary here)",
                "",
                "## File: <another_filename>",
                "(Your file summary here)",
            ])
        else:
            prompt.extend([
                "1. For each file below, provide a **technical summary** (3-5 sentences) detailing its specific responsibility, key functions/classes, and its relationship with other files in this folder.",
                "\n**Output Format:**",
                "Your response MUST strictly follow this Markdown structure:",
                "## File: <filename>",
                "(Your file summary here)",
                "",
                "## File: <another_filename>",
                "(Your file summary here)",
            ])

        prompt.append("\n**File Contents:**\n" + "\n".join(file_contents_prompt))

        # Make the single batched API call
        raw_summary = call_ai_api(
            prompt="\n".join(prompt),
            provider=ai_provider,
            model=ai_model,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            google_key=google_key,
            system_prompt="You are an expert at analyzing codebases and explaining how files work together within a folder. Your descriptions should be specific, technical, and actionable for an AI coding assistant.",
        )

        if not raw_summary:
            return
        
        # Parse the response
        if is_first_batch:
            # First, try to match with "## Overview"
            summary_match = re.search(r'## Overview\s*(.*?)(?=\n## File:|\Z)', raw_summary, re.DOTALL)
            if summary_match:
                folder.ai_folder_summary = summary_match.group(1).strip()
            else:
                # If "## Overview" is not present, try matching "## Folder Summary"
                summary_match = re.search(r'## Folder Summary\s*(.*?)(?=\n## File:|\Z)', raw_summary, re.DOTALL)
                if summary_match:
                    folder.ai_folder_summary = summary_match.group(1).strip()
                else:
                    # If neither is present, assume the first block is the summary
                    no_header_summary_match = re.search(r'(.*?)(?=\n## File:|\Z)', raw_summary, re.DOTALL)
                    if no_header_summary_match:
                        folder.ai_folder_summary = no_header_summary_match.group(1).strip()
        
        file_desc_matches = re.finditer(r'## File:\s*(.+?)\s*\n(.*?)(?=\n## File:|\Z)', raw_summary, re.DOTALL)
        for match in file_desc_matches:
            file_name = match.group(1).strip()
            description = match.group(2).strip()
            if file_name in file_map:
                file_map[file_name].description = description
        
        is_first_batch = False