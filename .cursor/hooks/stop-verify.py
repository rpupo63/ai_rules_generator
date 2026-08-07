#!/usr/bin/env python3
"""C6 stop hook: run `just check` before session end (Claude sync Stop + Cursor stop)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OVERRIDE_ENV = "STOP_VERIFY_OVERRIDE"
OVERRIDE_FILE = ".agent-sessions/.stop-verify-override"
CHECKPOINT = Path(__file__).resolve().parent / "session-end-checkpoint.py"

BLOCK_REASON = (
    "just check failed. Fix the failing checks, run `just check`, then try stopping again. "
    "To skip once: STOP_VERIFY_OVERRIDE=1 or touch .agent-sessions/.stop-verify-override"
)


def repo_root(payload: dict) -> Path | None:
    for key in ("cwd", "workspace_root", "project_root"):
        val = payload.get(key)
        if isinstance(val, str) and val:
            return Path(val).resolve()
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        for val in roots:
            if isinstance(val, str) and val:
                return Path(val).resolve()
    try:
        return Path.cwd().resolve()
    except OSError:
        return None


def has_justfile(root: Path) -> bool:
    return (root / "justfile").is_file() or (root / "Justfile").is_file()


def override_active(root: Path) -> bool:
    if os.environ.get(OVERRIDE_ENV, "").lower() in ("1", "true", "yes"):
        return True
    return (root / OVERRIDE_FILE).is_file()


def session_touched_tracked(root: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    for line in proc.stdout.splitlines():
        if line and not line.startswith("??"):
            return True
    return False


def run_just_check(root: Path) -> int:
    try:
        proc = subprocess.run(
            ["just", "check"],
            cwd=root,
            timeout=600,
            check=False,
        )
        return proc.returncode
    except (OSError, subprocess.TimeoutExpired):
        return 0


def write_checkpoint(payload: dict) -> None:
    if not CHECKPOINT.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(CHECKPOINT)],
            input=json.dumps(payload).encode(),
            check=False,
            timeout=120,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def should_skip(payload: dict, root: Path, *, cursor: bool) -> bool:
    if override_active(root):
        return True
    if not has_justfile(root):
        return True
    if not session_touched_tracked(root):
        return True
    if cursor:
        if int(payload.get("loop_count") or 0) >= 1:
            return True
    elif payload.get("stop_hook_active"):
        return True
    return False


def emit_block(payload: dict, *, cursor: bool) -> None:
    write_checkpoint(payload)
    if cursor:
        print(json.dumps({"followup_message": BLOCK_REASON}))
    else:
        print(json.dumps({"decision": "block", "reason": BLOCK_REASON}))


def main() -> int:
    cursor = "--cursor" in sys.argv
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    root = repo_root(payload)
    if root is None or not (root / ".git").exists():
        print("{}")
        return 0

    if should_skip(payload, root, cursor=cursor):
        print("{}")
        return 0

    if run_just_check(root) == 0:
        print("{}")
        return 0

    emit_block(payload, cursor=cursor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
