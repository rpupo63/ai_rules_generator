"""
Persistent cache for edit-pack warm path.

Fingerprint source trees cheaply (path + size + mtime) so warm
`context for` can skip AST scan when nothing changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .exclusions import ALWAYS_SKIP_DIRS, should_skip_dir, should_skip_file

logger = logging.getLogger(__name__)

CACHE_DIR_REL = ".ai-context/cache"
META_REL = f"{CACHE_DIR_REL}/meta.json"
PURPOSES_REL = f"{CACHE_DIR_REL}/purposes.json"
GRAPH_REL = ".ai-context/graph/graph.json"

# Bump when graph edge semantics change so warm cache cannot serve stale edges.
GRAPH_SCHEMA_VERSION = 2

# Extensions that affect edit-pack neighborhoods / fingerprints.
SOURCE_SUFFIXES = {
    ".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".java",
    ".gd", ".cs", ".kt", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".vue", ".svelte",
}


@dataclass
class CacheHit:
    """Loaded warm-path artifacts."""

    fingerprint: str
    purposes: Dict[str, str]
    graph_path: Path


def cache_dir(project_root: Path) -> Path:
    return project_root / CACHE_DIR_REL


def meta_path(project_root: Path) -> Path:
    return project_root / META_REL


def purposes_path(project_root: Path) -> Path:
    return project_root / PURPOSES_REL


def graph_path(project_root: Path) -> Path:
    return project_root / GRAPH_REL


def _iter_source_files(project_root: Path) -> List[Path]:
    """Cheap list of source-like files (exclusions only; no gitignore parse)."""
    root = project_root.resolve()
    out: List[Path] = []
    skip_names = ALWAYS_SKIP_DIRS

    def walk(dir_path: Path) -> None:
        try:
            entries = list(dir_path.iterdir())
        except OSError:
            return
        for entry in entries:
            name = entry.name
            if entry.is_dir():
                if name in skip_names or name.endswith(".egg-info"):
                    continue
                # Fast path: skip common generated dirs without full should_skip
                if name in {"vendor", "testdata", "node_modules"}:
                    continue
                if should_skip_dir(entry, root, None):
                    continue
                walk(entry)
            elif entry.is_file():
                if entry.suffix.lower() not in SOURCE_SUFFIXES:
                    continue
                if should_skip_file(entry, root, None):
                    continue
                out.append(entry)

    walk(root)
    return out


def fingerprint_project(project_root: Path) -> Tuple[str, int]:
    """
    Hash of sorted (rel_path, size, mtime_ns) for source files.

    Returns (hex_digest, file_count).
    """
    root = project_root.resolve()
    lines: List[str] = []
    files = _iter_source_files(root)
    for path in files:
        try:
            st = path.stat()
            rel = path.relative_to(root).as_posix()
            lines.append(f"{rel}\t{st.st_size}\t{st.st_mtime_ns}")
        except OSError:
            continue
    lines.sort()
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, len(lines)


def purposes_from_scan(scan_ctx) -> Dict[str, str]:
    """Extract folder_rel → purpose from a ScanContext."""
    out: Dict[str, str] = {}
    by_path = getattr(scan_ctx, "by_path", None) or {}
    for path, info in by_path.items():
        rel = (path or "").replace("\\", "/").strip("/")
        purpose = (getattr(info, "purpose", None) or "").strip()
        if rel and purpose:
            out[rel] = purpose
    return out


def write_cache(
    project_root: Path,
    *,
    fingerprint: str,
    file_count: int,
    purposes: Dict[str, str],
) -> None:
    """Write meta.json + purposes.json (graph written separately)."""
    cdir = cache_dir(project_root)
    cdir.mkdir(parents=True, exist_ok=True)
    meta = {
        "fingerprint": fingerprint,
        "file_count": file_count,
        "created_at": time.time(),
        "schema_version": 1,
        "graph_schema_version": GRAPH_SCHEMA_VERSION,
    }
    meta_path(project_root).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    purposes_path(project_root).write_text(
        json.dumps(purposes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def try_load_warm_cache(project_root: Path) -> Optional[CacheHit]:
    """
    Return CacheHit if fingerprint matches and graph + purposes load.

    Primary invalidation: fingerprint mismatch. Age is not the gate.
    """
    root = project_root.resolve()
    mp = meta_path(root)
    pp = purposes_path(root)
    gp = graph_path(root)
    if not (mp.is_file() and pp.is_file() and gp.is_file()):
        return None

    try:
        meta = json.loads(mp.read_text(encoding="utf-8"))
        purposes = json.loads(pp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.info("edit-pack cache unreadable: %s", exc)
        return None

    cached_fp = meta.get("fingerprint")
    if not cached_fp or not isinstance(purposes, dict):
        return None

    cached_graph_ver = meta.get("graph_schema_version")
    if cached_graph_ver != GRAPH_SCHEMA_VERSION:
        logger.info(
            "edit-pack cache graph schema mismatch (%s != %s); rebuilding",
            cached_graph_ver,
            GRAPH_SCHEMA_VERSION,
        )
        return None

    current_fp, _ = fingerprint_project(root)
    if current_fp != cached_fp:
        return None

    return CacheHit(
        fingerprint=current_fp,
        purposes={str(k): str(v) for k, v in purposes.items()},
        graph_path=gp,
    )
