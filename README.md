# AI Rules Generator

Structure-only codebase context for agents: ranked definition/reference maps
from vendored tree-sitter tag queries (Aider Apache-2.0 + GDScript), plus
optional globbed Cursor `.mdc` rules and an idempotent `AGENTS.md` pointer.

No model calls. No provider/API-key config. Routing belongs at your gateway.

## Install

```bash
pip install -e .
# optional PageRank (else in-degree ranking):
pip install -e '.[rank]'
```

## Usage

```bash
ai-rules-generator context --project-root /path/to/repo
ai-rules-generator context --write-graph --emit-cursor-rules
ai-rules-generator context show bootstrap
ai-rules-generator context for agent/autocommit-all.sh
```

Writes `.ai-context/CODEBASE.md` and patches `AGENTS.md` between
`<!-- codebase-context:begin/end -->` markers only.

## Queries

Tag queries live in `ai_rules_generator/queries/` (see `NOTICE`). Inputs are
symbol names and paths — never string literals, comments, or doc text.
Excluded: `vendor/`, `node_modules/`, and rollout-exclude path patterns.

## License

MIT. Vendored `*-tags.scm` from Aider: Apache-2.0 (see `queries/NOTICE`).
