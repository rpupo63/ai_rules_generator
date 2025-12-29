"""
Configuration management for AI Rules Generator.
Handles loading and saving user preferences including AI model selection.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class UserConfig:
    """User configuration preferences"""
    ai_provider: str = "openai"  # openai, anthropic, or none
    ai_model: str = "gpt-4o-mini"  # Model name
    openai_api_key: Optional[str] = None  # Optional: OpenAI API key
    anthropic_api_key: Optional[str] = None  # Optional: Anthropic API key
    enabled_tools: List[str] = None  # List of enabled AI coding tools

    def __post_init__(self):
        """Set default enabled tools if not provided"""
        if self.enabled_tools is None:
            self.enabled_tools = ["cursor", "claude-code"]  # Default to most popular

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        """Create from dictionary"""
        return cls(
            ai_provider=data.get('ai_provider', 'openai'),
            ai_model=data.get('ai_model', 'gpt-4o-mini'),
            openai_api_key=data.get('openai_api_key'),
            anthropic_api_key=data.get('anthropic_api_key'),
            enabled_tools=data.get('enabled_tools', ["cursor", "claude-code"])
        )


def get_config_path() -> Path:
    """Get the path to the user config file"""
    import sys
    import os

    # Use platform-appropriate config directory
    if sys.platform == 'win32':
        # Windows: Use APPDATA
        appdata = os.getenv('APPDATA')
        if appdata:
            config_dir = Path(appdata) / 'ai-rules-generator'
        else:
            config_dir = Path.home() / 'AppData' / 'Roaming' / 'ai-rules-generator'
    elif sys.platform == 'darwin':
        # macOS: Use ~/Library/Application Support
        config_dir = Path.home() / 'Library' / 'Application Support' / 'ai-rules-generator'
    else:
        # Linux/Unix: Use XDG_CONFIG_HOME or ~/.config
        xdg_config = os.getenv('XDG_CONFIG_HOME')
        if xdg_config:
            config_dir = Path(xdg_config) / 'ai-rules-generator'
        else:
            config_dir = Path.home() / '.config' / 'ai-rules-generator'

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'


def load_user_config() -> Optional[UserConfig]:
    """Load user configuration from file"""
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        return UserConfig.from_dict(data)
    except Exception as e:
        print(f"Warning: Failed to load config: {e}")
        return None


def save_user_config(config: UserConfig) -> None:
    """Save user configuration to file"""
    config_path = get_config_path()

    try:
        with open(config_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        print(f"Configuration saved to {config_path}")
    except Exception as e:
        print(f"Warning: Failed to save config: {e}")


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """Get available AI providers and their models"""
    return {
        'openai': {
            'name': 'OpenAI',
            'env_var': 'OPENAI_API_KEY',
            'models': [
                'gpt-4o',
                'gpt-4o-mini',
                'gpt-4-turbo',
                'gpt-4',
                'gpt-3.5-turbo'
            ]
        },
        'anthropic': {
            'name': 'Anthropic Claude',
            'env_var': 'ANTHROPIC_API_KEY',
            'models': [
                'claude-3-5-sonnet-20241022',
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ]
        },
        'none': {
            'name': 'None (Template-based only)',
            'env_var': None,
            'models': ['template']
        }
    }


def get_provider_display_name(provider_key: str) -> str:
    """Get display name for provider"""
    providers = get_available_providers()
    return providers.get(provider_key, {}).get('name', provider_key)


def get_provider_models(provider_key: str) -> list:
    """Get available models for a provider"""
    providers = get_available_providers()
    return providers.get(provider_key, {}).get('models', [])


def get_available_tools() -> Dict[str, Dict[str, str]]:
    """Get available AI coding tools and their file locations"""
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
    """Get display name for a tool"""
    tools = get_available_tools()
    return tools.get(tool_key, {}).get('name', tool_key)


def display_config(config: UserConfig, show_keys: bool = False) -> None:
    """Display configuration in a readable format. Max 35 lines."""
    print()
    print("=" * 60)
    print("Current Configuration")
    print("=" * 60)
    print()
    print(f"AI Provider: {get_provider_display_name(config.ai_provider)}")
    print(f"AI Model: {config.ai_model}")
    print()

    # Enabled Tools
    tools = get_available_tools()
    enabled_tool_names = [get_tool_display_name(tool) for tool in config.enabled_tools]
    print(f"Enabled AI Coding Tools: {', '.join(enabled_tool_names) if enabled_tool_names else 'None'}")
    print()

    # API Keys
    print("API Keys:")
    if config.openai_api_key:
        if show_keys:
            print(f"  OpenAI: {config.openai_api_key}")
        else:
            print(f"  OpenAI: {'*' * 10}{config.openai_api_key[-4:]}")
    else:
        print("  OpenAI: Not set (using environment variable)")

    if config.anthropic_api_key:
        if show_keys:
            print(f"  Anthropic: {config.anthropic_api_key}")
        else:
            print(f"  Anthropic: {'*' * 10}{config.anthropic_api_key[-4:]}")
    else:
        print("  Anthropic: Not set (using environment variable)")

    print()
    print(f"Config file: {get_config_path()}")
    print("=" * 60)
    print()


def reset_config() -> None:
    """Reset configuration to defaults. Max 10 lines."""
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()
        print("Configuration reset to defaults.")
    else:
        print("No configuration file found. Already using defaults.")


def mask_api_key(key: str) -> str:
    """Mask API key for display. Max 5 lines."""
    if not key or len(key) < 8:
        return "****"
    return f"{'*' * 10}{key[-4:]}"
