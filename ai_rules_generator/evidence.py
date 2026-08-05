"""
Language-agnostic evidence collection for What / How / Why context.

Detects multiple stacks (polyglot), manifests (Go, Node, Godot, Compose,
shell/ops), READMEs, and CI — without requiring a single primary language.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .detection import (
    detect_cpp,
    detect_folder_technology,
    detect_go,
    detect_java,
    detect_javascript_typescript,
    detect_python,
    detect_rust,
    detect_frameworks,
)

SKIP_DIR_NAMES = {
    ".git", ".svn", ".hg",
    ".cursor", ".claude", ".ai-rules", ".ai-context", ".agents",
    "node_modules", ".venv", "venv", "env", "__pycache__",
    "dist", "build", "out", "target", "bin", "obj",
    ".next", ".nuxt", ".svelte-kit", "coverage", ".tox",
    "vendor", ".turbo",
}

# Notes/docs dirs are not product surfaces unless they have a code manifest.
_NOTES_DIR_SUFFIXES = ("-notes", "_notes")
_NOTES_DIR_NAMES = frozenset({
    "docs", "doc", "notes", "lore", "lore-notes", "dm-notes",
})
_CODE_MANIFESTS = (
    "go.mod", "package.json", "project.godot", "Cargo.toml",
    "pyproject.toml", "requirements.txt", "Pipfile", "pom.xml",
    "build.gradle", "CMakeLists.txt",
)


@dataclass
class StackSignal:
    language: str
    frameworks: List[str] = field(default_factory=list)
    source: str = ""  # path that evidenced this stack
    weight: int = 1


@dataclass
class EntrypointSignal:
    path: str
    kind: str  # go_main, package_bin, godot, compose, script, ci, extension, …
    note: str = ""
    priority: int = 50  # lower = more important for CODEBASE How


@dataclass
class EvidenceBundle:
    """Collected facts about a repository."""

    project_root: Path
    readme_excerpt: str = ""
    readme_path: Optional[str] = None
    stacks: List[StackSignal] = field(default_factory=list)
    entrypoints: List[EntrypointSignal] = field(default_factory=list)
    top_packages: List[str] = field(default_factory=list)
    compose_services: List[str] = field(default_factory=list)
    godot_version: Optional[str] = None
    why_facts: List[Tuple[str, str]] = field(default_factory=list)  # (fact, source)
    constraint_docs: List[Tuple[str, str]] = field(default_factory=list)  # (path, label)
    unknowns: List[str] = field(default_factory=list)
    file_lang_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def languages(self) -> List[str]:
        """Distinct languages ordered by weight / frequency."""
        weights: Counter = Counter()
        for s in self.stacks:
            weights[s.language] += s.weight
        for lang, n in self.file_lang_counts.items():
            weights[lang] += max(1, n // 5)
        return [lang for lang, _ in weights.most_common()]

    @property
    def frameworks_by_language(self) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for s in self.stacks:
            cur = out.setdefault(s.language, [])
            for fw in s.frameworks:
                if fw not in cur:
                    cur.append(fw)
        return out

    @property
    def primary_entrypoints(self) -> List[EntrypointSignal]:
        """Entrypoints ranked for CODEBASE How (lower priority first; CI last)."""
        ranked = sorted(self.entrypoints, key=lambda e: (e.priority, e.path))
        # Dedupe by path
        seen: set = set()
        out: List[EntrypointSignal] = []
        for ep in ranked:
            if ep.path in seen:
                continue
            seen.add(ep.path)
            out.append(ep)
        return out

    @property
    def surfaces(self) -> List[str]:
        """Top-level product/ops surfaces (allowlist-first, code/ops only)."""
        preferred = (
            "backend", "frontend", "extension", "apps", "packages",
            "services", "api", "web", "mobile", "stack", "install",
            "bootstrap", "agent", "e2e",
        )
        found = [
            p for p in preferred
            if p in self.top_packages
            and _looks_like_code_surface(self.project_root, p)
        ]
        for p in self.top_packages:
            if p in found or p in SKIP_DIR_NAMES:
                continue
            if _is_notes_or_docs_dir(p):
                continue
            if _looks_like_code_surface(self.project_root, p):
                found.append(p)
        return found[:12]


_EXT_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".gd": "gdscript",
    ".sh": "shell",
    ".bash": "shell",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".c": "c",
    ".h": "c",
}


def _is_notes_or_docs_dir(name: str) -> bool:
    low = name.lower()
    if low in _NOTES_DIR_NAMES:
        return True
    return any(low.endswith(suf) for suf in _NOTES_DIR_SUFFIXES)


def _looks_like_code_surface(root: Path, name: str) -> bool:
    """True when a top-level dir has a code/ops manifest or source files."""
    folder = root / name
    if not folder.is_dir():
        return False
    for manifest in _CODE_MANIFESTS:
        if (folder / manifest).is_file():
            return True
    for compose_name in (
        "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    ):
        if (folder / compose_name).is_file():
            return True
    # Lightweight: any source file in the first two levels
    try:
        for child in folder.iterdir():
            if child.is_file() and child.suffix.lower() in _EXT_LANG:
                return True
            if child.is_dir() and child.name not in SKIP_DIR_NAMES:
                for nested in child.iterdir():
                    if nested.is_file() and nested.suffix.lower() in _EXT_LANG:
                        return True
                    break
    except OSError:
        return False
    return False


def _read_text(path: Path, max_chars: int = 4000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
        return data[:max_chars]
    except OSError:
        return ""


def _first_readme(root: Path) -> Optional[Path]:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            return p
    return None


def _parse_godot(project_godot: Path) -> Tuple[Optional[str], List[str]]:
    text = _read_text(project_godot, 2000)
    version = None
    m = re.search(r'config_version\s*=\s*(\d+)', text)
    # Godot 4 uses config_version=5 typically; also look for features
    feat = re.search(r'config/features=PackedStringArray\(([^)]+)\)', text)
    if feat:
        # e.g. "4.3", "Forward Plus"
        parts = re.findall(r'"([^"]+)"', feat.group(1))
        for p in parts:
            if re.match(r"^\d+\.\d+", p):
                version = p
                break
    if version is None:
        # Fallback: presence implies Godot project
        version = "unknown"
    facts = []
    name_m = re.search(r'config/name="([^"]+)"', text)
    if name_m:
        facts.append(f"Godot project name: {name_m.group(1)}")
    return version, facts


def _parse_compose_services(compose_path: Path) -> List[str]:
    text = _read_text(compose_path, 8000)
    # Lightweight YAML-ish: lines like "  service_name:" under services:
    services: List[str] = []
    in_services = False
    for line in text.splitlines():
        if re.match(r"^services:\s*$", line):
            in_services = True
            continue
        if in_services:
            if re.match(r"^[A-Za-z]", line):
                break
            m = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
            if m:
                services.append(m.group(1))
    return services


def _walk_limited(root: Path, max_files: int = 8000) -> List[Path]:
    files: List[Path] = []
    for path in root.rglob("*"):
        if len(files) >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return files


def _count_file_languages(files: List[Path]) -> Dict[str, int]:
    counts: Counter = Counter()
    for f in files:
        lang = _EXT_LANG.get(f.suffix.lower())
        if lang:
            counts[lang] += 1
    return dict(counts)


def collect_evidence(project_root: Path) -> EvidenceBundle:
    """Scan project_root for multi-stack evidence."""
    root = project_root.resolve()
    bundle = EvidenceBundle(project_root=root)

    readme = _first_readme(root)
    if readme:
        bundle.readme_path = str(readme.relative_to(root))
        raw = _read_text(readme, 3000)
        # Prefer first non-heading paragraphs
        paras = []
        for block in re.split(r"\n\s*\n", raw):
            block = block.strip()
            if not block or block.startswith("#") and "\n" not in block:
                if block.startswith("# ") and not paras:
                    continue
                if block.startswith("#"):
                    # strip heading line
                    lines = block.splitlines()[1:]
                    block = "\n".join(lines).strip()
            if block and not block.startswith("```"):
                paras.append(re.sub(r"\s+", " ", block)[:400])
            if len(paras) >= 2:
                break
        bundle.readme_excerpt = " ".join(paras)[:600]
        if bundle.readme_excerpt:
            bundle.why_facts.append(
                ("README describes project purpose (see excerpt in What)", bundle.readme_path)
            )

    # Root-level language detectors
    detectors = [
        ("python", detect_python),
        ("go", detect_go),
        ("rust", detect_rust),
        ("java", detect_java),
        ("cpp", detect_cpp),
    ]
    for label, fn in detectors:
        if fn(root):
            fws = detect_frameworks(root, label)
            bundle.stacks.append(StackSignal(label, fws, f"root:{label}", weight=5))

    js = detect_javascript_typescript(root)
    if js:
        fws = detect_frameworks(root, js)
        bundle.stacks.append(StackSignal(js, fws, "package.json", weight=5))

    # Godot
    godot = root / "project.godot"
    if godot.is_file():
        version, facts = _parse_godot(godot)
        bundle.godot_version = version
        bundle.stacks.append(
            StackSignal("gdscript", ["godot"], "project.godot", weight=8)
        )
        bundle.entrypoints.append(
            EntrypointSignal("project.godot", "godot", f"Godot {version}", priority=10)
        )
        for fact in facts:
            bundle.why_facts.append((fact, "project.godot"))
        if version and version != "unknown":
            bundle.why_facts.append(
                (f"Targets Godot {version}", "project.godot")
            )

    # Compose / ops
    for name in (
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    ):
        p = root / name
        if p.is_file():
            svcs = _parse_compose_services(p)
            bundle.compose_services.extend(svcs)
            note = (
                f"Compose: {', '.join(svcs[:6])}"
                if svcs
                else "Docker Compose"
            )
            bundle.entrypoints.append(
                EntrypointSignal(name, "compose", note, priority=18)
            )
            if svcs:
                bundle.why_facts.append(
                    (
                        f"Docker Compose defines services: {', '.join(svcs[:12])}",
                        name,
                    )
                )

    # Nested compose under stack/
    for compose in root.glob("**/docker-compose*.yml"):
        if any(part in SKIP_DIR_NAMES for part in compose.parts):
            continue
        rel = str(compose.relative_to(root))
        if rel in {e.path for e in bundle.entrypoints}:
            continue
        svcs = _parse_compose_services(compose)
        for s in svcs:
            if s not in bundle.compose_services:
                bundle.compose_services.append(s)
        bundle.entrypoints.append(
            EntrypointSignal(
                rel,
                "compose",
                (
                    f"Compose: {', '.join(svcs[:6])}"
                    if svcs
                    else f"{len(svcs)} services"
                ),
                priority=45,
            )
        )

    # Go mains (prefer over bare go.mod as entrypoint)
    _GO_UTIL_SEGMENTS = frozenset({
        "cmd", "util", "utils", "tool", "tools", "hack", "scratch", "tmp",
    })
    _GO_UTIL_PREFIXES = ("migrate", "verify", "generate")
    for main_go in root.glob("**/main.go"):
        if any(part in SKIP_DIR_NAMES for part in main_go.parts):
            continue
        rel = str(main_go.relative_to(root))
        # Prefer shallow / product mains; demote cmd tools and util binaries
        depth = rel.count("/")
        parts = [p.lower() for p in Path(rel).parts]
        penalty = 0
        if any(p in _GO_UTIL_SEGMENTS for p in parts):
            penalty += 40
        elif any(
            p.startswith(pref) for p in parts for pref in _GO_UTIL_PREFIXES
        ):
            penalty += 40
        note = "Go util / migration main" if penalty else "Go server main"
        bundle.entrypoints.append(
            EntrypointSignal(
                rel, "go_main", note, priority=5 + depth + penalty
            )
        )

    # go.mod module path (metadata; lower priority than main.go)
    go_mod = root / "go.mod"
    if go_mod.is_file():
        text = _read_text(go_mod, 500)
        m = re.search(r"^module\s+(\S+)", text, re.M)
        if m:
            bundle.why_facts.append((f"Go module `{m.group(1)}`", "go.mod"))
            if not any(e.kind == "go_main" and e.path.endswith("main.go") for e in bundle.entrypoints):
                bundle.entrypoints.append(
                    EntrypointSignal("go.mod", "go_mod", m.group(1), priority=25)
                )
    # Also check nested go.mod (e.g. backend/go.mod)
    for nested in root.glob("*/go.mod"):
        if nested == go_mod:
            continue
        text = _read_text(nested, 500)
        m = re.search(r"^module\s+(\S+)", text, re.M)
        if m:
            rel = str(nested.relative_to(root))
            bundle.why_facts.append((f"Go module `{m.group(1)}`", rel))

    # package.json scripts at root and one level of packages
    def _add_pkg_scripts(pkg_path: Path) -> None:
        if not pkg_path.is_file():
            return
        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        rel = str(pkg_path.relative_to(root))
        if data.get("name") and rel == "package.json":
            bundle.why_facts.append(
                (f"npm package `{data['name']}`", "package.json")
            )
        scripts = data.get("scripts") or {}
        for key in ("dev", "start", "build", "test"):
            if key in scripts:
                runner = "npm"
                note = f"{runner} run {key}"
                bundle.entrypoints.append(
                    EntrypointSignal(rel, "package_bin", note, priority=15)
                )
                break

    _add_pkg_scripts(root / "package.json")
    for pkg_dir in ("frontend", "extension", "web", "apps", "packages"):
        _add_pkg_scripts(root / pkg_dir / "package.json")
        # one more level for packages/*
        pkg_root = root / pkg_dir
        if pkg_root.is_dir() and pkg_dir == "packages":
            for sub in pkg_root.iterdir():
                if sub.is_dir():
                    _add_pkg_scripts(sub / "package.json")

    # Browser extension manifest
    for manifest_name in ("manifest.json", "manifest.chrome.json"):
        for man in (
            root / "extension" / manifest_name,
            root / "extension" / "public" / manifest_name,
            root / manifest_name,
        ):
            if man.is_file():
                rel = str(man.relative_to(root))
                bundle.entrypoints.append(
                    EntrypointSignal(rel, "extension", "browser extension", priority=12)
                )
                break

    # Constraint / safety docs (Why bullets — path only)
    for pattern, label in (
        ("EXTENSION_SAFE_FILL_GUIDE.md", "extension form-fill safety"),
        ("VERIFICATION.md", "manual verification"),
        ("DEPLOYMENT_SOP.md", "deployment SOP"),
        ("**/DEPLOY*.md", "deploy notes"),
        ("**/deploy*.md", "deploy notes"),
    ):
        if "*" in pattern:
            for doc in root.glob(pattern):
                if any(part in SKIP_DIR_NAMES for part in doc.parts):
                    continue
                if not doc.is_file():
                    continue
                rel = str(doc.relative_to(root))
                if any(rel == p for p, _ in bundle.constraint_docs):
                    continue
                bundle.constraint_docs.append((rel, label))
                if len(bundle.constraint_docs) >= 6:
                    break
        else:
            doc = root / pattern
            if doc.is_file():
                bundle.constraint_docs.append((pattern, label))

    # Top-level packages / layout
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in SKIP_DIR_NAMES:
            continue
        lang, fws = detect_folder_technology(child)
        rel = child.name
        bundle.top_packages.append(rel)
        if lang:
            bundle.stacks.append(
                StackSignal(lang, fws, f"{rel}/", weight=3)
            )

    # Common package roots
    for pkg_dir in ("backend", "frontend", "apps", "packages", "services", "extension"):
        p = root / pkg_dir
        if p.is_dir():
            lang, fws = detect_folder_technology(p)
            if lang:
                bundle.stacks.append(
                    StackSignal(lang, fws, f"{pkg_dir}/", weight=4)
                )
            for sub in p.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    slang, sfws = detect_folder_technology(sub)
                    if slang:
                        bundle.stacks.append(
                            StackSignal(
                                slang, sfws, f"{pkg_dir}/{sub.name}/", weight=2
                            )
                        )

    # Shell install / bootstrap scripts (ops repos)
    for pattern in ("install/*.sh", "bootstrap/**/*.sh", "scripts/*.sh"):
        for sh in root.glob(pattern):
            if any(part in SKIP_DIR_NAMES for part in sh.parts):
                continue
            if not sh.is_file():
                continue
            rel = str(sh.relative_to(root))
            bundle.entrypoints.append(
                EntrypointSignal(rel, "script", "shell entry", priority=30)
            )
            if not any(s.language == "shell" for s in bundle.stacks):
                bundle.stacks.append(
                    StackSignal("shell", [], rel, weight=2)
                )

    # CI last (high priority number = shown after real entrypoints)
    for ci in (
        root / ".github" / "workflows",
        root / ".gitlab-ci.yml",
    ):
        if ci.is_file():
            bundle.entrypoints.append(
                EntrypointSignal(
                    str(ci.relative_to(root)), "ci", "CI config", priority=90
                )
            )
        elif ci.is_dir():
            for wf in sorted(ci.glob("*.yml"))[:3]:
                bundle.entrypoints.append(
                    EntrypointSignal(
                        str(wf.relative_to(root)),
                        "ci",
                        "GitHub Actions",
                        priority=90,
                    )
                )

    files = _walk_limited(root)
    bundle.file_lang_counts = _count_file_languages(files)

    # Ensure file-count languages appear as stacks
    seen = {s.language for s in bundle.stacks}
    for lang, n in bundle.file_lang_counts.items():
        if n >= 3 and lang not in seen:
            bundle.stacks.append(
                StackSignal(lang, [], f"*.{lang} files ({n})", weight=max(1, n // 10))
            )
            seen.add(lang)

    if not bundle.languages:
        bundle.unknowns.append(
            "Could not detect a primary language stack from manifests or file extensions."
        )
    if not bundle.readme_excerpt and not bundle.primary_entrypoints:
        bundle.unknowns.append(
            "No README or clear entrypoints found; What/How may be incomplete."
        )

    return bundle


def frameworks_for_path(
    evidence: EvidenceBundle,
    rel_path: str,
    folder_language: Optional[str],
) -> List[str]:
    """
    Frameworks applicable to a folder — never the whole project's frameworks.

    Matches stack signals whose source is under this path or equal language
    at the nearest package root.
    """
    rel = (rel_path or "").replace("\\", "/").rstrip("/")
    matched: List[str] = []
    for s in evidence.stacks:
        src = s.source.rstrip("/")
        if src.endswith("/") or "/" in src or src.endswith(".godot") or src.endswith(".json"):
            src_dir = src.rstrip("/")
            if src_dir.endswith(".godot") or src_dir.endswith(".json") or src_dir.startswith("root:"):
                # Root-level signal: only apply if folder language matches
                if folder_language and s.language == folder_language and not rel:
                    for fw in s.frameworks:
                        if fw not in matched:
                            matched.append(fw)
                elif folder_language and s.language == folder_language and rel in (
                    "frontend", "backend", "extension", "apps", "packages"
                ):
                    # weak: only if path name suggests that stack's home
                    pass
                continue
            if rel == src_dir or rel.startswith(src_dir + "/") or src_dir.startswith(rel + "/"):
                if not folder_language or s.language == folder_language:
                    for fw in s.frameworks:
                        if fw not in matched:
                            matched.append(fw)
        elif folder_language and s.language == folder_language and s.frameworks:
            # Manifest at root for this language — apply only at root folder
            if not rel:
                for fw in s.frameworks:
                    if fw not in matched:
                        matched.append(fw)
    # Path-local detection
    folder_abs = evidence.project_root / rel if rel else evidence.project_root
    if folder_abs.is_dir() and folder_language:
        local = detect_frameworks(folder_abs, folder_language)
        for fw in local:
            if fw not in matched:
                matched.append(fw)
    return matched
