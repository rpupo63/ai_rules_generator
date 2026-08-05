"""
Configuration management for AI Rules Generator.

This module delegates to ai_model_picker for core configuration while
maintaining app-specific features like enabled tools selection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

# Re-export from ai_model_picker for backwards compatibility
from ai_model_picker import (
    get_config_path as _get_config_path,
    get_available_providers,
    get_provider_display_name,
    get_provider_models,
    get_provider_env_var,
    get_api_key as _get_api_key,
    set_api_key as _set_api_key,
    get_all_api_keys as _get_all_api_keys,
    get_api_key_with_fallback,
    get_default_provider as _get_default_provider,
    get_default_model as _get_default_model,
    set_default_provider as _set_default_provider,
    set_default_model as _set_default_model,
    get_model_api_id,
    load_config as _load_config,
    save_config as _save_config,
    reset_config as _reset_config,
    display_config as _display_config,
    setup_wizard as _base_setup_wizard,
    build_preference,
    load_preference as _load_preference,
    save_preference as _save_preference,
    ModelPreference,
)
from ai_model_picker.setup import mask_api_key
from ai_model_picker.types import UserConfig as BaseUserConfig

# App-specific config name
APP_NAME = "ai-rules-generator"


@dataclass
class UserConfig:
    """User configuration preferences (backwards compatible).

    API keys live in ``api_keys`` (all providers). Legacy
    ``openai_api_key`` / ``anthropic_api_key`` properties remain for callers.
    """

    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    api_keys: Dict[str, str] = field(default_factory=dict)
    enabled_tools: List[str] = None
    instructions: str = ""

    def __post_init__(self):
        """Set default enabled tools if not provided."""
        if self.enabled_tools is None:
            self.enabled_tools = ["cursor", "claude-code"]
        if self.api_keys is None:
            self.api_keys = {}

    @property
    def openai_api_key(self) -> Optional[str]:
        return self.api_keys.get("openai")

    @openai_api_key.setter
    def openai_api_key(self, value: Optional[str]) -> None:
        if value:
            self.api_keys["openai"] = value
        else:
            self.api_keys.pop("openai", None)

    @property
    def anthropic_api_key(self) -> Optional[str]:
        return self.api_keys.get("anthropic")

    @anthropic_api_key.setter
    def anthropic_api_key(self, value: Optional[str]) -> None:
        if value:
            self.api_keys["anthropic"] = value
        else:
            self.api_keys.pop("anthropic", None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (includes legacy key aliases)."""
        data = asdict(self)
        data["openai_api_key"] = self.openai_api_key
        data["anthropic_api_key"] = self.anthropic_api_key
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConfig":
        """Create from dictionary (supports legacy openai/anthropic fields)."""
        api_keys = dict(data.get("api_keys") or {})
        if data.get("openai_api_key"):
            api_keys["openai"] = data["openai_api_key"]
        if data.get("anthropic_api_key"):
            api_keys["anthropic"] = data["anthropic_api_key"]
        return cls(
            ai_provider=data.get("ai_provider", data.get("provider", "openai")),
            ai_model=data.get("ai_model", data.get("model", "gpt-4o-mini")),
            api_keys=api_keys,
            enabled_tools=data.get("enabled_tools", ["cursor", "claude-code"]),
            instructions=data.get("instructions") or "",
        )


def get_config_path() -> Path:
    """Get the path to the user config file."""
    return _get_config_path(APP_NAME)


def _load_local_config() -> dict:
    """Load raw config from file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_local_config(data: dict) -> None:
    """Save raw config to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)


def get_preference() -> ModelPreference:
    """Load secrets-free preference handoff for this app."""
    return _load_preference(APP_NAME)


def sync_preference(config: UserConfig) -> None:
    """Write preference.json from the current UserConfig (no API keys)."""
    pref = build_preference(
        provider=config.ai_provider,
        model=config.ai_model,
        instructions=config.instructions or "",
        app_name=APP_NAME,
    )
    _save_preference(pref, APP_NAME)


def load_user_config() -> Optional[UserConfig]:
    """Load user configuration from file."""
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        data = _load_local_config()
        base_config = _load_config(APP_NAME)
        api_keys = dict(base_config.api_keys or {})
        # Legacy fields in the same JSON
        if data.get("openai_api_key"):
            api_keys["openai"] = data["openai_api_key"]
        if data.get("anthropic_api_key"):
            api_keys["anthropic"] = data["anthropic_api_key"]

        pref = _load_preference(APP_NAME)
        instructions = pref.instructions or data.get("instructions") or base_config.instructions or ""

        return UserConfig(
            ai_provider=base_config.provider,
            ai_model=base_config.model,
            api_keys=api_keys,
            enabled_tools=data.get("enabled_tools", ["cursor", "claude-code"]),
            instructions=instructions,
        )
    except Exception as e:
        print(f"Warning: Failed to load config: {e}")
        return None


def save_user_config(config: UserConfig) -> None:
    """Save user configuration to file and sync preference handoff."""
    base_config = _load_config(APP_NAME)

    base_config.provider = config.ai_provider
    base_config.model = config.ai_model
    base_config.instructions = config.instructions or ""
    # Merge all provider keys from UserConfig
    for provider_key, key_value in (config.api_keys or {}).items():
        if key_value:
            base_config.api_keys[provider_key] = key_value

    _save_config(base_config, APP_NAME)

    local_config = _load_local_config()
    local_config["enabled_tools"] = config.enabled_tools
    local_config["instructions"] = config.instructions or ""
    # Keep legacy aliases populated for older readers
    if config.openai_api_key:
        local_config["openai_api_key"] = config.openai_api_key
    if config.anthropic_api_key:
        local_config["anthropic_api_key"] = config.anthropic_api_key
    _save_local_config(local_config)

    sync_preference(config)

    print(f"Configuration saved to {get_config_path()}")


def get_config_set_keys() -> List[str]:
    """Valid keys for 'config set <key> <value>'."""
    return [
        "provider",
        "model",
        "instructions",
        "api-key",
        "openai-key",
        "anthropic-key",
        "enabled-tools",
    ]


# ---------------------------------------------------------------------------
# Tool capability registry (AGENTS.md hub model)
# ---------------------------------------------------------------------------
#
# Every tool "meets in the middle" at the canonical AGENTS.md + .ai-rules/.
# Capabilities drive how the generator routes each tool to that source:
#
#   reads_agents_md : tool natively auto-loads a root AGENTS.md.  In symlink
#                     mode these tools need NO generated file at all.
#   entry           : the tool's own discovery path that must point at
#                     AGENTS.md (symlink / import / copy).  None = native only.
#   skills_link     : (target_dir, canonical_dir) symlinked so the tool's
#                     native skills folder resolves to .ai-rules/skills.
#   glob_rules      : tool consumes .cursor/rules/<folder>.mdc Tier-2 files
#                     (glob-scoped auto-attach - the one thing AGENTS.md lacks).
#
# `files` is retained purely for human-facing display / back-compat.

_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "cursor": {
        "name": "Cursor",
        "reads_agents_md": True,
        "entry": None,
        "skills_link": None,
        "glob_rules": True,
        "files": ["AGENTS.md", ".cursor/rules/*.mdc"],
    },
    "claude-code": {
        "name": "Claude Code",
        "reads_agents_md": False,
        "entry": "CLAUDE.md",
        "skills_link": (".claude/skills", ".ai-rules/skills"),
        "glob_rules": False,
        "files": ["CLAUDE.md", ".claude/skills/"],
    },
    "codex": {
        "name": "OpenAI Codex",
        "reads_agents_md": True,
        "entry": None,
        "skills_link": None,
        "glob_rules": False,
        "files": ["AGENTS.md"],
    },
    "copilot": {
        "name": "GitHub Copilot",
        # Copilot reads AGENTS.md, but its PR-review feature reads the
        # .github file, so we still point that path at AGENTS.md.
        "reads_agents_md": True,
        "entry": ".github/copilot-instructions.md",
        "skills_link": None,
        "glob_rules": False,
        "files": ["AGENTS.md", ".github/copilot-instructions.md"],
    },
    "windsurf": {
        "name": "Windsurf",
        "reads_agents_md": True,
        "entry": None,
        "skills_link": None,
        "glob_rules": False,
        "files": ["AGENTS.md", ".windsurfrules"],
    },
    "warp": {
        "name": "Warp",
        "reads_agents_md": True,
        "entry": None,
        "skills_link": None,
        "glob_rules": False,
        "files": ["AGENTS.md"],
    },
    "devin": {
        "name": "Devin",
        "reads_agents_md": True,
        "entry": None,
        "skills_link": None,
        "glob_rules": False,
        "files": ["AGENTS.md"],
    },
    "gemini": {
        "name": "Gemini CLI",
        # Gemini CLI uses GEMINI.md, not AGENTS.md - point it via symlink.
        "reads_agents_md": False,
        "entry": "GEMINI.md",
        "skills_link": None,
        "glob_rules": False,
        "files": ["GEMINI.md"],
    },
    "janie": {
        "name": "Janie",
        "reads_agents_md": False,
        "entry": ".janie/rules.md",
        "skills_link": None,
        "glob_rules": False,
        "files": [".janie/rules.md"],
    },
}


def get_available_tools() -> Dict[str, Dict[str, Any]]:
    """Get available AI coding tools and their capability metadata."""
    return _TOOL_REGISTRY


def get_tool_capabilities(tool_key: str) -> Dict[str, Any]:
    """Return the capability dict for a single tool (empty dict if unknown)."""
    return _TOOL_REGISTRY.get(tool_key, {})


def get_tool_display_name(tool_key: str) -> str:
    """Get display name for a tool."""
    return _TOOL_REGISTRY.get(tool_key, {}).get('name', tool_key)


def display_config(config: UserConfig, show_keys: bool = False) -> None:
    """Display configuration in a readable format (logic aligned with model_picker)."""
    print()
    print("=" * 60)
    print("Current Configuration")
    print("=" * 60)
    print()
    print(f"AI Provider: {get_provider_display_name(config.ai_provider)}")
    print(f"AI Model: {config.ai_model}")
    if config.instructions:
        preview = config.instructions.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        print(f"Instructions: {preview}")
    print()

    # Enabled Tools (app-specific)
    enabled_tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
    print(f"Enabled AI Coding Tools: {', '.join(enabled_tool_names) if enabled_tool_names else 'None'}")
    print()

    # API Keys: show all providers from model_picker
    base_config = _load_config(APP_NAME)
    providers = get_available_providers()
    print("API Keys:")
    for provider_key in providers:
        if provider_key == "none":
            continue
        key = base_config.api_keys.get(provider_key) or config.api_keys.get(provider_key)
        display_name = get_provider_display_name(provider_key)
        env_var = get_provider_env_var(provider_key)
        if key:
            if show_keys:
                print(f"  {display_name}: {key}")
            else:
                print(f"  {display_name}: {mask_api_key(key)}")
        else:
            env_hint = f" (using ${env_var})" if env_var else ""
            print(f"  {display_name}: Not set{env_hint}")

    print()
    print(f"Config file: {get_config_path()}")
    print("=" * 60)
    print()


def reset_config() -> None:
    """Reset configuration to defaults."""
    _reset_config(APP_NAME)
    print("Configuration reset to defaults.")
