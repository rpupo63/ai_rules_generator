"""
`context` command — structure-only codebase map (What/How/Why orientation).
"""

from __future__ import annotations

from .orchestration import generate_codebase_context, show_folder_context
from .paths import validate_and_resolve_paths


def cmd_context(args) -> None:
    """Generate lean `.ai-context/` orientation pack + conditional AGENTS pointer."""
    if getattr(args, "context_cmd", None) == "show":
        cmd_context_show(args)
        return
    if getattr(args, "context_cmd", None) == "for":
        cmd_context_for(args)
        return

    print("=" * 60)
    print("AI Rules Generator — Codebase Context")
    print("=" * 60)
    print()
    print("Structure-only ranked map (definitions / references).")
    print("No model calls. Does not overwrite AGENTS.md constitution.")
    print()

    _, project_root = validate_and_resolve_paths(args)

    enable_ast = not getattr(args, "no_ast", False)
    enable_graph = not getattr(args, "no_graph", False)
    dry_run = bool(getattr(args, "dry_run", False))
    emit_cursor = bool(getattr(args, "emit_cursor_rules", False))
    global_budget = int(getattr(args, "token_budget", 0) or 1_000_000)
    graph_token_budget = int(getattr(args, "graph_budget", 0) or 1000)
    write_graph = bool(getattr(args, "write_graph", False))

    print(f"  Project:     {project_root}")
    print(f"  Graph:       {'ON' if enable_graph else 'OFF'}")
    print(f"  Map budget:  {graph_token_budget} tokens")
    print(f"  Cursor rules:{'ON' if emit_cursor else 'OFF'}")
    print(f"  Dry run:     {dry_run}")
    print()

    result = generate_codebase_context(
        project_root,
        enable_ast=enable_ast,
        enable_graph=enable_graph,
        dry_run=dry_run,
        emit_cursor_rules=emit_cursor,
        global_budget=global_budget,
        graph_token_budget=graph_token_budget,
        write_graph=write_graph,
    )
    print(
        f"Done. files={result['files_scanned']} "
        f"symbols={result['symbols']} edges={result['edges']}"
    )


def cmd_context_show(args) -> None:
    _, project_root = validate_and_resolve_paths(args)
    text = show_folder_context(
        project_root,
        args.folder,
        full=bool(getattr(args, "full", False)),
        enable_ast=not getattr(args, "no_ast", False),
        enable_graph=not getattr(args, "no_graph", False),
    )
    print(text)


def cmd_context_for(args) -> None:
    """Alias: show context for a path (edit-pack path removed)."""
    _, project_root = validate_and_resolve_paths(args)
    path = getattr(args, "path", None) or getattr(args, "folder", None) or "."
    text = show_folder_context(
        project_root,
        str(path),
        full=True,
        enable_ast=not getattr(args, "no_ast", False),
        enable_graph=not getattr(args, "no_graph", False),
    )
    print(text)
