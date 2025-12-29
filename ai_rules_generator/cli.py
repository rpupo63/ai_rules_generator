"""
CLI interface and interactive configuration for AI rules generator.
"""

import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .models import ProjectConfig, get_available_languages, get_available_frameworks
from .config_manager import (
    get_available_providers,
    get_provider_display_name,
    get_provider_models,
    get_available_tools,
    get_tool_display_name
)

# Try to import getch for better input handling, fallback to input() if not available
try:
    import termios
    import tty

    def _getch():
        """Get a single character from stdin"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    HAS_GETCH = True
except ImportError:
    HAS_GETCH = False


@dataclass
class SelectionState:
    """State for multi-selection interface"""
    selected: List[str]
    remaining: List[str]
    query: str = ""


def _filter_options(options: List[str], query: str) -> List[str]:
    """Filter options by substring match (case-insensitive). Max 10 lines."""
    if not query:
        return options
    query_lower = query.lower()
    return [opt for opt in options if query_lower in opt.lower()]


def _display_filtered_options(options: List[str], query: str = "", title: str = "Options") -> List[str]:
    """Display filtered options with numbering. Max 25 lines."""
    filtered = _filter_options(options, query)

    print(f"\n{title}:")
    if query:
        print(f"  Search: '{query}' → {len(filtered)}/{len(options)} matches")
    else:
        print(f"  Showing all {len(filtered)} options")
    print()

    if not filtered:
        print("  ❌ No matches found. Try a different search term.")
        return filtered

    # Show up to 25 options for better visibility
    display_count = min(len(filtered), 25)
    for i, option in enumerate(filtered[:display_count], 1):
        display_name = option.replace('-', ' ').title()
        print(f"  {i:2}. {display_name}")

    if len(filtered) > display_count:
        print(f"  ... and {len(filtered) - display_count} more (type more to narrow down)")

    return filtered


def _parse_numeric_selection(user_input: str, filtered: List[str]) -> Optional[str]:
    """Parse numeric selection input. Max 20 lines."""
    try:
        num = int(user_input)
        max_valid = min(len(filtered), 25)
        if 1 <= num <= max_valid:
            return filtered[num - 1]
        else:
            print(f"  ⚠️  Invalid number. Please enter 1-{max_valid}")
            return None
    except ValueError:
        return None


def _select_from_options(options: List[str], prompt: str = "Select") -> Optional[str]:
    """Interactive searchable selection from a list of options. Max 35 lines."""
    query = ""
    filtered = options.copy()

    while True:
        filtered = _display_filtered_options(options, query, prompt)

        if not filtered:
            print("\n  💡 Type to search, or Ctrl+C to cancel")
        else:
            max_num = min(len(filtered), 25)
            print(f"\n  💡 Type to search, Enter to select #1, or number (1-{max_num}) to select:")

        user_input = input("  > ").strip()

        if not user_input:
            # Enter pressed - select first match
            if filtered:
                selected = filtered[0]
                print(f"\n  ✓ Selected: {selected.replace('-', ' ').title()}\n")
                return selected
            else:
                print("  ⚠️  No selection available. Please type to filter.")
                continue

        # Try parsing as number
        choice = _parse_numeric_selection(user_input, filtered)
        if choice:
            print(f"\n  ✓ Selected: {choice.replace('-', ' ').title()}\n")
            return choice

        # Not a number, treat as search query
        query = user_input
        filtered = _filter_options(options, query)

        # If exactly one match, auto-select it
        if len(filtered) == 1:
            selected = filtered[0]
            print(f"\n  ✓ Auto-selected: {selected.replace('-', ' ').title()}\n")
            return selected


def format_selected_items(selected: List[str], max_display: int = 5) -> str:
    """Format selected items for display. Max 10 lines."""
    displayed = [s.replace('-', ' ').title() for s in selected[:max_display]]
    result = ', '.join(displayed)

    if len(selected) > max_display:
        result += f" ... (+{len(selected) - max_display} more)"

    return result


def _display_selection_state(
    filtered: List[str],
    state: SelectionState,
    prompt: str
) -> None:
    """Display current selection state. Max 20 lines."""
    _display_filtered_options(
        state.remaining,
        state.query,
        f"{prompt} (selected: {len(state.selected)})"
    )

    if state.selected:
        selected_display = format_selected_items(state.selected)
        print(f"\n  ✓ Selected: {selected_display}")

    if not filtered:
        print("\n  💡 Type to search, 'done' to finish, or 'clear' to start over")
    else:
        max_num = min(len(filtered), 25)
        print(f"\n  💡 Type to search, Enter to select #1, number (1-{max_num}) to select, 'done' to finish:")


def _add_to_selection(state: SelectionState, choice: str) -> None:
    """Add choice to selection if not duplicate. Max 15 lines."""
    if choice not in state.selected:
        state.selected.append(choice)
        state.remaining.remove(choice)
        print(f"  ✓ Added: {choice.replace('-', ' ').title()}\n")
    else:
        print(f"  ⚠️  Already selected: {choice.replace('-', ' ').title()}\n")


def _parse_selection_input(
    user_input: str,
    filtered: List[str]
) -> Optional[str]:
    """Parse user input into a selection choice. Max 30 lines."""
    if not user_input:
        # Enter pressed - select first match
        return filtered[0] if filtered else None

    # Try parsing as number
    choice = _parse_numeric_selection(user_input, filtered)
    if choice:
        return choice

    # Treat as search query - auto-select if exactly one match
    new_filtered = _filter_options(filtered, user_input)
    if len(new_filtered) == 1:
        print(f"  ✓ Auto-selected: {new_filtered[0].replace('-', ' ').title()}\n")
        return new_filtered[0]

    return None


def _get_user_selection_action(
    state: SelectionState,
    filtered: List[str]
) -> str:
    """Get and process user selection action. Max 35 lines."""
    user_input = input("  > ").strip()
    user_input_lower = user_input.lower()

    # Handle special commands
    if user_input_lower == 'done':
        if state.selected:
            print(f"\n  ✓ Final selection ({len(state.selected)}): {format_selected_items(state.selected)}\n")
            return "done"
        else:
            print("  ⚠️  No selections made. Type 'done' again to skip, or select frameworks.")
            return "continue"

    if user_input_lower == 'clear':
        print("  ✓ Selection cleared.\n")
        return "clear"

    # Handle selection
    choice = _parse_selection_input(user_input, filtered)
    if choice:
        _add_to_selection(state, choice)

    return "continue"


def _select_multiple_from_options(
    options: List[str], 
    prompt: str = "Select",
    default_selected: Optional[List[str]] = None
) -> List[str]:
    """Interactive searchable multi-selection from options. Max 25 lines."""
    if default_selected is None:
        default_selected = []
    
    # Start with default selections if provided
    selected = [opt for opt in default_selected if opt in options]
    remaining = [opt for opt in options if opt not in selected]
    
    state = SelectionState(selected=selected, remaining=remaining)

    while True:
        state.query = ""

        while True:
            filtered = _filter_options(state.remaining, state.query)
            _display_selection_state(filtered, state, prompt)

            action = _get_user_selection_action(state, filtered)

            if action == "done":
                return state.selected
            elif action == "clear":
                state = SelectionState(selected=[], remaining=options.copy())
                break
            elif action == "continue":
                break


def select_ai_provider() -> str:
    """Select AI provider. Max 20 lines."""
    providers = get_available_providers()
    provider_options = []

    for key, info in providers.items():
        provider_options.append(key)

    print("\n" + "=" * 60)
    selected = _select_from_options(provider_options, "Select AI Provider")
    if not selected:
        print("Error: Provider selection required")
        sys.exit(1)

    return selected


def select_ai_model(provider: str) -> str:
    """Select AI model for the chosen provider. Max 20 lines."""
    models = get_provider_models(provider)

    if provider == "none":
        return "template"

    print("\n" + "=" * 60)
    selected = _select_from_options(models, f"Select Model for {get_provider_display_name(provider)}")
    if not selected:
        print("Error: Model selection required")
        sys.exit(1)

    return selected


def interactive_config() -> ProjectConfig:
    """Interactively collect project configuration. Max 45 lines."""
    print("=" * 60)
    print("AI Rules Generator")
    print("=" * 60)
    print()

    # Project description
    print("Enter project description (what does this project do?):")
    description = input("> ").strip()
    while not description:
        print("Description cannot be empty. Please enter a description:")
        description = input("> ").strip()

    # Monorepo
    print("\nIs this a monorepo? (y/n):")
    monorepo_input = input("> ").strip().lower()
    is_monorepo = monorepo_input in ['y', 'yes', 'true', '1']

    # Primary language - searchable dropdown
    languages = get_available_languages()
    print("\n" + "=" * 60)
    primary_language = _select_from_options(languages, "Select Primary Language")
    if not primary_language:
        print("Error: Language selection required")
        sys.exit(1)

    # Frameworks - searchable multi-select dropdown
    frameworks = []
    available_frameworks = get_available_frameworks(primary_language)
    if available_frameworks:
        print("=" * 60)
        frameworks = _select_multiple_from_options(
            available_frameworks,
            f"Select Frameworks for {primary_language.title()}"
        )
    else:
        print(f"\nNo specific frameworks available for {primary_language}")

    # Output file
    print("\nOutput file name (default: .cursorrules):")
    output_file = input("> ").strip()
    if not output_file:
        output_file = ".cursorrules"

    return ProjectConfig(
        description=description,
        is_monorepo=is_monorepo,
        primary_language=primary_language,
        frameworks=frameworks,
        output_file=output_file
    )
