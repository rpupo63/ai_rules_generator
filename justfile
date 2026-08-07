# C6 verification template — customize `_repo-check` per repo.
# Installed by install-repo-identity.sh (extended in C3-2).

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just check

# Run before claiming work is done (stop hooks call this).
check:
    @just _context-status
    @just _context-lint
    @just _repo-check

test:
    #!/usr/bin/env bash
    if [[ -f pyproject.toml ]] && command -v pytest >/dev/null 2>&1; then
      pytest -q
    elif [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
      npm test --if-present
    elif [[ -f Cargo.toml ]] && command -v cargo >/dev/null 2>&1; then
      cargo test
    else
      echo "just test: nothing configured (OK)"
    fi

lint:
    #!/usr/bin/env bash
    if [[ -f pyproject.toml ]] && command -v ruff >/dev/null 2>&1; then
      ruff check .
    elif [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
      npm run lint --if-present
    elif compgen -G "**/*.sh" >/dev/null 2>&1 && command -v shellcheck >/dev/null 2>&1; then
      find . -name '*.sh' -not -path './.git/*' -print0 | xargs -0 shellcheck
    else
      echo "just lint: nothing configured (OK)"
    fi

fmt:
    #!/usr/bin/env bash
    if [[ -f pyproject.toml ]] && command -v ruff >/dev/null 2>&1; then
      ruff format .
    elif [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
      npm run format --if-present
    else
      echo "just fmt: nothing configured (OK)"
    fi

handoff:
    #!/usr/bin/env bash
    mkdir -p .agent-sessions
    target=".agent-sessions/CURRENT.md"
    for src in templates/handoff.md .agent-sessions/handoff.md; do
      if [[ -f "$src" ]]; then
        if [[ ! -f "$target" ]]; then
          cp "$src" "$target"
          echo "created $target from $src"
        else
          echo "$target already exists"
        fi
        ${EDITOR:-${VISUAL:-nano}} "$target"
        exit 0
      fi
    done
    echo "handoff template missing — add templates/handoff.md (C2-11) or edit $target directly" >&2
    exit 1

_context-status:
    #!/usr/bin/env bash
    if [[ -x ./bin/context-status ]]; then
      ./bin/context-status --local
      exit $?
    fi
    if command -v context-status >/dev/null 2>&1; then
      context-status --local
      exit $?
    fi
    echo "context-status: not installed (skip)"

_context-lint:
    #!/usr/bin/env bash
    if [[ -x ./bin/ai-context-lint ]]; then
      ./bin/ai-context-lint
      exit $?
    fi
    if command -v ai-context-lint >/dev/null 2>&1; then
      ai-context-lint
      exit $?
    fi
    echo "ai-context-lint: not installed (skip)"

_repo-check:
    #!/usr/bin/env bash
    ran=0
    failed=0
    if [[ -f pyproject.toml ]] && command -v pytest >/dev/null 2>&1; then
      ran=1
      pytest -q || failed=1
    fi
    if [[ $ran -eq 0 ]]; then
      echo "just check: no repo-specific checks configured (OK)"
    fi
    exit "$failed"
