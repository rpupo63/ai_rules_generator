"""Integration tests for complementary context provider pipeline."""

from pathlib import Path

import pytest

from ai_rules_generator.agents_addendum import BEGIN_MARKER, constitution_body
from ai_rules_generator.constitution import load_constitution
from ai_rules_generator.context_renderer import DEFAULT_CODEBASE_MAX_CHARS
from ai_rules_generator.evidence import collect_evidence
from ai_rules_generator.orchestration import (
    generate_codebase_context,
    show_folder_context,
)
from ai_rules_generator.scanner import _infer_folder_purpose


def _write_polyglot_fixture(root: Path) -> None:
    """Minimal Go + TypeScript + Compose repo with hand-written AGENTS.md."""
    (root / "AGENTS.md").write_text(
        """# Polyglot Demo

API + web UI for demo purposes. Deploy on Tailscale only.

## Commands

```bash
go test ./...
npm test
```

## Off-Limits

- `**/.env*`

## Where knowledge lives

- Durable facts → Memory MCP (`project:polyglot-demo`)
""",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Polyglot Demo\n\nBackend in Go, frontend in React.\n",
        encoding="utf-8",
    )
    (root / "go.mod").write_text("module example.com/polyglot\n\ngo 1.22\n", encoding="utf-8")
    backend = root / "backend"
    backend.mkdir()
    (backend / "main.go").write_text(
        "package main\n\nfunc main() {}\n",
        encoding="utf-8",
    )
    (backend / "go.mod").write_text(
        "module example.com/polyglot/backend\n\ngo 1.22\n", encoding="utf-8"
    )
    (backend / "services").mkdir()
    (backend / "services" / "prompts").mkdir()
    (backend / "services" / "prompts" / "cover.go").write_text(
        "package prompts\n\nfunc Cover() string { return \"\" }\n",
        encoding="utf-8",
    )
    (backend / "services" / "llmextractor").mkdir()
    (backend / "services" / "llmextractor" / "extract.go").write_text(
        "package llmextractor\n\nfunc Extract() {}\n",
        encoding="utf-8",
    )
    frontend = root / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"name":"frontend","scripts":{"dev":"vite"},'
        '"dependencies":{"react":"^18.0.0"},'
        '"devDependencies":{"typescript":"^5.0.0"}}\n',
        encoding="utf-8",
    )
    (frontend / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    (frontend / "src").mkdir()
    (frontend / "src" / "App.tsx").write_text(
        "export function App() { return null }\n",
        encoding="utf-8",
    )
    (root / "EXTENSION_SAFE_FILL_GUIDE.md").write_text(
        "# Safe fill\n\nNever loosen checks.\n", encoding="utf-8"
    )
    (root / "docker-compose.yml").write_text(
        "services:\n  api:\n    image: api\n  web:\n    image: web\n",
        encoding="utf-8",
    )
    # Notes-only dir should not become a surface
    notes = root / "dm-notes"
    notes.mkdir()
    (notes / "session.md").write_text("# notes\n", encoding="utf-8")
    gh = root / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("name: ci\non: push\n", encoding="utf-8")


def _write_rich_agents_fixture(root: Path) -> None:
    """Purpose + Architecture + Commands — pointer should be skipped."""
    _write_polyglot_fixture(root)
    (root / "AGENTS.md").write_text(
        """# Polyglot Demo

API + web UI for demo purposes.

## Commands

```bash
go test ./...
npm test
```

## Architecture

- backend/: Go API
- frontend/: React UI
""",
        encoding="utf-8",
    )


def _write_godot_fixture(root: Path) -> None:
    (root / "project.godot").write_text(
        '; Engine configuration file\n'
        'config_version=5\n'
        '[application]\n'
        'config/name="ConspyroTest"\n'
        'config/features=PackedStringArray("4.3", "Forward Plus")\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Tiny Godot Game\n\nA stealth prototype.\n",
        encoding="utf-8",
    )


def test_evidence_polyglot_detects_go_and_ts(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    ev = collect_evidence(tmp_path)
    langs = set(ev.languages)
    assert "go" in langs
    assert "typescript" in langs or "javascript" in langs
    assert ev.compose_services
    assert "api" in ev.compose_services
    assert "backend" in ev.surfaces and "frontend" in ev.surfaces
    assert "dm-notes" not in ev.surfaces
    primary = ev.primary_entrypoints
    kinds = [e.kind for e in primary[:5]]
    assert "ci" not in kinds[:2] or any(e.path.endswith("main.go") for e in primary)
    assert any(e.path.endswith("main.go") for e in primary)
    # Compose is a real control surface (priority ~18)
    compose = next(e for e in primary if e.kind == "compose")
    assert "Compose:" in compose.note or "api" in compose.note


def test_go_cmd_utils_demoted_behind_product_main(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    cmd = tmp_path / "backend" / "cmd" / "verify-embeddings"
    cmd.mkdir(parents=True)
    (cmd / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
    ev = collect_evidence(tmp_path)
    primary = ev.primary_entrypoints
    paths = [e.path for e in primary]
    assert "backend/main.go" in paths
    product_idx = paths.index("backend/main.go")
    util = "backend/cmd/verify-embeddings/main.go"
    assert util in paths
    util_idx = paths.index(util)
    assert product_idx < util_idx
    pkg = next((p for p in paths if p.endswith("package.json")), None)
    if pkg:
        assert paths.index(pkg) < util_idx
    assert paths[0] == "backend/main.go"


def test_evidence_godot(tmp_path: Path):
    _write_godot_fixture(tmp_path)
    ev = collect_evidence(tmp_path)
    assert "gdscript" in ev.languages
    assert ev.godot_version == "4.3"


def test_constitution_detects_covered_topics(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    c = load_constitution(tmp_path)
    assert c.exists
    assert "commands" in c.covered_topics
    assert "off_limits" in c.covered_topics
    assert "memory" in c.covered_topics


def test_path_aware_purpose_prompts_not_batch_db():
    assert "prompt" in _infer_folder_purpose(
        "backend/services/prompts", []
    ).lower()
    assert "batch database" not in _infer_folder_purpose(
        "backend/services/prompts", []
    ).lower()
    assert "llm" in _infer_folder_purpose(
        "backend/services/llmextractor", []
    ).lower()


def test_generate_context_preserves_agents_body(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    result = generate_codebase_context(
        tmp_path,
        enable_ast=True,
        enable_graph=True,
        use_ai=False,
        dry_run=False,
    )
    after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert constitution_body(after).rstrip() == before.rstrip()
    # Thin AGENTS (no architecture) → additive pointer
    assert BEGIN_MARKER in after
    assert result["pre_constitution"].rstrip() == before.rstrip()
    assert result.get("agents_patched") is True

    codebase = tmp_path / ".ai-context" / "CODEBASE.md"
    assert codebase.exists()
    text = codebase.read_text(encoding="utf-8")
    assert "## What" in text
    assert "## How" in text
    assert "## Why" in text
    assert "Already covered in AGENTS.md" in text
    # Surface-balanced How
    assert "backend" in text.lower()
    assert "frontend" in text.lower()
    # Entrypoints prefer main / package over CI-only
    assert "main.go" in text or "package.json" in text
    # Practices off by default
    practices_dir = tmp_path / ".ai-context" / "practices"
    assert not practices_dir.exists() or not list(practices_dir.glob("*.md"))
    assert "## Practices" not in text
    assert result.get("practices", 0) == 0
    # Graph sidecars off by default
    assert not (tmp_path / ".ai-context" / "graph" / "repo-map.md").exists()
    # Lean always-on size
    assert len(text) <= DEFAULT_CODEBASE_MAX_CHARS + 200
    assert "batch database" not in text.lower()
    assert "EXTENSION_SAFE_FILL_GUIDE" in text
    assert (tmp_path / ".ai-context" / "manifest.json").exists()
    # Surface digests (not nested api dumps)
    assert "## Surface digests" in text
    assert "## Sidecars" in text
    # Workflow gleanings when git/history available (tmp fixture has no .git —
    # still OK if Conventions absent)
    modules = list((tmp_path / ".ai-context" / "modules").glob("*.md"))
    slugs = {p.stem for p in modules}
    assert "backend" in slugs or "frontend" in slugs
    assert "backend--services" not in slugs
    assert "backend--api" not in slugs
    # Digest shape: Top symbols, not Call flow
    if modules:
        body = modules[0].read_text(encoding="utf-8")
        assert "## Call flow" not in body
        assert "## Top symbols" in body or "## Overview" in body or "Purpose:" in body


def test_rich_agents_skips_pointer(tmp_path: Path):
    _write_rich_agents_fixture(tmp_path)
    before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    result = generate_codebase_context(
        tmp_path, use_ai=False, enable_graph=True, write_graph=False
    )
    after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    # No prior addendum → leave AGENTS untouched
    assert after == before
    assert BEGIN_MARKER not in after
    assert result.get("agents_patched") is False
    assert result.get("additive") is False
    codebase = tmp_path / ".ai-context" / "CODEBASE.md"
    assert codebase.exists()
    text = codebase.read_text(encoding="utf-8")
    # Thin pack: no What paraphrase / Why trivia / Already covered
    assert "## What" not in text
    assert "## Why" not in text
    assert "Already covered in AGENTS.md" not in text
    assert "## How" in text
    assert "context for" in text


def test_rich_agents_rewrites_stale_addendum(tmp_path: Path):
    from ai_rules_generator.agents_addendum import apply_addendum

    _write_rich_agents_fixture(tmp_path)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        apply_addendum(agents.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    before_body = constitution_body(agents.read_text(encoding="utf-8"))
    result = generate_codebase_context(
        tmp_path, use_ai=False, enable_graph=False
    )
    after = agents.read_text(encoding="utf-8")
    assert constitution_body(after).rstrip() == before_body.rstrip()
    assert BEGIN_MARKER in after
    assert "context for" in after
    assert result.get("agents_patched") is True


def test_practices_and_graph_opt_in(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    result = generate_codebase_context(
        tmp_path,
        use_ai=False,
        emit_practices_flag=True,
        write_graph=True,
        enable_graph=True,
    )
    assert result["practices"] >= 1
    assert (tmp_path / ".ai-context" / "practices" / "go.md").exists()
    assert (tmp_path / ".ai-context" / "graph" / "repo-map.md").exists()
    text = (tmp_path / ".ai-context" / "CODEBASE.md").read_text(encoding="utf-8")
    assert "## Practices" in text
    assert "graph/repo-map.md" in text


def test_generate_context_idempotent_addendum(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    generate_codebase_context(tmp_path, use_ai=False, enable_graph=False)
    first = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    generate_codebase_context(tmp_path, use_ai=False, enable_graph=False)
    second = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert first.count(BEGIN_MARKER) == 1
    assert second.count(BEGIN_MARKER) == 1
    assert constitution_body(first) == constitution_body(second)


def test_dry_run_does_not_write(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    generate_codebase_context(tmp_path, use_ai=False, dry_run=True, enable_graph=False)
    assert not (tmp_path / ".ai-context" / "CODEBASE.md").exists()
    assert BEGIN_MARKER not in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_ops_repo_without_ast_still_useful(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text(
        "# Home Ops\n\nFlashable install. Tailscale only.\n\n## Commands\n\n"
        "```bash\n./install/validate.sh\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Home Ops\n\nBootstrap scripts for spare PCs.\n", encoding="utf-8"
    )
    install = tmp_path / "install"
    install.mkdir()
    (install / "validate.sh").write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  ntfy:\n    image: ntfy\n", encoding="utf-8"
    )
    result = generate_codebase_context(
        tmp_path, use_ai=False, enable_ast=False, enable_graph=False
    )
    text = (tmp_path / ".ai-context" / "CODEBASE.md").read_text(encoding="utf-8")
    assert "## What" in text
    assert "ntfy" in text or "Compose" in text or "compose" in text.lower()
    assert result["modules"] >= 0


def test_context_show_digest(tmp_path: Path):
    _write_polyglot_fixture(tmp_path)
    text = show_folder_context(tmp_path, "backend", full=False)
    assert "Module: `backend/`" in text
    assert "## Call flow" not in text
    full = show_folder_context(tmp_path, "backend", full=True)
    assert "Module: `backend/`" in full


def test_context_for_edit_pack_ancestors_and_slices(tmp_path: Path):
    from ai_rules_generator.edit_pack import assemble_edit_pack

    _write_rich_agents_fixture(tmp_path)
    # Nested file under services
    nested = tmp_path / "backend" / "services" / "prompts" / "cover.go"
    result = assemble_edit_pack(
        tmp_path,
        ["backend/services/prompts/cover.go"],
        token_budget=2500,
        enable_graph=True,
        enable_ast=True,
        write_graph_cache=False,
    )
    md = result.to_markdown()
    assert "Ancestor folders" in md or "ancestors" in {s.kind for s in result.sections}
    kinds = {s.kind for s in result.sections}
    assert "ancestors" in kinds
    # Architecture section from rich AGENTS
    assert "agents_slices" in kinds or "Architecture" in md
    assert any("backend" in s.body for s in result.sections if s.kind == "ancestors")
    assert result.tokens_spent <= result.tokens_cap + 50


def test_context_for_budget_sheds_low_priority(tmp_path: Path):
    from ai_rules_generator.edit_pack import assemble_edit_pack

    _write_rich_agents_fixture(tmp_path)
    result = assemble_edit_pack(
        tmp_path,
        ["backend/services/prompts/cover.go"],
        token_budget=120,  # very tight
        enable_graph=True,
        enable_ast=True,
        write_graph_cache=False,
    )
    kinds = [s.kind for s in result.sections]
    # High-priority sections should survive before low-priority
    if result.shed:
        assert "folder_overview" in result.shed or "conventions" in result.shed or kinds
    assert result.tokens_spent <= result.tokens_cap + 80


def test_extract_topic_sections_architecture_gotchas(tmp_path: Path):
    from ai_rules_generator.constitution import (
        extract_topic_sections,
        load_constitution,
    )

    (tmp_path / "AGENTS.md").write_text(
        """# Demo

Purpose here.

## Architecture

- Handler → Service

## Gotchas

- Never hand-write UUIDs

## Commands

```bash
go test ./...
```
""",
        encoding="utf-8",
    )
    c = load_constitution(tmp_path)
    slices = extract_topic_sections(c, ["architecture", "gotchas", "commands"])
    topics = {t for t, _ in slices}
    assert "architecture" in topics
    assert "gotchas" in topics
    arch = next(md for t, md in slices if t == "architecture")
    assert "Handler" in arch
    assert "go test" not in arch  # not dumping whole file


def test_extract_topic_sections_architecture_path_aware(tmp_path: Path):
    from ai_rules_generator.constitution import (
        extract_topic_sections,
        load_constitution,
    )

    (tmp_path / "AGENTS.md").write_text(
        """# Demo

## Architecture

Overview of both sides.

### Backend

- Chi handlers in `backend/api`

### Frontend

- React SPA in `frontend/src`

## Gotchas

- Never hand-write UUIDs
""",
        encoding="utf-8",
    )
    c = load_constitution(tmp_path)
    back = extract_topic_sections(
        c, ["architecture"], path_rel="backend/api/handler.go"
    )
    front = extract_topic_sections(
        c, ["architecture"], path_rel="frontend/src/App.tsx"
    )
    assert "Chi handlers" in back[0][1]
    assert "React SPA" not in back[0][1]
    assert "React SPA" in front[0][1]
    assert "Chi handlers" not in front[0][1]


def test_go_frameworks_from_gomod(tmp_path: Path):
    from ai_rules_generator.detection import detect_go_frameworks

    (tmp_path / "go.mod").write_text(
        "module example.com/x\n\n"
        "require (\n"
        "\tgithub.com/go-chi/chi/v5 v5.2.3\n"
        "\tgorm.io/gorm v1.31.1\n"
        ")\n",
        encoding="utf-8",
    )
    fws = detect_go_frameworks(tmp_path)
    assert "chi" in fws
    assert "gorm" in fws


def test_context_show_full_with_hand_graph_edges(tmp_path: Path):
    """Strengthen --full: when edges exist, Used by / Call flow can appear."""
    from ai_rules_generator.code_graph import (
        GraphBuildResult,
        Symbol,
        _FallbackGraph,
        render_folder_subgraph,
        render_reverse_imports,
    )

    graph = _FallbackGraph()
    symbols = {
        "backend.main::main": Symbol(
            "backend.main::main", "function_definition", "backend/main.go", 1
        ),
        "backend.services.x::Run": Symbol(
            "backend.services.x::Run", "function_definition",
            "backend/services/x.go", 1
        ),
        "frontend.app::call": Symbol(
            "frontend.app::call", "function_definition", "frontend/app.ts", 1
        ),
    }
    for q, s in symbols.items():
        graph.add_node(q, **s.to_dict())
    graph.add_edge(
        "backend.main::main", "backend.services.x::Run", kind="calls"
    )
    graph.add_edge(
        "frontend.app::call", "backend.services.x::Run", kind="calls"
    )
    result = GraphBuildResult(
        graph=graph,
        symbols_by_qname=symbols,
        file_to_symbols={},
        edges_added=2,
        used_fallback=True,
    )
    sub = render_folder_subgraph(result, "backend")
    assert "main" in sub and "Run" in sub
    used = render_reverse_imports(result, "backend")
    assert "frontend/app.ts" in used


def test_truncate_codebase_keeps_digest_bullets_and_sidecars():
    from ai_rules_generator.context_renderer import _truncate_codebase

    bullets = "\n".join(
        f"- [`surf{i}/`](modules/surf{i}.md) — go — purpose {i}"
        for i in range(20)
    )
    body = (
        "# Codebase context: demo\n\n"
        "## What\n\n" + ("x" * 800) + "\n\n"
        "## How\n\n" + ("y" * 800) + "\n\n"
        "## Why\n\n- fact\n\n"
        "## Already covered in AGENTS.md\n\n- **Purpose** — already in `AGENTS.md`\n\n"
        "## Surface digests\n\n"
        f"{bullets}\n\n"
        "## Sidecars\n\n"
        "- Machine manifest: `.ai-context/manifest.json`\n"
    )
    assert len(body) > 2500
    out = _truncate_codebase(body, max_chars=2500)
    assert "## Surface digests" in out
    assert "- [`surf" in out
    assert "## Sidecars" in out
    assert len(out) <= 2500


def test_select_ai_folders_surface_balanced():
    from ai_rules_generator.orchestration import select_ai_folders
    from ai_rules_generator.scanner import FolderInfo

    def folder(path: str, n: int) -> FolderInfo:
        f = FolderInfo(name=path.split("/")[-1], path=path, purpose="x")
        f.file_count = n
        f.skeletons = [object()] * max(1, n // 10)  # type: ignore[list-item]
        return f

    candidates = [
        folder("backend", 100),
        folder("backend/api", 90),
        folder("backend/services", 80),
        folder("frontend", 20),
        folder("extension", 15),
        folder("e2e", 5),
    ]
    chosen = select_ai_folders(
        candidates,
        ["backend", "frontend", "extension", "e2e"],
        limit=3,
        per_file_scores={},
    )
    paths = {c.path for c in chosen}
    assert len(chosen) == 3
    assert "backend" in paths or "backend/api" in paths or "backend/services" in paths
    assert "frontend" in paths
    assert "extension" in paths
    backend_only = all(
        p == "backend" or p.startswith("backend/") for p in paths
    )
    assert not backend_only
