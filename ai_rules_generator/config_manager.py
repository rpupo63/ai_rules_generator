"""
Configuration management for AI Rules Generator.

This module delegates to ai_model_picker for core configuration while
maintaining app-specific features like enabled tools selection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

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
)
from ai_model_picker.setup import mask_api_key
from ai_model_picker.types import UserConfig as BaseUserConfig

# App-specific config name
APP_NAME = "ai-rules-generator"


@dataclass
class UserConfig:
    """User configuration preferences (backwards compatible)."""
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    enabled_tools: List[str] = None

    def __post_init__(self):
        """Set default enabled tools if not provided."""
        if self.enabled_tools is None:
            self.enabled_tools = ["cursor", "claude-code"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        """Create from dictionary."""
        return cls(
            ai_provider=data.get('ai_provider', 'openai'),
            ai_model=data.get('ai_model', 'gpt-4o-mini'),
            openai_api_key=data.get('openai_api_key'),
            anthropic_api_key=data.get('anthropic_api_key'),
            enabled_tools=data.get('enabled_tools', ["cursor", "claude-code"])
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


def load_user_config() -> Optional[UserConfig]:
    """Load user configuration from file."""
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)

        # Map from ai_model_picker format to UserConfig
        base_config = _load_config(APP_NAME)

        return UserConfig(
            ai_provider=base_config.provider,
            ai_model=base_config.model,
            openai_api_key=base_config.api_keys.get('openai'),
            anthropic_api_key=base_config.api_keys.get('anthropic'),
            enabled_tools=data.get('enabled_tools', ["cursor", "claude-code"])
        )
    except Exception as e:
        print(f"Warning: Failed to load config: {e}")
        return None


def save_user_config(config: UserConfig) -> None:
    """Save user configuration to file."""
    # Load existing config from ai_model_picker
    base_config = _load_config(APP_NAME)

    # Update with UserConfig values
    base_config.provider = config.ai_provider
    base_config.model = config.ai_model

    if config.openai_api_key:
        base_config.api_keys['openai'] = config.openai_api_key
    if config.anthropic_api_key:
        base_config.api_keys['anthropic'] = config.anthropic_api_key

    # Save base config
    _save_config(base_config, APP_NAME)

    # Save app-specific fields separately (enabled_tools)
    local_config = _load_local_config()
    local_config['enabled_tools'] = config.enabled_tools
    _save_local_config(local_config)

    print(f"Configuration saved to {get_config_path()}")


def get_config_set_keys() -> List[str]:
    """Valid keys for 'config set <key> <value>'."""
    return ['provider', 'model', 'openai-key', 'anthropic-key', 'enabled-tools']


def get_available_tools() -> Dict[str, Dict[str, str]]:
    """Get available AI coding tools and their file locations."""
    return {
        "cursor": {
            "name": "Cursor",
            "files": [".cursorrules", ".cursor/rules/*.mdc"]
        },
        "claude-code": {
            "name": "Claude Code",
            "files": ["CLAUDE.md", ".claude/rules/"]
        },
        "windsurf": {
            "name": "Windsurf",
            "files": [".windsurfrules"]
        },
        "copilot": {
            "name": "GitHub Copilot",
            "files": [".github/copilot-instructions.md", ".copilot/instructions.md"]
        },
        "warp": {
            "name": "Warp",
            "files": [".warp/rules.md"]
        },
        "janie": {
            "name": "Janie",
            "files": [".janie/rules.md"]
        }
    }


def get_tool_display_name(tool_key: str) -> str:
    """Get display name for a tool."""
    tools = get_available_tools()
    return tools.get(tool_key, {}).get('name', tool_key)


def display_config(config: UserConfig, show_keys: bool = False) -> None:
    """Display configuration in a readable format (logic aligned with model_picker)."""
    print()
    print("=" * 60)
    print("Current Configuration")
    print("=" * 60)
    print()
    print(f"AI Provider: {get_provider_display_name(config.ai_provider)}")
    print(f"AI Model: {config.ai_model}")
    print()

    # Enabled Tools (app-specific)
    enabled_tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
    print(f"Enabled AI Coding Tools: {', '.join(enabled_tool_names) if enabled_tool_names else 'None'}")
    print()

    # API Keys: show all providers from model_picker (same as model_picker display_config)
    base_config = _load_config(APP_NAME)
    providers = get_available_providers()
    print("API Keys:")
    for provider_key in providers:
        if provider_key == "none":
            continue
        key = base_config.api_keys.get(provider_key)
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
