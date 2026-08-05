---
name: context-for
description: >-
  Load a path-scoped edit pack before changing nested or unfamiliar files.
  Use when editing deep paths in a repo with ai-rules-generator / .ai-context,
  or when the user asks for blast-radius / neighborhood context.
---

# context for — edit packs

## When

Before editing nested or unfamiliar paths in a repo that has:

- `ai-rules-generator` available, and/or
- `.ai-context/` (or an `AGENTS.md` constitution)

Skip for trivial one-line edits in a file you already fully understand.

## Do

1. Identify the file(s) you are about to change.
2. Run:

```bash
ai-rules-generator context for <path> [<path>...] --budget 2500
```

3. Read the stdout pack. Weight sections in this order:
   - **Used by** + **AGENTS contracts** — highest trust (blast radius + law)
   - Ancestor folders / purposes — orientation
   - **Calls / Neighborhood** — hints only (regex graph; can miss or over-link)
4. Then edit. Prefer respecting Used-by consumers and AGENTS contracts.
5. If the pack says call graph is weak for this language, run search (`rg` / IDE refs) before assuming no deps.

Optional: `--write` stores under `.ai-context/edits/`; `--json` for structured output.

## Notes

- First run on a dirty tree is cold (AST scan). Later runs with unchanged sources are warm (fingerprint cache) and should be sub-second.
- Do **not** treat `.ai-context/practices/` or awesome-cursorrules dumps as repo law.
- Constitution stays in `AGENTS.md`; the pack is complementary blast-radius context only.
- Calls are demoted/deduped high-fan-in helpers; absence of an edge ≠ absence of a dependency.
