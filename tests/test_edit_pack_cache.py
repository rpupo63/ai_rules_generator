"""Tests for edit-pack warm cache and rich-AGENTS convention skipping."""

from pathlib import Path

import pytest

from ai_rules_generator.cache_store import (
    GRAPH_SCHEMA_VERSION,
    fingerprint_project,
    meta_path,
    purposes_path,
    try_load_warm_cache,
    write_cache,
)
from ai_rules_generator.edit_pack import assemble_edit_pack


def _mini_go_repo(root: Path, *, rich_agents: bool = True) -> None:
    if rich_agents:
        (root / "AGENTS.md").write_text(
            """# Mini

API service.

## Commands

```bash
go test ./...
```

## Architecture

- Handler → Service

## Gotchas

- Never hand-write UUIDs
""",
            encoding="utf-8",
        )
    else:
        (root / "AGENTS.md").write_text(
            "# Mini\n\nThin notes only.\n",
            encoding="utf-8",
        )
    (root / "go.mod").write_text("module example.com/mini\ngo 1.22\n", encoding="utf-8")
    api = root / "api"
    api.mkdir()
    (api / "handler.go").write_text(
        "package api\n\nfunc Handler() {}\n",
        encoding="utf-8",
    )
    svc = root / "services"
    svc.mkdir()
    (svc / "s3.go").write_text(
        "package services\n\nfunc UploadFile() {}\n\n"
        "func Handler() { UploadFile() }\n",
        encoding="utf-8",
    )


def test_fingerprint_stable_until_source_changes(tmp_path: Path):
    _mini_go_repo(tmp_path)
    a, n1 = fingerprint_project(tmp_path)
    b, n2 = fingerprint_project(tmp_path)
    assert a == b
    assert n1 == n2
    assert n1 >= 1
    (tmp_path / "api" / "handler.go").write_text(
        "package api\n\nfunc Handler() { /* changed */ }\n",
        encoding="utf-8",
    )
    c, _ = fingerprint_project(tmp_path)
    assert c != a


def test_warm_cache_skips_scan_on_second_call(tmp_path: Path, monkeypatch):
    _mini_go_repo(tmp_path)

    # Cold: builds cache
    first = assemble_edit_pack(
        tmp_path,
        ["api/handler.go"],
        token_budget=2500,
        enable_graph=True,
        enable_ast=True,
        write_graph_cache=True,
        use_cache=True,
    )
    assert first.paths == ["api/handler.go"]
    assert meta_path(tmp_path).is_file()
    assert purposes_path(tmp_path).is_file()
    assert (tmp_path / ".ai-context" / "graph" / "graph.json").is_file()
    hit = try_load_warm_cache(tmp_path)
    assert hit is not None

    calls = {"scan": 0}

    def boom(*_a, **_k):
        calls["scan"] += 1
        raise AssertionError("scan_project must not run on warm path")

    monkeypatch.setattr(
        "ai_rules_generator.scanner.scan_project",
        boom,
    )
    # Also block evidence if warm path incorrectly falls through
    monkeypatch.setattr(
        "ai_rules_generator.evidence.collect_evidence",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("collect_evidence must not run on warm path")
        ),
    )

    second = assemble_edit_pack(
        tmp_path,
        ["api/handler.go"],
        token_budget=2500,
        enable_graph=True,
        enable_ast=True,
        write_graph_cache=True,
        use_cache=True,
    )
    assert calls["scan"] == 0
    assert "ancestors" in {s.kind for s in second.sections}
    # Rich AGENTS → no conventions
    assert "conventions" not in {s.kind for s in second.sections}
    assert "Conventions (evidenced)" not in second.to_markdown()


def test_rich_agents_omits_conventions_even_cold(tmp_path: Path):
    _mini_go_repo(tmp_path, rich_agents=True)
    result = assemble_edit_pack(
        tmp_path,
        ["api/handler.go"],
        token_budget=2500,
        use_cache=False,
        write_graph_cache=False,
    )
    assert "conventions" not in {s.kind for s in result.sections}


def test_golden_used_by_section_when_edges_exist(tmp_path: Path):
    """Stable section presence for a tiny calling graph."""
    from ai_rules_generator.code_graph import (
        GraphBuildResult,
        Symbol,
        _FallbackGraph,
        serialize,
    )
    from ai_rules_generator.cache_store import write_cache, fingerprint_project
    from ai_rules_generator.constitution import load_constitution
    from ai_rules_generator.edit_pack import assemble_edit_pack

    _mini_go_repo(tmp_path)
    graph = _FallbackGraph()
    symbols = {
        "api.handler::Handler": Symbol(
            "api.handler::Handler", "function_definition", "api/handler.go", 1
        ),
        "services.s3::UploadFile": Symbol(
            "services.s3::UploadFile", "function_definition", "services/s3.go", 1
        ),
        "cmd.main::main": Symbol(
            "cmd.main::main", "function_definition", "cmd/main.go", 1
        ),
    }
    for q, s in symbols.items():
        graph.add_node(q, **s.to_dict())
    graph.add_edge("api.handler::Handler", "services.s3::UploadFile", kind="calls")
    graph.add_edge("cmd.main::main", "api.handler::Handler", kind="calls")
    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=2,
        used_fallback=True,
    )
    gpath = tmp_path / ".ai-context" / "graph" / "graph.json"
    serialize(result, gpath)
    fp, n = fingerprint_project(tmp_path)
    write_cache(
        tmp_path,
        fingerprint=fp,
        file_count=n,
        purposes={"api": "HTTP API endpoints and handlers", "services": "services"},
    )

    pack = assemble_edit_pack(
        tmp_path,
        ["api/handler.go"],
        token_budget=2500,
        use_cache=True,
        write_graph_cache=False,
        constitution=load_constitution(tmp_path),
    )
    md = pack.to_markdown()
    kinds = {s.kind for s in pack.sections}
    assert "ancestors" in kinds
    assert "used_by" in kinds
    assert "cmd/main.go" in md
    assert "Conventions (evidenced)" not in md


def test_graph_schema_version_mismatch_forces_miss(tmp_path: Path):
    """Old graph_schema_version must not warm-load (wrong edges)."""
    from ai_rules_generator.code_graph import (
        GraphBuildResult,
        Symbol,
        _FallbackGraph,
        serialize,
    )
    import json

    _mini_go_repo(tmp_path)
    graph = _FallbackGraph()
    symbols = {
        "api.handler::Handler": Symbol(
            "api.handler::Handler", "function_definition", "api/handler.go", 1
        ),
    }
    graph.add_node("api.handler::Handler", **symbols["api.handler::Handler"].to_dict())
    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=0,
        used_fallback=True,
    )
    serialize(result, tmp_path / ".ai-context" / "graph" / "graph.json")
    fp, n = fingerprint_project(tmp_path)
    write_cache(tmp_path, fingerprint=fp, file_count=n, purposes={"api": "API"})
    # Downgrade schema so warm path must miss
    mp = meta_path(tmp_path)
    meta = json.loads(mp.read_text(encoding="utf-8"))
    assert meta.get("graph_schema_version") == GRAPH_SCHEMA_VERSION
    meta["graph_schema_version"] = 1
    mp.write_text(json.dumps(meta) + "\n", encoding="utf-8")
    assert try_load_warm_cache(tmp_path) is None


def test_folder_seed_used_by_and_call_flow_cap(tmp_path: Path):
    """Folder packs always emit Used-by; Call flow ≤8 when emitted."""
    from ai_rules_generator.code_graph import (
        GraphBuildResult,
        Symbol,
        _FallbackGraph,
    )
    from ai_rules_generator.constitution import load_constitution
    from ai_rules_generator.edit_pack import _build_candidate_sections

    _mini_go_repo(tmp_path)
    graph = _FallbackGraph()
    symbols = {}
    # Intra-folder call spam (would be Call flow)
    for i in range(12):
        a = f"api.a{i}::A{i}"
        b = f"api.b{i}::B{i}"
        symbols[a] = Symbol(a, "function_definition", f"api/a{i}.go", 1)
        symbols[b] = Symbol(b, "function_definition", f"api/b{i}.go", 1)
        graph.add_node(a, **symbols[a].to_dict())
        graph.add_node(b, **symbols[b].to_dict())
        graph.add_edge(a, b, kind="calls")
    # Two external consumers (Used-by < 3 → Call flow still emitted)
    for i, consumer in enumerate(["cmd/main.go", "routes/r.go"]):
        q = f"ext.c{i}::C"
        symbols[q] = Symbol(q, "function_definition", consumer, 1)
        graph.add_node(q, **symbols[q].to_dict())
        graph.add_edge(q, "api.a0::A0", kind="calls")

    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=14,
        used_fallback=True,
    )
    sections = _build_candidate_sections(
        paths=["api"],
        constitution=load_constitution(tmp_path),
        scan_ctx=None,
        graph_result=result,
        workflow_lines=[],
        purposes={"api": "HTTP API"},
    )
    by_kind = {s.kind: s for s in sections}
    assert "used_by" in by_kind
    assert "cmd/main.go" in by_kind["used_by"].body
    assert "outbound" in by_kind
    call_bullets = [
        ln for ln in by_kind["outbound"].body.splitlines() if ln.startswith("- `")
    ]
    assert len(call_bullets) <= 8


def test_folder_seed_skips_call_flow_when_used_by_rich(tmp_path: Path):
    from ai_rules_generator.code_graph import (
        GraphBuildResult,
        Symbol,
        _FallbackGraph,
    )
    from ai_rules_generator.constitution import load_constitution
    from ai_rules_generator.edit_pack import _build_candidate_sections

    _mini_go_repo(tmp_path)
    graph = _FallbackGraph()
    symbols = {
        "api.h::H": Symbol("api.h::H", "function_definition", "api/h.go", 1),
    }
    graph.add_node("api.h::H", **symbols["api.h::H"].to_dict())
    graph.add_edge("api.h::H", "api.h::H", kind="calls")  # intra
    for i in range(3):
        q = f"ext.c{i}::C"
        symbols[q] = Symbol(q, "function_definition", f"cmd/c{i}.go", 1)
        graph.add_node(q, **symbols[q].to_dict())
        graph.add_edge(q, "api.h::H", kind="calls")
    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=4,
        used_fallback=True,
    )
    sections = _build_candidate_sections(
        paths=["api"],
        constitution=load_constitution(tmp_path),
        scan_ctx=None,
        graph_result=result,
        workflow_lines=[],
        purposes={"api": "HTTP API"},
    )
    kinds = {s.kind for s in sections}
    assert "used_by" in kinds
    assert "outbound" not in kinds
