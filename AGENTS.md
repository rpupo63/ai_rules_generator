# ai_rules_generator

One-line purpose. Stack versions (language/framework). Deploy target if any.

## Commands

```bash
# build / test / run — fill in real commands
```

## Architecture

- Boundaries agents must respect (layers, dirs, do-not-touch).
- Key entrypoints.

## Where knowledge lives

- **Procedures** → skills (`~/.agents/skills`)
- **Project facts** → this file (`CLAUDE.md` → symlink)
- **Durable corrections** → Memory MCP (`user:beto`, `project:<github-slug>`)
- **Session handoffs** → `.agent-sessions/CURRENT.md`
- **Repo tool allows** → `.agents/permissions.json`
