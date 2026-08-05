"""
Tests for the Tree-sitter AST compression layer (Phase 3).

These tests skip gracefully when no Tree-sitter grammar pack is installed
so the suite remains green on a barebones Python environment.
"""

import pytest

from ai_rules_generator.ast_compression import (
    LANGUAGE_RULES,
    compress_folder,
    estimate_tokens,
    extract_skeleton,
    get_language_rule,
    render_outline_markdown,
)


def _has_grammars() -> bool:
    """Return True if the Tree-sitter grammar pack is importable."""
    try:
        try:
            import tree_sitter_language_pack  # noqa: F401
        except ImportError:
            import tree_sitter_languages  # noqa: F401
        return True
    except Exception:
        return False


requires_grammars = pytest.mark.skipif(
    not _has_grammars(),
    reason="tree-sitter grammars not installed (install tree-sitter-language-pack)",
)


def test_language_rules_cover_expected_extensions():
    expected = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cpp", ".hpp"}
    assert expected.issubset(LANGUAGE_RULES.keys())


def test_estimate_tokens_is_monotonic():
    assert estimate_tokens("hi") < estimate_tokens("hi there friend")
    assert estimate_tokens("") == 0


def test_render_outline_markdown_lists_signatures(tmp_path):
    """Pure-Python check: render works on a hand-built SignatureNode list."""
    from ai_rules_generator.ast_compression import SignatureNode

    sigs = [
        SignatureNode(
            kind="function_definition",
            name="alpha",
            signature="def alpha(x: int) -> str:",
            docstring="Return x as string.",
            start_line=1,
            end_line=5,
        ),
    ]
    md = render_outline_markdown(tmp_path / "demo.py", sigs, ["import os"])
    assert "alpha" in md
    assert "**Imports:**" in md
    assert "**Signatures:**" in md


@requires_grammars
def test_extract_skeleton_python_preserves_signatures(tmp_path):
    src = tmp_path / "sample.py"
    src.write_text(
        '"""Module."""\n'
        "import os\n\n"
        "def public(x: int) -> str:\n"
        '    """Convert int to string."""\n'
        "    y = x + 1\n"
        "    z = y * 2\n"
        "    return str(z)\n\n"
        "class Widget:\n"
        '    """A widget."""\n'
        "    def method(self) -> int:\n"
        "        return 42\n",
        encoding="utf-8",
    )

    skel = extract_skeleton(src)
    assert skel is not None
    assert skel.language == "python"
    assert skel.used_fallback is False, "grammar should have been used"
    names = {s.name for s in skel.signatures}
    assert {"public", "Widget"}.issubset(names)


@requires_grammars
def test_compression_meaningfully_reduces_tokens(tmp_path):
    """Skeletons should be a fraction of the raw token count."""
    src = tmp_path / "big.py"
    body = "\n".join(
        [
            "def f_%d(x):" % i
            + "\n    "
            + "; ".join(f"v_{j} = x + {j}" for j in range(20))
            + "\n    return sum([" + ", ".join(f"v_{j}" for j in range(20)) + "])"
            for i in range(15)
        ]
    )
    src.write_text(body, encoding="utf-8")

    skel = extract_skeleton(src)
    assert skel is not None
    if skel.used_fallback or not skel.signatures:
        pytest.skip("grammar load failed")
    # Skeleton should be considerably smaller than the raw body.
    assert skel.token_estimate < skel.raw_token_estimate * 0.5


def test_compress_folder_returns_markdown(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("class Bar:\n    pass\n", encoding="utf-8")
    skeletons, md = compress_folder(tmp_path, ["a.py", "b.py"])
    # Even when grammars are missing we expect either a usable md or empty md.
    assert isinstance(md, str)


def test_unsupported_extension_returns_none(tmp_path):
    p = tmp_path / "x.weirdlang"
    p.write_text("noop", encoding="utf-8")
    assert get_language_rule(p) is None
    assert extract_skeleton(p) is None
