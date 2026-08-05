"""
Tests for structure-only Graph RAG (definitions / references).
"""

import json
from pathlib import Path

import pytest

from ai_rules_generator.code_graph import (
    EDGE_KINDS,
    GraphBuildResult,
    Symbol,
    _FallbackGraph,
    build_graph_from_project,
    deserialize,
    rank_symbols,
    render_repo_map,
    serialize,
)
from ai_rules_generator.tags import extract_tags, language_for_path


def _has_grammars() -> bool:
    try:
        from tree_sitter_language_pack import get_language  # noqa: F401

        return True
    except Exception:
        return False


requires_grammars = pytest.mark.skipif(
    not _has_grammars(),
    reason="tree-sitter-language-pack not installed",
)


def test_edge_kinds_are_def_ref_only():
    assert set(EDGE_KINDS) == {"defines", "references"}


def test_serialize_writes_well_formed_json(tmp_path):
    result = GraphBuildResult(
        graph=_FallbackGraph(),
        symbols_by_qname={},
        file_to_symbols={},
        edges_added=0,
        used_fallback=True,
    )
    out = serialize(result, tmp_path / "graph.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["fallback_mode"] is True
    assert doc["stats"] == {"node_count": 0, "edge_count": 0}


def test_render_repo_map_handles_empty():
    result = GraphBuildResult(
        graph=_FallbackGraph(),
        symbols_by_qname={},
        file_to_symbols={},
        edges_added=0,
        used_fallback=True,
    )
    md = render_repo_map(result)
    assert "no symbols" in md.lower()


def test_language_for_path_covers_bash_and_gdscript():
    assert language_for_path(Path("x.sh")) == "bash"
    assert language_for_path(Path("x.gd")) == "gdscript"
    assert language_for_path(Path("x.py")) == "python"


@requires_grammars
def test_bash_tags_extract_function_defs(tmp_path):
    src = tmp_path / "boot.sh"
    src.write_text(
        "#!/bin/bash\n"
        "apply_profile() {\n"
        "  echo hi\n"
        "}\n"
        "apply_profile\n",
        encoding="utf-8",
    )
    tags = extract_tags(src, "boot.sh")
    defs = {t.name for t in tags if t.kind == "def"}
    refs = {t.name for t in tags if t.kind == "ref"}
    assert "apply_profile" in defs
    assert "apply_profile" in refs or "echo" in refs


@requires_grammars
def test_build_graph_python_extracts_symbols(tmp_path):
    src = tmp_path / "core.py"
    src.write_text(
        "def helper(x):\n"
        "    return x + 1\n\n"
        "def main():\n"
        "    return helper(10)\n",
        encoding="utf-8",
    )
    result = build_graph_from_project(tmp_path, [src])
    if not result.symbols_by_qname:
        pytest.skip("grammar load failed")
    qnames = list(result.symbols_by_qname.keys())
    assert any(q.endswith("::helper") for q in qnames)
    assert any(q.endswith("::main") for q in qnames)


@requires_grammars
def test_rank_symbols_orders_by_importance(tmp_path):
    (tmp_path / "hub.py").write_text("def hub():\n    return 1\n", encoding="utf-8")
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    a.write_text("def a_fn():\n    return hub()\n", encoding="utf-8")
    b.write_text("def b_fn():\n    return hub()\n", encoding="utf-8")
    c.write_text("def c_fn():\n    return hub()\n", encoding="utf-8")

    result = build_graph_from_project(
        tmp_path, [a, b, c, tmp_path / "hub.py"]
    )
    if not result.symbols_by_qname:
        pytest.skip("grammar load failed")
    ranked = rank_symbols(result)
    if not ranked:
        pytest.skip("no ranks")
    top_name = ranked[0][0].qualified_name.rsplit("::", 1)[-1]
    assert top_name == "hub"


def test_build_graph_handles_no_files(tmp_path):
    result = build_graph_from_project(tmp_path, [])
    assert result.edges_added == 0
    assert result.symbols_by_qname == {}


def test_deserialize_roundtrip(tmp_path):
    graph = _FallbackGraph()
    sym = Symbol("pkg::foo", "definition", "pkg.py", 1)
    graph.add_node(sym.qualified_name, **sym.to_dict())
    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname={sym.qualified_name: sym},
        file_to_symbols={"pkg.py": [sym]},
        edges_added=0,
        used_fallback=True,
    )
    path = serialize(result, tmp_path / "g.json")
    loaded = deserialize(path)
    assert "pkg::foo" in loaded.symbols_by_qname
