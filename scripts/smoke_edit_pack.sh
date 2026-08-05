#!/usr/bin/env bash
# Local perf smoke for edit-pack warm path.
# Usage:
#   ./scripts/smoke_edit_pack.sh [/path/to/repo] [rel/path/to/file.go]
# Defaults: ~/Projects/faradhaven + backend/api/character_handler.go
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="${ROOT}/venv/bin/ai-rules-generator"
PROJECT="${1:-${HOME}/Projects/faradhaven}"
TARGET="${2:-backend/api/character_handler.go}"
BUDGET="${BUDGET:-2500}"
WARM_LIMIT_S="${WARM_LIMIT_S:-1.0}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI — run from rules_generator with venv installed" >&2
  exit 1
fi
if [[ ! -d "$PROJECT" ]]; then
  echo "Project not found: $PROJECT" >&2
  exit 1
fi

echo "Project: $PROJECT"
echo "Target:  $TARGET"
echo "Budget:  $BUDGET"
echo

# Invalidate fingerprint cache so first call is cold
rm -f "$PROJECT/.ai-context/cache/meta.json"
rm -f "$PROJECT/.ai-context/cache/purposes.json"

echo "=== COLD ==="
START=$(date +%s.%N)
"$CLI" context for "$TARGET" --project-root "$PROJECT" --budget "$BUDGET" \
  > /tmp/edit_pack_cold.md 2>/tmp/edit_pack_cold.err || true
END=$(date +%s.%N)
COLD=$(python3 -c "print(round(float('$END')-float('$START'), 3))")
grep -E '^## |^Paths:|^_Budget' /tmp/edit_pack_cold.md | head -20 || true
echo "cold_elapsed_s=$COLD"
echo

echo "=== WARM ==="
START=$(date +%s.%N)
"$CLI" context for "$TARGET" --project-root "$PROJECT" --budget "$BUDGET" \
  > /tmp/edit_pack_warm.md 2>/tmp/edit_pack_warm.err || true
END=$(date +%s.%N)
WARM=$(python3 -c "print(round(float('$END')-float('$START'), 3))")
grep -E '^## |^Paths:|^_Budget' /tmp/edit_pack_warm.md | head -20 || true
echo "warm_elapsed_s=$WARM"
echo

WARM="$WARM" WARM_LIMIT_S="$WARM_LIMIT_S" python3 - <<'PY'
from pathlib import Path
import os
import re
md = Path("/tmp/edit_pack_warm.md").read_text()
warm = float(os.environ["WARM"])
limit = float(os.environ["WARM_LIMIT_S"])
ok = True
if "Used by" not in md and "Ancestor folders" not in md:
    print("FAIL: missing Used by / Ancestor folders")
    ok = False
if "awesome-cursorrules" in md.lower() or "## Practice" in md:
    print("FAIL: practices noise present")
    ok = False
if "respondJSON" in md:
    print("FAIL: boilerplate respondJSON in pack")
    ok = False
# Calls section: when present with edges, require diverse callees (≥3 unique)
calls_m = re.search(
    r"## Calls / deps.*?\n(.*?)(?=\n## |\Z)",
    md,
    re.S,
)
if not calls_m:
    calls_m = re.search(
        r"## Neighborhood.*?\n(.*?)(?=\n## |\Z)",
        md,
        re.S,
    )
if calls_m:
    body = calls_m.group(1)
    # Prefer tgt side of src -> file::callee
    callees = re.findall(r"->\s*`[^`]*::([^`]+)`", body)
    unique = {c for c in callees if c}
    print(f"calls_unique_callees={len(unique)} names={sorted(unique)[:8]}")
    if unique and len(unique) < 3:
        print("FAIL: Calls present but <3 unique callees (likely spam)")
        ok = False
m = re.search(r"_Budget:\s*([\d,]+)\s*/\s*([\d,]+)", md)
if m:
    spent = int(m.group(1).replace(",", ""))
    cap = int(m.group(2).replace(",", ""))
    print(f"tokens={spent}/{cap}")
    if spent > cap:
        print("FAIL: over budget")
        ok = False
else:
    print("WARN: no budget line")
print(f"warm_elapsed_s={warm} limit={limit}")
if warm > limit:
    print(f"FAIL: warm path slower than {limit}s")
    ok = False
else:
    print(f"PASS: warm path <= {limit}s")
if "Conventions (evidenced)" in md:
    print("NOTE: Conventions section present (ok if AGENTS is thin)")
raise SystemExit(0 if ok else 1)
PY
