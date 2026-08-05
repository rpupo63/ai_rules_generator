"""
Emit language/framework best-practice files from awesome-cursorrules.

Writes `.ai-context/practices/<name>.md` for stacks detected in evidence.
Deterministic — no LLM required.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple

from .config import LANGUAGE_FRAMEWORK_MAP, UNIVERSAL_RULES
from .context_model import PracticeRef
from .evidence import EvidenceBundle
from .file_utils import extract_rule_content, read_rule_file
from .token_budget import TokenBudget


PRACTICES_DIR = "practices"
# Soft per-file line cap so practices stay progressive, not always-on dumps.
DEFAULT_PRACTICE_MAX_LINES = 120


def _resolve_base_path(base_path: Optional[Path] = None) -> Path:
    if base_path is not None:
        return base_path
    return Path(__file__).resolve().parent


def select_practice_targets(
    evidence: EvidenceBundle,
) -> List[Tuple[str, str]]:
    """
    Return ordered (slug, rule_name) pairs to emit.

    slug is the output filename stem; rule_name is passed to read_rule_file.
    """
    targets: List[Tuple[str, str]] = []
    seen: Set[str] = set()

    def add(slug: str, rule_name: str) -> None:
        if slug in seen or not rule_name:
            return
        seen.add(slug)
        targets.append((slug, rule_name))

    for lang in evidence.languages:
        key = lang.lower()
        # Map gdscript -> no dedicated rule yet; skip
        info = LANGUAGE_FRAMEWORK_MAP.get(key)
        if not info and key == "javascript":
            info = LANGUAGE_FRAMEWORK_MAP.get("typescript")
            key = "typescript"
        if not info:
            continue
        rule = info.get("rule_file")
        if rule:
            add(key, rule.replace(".mdc", ""))
        for fw in evidence.frameworks_by_language.get(lang, [])[:4]:
            # Framework rule files often share the framework name
            add(fw, fw)
        for extra in (info.get("additional") or [])[:2]:
            add(extra, extra)

    # Always include a couple of universals when we have any stack
    if targets:
        for uni in UNIVERSAL_RULES[:2]:
            add(uni, uni)

    return targets[:12]


def emit_practices(
    project_root: Path,
    evidence: EvidenceBundle,
    *,
    base_path: Optional[Path] = None,
    dry_run: bool = False,
    budget: Optional[TokenBudget] = None,
    max_lines: int = DEFAULT_PRACTICE_MAX_LINES,
) -> List[PracticeRef]:
    """
    Write practice markdown files and return PracticeRef list for CODEBASE index.
    """
    base = _resolve_base_path(base_path)
    out_dir = project_root / ".ai-context" / PRACTICES_DIR
    refs: List[PracticeRef] = []

    targets = select_practice_targets(evidence)
    if not targets:
        return refs

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for slug, rule_name in targets:
        raw = read_rule_file(base, rule_name)
        if not raw:
            continue
        body = extract_rule_content(raw).strip()
        if not body:
            continue
        lines = body.splitlines()
        if len(lines) > max_lines:
            body = "\n".join(lines[:max_lines]) + (
                f"\n\n_(truncated; full rule in awesome-cursorrules "
                f"`{rule_name}`.)_\n"
            )
        kind = (
            "universal"
            if slug in ("clean-code", "codequality", "gitflow", "database")
            else (
                "framework"
                if slug not in evidence.languages
                and slug
                not in {"typescript", "javascript", "python", "go", "rust"}
                else "language"
            )
        )
        header = (
            f"# Practice: {slug}\n\n"
            f"> From bundled awesome-cursorrules (`{rule_name}`). "
            f"Progressive disclosure — not always-on constitution.\n\n"
        )
        full = header + body.rstrip() + "\n"
        if budget is not None:
            outcome = budget.fit_or_truncate(
                full, kind="practice", folder=slug
            )
            if outcome is None:
                continue
            full, _ = outcome

        rel = f"{PRACTICES_DIR}/{slug}.md"
        path = out_dir / f"{slug}.md"
        if not dry_run:
            path.write_text(full, encoding="utf-8")
        refs.append(PracticeRef(name=slug, path=rel, kind=kind))

    return refs
