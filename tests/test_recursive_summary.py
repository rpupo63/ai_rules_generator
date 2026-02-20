"""
Integration tests for recursive AI summary generation.

Clones a real Go project (faradhaven), runs the Tier 1 (deterministic, no LLM)
pipeline, and validates that the output is a well-structured, AI-followable
project summary.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ai_rules_generator.scanner import scan_project, ScanContext, FolderInfo
from ai_rules_generator.detection import detect_folder_technology
from ai_rules_generator.models import ProjectConfig
from ai_rules_generator.recursive_docs import (
    _folder_path_to_filename,
    generate_folder_docs_tree,
    generate_project_overview,
)

@pytest.fixture(scope="session")
def google_key():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY / GOOGLE_API_KEY not set, skipping AI-dependent tests")
    return key


# ---------------------------------------------------------------------------
# Fixtures (session-scoped: clone once, scan once, generate once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cloned_repo(tmp_path_factory):
    """Clone faradhaven (Go project) into a temp directory."""
    dest = tmp_path_factory.mktemp("faradhaven")
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "git@github.com:rpupo63/faradhaven.git", str(dest)],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        pytest.skip(f"Could not clone repo (network?): {exc}")
    return dest


@pytest.fixture(scope="session")
def scan_result(cloned_repo, project_config) -> ScanContext:
    """Scan the project. Scanning is now purely deterministic (no AI calls)."""
    return scan_project(
        project_root=cloned_repo,
        project_config=project_config,
        max_depth=4,
    )


@pytest.fixture(scope="session")
def detected_tech(cloned_repo):
    """Detect tech in backend/ where go.mod lives."""
    return detect_folder_technology(cloned_repo / "backend")


@pytest.fixture(scope="session")
def project_config(detected_tech) -> ProjectConfig:
    language, frameworks = detected_tech
    return ProjectConfig(
        description="Faradhaven Go Project",
        is_monorepo=False,
        primary_language=language or "go",
        frameworks=frameworks,
    )


@pytest.fixture(scope="session")
def base_path() -> Path:
    """Resolve to the ai_rules_generator package dir (where awesome-cursorrules lives)."""
    return Path(__file__).resolve().parent.parent / "ai_rules_generator"


@pytest.fixture(scope="session")
def generated_output(cloned_repo, project_config, base_path, scan_result, google_key) -> Path:
    """Run the full recursive docs generation and return the .ai-rules/ directory.
    This fixture uses AI for folder summaries.
    Also copies output to tests/faradhaven_eval_output/ for manual inspection."""
    ai_rules_dir = cloned_repo / ".ai-rules"
    ai_rules_dir.mkdir(parents=True, exist_ok=True)

    # Generate project-rules.md
    overview_content = generate_project_overview(
        scan_ctx=scan_result,
        config=project_config,
        base_path=base_path,
        use_ai=True,
        ai_provider="google",
        ai_model="gemini-2.0-flash",
        google_key=google_key,
    )
    (ai_rules_dir / "project-rules.md").write_text(overview_content, encoding="utf-8")

    # Generate per-folder structure docs (with AI folder summaries)
    created_files = generate_folder_docs_tree(
        scan_ctx=scan_result,
        config=project_config,
        project_root=cloned_repo,
        ai_rules_dir=ai_rules_dir,
        base_path=base_path,
        use_ai=True,
        ai_provider="google",
        ai_model="gemini-2.0-flash",
        google_key=google_key,
    )

    # Generate README listing all structure files
    readme_lines = ["# AI Rules\n", "## Structure Files\n"]
    structure_dir = ai_rules_dir / "structure"
    if structure_dir.exists():
        for md_file in sorted(structure_dir.glob("*.md")):
            readme_lines.append(f"- `{md_file.name}`")
    (ai_rules_dir / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")

    # Copy to tests/faradhaven_eval_output/ for manual evaluation
    eval_dir = Path(__file__).resolve().parent / "faradhaven_eval_output"
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    shutil.copytree(ai_rules_dir, eval_dir)
    return ai_rules_dir


# ---------------------------------------------------------------------------
# TestScanContext - Scanner produces valid tree
# ---------------------------------------------------------------------------

class TestScanContext:
    def test_root_exists(self, scan_result):
        root = scan_result.root
        assert root is not None
        assert root.path == ""
        assert root.name == "root"
        assert len(root.children) > 0, "Root should have child folders"

    def test_flat_list_nonempty(self, scan_result):
        assert len(scan_result.flat) >= 2, "Flat list should have at least 2 entries"

    def test_flat_consistent_with_by_path(self, scan_result):
        for folder in scan_result.flat:
            key = folder.path if folder.path else "(root)"
            assert key in scan_result.by_path, f"Flat folder '{key}' missing from by_path"

    def test_by_path_has_root(self, scan_result):
        assert "(root)" in scan_result.by_path

    def test_prompt_text_nonempty(self, scan_result):
        assert scan_result.prompt_text, "prompt_text should not be empty"
        assert "Project File Structure" in scan_result.prompt_text

    def test_folder_info_has_purpose(self, scan_result):
        for folder in scan_result.flat:
            assert folder.purpose, f"Folder '{folder.path}' has no purpose"

    def test_few_generic_purposes(self, scan_result):
        """After enrichment, at most 2 folders should still have the generic 'project files' label."""
        generic = [f for f in scan_result.flat if f.purpose == "project files"]
        assert len(generic) <= 2, (
            f"Expected <= 2 generic 'project files' folders, got {len(generic)}: "
            f"{ [f.path for f in generic]}"
        )

    def test_files_have_roles(self, scan_result):
        for folder in scan_result.flat:
            for f in folder.files:
                assert f.role, f"File '{f.name}' in '{folder.path}' has no role"


# ---------------------------------------------------------------------------
# TestDetection - Auto-detects Go
# ---------------------------------------------------------------------------

class TestDetection:
    def test_detects_go(self, detected_tech):
        language, _ = detected_tech
        assert language == "go", f"Expected 'go', got '{language}'"


# ---------------------------------------------------------------------------
# TestOutputStructure - .ai-rules/ directory layout
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_ai_rules_dir_exists(self, generated_output):
        assert generated_output.is_dir()

    def test_project_rules_exists(self, generated_output):
        assert (generated_output / "project-rules.md").is_file()

    def test_structure_dir_exists(self, generated_output):
        assert (generated_output / "structure").is_dir()

    def test_readme_exists(self, generated_output):
        assert (generated_output / "README.md").is_file()

    @pytest.mark.skip(reason="Snapshot test temporarily skipped")
    def test_scan_snapshot_exists(self, cloned_repo):
        assert (cloned_repo / ".ai-rules" / ".scan-snapshot.json").is_file()


# ---------------------------------------------------------------------------
# TestPerFolderDocs - Per-folder .md files
# ---------------------------------------------------------------------------

class TestPerFolderDocs:
    def test_root_md_exists(self, generated_output):
        assert (generated_output / "structure" / "root.md").is_file()

    def test_backend_md_exists(self, generated_output):
        assert (generated_output / "structure" / "backend.md").is_file()

    def test_at_least_three_structure_files(self, generated_output):
        structure_dir = generated_output / "structure"
        md_files = list(structure_dir.glob("*.md"))
        assert len(md_files) >= 3, f"Expected >= 3 structure files, got {len(md_files)}"

    def test_filenames_use_separator_convention(self, generated_output):
        structure_dir = generated_output / "structure"
        for md_file in structure_dir.glob("*.md"):
            assert "/" not in md_file.name, f"Filename contains '/': {md_file.name}"
            assert "\\" not in md_file.name, f"Filename contains '\\': {md_file.name}"


# ---------------------------------------------------------------------------
# TestProjectRulesContent - project-rules.md quality
# ---------------------------------------------------------------------------

class TestProjectRulesContent:
    @pytest.fixture(scope="class")
    def rules_text(self, generated_output):
        return (generated_output / "project-rules.md").read_text(encoding="utf-8")

    def test_has_heading(self, rules_text):
        assert rules_text.startswith("#"), "project-rules.md should start with a heading"

    def test_has_project_context(self, rules_text):
        assert "Project Context" in rules_text

    def test_has_tech_stack(self, rules_text):
        text_lower = rules_text.lower()
        assert "go" in text_lower, "Should mention Go in tech stack"

    def test_has_folder_tree(self, rules_text):
        assert "Project File Structure" in rules_text

    def test_references_structure_files(self, rules_text):
        assert "structure/" in rules_text

    def test_lists_root_md(self, rules_text):
        assert "root.md" in rules_text

    def test_minimum_content_length(self, rules_text):
        non_empty_lines = [l for l in rules_text.splitlines() if l.strip()]
        assert len(non_empty_lines) >= 15, (
            f"Expected >= 15 non-empty lines, got {len(non_empty_lines)}"
        )


# ---------------------------------------------------------------------------
# TestStructureFileContent - Individual structure file quality (Deterministic)
# ---------------------------------------------------------------------------

class TestStructureFileContent:
    @pytest.fixture(scope="class")
    def structure_files(self, generated_output):
        structure_dir = generated_output / "structure"
        return list(structure_dir.glob("*.md"))

    def test_all_start_with_heading(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            assert content.startswith("#"), f"{f.name} should start with a '#' heading"

    def test_all_have_purpose(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            assert "**Purpose:**" in content, f"{f.name} missing **Purpose:**"

    def test_all_have_path(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            assert "**Path:**" in content, f"{f.name} missing **Path:**"

    def test_all_have_stats(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            assert "## Stats" in content, f"{f.name} missing ## Stats section"

    def test_lists_folders_or_files(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            has_subfolders = "## Subfolders" in content
            has_files = "## Files" in content
            assert has_subfolders or has_files, (
                f"{f.name} has neither Subfolders nor Files section"
            )

    def test_no_trivially_small_files(self, structure_files):
        for f in structure_files:
            content = f.read_text(encoding="utf-8")
            assert len(content) >= 50, (
                f"{f.name} is trivially small ({len(content)} chars)"
            )


# ---------------------------------------------------------------------------
# TestAIFolderSummary - Validate the AI-generated folder/file summaries
# ---------------------------------------------------------------------------

class TestAIFolderSummary:
    @pytest.fixture(scope="class")
    def backend_api_doc(self, generated_output):
        """Content of the `backend--api.md` file."""
        doc_path = generated_output / "structure" / "backend--api.md"
        assert doc_path.is_file(), "`backend--api.md` not found, AI generation might have failed."
        return doc_path.read_text(encoding="utf-8")

    def test_folder_summary_exists(self, backend_api_doc):
        """Check for the '## Overview' section in a key folder doc."""
        assert "## Overview" in backend_api_doc, "Missing '## Overview' section, indicating folder summary was not generated."
        # Check that the summary has some content
        overview_section = backend_api_doc.split("## Overview")[1]
        assert len(overview_section.strip().split("##")[0].strip()) > 50, "Folder overview summary seems too short."

    def test_file_descriptions_exist(self, backend_api_doc):
        """Check that file sections have AI-generated descriptions."""
        # Check for multiple file headings
        assert backend_api_doc.count("### `") > 2, "Expected multiple file subsections."

        # Check that a specific, known file has a description
        auth_handler_section = re.search(r'### `auth_handler\.go`\s*\n(.*?)(?=\n###|\Z)', backend_api_doc, re.DOTALL)
        assert auth_handler_section, "`auth_handler.go` section not found."

        # Check that the section has a description beyond just the role line
        description_part = auth_handler_section.group(1).strip()
        lines = [line.strip() for line in description_part.splitlines() if line.strip()]
        # Expecting at least: Role line + description + exports
        assert len(lines) >= 2, "File description for `auth_handler.go` is missing or empty."
        # The second non-empty line should be a substantial AI-generated description
        # (not just a short metadata line like "**Key Exports:**")
        desc_lines = [l for l in lines[1:] if not l.startswith("**Key Exports") and not l.startswith("- `")]
        assert any(len(l) > 50 for l in desc_lines), (
            f"No substantial AI description found for `auth_handler.go`. Lines: {desc_lines[:3]}"
        )


# ---------------------------------------------------------------------------
# TestAIFollowability - Usable by AI assistants
# ---------------------------------------------------------------------------

class TestAIFollowability:
    def test_file_listings_include_roles(self, scan_result):
        """At least some files should have inferred roles beyond 'source file'."""
        roles = set()
        for folder in scan_result.flat:
            for f in folder.files:
                roles.add(f.role)
        non_generic = roles - {"source file"}
        assert len(non_generic) >= 1, "Expected at least one non-generic file role"

    def test_prompt_text_mentions_backend(self, scan_result):
        assert "backend" in scan_result.prompt_text.lower(), (
            "Prompt text should mention known folder 'backend'"
        )

    def test_readme_lists_structure_files(self, generated_output):
        readme = (generated_output / "README.md").read_text(encoding="utf-8")
        structure_dir = generated_output / "structure"
        md_files = list(structure_dir.glob("*.md"))
        for md_file in md_files:
            assert md_file.name in readme, (
                f"README should list structure file '{md_file.name}'"
            )


# ---------------------------------------------------------------------------
# TestFolderPathToFilename - Unit test (no clone needed)
# ---------------------------------------------------------------------------

class TestFolderPathToFilename:
    def test_empty_path_is_root(self):
        assert _folder_path_to_filename("") == "root.md"

    def test_simple_folder(self):
        assert _folder_path_to_filename("src") == "src.md"

    def test_nested_folder(self):
        assert _folder_path_to_filename("src/components") == "src--components.md"

    def test_deeply_nested(self):
        assert _folder_path_to_filename("a/b/c") == "a--b--c.md"

    def test_backslash_normalized(self):
        assert _folder_path_to_filename("src\\utils") == "src--utils.md"