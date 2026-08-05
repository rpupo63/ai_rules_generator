"""Config subcommands — tool preferences only (no model/provider surface)."""

from __future__ import annotations

from .config_manager import (
    UserConfig,
    display_config,
    get_config_set_keys,
    load_user_config,
    reset_config,
    save_user_config,
)


def cmd_config_show(args) -> None:
    display_config()


def cmd_config_edit(args) -> None:
    cfg = load_user_config() or UserConfig()
    print("Current enabled tools:", ", ".join(cfg.enabled_tools))
    raw = input("enabled-tools (comma-separated, Enter to keep): ").strip()
    if raw:
        cfg.enabled_tools = [t.strip() for t in raw.split(",") if t.strip()]
    note = input("instructions (Enter to keep): ").strip()
    if note:
        cfg.instructions = note
    save_user_config(cfg)
    print("Saved.")


def cmd_config_set(args) -> None:
    cfg = load_user_config() or UserConfig()
    key = args.key
    value = args.value
    if key == "enabled-tools":
        cfg.enabled_tools = [t.strip() for t in value.split(",") if t.strip()]
    elif key == "instructions":
        cfg.instructions = value
    else:
        raise ValueError(
            f"Unknown key {key!r}. Allowed: {', '.join(get_config_set_keys())}"
        )
    save_user_config(cfg)
    print(f"Set {key}.")


def cmd_config_reset(args) -> None:
    reset_config()
    print("Config reset.")
