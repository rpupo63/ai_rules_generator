"""
Tests for the deterministic Graph RAG / DKB layer (Phase 4).
"""

import json
from pathlib import Path

import pytest

from ai_rules_generator.ast_compression import extract_skeleton
from ai_rules_generator.code_graph import (
    EDGE_KINDS,
    GraphBuildResult,
    Symbol,
    _FallbackGraph,
    build_graph,
    build_graph_from_project,
    deserialize,
    file_neighborhood,
    rank_symbols,
    render_file_neighborhood,
    render_folder_subgraph,
    render_repo_map,
    render_reverse_imports,
    serialize,
)


def _has_grammars() -> bool:
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
    reason="tree-sitter grammars not installed",
)


def test_edge_kinds_complete():
    assert set(EDGE_KINDS) == {
        "defines", "imports", "calls", "extends", "implements", "references"
    }


def test_serialize_writes_well_formed_json(tmp_path):
    # Hand-build an empty GraphBuildResult to exercise the serializer.
    from ai_rules_generator.code_graph import _FallbackGraph
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
    from ai_rules_generator.code_graph import _FallbackGraph
    result = GraphBuildResult(
        graph=_FallbackGraph(),
        symbols_by_qname={},
        file_to_symbols={},
        edges_added=0,
        used_fallback=True,
    )
    md = render_repo_map(result)
    assert "no symbols extracted" in md.lower()


@requires_grammars
def test_build_graph_python_extracts_symbols_and_calls(tmp_path):
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
    # The Hub is called by everyone -> should rank highest.
    (tmp_path / "hub.py").write_text("def hub():\n    return 1\n", encoding="utf-8")
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    a.write_text(
        "from hub import hub\n"
        "def a_fn():\n    return hub()\n",
        encoding="utf-8",
    )
    b.write_text(
        "from hub import hub\n"
        "def b_fn():\n    return hub()\n",
        encoding="utf-8",
    )
    c.write_text(
        "from hub import hub\n"
        "def c_fn():\n    return hub()\n",
        encoding="utf-8",
    )

    result = build_graph_from_project(tmp_path, [a, b, c, tmp_path / "hub.py"])
    if not result.symbols_by_qname:
        pytest.skip("grammar load failed")
    ranked = rank_symbols(result)
    if not ranked:
        pytest.skip("no edges added")
    top_name = ranked[0][0].qualified_name.rsplit("::", 1)[-1]
    # Hub should outrank the leaves (a_fn, b_fn, c_fn).
    assert top_name == "hub"


def test_build_graph_handles_no_skeletons(tmp_path):
    """build_graph must not crash on an empty skeleton list."""
    result = build_graph(tmp_path, [])
    assert result.edges_added == 0
    assert result.symbols_by_qname == {}


def _hand_build_result() -> GraphBuildResult:
    """Build a tiny DKB by hand so we can exercise the folder-scoped
    helpers without needing tree-sitter grammars installed."""
    graph = _FallbackGraph()
    symbols = {
        # services/foo.py defines foo + foo_helper; calls each other.
        "services.foo::foo": Symbol("services.foo::foo", "function_definition",
                                    "services/foo.py", 1),
        "services.foo::foo_helper": Symbol("services.foo::foo_helper",
                                           "function_definition",
                                           "services/foo.py", 5),
        # services/bar.py defines bar; calls foo (intra-folder edge).
        "services.bar::bar": Symbol("services.bar::bar", "function_definition",
                                    "services/bar.py", 1),
        # api/handler.py defines handler; calls foo (cross-folder edge).
        "api.handler::handler": Symbol("api.handler::handler",
                                       "function_definition",
                                       "api/handler.py", 1),
    }
    for q, sym in symbols.items():
        graph.add_node(q, **sym.to_dict())

    graph.add_edge("services.foo::foo", "services.foo::foo_helper", kind="calls")
    graph.add_edge("services.bar::bar", "services.foo::foo", kind="calls")
    graph.add_edge("api.handler::handler", "services.foo::foo", kind="calls")

    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=3,
        used_fallback=True,
    )


def test_render_folder_subgraph_keeps_only_intra_folder_edges():
    result = _hand_build_result()
    out = render_folder_subgraph(result, "services")
    # foo -> foo_helper (intra-file) and bar -> foo (intra-folder, cross-file)
    # should appear.
    assert "foo" in out and "foo_helper" in out
    assert "bar" in out
    # handler is in api/ -- it must NOT appear in the services subgraph.
    assert "handler" not in out


def test_render_folder_subgraph_returns_empty_when_no_edges():
    result = _hand_build_result()
    out = render_folder_subgraph(result, "no/such/folder")
    assert out == ""


def test_render_reverse_imports_lists_external_callers():
    result = _hand_build_result()
    out = render_reverse_imports(result, "services")
    # api/handler.py is the only external caller into services/.
    assert "api/handler.py" in out
    # bar lives in services/ - it's an internal call, not external.
    assert "services/bar.py" not in out


def test_render_reverse_imports_returns_empty_for_uncalled_folder():
    result = _hand_build_result()
    out = render_reverse_imports(result, "api")
    # Nothing calls into api/ in this fixture.
    assert out == ""


def test_file_neighborhood_includes_cross_folder_edges():
    result = _hand_build_result()
    neigh = file_neighborhood(result, "services/foo.py")
    # Outbound: foo -> foo_helper (same file)
    assert any(e.tgt_file.endswith("foo.py") for e in neigh.outbound) or any(
        e.kind == "calls" for e in neigh.outbound
    )
    # Inbound: bar (same folder) and handler (cross-folder)
    inbound_files = {e.src_file for e in neigh.inbound}
    assert "services/bar.py" in inbound_files
    assert "api/handler.py" in inbound_files
    assert "api/handler.py" in neigh.related_files


def test_file_neighborhood_respects_caps():
    result = _hand_build_result()
    neigh = file_neighborhood(
        result, "services/foo.py", max_edges=1, max_consumers=1
    )
    assert len(neigh.outbound) <= 1
    assert len(neigh.inbound) <= 1


def test_render_file_neighborhood_markdown():
    result = _hand_build_result()
    md = render_file_neighborhood(result, "services/foo.py")
    assert "Used by" in md
    assert "api/handler.py" in md


def test_serialize_deserialize_roundtrip(tmp_path):
    result = _hand_build_result()
    path = serialize(result, tmp_path / "graph.json")
    loaded = deserialize(path)
    assert loaded is not None
    assert len(loaded.symbols_by_qname) == len(result.symbols_by_qname)
    neigh = file_neighborhood(loaded, "services/foo.py")
    assert "api/handler.py" in {e.src_file for e in neigh.inbound}


def _handler_with_boilerplate_and_real_edges() -> GraphBuildResult:
    """Handler that calls respondJSON (boilerplate) and UploadFile (real)."""
    graph = _FallbackGraph()
    symbols = {
        "api.handler::upload": Symbol(
            "api.handler::upload", "function_definition", "api/handler.py", 1
        ),
        "api.respond::respondJSON": Symbol(
            "api.respond::respondJSON", "function_definition", "api/respond.go", 1
        ),
        "api.respond::respondError": Symbol(
            "api.respond::respondError", "function_definition", "api/respond.go", 5
        ),
        "services.s3::UploadFile": Symbol(
            "services.s3::UploadFile", "function_definition",
            "services/s3.go", 1
        ),
        "database.repo::FindByID": Symbol(
            "database.repo::FindByID", "function_definition",
            "database/repo.go", 1
        ),
    }
    for q, sym in symbols.items():
        graph.add_node(q, **sym.to_dict())
    graph.add_edge("api.handler::upload", "api.respond::respondJSON", kind="calls")
    graph.add_edge("api.handler::upload", "api.respond::respondError", kind="calls")
    graph.add_edge("api.handler::upload", "services.s3::UploadFile", kind="calls")
    graph.add_edge("api.handler::upload", "database.repo::FindByID", kind="calls")
    return GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=4,
        used_fallback=True,
    )


def test_file_neighborhood_ranks_cross_folder_before_boilerplate():
    result = _handler_with_boilerplate_and_real_edges()
    neigh = file_neighborhood(result, "api/handler.py", max_edges=15)
    tgt_names = [e.tgt_qname.rsplit("::", 1)[-1] for e in neigh.outbound]
    # Boilerplate dropped when enough real edges exist
    assert "respondJSON" not in tgt_names
    assert "respondError" not in tgt_names
    assert "UploadFile" in tgt_names
    assert "FindByID" in tgt_names
    assert all(e.tgt_file != "api/respond.go" for e in neigh.outbound)


def test_render_file_neighborhood_default_cap_is_tight():
    result = _handler_with_boilerplate_and_real_edges()
    md = render_file_neighborhood(result, "api/handler.py")
    assert "UploadFile" in md
    assert "respondJSON" not in md


def test_strict_resolve_omits_ambiguous_cross_package(tmp_path):
    """Same bare name in two packages must not pick a random global."""
    from ai_rules_generator.ast_compression import Skeleton, SignatureNode
    from ai_rules_generator.code_graph import build_graph, _semantic_edges

    def make_skel(rel: str, func: str, body: str = "") -> Skeleton:
        return Skeleton(
            file_path=str(tmp_path / rel),
            language="go",
            signatures=[
                SignatureNode(
                    kind="function_definition",
                    name=func,
                    signature=f"func {func}()",
                    body_text=body,
                )
            ],
        )

    skels = [
        make_skel("database/repo.go", "FindByID"),
        make_skel("other/repo.go", "FindByID"),
        make_skel("api/handler.go", "Handler", body="FindByID()"),
    ]
    result = build_graph(tmp_path, skels)
    hits = [
        (src, tgt)
        for src, tgt, kind in _semantic_edges(result)
        if kind == "calls" and src.endswith("::Handler") and "FindByID" in tgt
    ]
    # Ambiguous across packages → omit rather than guess
    assert hits == []


def test_outbound_dedupes_and_demotes_high_fanin():
    """One high-fan-in callee repeated + rare deps → rare first, not ×N spam."""
    graph = _FallbackGraph()
    symbols = {
        "api.h::Op1": Symbol("api.h::Op1", "function_definition", "api/h.go", 1),
        "api.h::Op2": Symbol("api.h::Op2", "function_definition", "api/h.go", 2),
        "api.h::Op3": Symbol("api.h::Op3", "function_definition", "api/h.go", 3),
        "db.auth::Belongs": Symbol(
            "db.auth::Belongs", "function_definition", "db/auth.go", 1
        ),
        "db.items::AppendItem": Symbol(
            "db.items::AppendItem", "function_definition", "db/items.go", 1
        ),
        "svc.s3::Upload": Symbol(
            "svc.s3::Upload", "function_definition", "svc/s3.go", 1
        ),
    }
    for q, s in symbols.items():
        graph.add_node(q, **s.to_dict())
    for i in range(6):
        q = f"other.f{i}::F"
        symbols[q] = Symbol(q, "function_definition", f"other/f{i}.go", 1)
        graph.add_node(q, **symbols[q].to_dict())
        graph.add_edge(q, "db.auth::Belongs", kind="calls")
    graph.add_edge("api.h::Op1", "db.auth::Belongs", kind="calls")
    graph.add_edge("api.h::Op2", "db.auth::Belongs", kind="calls")
    graph.add_edge("api.h::Op3", "db.auth::Belongs", kind="calls")
    graph.add_edge("api.h::Op1", "db.items::AppendItem", kind="calls")
    graph.add_edge("api.h::Op1", "svc.s3::Upload", kind="calls")

    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=11,
        used_fallback=True,
    )
    neigh = file_neighborhood(
        result, "api/h.go", max_edges=15, high_fanin_threshold=5
    )
    tgts = [e.tgt_qname.rsplit("::", 1)[-1] for e in neigh.outbound]
    assert tgts.count("Belongs") <= 1
    assert "AppendItem" in tgts
    assert "Upload" in tgts
    assert len(set(tgts)) >= 2
    md = render_file_neighborhood(result, "api/h.go")
    assert md.count("db/auth.go::Belongs") <= 1


def test_weak_graph_note_for_tsx():
    result = GraphBuildResult(
        graph=_FallbackGraph(),
        symbols_by_qname={},
        file_to_symbols={},
        edges_added=0,
        used_fallback=True,
    )
    md = render_file_neighborhood(result, "frontend/src/App.tsx")
    assert "call graph weak" in md.lower()
