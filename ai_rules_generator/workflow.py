"""
Glean coding workflow / conventions from repo evidence (not LLM invention).

Sources: git history, AGENTS.md, tsconfig/eslint/mypy, package manifests,
agent identity artifacts (.agent-sessions, .agents/, CLAUDE.md symlink).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .constitution import Constitution


@dataclass
class WorkflowFact:
    """One evidenced workflow / convention bullet."""

    category: str  # commits | branches | type_safety | storage | language | style
    text: str
    source: str
    confidence: str = "medium"  # high | medium | low


@dataclass
class WorkflowBundle:
    facts: List[WorkflowFact] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)

    def by_category(self) -> Dict[str, List[WorkflowFact]]:
        out: Dict[str, List[WorkflowFact]] = {}
        for f in self.facts:
            out.setdefault(f.category, []).append(f)
        return out


def _run_git(root: Path, *args: str, timeout: float = 8.0) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _read_text(path: Path, max_chars: int = 8000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def _collect_git_workflow(root: Path) -> Tuple[List[WorkflowFact], List[str]]:
    facts: List[WorkflowFact] = []
    unknowns: List[str] = []

    if not (root / ".git").exists():
        return facts, unknowns

    # Default / current branch
    head = (_run_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    default = ""
    sym = _run_git(root, "symbolic-ref", "refs/remotes/origin/HEAD")
    if sym:
        # refs/remotes/origin/main -> main
        default = sym.strip().rsplit("/", 1)[-1]
    if not default:
        for candidate in ("main", "master"):
            check = _run_git(root, "show-ref", "--verify", f"refs/heads/{candidate}")
            if check is not None:
                default = candidate
                break
    default = default or head or "main"

    # Recent commit subjects (style + merge habit)
    log = _run_git(root, "log", "--pretty=%s", "-n", "40") or ""
    subjects = [ln.strip() for ln in log.splitlines() if ln.strip()]
    if not subjects:
        return facts, unknowns

    conv_re = re.compile(
        r"^(feat|fix|chore|refactor|docs|test|ci|build|perf|style)"
        r"(\([^)]+\))?!?:\s+",
        re.I,
    )
    conv_hits = sum(1 for s in subjects if conv_re.match(s))
    conv_ratio = conv_hits / max(1, len(subjects))
    if conv_ratio >= 0.4:
        facts.append(
            WorkflowFact(
                "commits",
                f"Commit messages often use Conventional Commits "
                f"({conv_hits}/{len(subjects)} recent).",
                "git log",
                "high" if conv_ratio >= 0.6 else "medium",
            )
        )
    elif conv_ratio < 0.15:
        facts.append(
            WorkflowFact(
                "commits",
                "Commit messages are mostly free-form (few Conventional Commit prefixes).",
                "git log",
                "medium",
            )
        )

    merges = _run_git(root, "log", "--merges", "--oneline", "-n", "20") or ""
    merge_n = len([ln for ln in merges.splitlines() if ln.strip()])
    # Commits whose first parent is default branch tip ancestry — approximate
    # "direct to main" vs feature work via branch name inventory.
    refs = _run_git(
        root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"
    ) or ""
    branch_names = [ln.strip() for ln in refs.splitlines() if ln.strip()]
    feature_pat = re.compile(
        r"(^|/)(feature|feat|fix|hotfix|bugfix|chore|refactor|vm)/",
        re.I,
    )
    pr_pat = re.compile(r"pull/\d+|pr/\d+", re.I)
    feature_branches = [
        b for b in branch_names
        if feature_pat.search(b) or pr_pat.search(b)
    ]
    # Exclude default and HEAD-ish
    feature_branches = [
        b for b in feature_branches
        if b not in {default, f"origin/{default}", "origin", "HEAD"}
        and not b.endswith(f"/{default}")
    ]

    if merge_n >= 3 and feature_branches:
        facts.append(
            WorkflowFact(
                "branches",
                f"History shows merge commits plus feature-like branches "
                f"({len(feature_branches)} refs) — likely PR / branch workflow "
                f"into `{default}`.",
                "git log --merges + refs",
                "medium",
            )
        )
    elif merge_n == 0 and head == default:
        facts.append(
            WorkflowFact(
                "branches",
                f"Recent history has no merge commits; work appears to land "
                f"directly on `{default}` (trunk-ish).",
                "git log --merges",
                "medium",
            )
        )
    elif feature_branches:
        facts.append(
            WorkflowFact(
                "branches",
                f"Feature-like branch names present "
                f"({', '.join(feature_branches[:4])}"
                f"{'…' if len(feature_branches) > 4 else ''}); "
                f"default branch is `{default}`.",
                "git refs",
                "medium",
            )
        )
    else:
        facts.append(
            WorkflowFact(
                "branches",
                f"Default / active branch is `{default}` "
                f"(little evidence of long-lived feature branches in refs).",
                "git",
                "low",
            )
        )

    # Sample subjects that look like session checkpoints (beto habit)
    checkpoint_n = sum(
        1 for s in subjects if "checkpoint" in s.lower() or "chore(sessions)" in s.lower()
    )
    if checkpoint_n >= 2:
        facts.append(
            WorkflowFact(
                "storage",
                f"Session checkpoint commits appear in history "
                f"({checkpoint_n} recent) — agent handoffs likely tracked in-repo.",
                "git log",
                "high",
            )
        )

    return facts, unknowns


def _json_load(path: Path) -> Optional[dict]:
    try:
        data = json.loads(_read_text(path, 50_000))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _collect_type_safety(root: Path) -> List[WorkflowFact]:
    facts: List[WorkflowFact] = []

    # TypeScript / JS
    ts_configs = list(root.glob("**/tsconfig*.json"))
    ts_configs = [
        p for p in ts_configs
        if "node_modules" not in p.parts and ".ai-context" not in p.parts
    ][:8]
    strict_true = 0
    strict_false = 0
    for p in ts_configs:
        text = _read_text(p)
        # Cheap parse — also try JSON
        data = _json_load(p) or {}
        opts = data.get("compilerOptions") or {}
        if opts.get("strict") is True or opts.get("strictNullChecks") is True:
            strict_true += 1
        elif opts.get("strict") is False or opts.get("strictNullChecks") is False:
            strict_false += 1
        elif '"strict": true' in text or '"strictNullChecks": true' in text:
            strict_true += 1
        elif '"strict": false' in text or '"strictNullChecks": false' in text:
            strict_false += 1

    if strict_true and not strict_false:
        facts.append(
            WorkflowFact(
                "type_safety",
                f"TypeScript `strict` / `strictNullChecks` enabled "
                f"({strict_true} tsconfig).",
                "tsconfig",
                "high",
            )
        )
    elif strict_false and not strict_true:
        facts.append(
            WorkflowFact(
                "type_safety",
                f"TypeScript strictness is relaxed "
                f"(`strict`/`strictNullChecks` false in {strict_false} tsconfig).",
                "tsconfig",
                "high",
            )
        )
    elif strict_true and strict_false:
        facts.append(
            WorkflowFact(
                "type_safety",
                "TypeScript strictness is mixed across tsconfigs "
                "(some strict, some relaxed).",
                "tsconfig",
                "medium",
            )
        )

    # Zod / runtime validation in package.json deps
    for pkg in list(root.glob("**/package.json"))[:12]:
        if "node_modules" in pkg.parts:
            continue
        data = _json_load(pkg) or {}
        deps = {}
        deps.update(data.get("dependencies") or {})
        deps.update(data.get("devDependencies") or {})
        validators = [
            name for name in ("zod", "yup", "joi", "io-ts", "valibot", "arktype")
            if name in deps
        ]
        if validators:
            rel = str(pkg.relative_to(root))
            facts.append(
                WorkflowFact(
                    "type_safety",
                    f"Runtime schema validation via {', '.join(validators)} "
                    f"({rel}).",
                    rel,
                    "high",
                )
            )
            break

    # Python
    for name in ("mypy.ini", "pyproject.toml", "pyrightconfig.json", ".pyrightconfig.json"):
        p = root / name
        if not p.is_file():
            # one level down
            hits = list(root.glob(f"*/{name}"))[:3]
            if not hits:
                continue
            p = hits[0]
        text = _read_text(p, 4000)
        rel = str(p.relative_to(root))
        if name.endswith(".toml") or name == "pyproject.toml":
            if "[tool.mypy]" in text or name == "mypy.ini":
                facts.append(
                    WorkflowFact(
                        "type_safety",
                        f"Python type checking configured ({rel}).",
                        rel,
                        "high",
                    )
                )
                break
            if "pyright" in text.lower():
                facts.append(
                    WorkflowFact(
                        "type_safety",
                        f"Pyright configured ({rel}).",
                        rel,
                        "high",
                    )
                )
                break
        if name == "mypy.ini":
            facts.append(
                WorkflowFact(
                    "type_safety",
                    f"Python type checking configured ({rel}).",
                    rel,
                    "high",
                )
            )
            break
        if "pyright" in name.lower():
            facts.append(
                WorkflowFact(
                    "type_safety",
                    f"Pyright configured ({rel}).",
                    rel,
                    "high",
                )
            )
            break

    # Go lint / staticcheck
    for name in (".golangci.yml", ".golangci.yaml", "golangci.yml"):
        if (root / name).is_file() or list(root.glob(f"*/{name}")):
            facts.append(
                WorkflowFact(
                    "type_safety",
                    "golangci-lint config present (static analysis on Go).",
                    name,
                    "high",
                )
            )
            break

    # ESLint
    eslint_hits = list(root.glob("**/eslint.config.*")) + list(root.glob("**/.eslintrc*"))
    eslint_hits = [p for p in eslint_hits if "node_modules" not in p.parts][:3]
    if eslint_hits:
        facts.append(
            WorkflowFact(
                "type_safety",
                f"ESLint configured (`{eslint_hits[0].relative_to(root)}`).",
                str(eslint_hits[0].relative_to(root)),
                "medium",
            )
        )

    return facts


def _collect_storage_philosophy(
    root: Path, constitution: Constitution
) -> List[WorkflowFact]:
    facts: List[WorkflowFact] = []
    body = constitution.body if constitution.exists else ""

    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if agents.is_file() and claude.is_symlink():
        facts.append(
            WorkflowFact(
                "storage",
                "`CLAUDE.md` → `AGENTS.md` symlink (single constitution file).",
                "CLAUDE.md",
                "high",
            )
        )
    elif agents.is_file():
        facts.append(
            WorkflowFact(
                "storage",
                "Project constitution lives in repo-root `AGENTS.md`.",
                "AGENTS.md",
                "high",
            )
        )

    if (root / ".agent-sessions").is_dir():
        facts.append(
            WorkflowFact(
                "storage",
                "Session handoffs under `.agent-sessions/` "
                "(lean checkpoints in-repo).",
                ".agent-sessions/",
                "high",
            )
        )
    elif re.search(r"\.agent-sessions|session[- ]handoff", body, re.I):
        facts.append(
            WorkflowFact(
                "storage",
                "AGENTS.md references session handoffs "
                "(.agent-sessions / handoff skill).",
                "AGENTS.md",
                "high",
            )
        )

    if (root / ".agents" / "permissions.json").is_file():
        facts.append(
            WorkflowFact(
                "storage",
                "Repo tool allows in `.agents/permissions.json` "
                "(cross-tool permission sync).",
                ".agents/permissions.json",
                "high",
            )
        )

    if re.search(r"memory mcp|durable (facts|corrections)|project:<", body, re.I):
        facts.append(
            WorkflowFact(
                "storage",
                "Durable corrections pointed at Memory MCP from AGENTS.md "
                "(not duplicated into always-on rules).",
                "AGENTS.md",
                "high",
            )
        )

    if re.search(
        r"where knowledge lives|procedures\s*→|project facts",
        body,
        re.I,
    ):
        facts.append(
            WorkflowFact(
                "storage",
                "AGENTS.md defines a knowledge split "
                "(procedures / project facts / durable memory).",
                "AGENTS.md",
                "high",
            )
        )

    # Cursor / Claude local rules
    if (root / ".cursor" / "rules").is_dir():
        facts.append(
            WorkflowFact(
                "storage",
                "Cursor rules present under `.cursor/rules/`.",
                ".cursor/rules/",
                "medium",
            )
        )

    return facts


def _collect_language_prefs(root: Path, languages: Sequence[str]) -> List[WorkflowFact]:
    facts: List[WorkflowFact] = []
    if languages:
        facts.append(
            WorkflowFact(
                "language",
                "Primary languages by evidence weight: "
                + ", ".join(languages[:5])
                + ".",
                "stack detection",
                "high",
            )
        )

    # Package managers
    managers = []
    if (root / "pnpm-lock.yaml").is_file() or list(root.glob("*/pnpm-lock.yaml")):
        managers.append("pnpm")
    if (root / "yarn.lock").is_file() or list(root.glob("*/yarn.lock")):
        managers.append("yarn")
    if (root / "bun.lockb").is_file() or list(root.glob("*/bun.lockb")):
        managers.append("bun")
    if (root / "package-lock.json").is_file() or list(root.glob("*/package-lock.json")):
        managers.append("npm")
    if managers:
        facts.append(
            WorkflowFact(
                "language",
                f"JS package manager lockfile(s): {', '.join(dict.fromkeys(managers))}.",
                "lockfiles",
                "high",
            )
        )

    if (root / "go.mod").is_file() or list(root.glob("*/go.mod")):
        facts.append(
            WorkflowFact(
                "language",
                "Go modules (`go.mod`) — prefer `go test` / module-local packages.",
                "go.mod",
                "medium",
            )
        )

    return facts


def _collect_agents_workflow_text(constitution: Constitution) -> List[WorkflowFact]:
    """Pull explicit workflow bullets already authored in AGENTS.md."""
    if not constitution.exists:
        return []
    facts: List[WorkflowFact] = []
    body = constitution.body
    patterns = [
        (
            r"(?im)^(?:[-*]\s+)?(?:never |do not )?commit to main\b.*$",
            "branches",
        ),
        (
            r"(?im)^(?:[-*]\s+)?.*\b(feature branch|pull request|\bPR\b|vm/\S+)\b.*$",
            "branches",
        ),
        (
            r"(?im)^(?:[-*]\s+)?.*\b(type.?safe|typescript strict|zod|mypy)\b.*$",
            "type_safety",
        ),
        (
            r"(?im)^(?:[-*]\s+)?.*\b(surgical|karpathy|simplicity first)\b.*$",
            "style",
        ),
    ]
    seen: set = set()
    for pat, cat in patterns:
        for m in re.finditer(pat, body):
            line = re.sub(r"^[-*]\s+", "", m.group(0).strip())
            if len(line) < 12 or line.lower() in seen:
                continue
            seen.add(line.lower())
            facts.append(
                WorkflowFact(
                    cat,
                    line[:200],
                    "AGENTS.md",
                    "high",
                )
            )
            if len(facts) >= 6:
                return facts
    return facts


def collect_workflow(
    project_root: Path,
    *,
    constitution: Optional[Constitution] = None,
    languages: Optional[Sequence[str]] = None,
) -> WorkflowBundle:
    """Collect evidenced workflow / convention facts for CODEBASE."""
    root = project_root.resolve()
    if constitution is None:
        from .constitution import load_constitution
        constitution = load_constitution(root)

    bundle = WorkflowBundle()
    git_facts, git_unknowns = _collect_git_workflow(root)
    bundle.facts.extend(git_facts)
    bundle.unknowns.extend(git_unknowns)

    bundle.facts.extend(_collect_agents_workflow_text(constitution))
    bundle.facts.extend(_collect_type_safety(root))
    bundle.facts.extend(_collect_storage_philosophy(root, constitution))
    bundle.facts.extend(_collect_language_prefs(root, languages or []))

    # Dedupe near-identical texts
    seen: set = set()
    uniq: List[WorkflowFact] = []
    for f in bundle.facts:
        key = (f.category, f.text.lower()[:120])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    bundle.facts = uniq
    return bundle


def workflow_lines_for_codebase(
    bundle: WorkflowBundle,
    *,
    max_bullets: int = 10,
) -> List[str]:
    """
    Render lean markdown bullets for CODEBASE Conventions section.

    Prefer high-confidence; keep category diversity.
    """
    if not bundle.facts:
        return []

    # Order categories for agent usefulness
    order = (
        "branches",
        "commits",
        "type_safety",
        "storage",
        "language",
        "style",
    )
    by_cat = bundle.by_category()
    picked: List[WorkflowFact] = []
    # Round-robin for diversity
    while len(picked) < max_bullets:
        progressed = False
        for cat in order:
            group = by_cat.get(cat) or []
            # Prefer high confidence first
            group = sorted(
                group,
                key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.confidence, 3), f.text),
            )
            for fact in group:
                if fact in picked:
                    continue
                picked.append(fact)
                progressed = True
                break
            if len(picked) >= max_bullets:
                break
        if not progressed:
            break

    lines = ["Conventions / workflow (evidenced — verify before inventing policy):"]
    for fact in picked:
        lines.append(f"- {fact.text} _(source: `{fact.source}`)_")
    return lines
