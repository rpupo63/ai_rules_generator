# AI Rules Generator

**Edit-scoped context for agents**: give an LLM the parent-folder roles, blast-radius neighborhood, and matched `AGENTS.md` contracts for the path it is about to change—without dumping the whole repo or overwriting your constitution.

Primary agent affordance is `context for <path>`. Always-on `.ai-context/CODEBASE.md` stays a thin orientation card (entrypoints + evidenced conventions when `AGENTS.md` is already rich). Cursor/Claude rule emitters remain behind `--legacy-rules` / `--emit-cursor-rules`.

## Features

- **Edit packs**: `context for <path>` — ancestors + call/used-by neighborhood + AGENTS topic slices under a token budget
- **Complementary always-on pack**: `.ai-context/CODEBASE.md`; never rewrites user `AGENTS.md` body outside a delimited pointer
- **Constitution-aware**: thin CODEBASE when purpose/architecture/commands already live in `AGENTS.md`
- **Polyglot evidence**: multi-stack detection (Go, TS, Python, Godot, Compose/ops, shell) including Go frameworks from `go.mod`
- **Deterministic by default**: AST + graph ranking without API keys; optional `--ai` folder enrichment
- **Legacy rules path**: `--legacy-rules` still emits full AGENTS.md + `.ai-rules/skills` + tool symlinks
- **Optional Cursor Tier-2**: `--emit-cursor-rules` for glob-scoped `.mdc`

## Quick Start

### 1. Install

Choose your preferred package manager:

**macOS (Homebrew):**

```bash
brew tap rpupo63/ai-rules-generator
brew install ai-rules-generator
```

**Arch Linux (AUR):**

```bash
yay -S ai-rules-generator
```

**Debian/Ubuntu (APT):**

```bash
sudo apt install ai-rules-generator
```

**Linux (Flatpak):**

```bash
flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator
```

**Windows (WinGet):**

```powershell
winget install AIRulesGenerator.AIRulesGenerator
```

**Any Platform (pip):**

```bash
pip install ai-rules-generator
```

### 2. Configure (One-Time Setup)

Run the interactive setup:

```bash
ai-rules-generator init
```

This will:

- Let you choose your AI provider (OpenAI, Anthropic, or None)
- Let you select a model
- Store your API keys securely in the config file
- Let you choose which AI coding tools you use

**No need to modify .bashrc, .zshrc, or PowerShell profile!** Everything is stored in:

- **Linux**: `~/.config/ai-rules-generator/config.json`
- **macOS**: `~/Library/Application Support/ai-rules-generator/config.json`
- **Windows**: `%APPDATA%\ai-rules-generator\config.json`

### 3. Edit pack before changing a deep file (recommended for agents)

```bash
ai-rules-generator context for backend/seed/04_classes/foo.go --budget 2500
# multiple paths:
ai-rules-generator context for backend/api/handlers.go frontend/src/lib/api.ts
# optional: JSON + write under .ai-context/edits/
ai-rules-generator context for backend/api/handlers.go --json --write
```

An edit pack includes (budgeted, highest priority kept first):

1. Matched `AGENTS.md` contract slices (architecture / gotchas / seed / …)
2. Ancestor folder one-liners (`backend/` → `backend/seed/` → …)
3. Inbound **Used by** (blast radius) and outbound calls/deps from the AST graph
4. Local symbols; evidenced conventions when not already in AGENTS

**Agent pattern:** before editing unfamiliar nested paths, run `context for` on those paths and load the markdown into the session. Skill: [`skills/context-for/SKILL.md`](skills/context-for/SKILL.md). Do not treat awesome-cursorrules practices as repo law.

Warm cache: after the first cold run, unchanged source trees reuse `.ai-context/cache/` + `graph.json` and skip AST scan (target &lt;1s). Local check:

```bash
./scripts/smoke_edit_pack.sh /path/to/repo backend/api/foo.go
```

### 4. Always-on orientation pack (optional)

```bash
ai-rules-generator context
# or: ai-rules-generator project-init
# or: ai-rules-generator update
```

Writes:

- `.ai-context/CODEBASE.md` — entrypoints + **Conventions**; full What/How/Why only when `AGENTS.md` is thin
- `.ai-context/modules/*.md` — surface-root digests (when not thin-skipped)
- `AGENTS.md` — delimited pointer (additive when thin; rewrites stale pointers to `context for` when rich)

**Conventions** are gleaned from the repo (not invented): git habits, tsconfig/eslint/zod, `.agent-sessions/`, Memory MCP, `.agents/permissions.json`.

Off by default (opt in):

- `--practices` → `.ai-context/practices/` from bundled awesome-cursorrules (generic; prefer edit packs)
- `--write-graph` → `.ai-context/graph/` sidecars (edit packs reuse `graph.json` when fresh)

Folder digests (no pack rewrite):

```bash
ai-rules-generator context show backend/api
ai-rules-generator context show backend/api --full   # skeleton + call-flow
```

Optional LLM folder overviews (importance-ranked, capped; not used by edit packs):

```bash
ai-rules-generator context --ai --ai-max-folders 12
```

Identity bootstrap stays with Sync `install-repo-identity.sh`.

Legacy full-rules generation:

```bash
ai-rules-generator project-init --legacy-rules
```

### 5. Generate Rules for Your Project (legacy docs below)

Navigate to your project and run:

```bash
cd /path/to/your/project
ai-rules-generator project-init
```

Done! Your project now has AI rules configured for all your selected AI coding tools.

## Installation Details

### Homebrew (macOS/Linux)

```bash
# Add the tap (first time only)
brew tap rpupo63/ai-rules-generator

# Install
brew install ai-rules-generator

# Update
brew upgrade ai-rules-generator
```

### AUR (Arch Linux)

```bash
# Using yay
yay -S ai-rules-generator

# Or using paru
paru -S ai-rules-generator

# Update
yay -Syu ai-rules-generator
```

### APT (Debian/Ubuntu)

```bash
# Add PPA (first time only)
sudo add-apt-repository ppa:rpupo63/ai-rules-generator
sudo apt update

# Install
sudo apt install ai-rules-generator

# Update
sudo apt update && sudo apt upgrade ai-rules-generator
```

Or install from .deb file:

```bash
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator_1.0.0-1_all.deb
sudo apt install ./ai-rules-generator_1.0.0-1_all.deb
```

### Flatpak (Linux - Universal)

```bash
# Install from Flathub
flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator

# Run
flatpak run com.github.ai_rules_generator.AIRulesGenerator

# Update
flatpak update com.github.ai_rules_generator.AIRulesGenerator
```

### winget (Windows)

```powershell
# Install
winget install AIRulesGenerator.AIRulesGenerator

# Update
winget upgrade AIRulesGenerator.AIRulesGenerator
```

### pip (All Platforms)

```bash
# Install from PyPI
pip install ai-rules-generator

# Install with AI provider support
pip install ai-rules-generator[all]        # Both OpenAI and Anthropic
pip install ai-rules-generator[openai]     # OpenAI only
pip install ai-rules-generator[anthropic]  # Anthropic only

# Update
pip install --upgrade ai-rules-generator

# Install from source (development)
git clone https://github.com/rpupo63/ai-rules-generator.git
cd ai-rules-generator
pip install -e .[all]
```

## Usage

### Available Commands

```bash
# Global configuration (one-time setup)
ai-rules-generator init              # Interactive setup
ai-rules-generator config show       # View current configuration
ai-rules-generator config edit       # Edit configuration
ai-rules-generator config reset      # Reset to defaults

# Project-level commands
ai-rules-generator project-init      # Initialize rules for current project
```

Or use the shorter alias:

```bash
ai-rules init
ai-rules project-init
```

### Configuration Management

The `init` command provides an interactive setup. You can also manage configuration manually:

```bash
# Set AI provider
ai-rules-generator config set provider openai

# Set AI model
ai-rules-generator config set model gpt-4o

# Set API keys
ai-rules-generator config set openai-key sk-...
ai-rules-generator config set anthropic-key sk-ant-...

# Set enabled tools (comma-separated)
ai-rules-generator config set enabled-tools cursor,claude-code,windsurf
```

### What Gets Generated

After running `project-init`, your project will have:

**Shared Rules (always created):**

- `.ai-rules/` - Directory with organized rule files
  - `project-rules.md` - Main project rules
  - `language-*.md` - Language-specific best practices
  - `framework-*.md` - Framework-specific rules
  - `universal-*.md` - Universal best practices
  - `README.md` - Index of all rule files

**Tool-Specific Files (based on your selection):**

- **Cursor**: `.cursorrules` + `.cursor/rules/*.mdc`
- **Claude Code**: `CLAUDE.md` + `.claude/rules/`
- **Windsurf**: `.windsurfrules`
- **GitHub Copilot**: `.github/copilot-instructions.md`
- **Warp**: `.warp/rules.md`
- **Janie**: `.janie/rules.md`

All tool files reference the shared `.ai-rules/` directory, keeping rules DRY and maintainable.

## Supported AI Coding Tools

The tool supports **6 AI coding tools**. During `init`, select which tools you use:

1. **Cursor** - `.cursorrules` + `.cursor/rules/*.mdc` files
2. **Claude Code** - `CLAUDE.md` + `.claude/rules/` directory
3. **Windsurf** - `.windsurfrules` file
4. **GitHub Copilot** - `.github/copilot-instructions.md`
5. **Warp** - `.warp/rules.md` file
6. **Janie** - `.janie/rules.md` file

To change which tools are enabled:

```bash
ai-rules-generator config edit
```

## Supported Languages

Python, TypeScript, JavaScript, Rust, C++, Java, Go, Kotlin, Swift, Elixir, PHP, Ruby, Scala, R, Solidity, HTML, CSS, and more.

## Supported Frameworks

100+ frameworks including:

- **Python**: FastAPI, Django, Flask, Temporal
- **TypeScript/JavaScript**: Next.js, React, Vue, Svelte, Angular, Astro, Node.js
- **And many more...**

During interactive mode, you'll see framework options specific to your selected language.

## AI Providers

### OpenAI

- gpt-4o (recommended)
- gpt-4o-mini (faster, cheaper)
- gpt-4-turbo
- gpt-4
- gpt-3.5-turbo

### Anthropic Claude

- claude-3-5-sonnet-20241022 (recommended)
- claude-3-5-haiku-20241022 (faster)
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

### None (Template-based)

Use template-based generation without AI API calls.

## API Key Management

API keys are stored securely in the config file. No need to manually edit environment variables!

### Storing API Keys

**Option 1: Interactive setup (recommended)**

```bash
ai-rules-generator init
# Enter API keys when prompted
```

**Option 2: Command line**

```bash
ai-rules-generator config set openai-key sk-...
ai-rules-generator config set anthropic-key sk-ant-...
```

**Option 3: Environment variables (optional)**

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
```

Environment variables take precedence if set, but the config file is more convenient.

### Security Note

- Config file is stored with user-only read/write permissions
- API keys are stored as plain text in the config file
- Both config file and environment variables have similar security profiles
- Use `--show-keys` flag cautiously when displaying configuration

## Examples

### Single Project Setup

```bash
# One-time global setup
ai-rules-generator init

# In your project
cd my-fastapi-project
ai-rules-generator project-init
```

### Monorepo Setup

```bash
# One-time global setup
ai-rules-generator init

# In your monorepo root
cd my-monorepo
ai-rules-generator project-init
# Automatically detects packages and creates rules for each
```

### Template-based (No API Key)

```bash
# Configure to use template mode
ai-rules-generator init
# Select: none -> template

# Generate rules without AI
cd my-project
ai-rules-generator project-init
```

## Configuration File

Your configuration is stored in a platform-appropriate location:

**Linux:**

```bash
~/.config/ai-rules-generator/config.json
```

**macOS:**

```bash
~/Library/Application Support/ai-rules-generator/config.json
```

**Windows:**

```powershell
%APPDATA%\ai-rules-generator\config.json
```

Example config:

```json
{
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini",
  "openai_api_key": "sk-...",
  "anthropic_api_key": null,
  "enabled_tools": ["cursor", "claude-code", "windsurf"]
}
```

## Troubleshooting

### Command not found after installation

Make sure your PATH includes the installation directory:

- **pip**: `~/.local/bin` (Linux/macOS) or `%APPDATA%\Python\Scripts` (Windows)
- **Homebrew**: `/usr/local/bin` (Intel) or `/opt/homebrew/bin` (Apple Silicon)

### Config file location

View your config path:

```bash
python -c "from ai_rules_generator.config_manager import get_config_path; print(get_config_path())"
```

### Reset configuration

```bash
ai-rules-generator config reset
ai-rules-generator init
```

## Contributing

Contributions welcome! Please read [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and publishing instructions.

### Publishing Scripts

Individual publish scripts are available for each package manager in the `scripts/` directory:

- **PyPI**: `./scripts/publish_pypi.sh [version]`
- **Homebrew**: `./scripts/publish_homebrew.sh [version]`
- **AUR**: `./scripts/publish_aur.sh [version]`
- **Debian/Ubuntu**: `./scripts/publish_debian.sh [version]`
- **Flatpak**: `./scripts/publish_flatpak.sh [version]`
- **WinGet**: `./scripts/publish_winget.sh [version]`

See [scripts/README.md](scripts/README.md) for detailed usage instructions. For full deployment workflow, see [PUBLISHING.md](PUBLISHING.md).

## License

MIT

## Credits

Built using best practices from [awesome-cursorrules](https://github.com/awesome-cursorrules/awesome-cursorrules).

## Links

- 📖 Documentation: This README
- 🐛 Issues: https://github.com/rpupo63/ai-rules-generator/issues
- 💬 Discussions: https://github.com/rpupo63/ai-rules-generator/discussions
- 📦 PyPI: https://pypi.org/project/ai-rules-generator/
- 🍺 Homebrew: `brew tap rpupo63/ai-rules-generator`
- 🐧 AUR: https://aur.archlinux.org/packages/ai-rules-generator
- 📦 Debian/Ubuntu PPA: `ppa:rpupo63/ai-rules-generator`
- 📦 Flatpak: https://flathub.org/apps/com.github.ai_rules_generator.AIRulesGenerator
- 🪟 winget: `winget install AIRulesGenerator.AIRulesGenerator`
