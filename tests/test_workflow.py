"""Tests for workflow / conventions evidence gleaning."""

from pathlib import Path
import subprocess

from ai_rules_generator.constitution import load_constitution
from ai_rules_generator.orchestration import generate_codebase_context
from ai_rules_generator.workflow import collect_workflow, workflow_lines_for_codebase


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "feat: initial scaffold")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-m", "fix: tidy readme")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    _git(root, "add", "b.txt")
    _git(root, "commit", "-m", "chore: ignore noise")


def test_collect_workflow_conventional_commits_and_trunk(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# Demo\n\nPurpose here.\n\n## Commands\n\n```bash\necho ok\n```\n",
        encoding="utf-8",
    )
    constitution = load_constitution(tmp_path)
    bundle = collect_workflow(tmp_path, constitution=constitution, languages=["go"])
    cats = {f.category for f in bundle.facts}
    assert "commits" in cats
    assert any("Conventional Commits" in f.text for f in bundle.facts)
    assert any(f.category == "branches" for f in bundle.facts)
    lines = workflow_lines_for_codebase(bundle)
    assert lines and lines[0].startswith("Conventions")
    assert any(ln.startswith("- ") for ln in lines)


def test_collect_type_safety_from_tsconfig_and_zod(tmp_path: Path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true,"strictNullChecks":true}}\n',
        encoding="utf-8",
    )
    (frontend / "package.json").write_text(
        '{"name":"app","dependencies":{"zod":"^3.0.0"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("# App\n\nDemo.\n", encoding="utf-8")
    bundle = collect_workflow(
        tmp_path,
        constitution=load_constitution(tmp_path),
        languages=["typescript"],
    )
    texts = " ".join(f.text for f in bundle.facts)
    assert "strict" in texts.lower()
    assert "zod" in texts.lower()


def test_storage_philosophy_from_artifacts(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text(
        "# App\n\n"
        "## Where knowledge lives\n\n"
        "- Durable facts → Memory MCP (`project:demo`)\n"
        "- Session handoffs → `.agent-sessions/`\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").symlink_to("AGENTS.md")
    (tmp_path / ".agent-sessions").mkdir()
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "permissions.json").write_text("{}\n", encoding="utf-8")
    bundle = collect_workflow(
        tmp_path,
        constitution=load_constitution(tmp_path),
        languages=[],
    )
    texts = " ".join(f.text.lower() for f in bundle.facts)
    assert "agents.md" in texts or "constitution" in texts
    assert "agent-sessions" in texts
    assert "permissions.json" in texts
    assert "memory mcp" in texts


def test_generate_context_includes_conventions_section(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# Polyglot Demo\n\nAPI demo.\n\n## Commands\n\n```bash\ngo test\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.go").write_text(
        "package main\nfunc main() {}\n", encoding="utf-8"
    )
    (tmp_path / "backend" / "go.mod").write_text(
        "module example.com/demo\n\ngo 1.22\n", encoding="utf-8"
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"name":"fe","scripts":{"dev":"vite"},'
        '"dependencies":{"react":"18","zod":"3"},'
        '"devDependencies":{"typescript":"5"}}\n',
        encoding="utf-8",
    )
    (frontend / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":false,"strictNullChecks":false}}\n',
        encoding="utf-8",
    )
    (frontend / "src").mkdir()
    (frontend / "src" / "App.tsx").write_text(
        "export function App() { return null }\n", encoding="utf-8"
    )

    generate_codebase_context(tmp_path, use_ai=False, enable_graph=False)
    text = (tmp_path / ".ai-context" / "CODEBASE.md").read_text(encoding="utf-8")
    assert "## Conventions" in text
    assert "Conventional Commits" in text or "commit" in text.lower()
    assert "strict" in text.lower() or "zod" in text.lower()
    assert "source:" in text
