"""
Tests for the unlimited-depth scan + budget-aware Tier-2 emission.

The scanner used to cap at depth 4; with the context-engineering refactor
it's bounded only by the global TokenBudget.  These tests build a synthetic
deep tree and assert that every leaf folder gets representation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ai_rules_generator.models import ProjectConfig
from ai_rules_generator.scanner import scan_project
from ai_rules_generator.token_budget import TokenBudget


def _make_deep_tree(root: Path, depth: int) -> Path:
    """Create a chain folder1/folder2/.../folderN each with a .py file."""
    current = root
    for i in range(1, depth + 1):
        current = current / f"folder{i}"
        current.mkdir()
        # Make each folder have one trivial source file so it qualifies as
        # significant (file_count >= 1).
        (current / "mod.py").write_text(
            f"def func_{i}():\n    return {i}\n",
            encoding="utf-8",
        )
    return current


def test_scan_project_sees_every_level_when_unlimited(tmp_path):
    _make_deep_tree(tmp_path, depth=8)
    cfg = ProjectConfig(
        description="Deep",
        is_monorepo=False,
        primary_language="python",
        frameworks=[],
    )
    ctx = scan_project(tmp_path, cfg, extract_signatures=False)

    # Folder names produced by _make_deep_tree.
    expected = {f"folder{i}" for i in range(1, 9)}
    seen = {f.name for f in ctx.flat}
    missing = expected - seen
    assert not missing, (
        f"depth-8 scan should see every folder; missing: {missing}"
    )


def test_scan_project_default_is_effectively_unlimited():
    """Regression guard: the default `max_depth` parameter must be a
    sentinel that allows arbitrarily deep recursion."""
    import inspect

    from ai_rules_generator import scanner

    sig = inspect.signature(scanner.scan_project)
    default = sig.parameters["max_depth"].default
    assert default == sys.maxsize, (
        "scan_project must default to unlimited depth; got "
        f"{default!r}"
    )


def test_emit_tier2_force_emits_header_for_every_folder_even_under_tight_budget(tmp_path):
    """Headers are priority-0 force-spent; they must always be present
    no matter how small the global budget is."""
    pytest.importorskip("tree_sitter")
    try:
        import tree_sitter_language_pack  # noqa: F401
    except ImportError:
        try:
            import tree_sitter_languages  # noqa: F401
        except ImportError:
            pytest.skip("no tree-sitter grammars available")

    _make_deep_tree(tmp_path, depth=5)
    cfg = ProjectConfig(
        description="Deep",
        is_monorepo=False,
        primary_language="python",
        frameworks=[],
    )
    ctx = scan_project(tmp_path, cfg, extract_signatures=True)
    folders_with_skeletons = [f for f in ctx.flat if f.skeletons]
    if not folders_with_skeletons:
        pytest.skip("no skeletons extracted; grammar load failed")

    from ai_rules_generator.orchestration import emit_tier2_folder_files

    # Deliberately tight budget - just enough for headers + maybe one
    # skeleton, but not enough for everything.
    budget = TokenBudget(cap=500)
    written = emit_tier2_folder_files(
        tmp_path, ctx, cfg, budget=budget,
    )

    # One file per folder with a skeleton should exist on disk regardless
    # of how much was shed.
    assert len(written) == len(folders_with_skeletons)
    for p in written:
        body = p.read_text(encoding="utf-8")
        # Header section is always there.
        assert "- Folder:" in body
        assert "- Language:" in body
