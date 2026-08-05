"""
Local tool preferences (no model / provider config).

Model routing belongs at the gateway (LiteLLM / Aperture). This package is
deterministic and must not carry vendor model names or API keys.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_NAME = "ai-rules-generator"

AVAILABLE_TOOLS: Dict[str, Dict[str, str]] = {
    "cursor": {"display": "Cursor"},
    "claude_code": {"display": "Claude Code"},
    "windsurf": {"display": "Windsurf"},
    "copilot": {"display": "GitHub Copilot"},
}


@dataclass
class UserConfig:
    """User preferences for tool emitters (not models)."""

    enabled_tools: List[str] = field(default_factory=lambda: ["cursor", "claude_code"])
    instructions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConfig":
        return cls(
            enabled_tools=list(
                data.get("enabled_tools") or ["cursor", "claude_code"]
            ),
            instructions=str(data.get("instructions") or ""),
        )


def get_config_path() -> Path:
    return Path.home() / ".config" / APP_NAME / "config.json"


def load_user_config() -> Optional[UserConfig]:
    path = get_config_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return UserConfig.from_dict(data)


def save_user_config(config: UserConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")


def get_available_tools() -> List[str]:
    return list(AVAILABLE_TOOLS.keys())


def get_tool_display_name(tool: str) -> str:
    return AVAILABLE_TOOLS.get(tool, {}).get("display", tool)


def get_config_set_keys() -> List[str]:
    return ["enabled-tools", "instructions"]


def display_config(config: Optional[UserConfig] = None) -> None:
    cfg = config or load_user_config() or UserConfig()
    print(f"enabled_tools: {', '.join(cfg.enabled_tools)}")
    print(f"instructions:  {cfg.instructions or '(none)'}")


def reset_config() -> None:
    path = get_config_path()
    if path.exists():
        path.unlink()
