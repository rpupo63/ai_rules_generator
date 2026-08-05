"""
Structure-only orchestration: build repo map, optional cursor rules, AGENTS pointer.

Prose emitters and LLM enrichment paths have been removed. Generation is
deterministic: tags → graph → ranked map.

Reads optional `.ai-context/context-manifest.yml` (or repo-root
`context-manifest.yml`) so nightly timers need no per-repo arg list.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from . import __version__
from .agents_addendum import soft_addendum_body, patch_agents_md
from .code_graph import (
    build_graph_from_project,
    estimate_tokens,
    rank_files,
    render_repo_map,
    render_reverse_imports,
    serialize,
)
from .exclusions import get_exclusion_context, should_skip_dir, should_skip_file
from .models import ProjectConfig
from .rule_renderer import (
    TierFile,
    detect_folder_language,
    render_tier2_folder,
    write_tier_files,
)
from .scanner import ScanContext, scan_project
from .tags import language_for_path
from .token_budget import DEFAULT_GLOBAL_BUDGET, DEFAULT_MAP_BUDGET, TokenBudget

logger = logging.getLogger(__name__)

AI_CONTEXT_DIR = ".ai-context"
MANIFEST_FILENAME = "manifest.json"
CONTEXT_MANIFEST_NAMES = (
    f"{AI_CONTEXT_DIR}/context-manifest.yml",
    f"{AI_CONTEXT_DIR}/context-manifest.yaml",
    "context-manifest.yml",
    "context-manifest.yaml",
)

# Cap on glob-scoped .mdc rules — scales with usefulness, not directory count.
DEFAULT_MAX_CURSOR_FOLDERS = 8


@dataclass
class ContextManifest:
    """Repo-local generation knobs (from context-manifest.yml)."""

    version: int = 1
    budget_tokens: int = DEFAULT_MAP_BUDGET
    languages: List[str] = field(default_factory=list)
    always: List[str] = field(default_factory=list)
    never: List[str] = field(default_factory=list)
    seed_from: List[str] = field(default_factory=list)
    emit: List[str] = field(default_factory=lambda: ["map"])

    @property
    def emit_map(self) -> bool:
        return not self.emit or "map" in self.emit

    @property
    def emit_cursor_rules(self) -> bool:
        return "cursor-rules" in self.emit


def _parse_simple_manifest_yaml(text: str) -> Dict:
    """
    Minimal YAML subset for context-manifest.yml — no PyYAML dependency.

    Supports: integers, bare words, quoted strings, and `[a, b]` / multi-line
    `- item` lists for known top-level keys.
    """
    data: Dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "" or rest == "|" or rest == ">":
            # Block list
            items: List[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i].split("#", 1)[0].rstrip()
                if not nxt.strip():
                    i += 1
                    continue
                m = re.match(r"^\s+-\s+(.*)$", nxt)
                if not m:
                    break
                items.append(_unquote(m.group(1).strip()))
                i += 1
            data[key] = items
            continue
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                data[key] = [_unquote(p.strip()) for p in inner.split(",")]
        elif re.fullmatch(r"-?\d+", rest):
            data[key] = int(rest)
        else:
            data[key] = _unquote(rest)
        i += 1
    return data


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def load_context_manifest(project_root: Path) -> Optional[ContextManifest]:
    """Load the first context-manifest.yml found under the project root."""
    root = Path(project_root).resolve()
    for rel in CONTEXT_MANIFEST_NAMES:
        path = root / rel
        if not path.is_file():
            continue
        try:
            raw = _parse_simple_manifest_yaml(path.read_text(encoding="utf-8"))
        except OSError as exc:
            logger.warning("Could not read %s: %s", path, exc)
            continue
        languages = raw.get("languages") or []
        always = raw.get("always") or []
        never = raw.get("never") or []
        seed_from = raw.get("seed_from") or []
        emit = raw.get("emit") or ["map"]
        if isinstance(languages, str):
            languages = [languages]
        if isinstance(always, str):
            always = [always]
        if isinstance(never, str):
            never = [never]
        if isinstance(seed_from, str):
            seed_from = [seed_from]
        if isinstance(emit, str):
            emit = [emit]
        budget = raw.get("budget_tokens", DEFAULT_MAP_BUDGET)
        try:
            budget_i = int(budget)
        except (TypeError, ValueError):
            budget_i = DEFAULT_MAP_BUDGET
        return ContextManifest(
            version=int(raw.get("version") or 1),
            budget_tokens=budget_i,
            languages=[str(x) for x in languages],
            always=[str(x) for x in always],
            never=[str(x) for x in never],
            seed_from=[str(x) for x in seed_from],
            emit=[str(x) for x in emit],
        )
    return None


def _match_never(rel: str, never_patterns: Sequence[str]) -> bool:
    if not never_patterns:
        return False
    for pat in never_patterns:
        if fnmatch(rel, pat) or fnmatch(rel.split("/")[0], pat.rstrip("/*")):
            return True
        # Prefix folder match for patterns like build/**
        if pat.endswith("/**") and (rel == pat[:-3] or rel.startswith(pat[:-2])):
            return True
    return False


def _include_filter(
    project_root: Path,
    *,
    languages: Optional[Sequence[str]] = None,
    never: Optional[Sequence[str]] = None,
):
    excl = get_exclusion_context(project_root)
    gitignore = excl["gitignore_patterns"]
    lang_allow: Optional[Set[str]] = (
        {x.lower() for x in languages} if languages else None
    )
    never_pats = list(never or [])

    def _should(abs_path: Path, rel: str) -> bool:
        if _match_never(rel, never_pats):
            return False
        parts = Path(rel).parts
        for i in range(len(parts) - 1):
            d = project_root.joinpath(*parts[: i + 1])
            if should_skip_dir(d, project_root, gitignore):
                return False
            prefix = "/".join(parts[: i + 1])
            if _match_never(prefix, never_pats) or _match_never(prefix + "/**", never_pats):
                return False
        if should_skip_file(abs_path, project_root, gitignore):
            return False
        lang = language_for_path(abs_path)
        if lang is None:
            return False
        if lang_allow is not None and lang.lower() not in lang_allow:
            return False
        return True

    return _should


def build_repo_map(
    project_root: Path,
    *,
    scan_ctx: Optional[ScanContext] = None,
    token_budget: int = DEFAULT_MAP_BUDGET,
    write_graph: bool = False,
    languages: Optional[Sequence[str]] = None,
    never: Optional[Sequence[str]] = None,
):
    """Build the structure-only graph and Markdown repo map."""
    root = project_root.resolve()
    ctx = scan_ctx or scan_project(root)
    result = build_graph_from_project(
        root,
        ctx.files,
        should_include=_include_filter(root, languages=languages, never=never),
    )
    md = render_repo_map(result, token_budget=token_budget)
    if write_graph:
        graph_dir = root / AI_CONTEXT_DIR / "graph"
        serialize(result, graph_dir / "graph.json")
        (graph_dir / "repo-map.md").write_text(md + "\n", encoding="utf-8")
    return result, md


def _rule_is_file_listing_only(skeleton: str, reverse_imports: str) -> bool:
    """
    True when the .mdc body would only restate the folder's file listing.

    After the structure-only trim, skeletons are bullet file paths.  A rule
    that adds no reverse-import / used-by signal is directory noise — skip it.
    """
    if reverse_imports.strip():
        return False
    # Skeleton that is only `- `path`` lines (plus blanks) = file listing.
    useful = False
    for line in skeleton.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^- `[^`]+`$", s):
            continue
        useful = True
        break
    return not useful


def emit_tier2_folder_files(
    project_root: Path,
    scan_ctx: ScanContext,
    graph_result,
    *,
    config: Optional[ProjectConfig] = None,
    max_folders: int = DEFAULT_MAX_CURSOR_FOLDERS,
    dry_run: bool = False,
) -> List[TierFile]:
    """Emit glob-scoped `.mdc` rules for top-ranked folders (capped).

    Skips any folder whose rule would only restate its file listing.
    """
    cfg = config or ProjectConfig(
        description=project_root.name,
        is_monorepo=False,
        primary_language="",
        frameworks=[],
    )
    file_ranks = {f: s for f, s in rank_files(graph_result)}
    folder_scores = []
    for rel, folder in scan_ctx.folders.items():
        if not rel:
            continue
        score = 0.0
        for path in folder.files:
            try:
                r = str(path.resolve().relative_to(project_root)).replace("\\", "/")
            except ValueError:
                continue
            score += file_ranks.get(r, 0.0)
        folder_scores.append((rel, folder, score))
    folder_scores.sort(key=lambda t: t[2], reverse=True)

    files: List[TierFile] = []
    for rel, folder, _score in folder_scores:
        if len(files) >= max_folders:
            break
        file_rels = []
        for p in folder.files:
            try:
                file_rels.append(
                    str(p.resolve().relative_to(project_root)).replace("\\", "/")
                )
            except ValueError:
                continue
        lang = folder.language or detect_folder_language(file_rels) or cfg.primary_language
        rev = render_reverse_imports(graph_result, rel)
        skeleton = "\n".join(f"- `{f}`" for f in file_rels[:40])
        if _rule_is_file_listing_only(skeleton, rev):
            logger.debug("skip cursor rule for %s (file-listing only)", rel)
            continue
        glob_pattern = f"{rel}/**/*" if rel else "**/*"
        tf = render_tier2_folder(
            folder_name=rel or project_root.name,
            glob_pattern=glob_pattern,
            language=lang or "",
            frameworks=list(cfg.frameworks or []),
            skeleton_markdown=skeleton,
            reverse_imports=rev,
        )
        files.append(tf)

    if not dry_run and files:
        write_tier_files(project_root, files)
    return files


def _always_section(project_root: Path, always: Sequence[str]) -> str:
    if not always:
        return ""
    lines = ["## Always-on paths", ""]
    for rel in always:
        p = project_root / rel
        exists = "present" if p.exists() else "missing"
        lines.append(f"- `{rel}` ({exists})")
    lines.append("")
    return "\n".join(lines)


def _build_pack_manifest(
    project_root: Path,
    *,
    write_graph: bool,
    cursor_rule_count: int,
    languages: Sequence[str],
    budget_tokens: int,
) -> dict:
    files = {
        "codebase": f"{AI_CONTEXT_DIR}/CODEBASE.md",
    }
    if write_graph:
        files["graph"] = f"{AI_CONTEXT_DIR}/graph/"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "ai-rules-generator",
        "generator_version": __version__,
        "project_name": project_root.name,
        "budget_tokens": budget_tokens,
        "languages": list(languages),
        "constitution_present": (project_root / "AGENTS.md").is_file()
        or (project_root / "CLAUDE.md").is_file(),
        "cursor_rules": cursor_rule_count,
        "files": files,
    }


def generate_codebase_context(
    project_root: Path,
    *,
    enable_ast: bool = True,
    enable_graph: bool = True,
    dry_run: bool = False,
    emit_cursor_rules: bool = False,
    global_budget: Optional[int] = None,
    graph_token_budget: Optional[int] = None,
    write_graph: bool = False,
    write_modules: bool = False,
    emit_practices_flag: bool = False,
    context_manifest: Optional[ContextManifest] = None,
    **_ignored,
) -> dict:
    """
    Primary entry: structure-only `.ai-context/` map + AGENTS.md pointer.

    Keyword leftovers from the old AI/prose pipeline are accepted and ignored.
    XML emitter is intentionally absent — Markdown only.
    """
    root = Path(project_root).resolve()
    manifest = context_manifest if context_manifest is not None else load_context_manifest(root)

    # Repo context-manifest.yml is the contract for nightlies (no per-repo args).
    # When present, its budget_tokens wins; otherwise CLI / Aider-like default.
    if manifest is not None:
        map_budget = int(manifest.budget_tokens)
    elif graph_token_budget is not None:
        map_budget = int(graph_token_budget)
    else:
        map_budget = DEFAULT_MAP_BUDGET
    map_budget = max(1, map_budget)

    g_budget = (
        int(global_budget)
        if global_budget is not None
        else (int(manifest.budget_tokens) if manifest else DEFAULT_GLOBAL_BUDGET)
    )
    # Legacy CLI may pass a huge global; never let the ranked map exceed map_budget.
    if g_budget > 0:
        map_budget = min(map_budget, g_budget)

    languages = list(manifest.languages) if manifest and manifest.languages else []
    never = list(manifest.never) if manifest else []
    always = list(manifest.always) if manifest else []

    want_cursor = emit_cursor_rules or (manifest.emit_cursor_rules if manifest else False)
    want_map = manifest.emit_map if manifest else True

    budget = TokenBudget(g_budget)
    scan_ctx = scan_project(root) if enable_ast or enable_graph else ScanContext(
        project_root=root, files=[], folders={}
    )

    graph_result = None
    repo_map_md = ""
    if want_map and (enable_graph or enable_ast):
        graph_result, repo_map_md = build_repo_map(
            root,
            scan_ctx=scan_ctx,
            token_budget=map_budget,
            write_graph=False,
            languages=languages or None,
            never=never or None,
        )

    always_block = _always_section(root, always)
    codebase_md = (
        f"# Codebase map\n\n"
        f"Structure-only ranked symbols (definitions / references).\n\n"
        f"{always_block}"
        f"{repo_map_md}\n"
    )
    # Charge only the ranked map body against the map budget for acceptance;
    # header/always are tiny and stay with the artifact.
    map_tokens = estimate_tokens(repo_map_md)
    budget.force_spend(codebase_md, kind="codebase")

    ctx_dir = root / AI_CONTEXT_DIR
    pack_manifest = _build_pack_manifest(
        root,
        write_graph=write_graph,
        cursor_rule_count=0,
        languages=languages,
        budget_tokens=map_budget,
    )

    if not dry_run and want_map:
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "CODEBASE.md").write_text(codebase_md, encoding="utf-8")
        if write_graph and graph_result is not None:
            serialize(graph_result, ctx_dir / "graph" / "graph.json")
            (ctx_dir / "graph" / "repo-map.md").write_text(
                repo_map_md + "\n", encoding="utf-8"
            )

    cursor_files: List[TierFile] = []
    if want_cursor and graph_result is not None:
        cursor_files = emit_tier2_folder_files(
            root, scan_ctx, graph_result, dry_run=dry_run
        )
    pack_manifest["cursor_rules"] = len(cursor_files)

    if not dry_run:
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / MANIFEST_FILENAME).write_text(
            json.dumps(pack_manifest, indent=2) + "\n", encoding="utf-8"
        )
        body = soft_addendum_body(
            has_practices=False,
            has_graph=write_graph,
            edit_pack_focused=False,
        )
        patch_agents_md(root, addendum_body=body)

    return {
        "project_root": str(root),
        "files_scanned": len(scan_ctx.files),
        "symbols": len(graph_result.symbols_by_qname) if graph_result else 0,
        "edges": graph_result.edges_added if graph_result else 0,
        "cursor_rules": len(cursor_files),
        "map_tokens": map_tokens,
        "generator_version": __version__,
        "dry_run": dry_run,
        "budget": budget,
        "manifest": pack_manifest,
    }


def show_folder_context(
    project_root: Path,
    folder: str,
    *,
    full: bool = False,
    enable_ast: bool = True,
    enable_graph: bool = True,
) -> str:
    """Print a small on-demand digest for one folder."""
    root = Path(project_root).resolve()
    result, _md = build_repo_map(root, token_budget=min(800, DEFAULT_MAP_BUDGET))
    rev = render_reverse_imports(result, folder)
    lines = [f"# Folder `{folder}`", ""]
    syms = [
        s for s in result.symbols_by_qname.values()
        if s.file == folder or s.file.startswith(folder.rstrip("/") + "/")
    ]
    lines.append(f"Symbols: {len(syms)}")
    for s in syms[:40]:
        lines.append(f"- `{s.file}` :: `{s.qualified_name.rsplit('::', 1)[-1]}`")
    if full and rev:
        lines.extend(["", "## References", rev])
    return "\n".join(lines) + "\n"


# Compatibility shims for legacy command imports (rules setup removed).
def generate_single_project_rules_setup(*_a, **_k) -> None:
    raise RuntimeError(
        "Legacy rule setup was removed. Use `ai-rules-generator context` "
        "(structure-only map) or `--emit-cursor-rules`."
    )


def generate_monorepo_project_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def generate_single_project_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def generate_monorepo_rules(*_a, **_k) -> None:
    generate_single_project_rules_setup()


def discover_and_print_packages(project_root: Path):
    return []
