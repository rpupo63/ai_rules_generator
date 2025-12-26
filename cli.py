"""
CLI interface and interactive configuration for AI rules generator.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
from models import ProjectConfig, get_available_languages, get_available_frameworks

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


def _filter_options(options: List[str], query: str) -> List[str]:
    """Filter options by substring match (case-insensitive)"""
    if not query:
        return options
    query_lower = query.lower()
    return [opt for opt in options if query_lower in opt.lower()]


def _display_filtered_options(options: List[str], query: str = "", title: str = "Options"):
    """Display filtered options with numbering"""
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


def _select_from_options(options: List[str], prompt: str = "Select") -> Optional[str]:
    """Interactive searchable selection from a list of options"""
    query = ""
    filtered = options.copy()
    
    while True:
        _display_filtered_options(options, query, prompt)
        
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
        
        # Check if it's a number
        try:
            num = int(user_input)
            max_valid = min(len(filtered), 25)
            if 1 <= num <= max_valid:
                selected = filtered[num - 1]
                print(f"\n  ✓ Selected: {selected.replace('-', ' ').title()}\n")
                return selected
            else:
                print(f"  ⚠️  Invalid number. Please enter 1-{max_valid}")
                continue
        except ValueError:
            # Not a number, treat as search query
            query = user_input
            filtered = _filter_options(options, query)
            
            # If exactly one match, auto-select it
            if len(filtered) == 1:
                selected = filtered[0]
                print(f"\n  ✓ Auto-selected: {selected.replace('-', ' ').title()}\n")
                return selected


def _select_multiple_from_options(options: List[str], prompt: str = "Select") -> List[str]:
    """Interactive searchable multi-selection from a list of options"""
    selected = []
    remaining = options.copy()
    
    while True:
        query = ""
        filtered = remaining.copy()
        
        while True:
            _display_filtered_options(remaining, query, f"{prompt} (selected: {len(selected)})")
            
            if selected:
                selected_display = ', '.join([s.replace('-', ' ').title() for s in selected[:5]])
                if len(selected) > 5:
                    selected_display += f" ... (+{len(selected) - 5} more)"
                print(f"\n  ✓ Selected: {selected_display}")
            
            if not filtered:
                print("\n  💡 Type to search, 'done' to finish, or 'clear' to start over")
            else:
                max_num = min(len(filtered), 25)
                print(f"\n  💡 Type to search, Enter to select #1, number (1-{max_num}) to select, 'done' to finish:")
            
            user_input = input("  > ").strip()
            user_input_lower = user_input.lower()
            
            if user_input_lower == 'done':
                if selected:
                    print(f"\n  ✓ Final selection ({len(selected)}): {', '.join([s.replace('-', ' ').title() for s in selected])}\n")
                    return selected
                else:
                    print("  ⚠️  No selections made. Type 'done' again to skip, or select frameworks.")
                    continue
            
            if user_input_lower == 'clear':
                selected = []
                remaining = options.copy()
                print("  ✓ Selection cleared.\n")
                break
            
            if not user_input:
                # Enter pressed - select first match
                if filtered:
                    choice = filtered[0]
                    if choice not in selected:
                        selected.append(choice)
                        remaining.remove(choice)
                        print(f"  ✓ Added: {choice.replace('-', ' ').title()}\n")
                    else:
                        print(f"  ⚠️  Already selected: {choice.replace('-', ' ').title()}\n")
                    break
                else:
                    print("  ⚠️  No selection available. Please type to filter.")
                    continue
            
            # Check if it's a number
            try:
                num = int(user_input)
                max_valid = min(len(filtered), 25)
                if 1 <= num <= max_valid:
                    choice = filtered[num - 1]
                    if choice not in selected:
                        selected.append(choice)
                        remaining.remove(choice)
                        print(f"  ✓ Added: {choice.replace('-', ' ').title()}\n")
                    else:
                        print(f"  ⚠️  Already selected: {choice.replace('-', ' ').title()}\n")
                    break
                else:
                    print(f"  ⚠️  Invalid number. Please enter 1-{max_valid}")
                    continue
            except ValueError:
                # Not a number, treat as search query
                query = user_input
                filtered = _filter_options(remaining, query)
                
                # If exactly one match, auto-select it
                if len(filtered) == 1:
                    choice = filtered[0]
                    if choice not in selected:
                        selected.append(choice)
                        remaining.remove(choice)
                        print(f"  ✓ Auto-selected: {choice.replace('-', ' ').title()}\n")
                        break
                    else:
                        print(f"  ⚠️  Already selected: {choice.replace('-', ' ').title()}\n")
                        break


def interactive_config() -> ProjectConfig:
    """Interactively collect project configuration"""
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

