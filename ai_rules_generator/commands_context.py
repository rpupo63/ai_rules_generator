"""
`context` command — complementary What/How/Why codebase context provider.
"""

from __future__ import annotations

import os

from .config_manager import load_user_config, UserConfig
from .linker import LinkMode
from .edit_pack import assemble_edit_pack, write_edit_pack
from .orchestration import (
    generate_codebase_context,
    generate_monorepo_project_rules,
    generate_single_project_rules_setup,
    show_folder_context,
)
from .paths import validate_and_resolve_paths


def cmd_context(args) -> None:
    """Generate lean `.ai-context/` orientation pack + conditional AGENTS pointer."""
    # Subcommands are dispatched via their own defaults; guard if mis-routed.
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
    print("Lean orientation map (What / How / Why).")
    print("Does not overwrite AGENTS.md constitution — pointer only when additive.")
    print()

    _, project_root = validate_and_resolve_paths(args)

    use_ai = bool(getattr(args, "ai", False)) and not getattr(args, "no_ai", False)
    if getattr(args, "no_ai", False):
        use_ai = False

    user_config = load_user_config() or UserConfig()
    ai_provider = user_config.ai_provider if use_ai else "none"
    ai_model = user_config.ai_model if use_ai else "template"
    if use_ai and ai_provider != "none":
        from ai_model_picker import get_model_api_id
        resolved = get_model_api_id(ai_model, ai_provider, "ai-rules-generator")
        if resolved == ai_model and " " in ai_model:
            fallback = {
                "google": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            }.get(ai_provider)
            if fallback:
                print(f"  Note: model {ai_model!r} has no API id mapping; using {fallback!r}")
                ai_model = fallback
            else:
                ai_model = resolved
        else:
            ai_model = resolved
    openai_key = user_config.openai_api_key or os.getenv("OPENAI_API_KEY")
    anthropic_key = user_config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    enable_ast = not getattr(args, "no_ast", False)
    enable_graph = not getattr(args, "no_graph", False)
    dry_run = bool(getattr(args, "dry_run", False))
    emit_cursor = bool(getattr(args, "emit_cursor_rules", False))
    global_budget = int(getattr(args, "token_budget", 0) or 1_000_000)
    graph_token_budget = int(getattr(args, "graph_budget", 0) or 1000)
    ai_max_folders = int(getattr(args, "ai_max_folders", 12) or 12)
    write_graph = bool(getattr(args, "write_graph", False))
    write_modules = not bool(getattr(args, "no_modules", False))
    emit_practices_flag = bool(getattr(args, "practices", False))

    print(f"  Project:     {project_root}")
    print(f"  AST:         {'ON' if enable_ast else 'OFF'}")
    print(f"  Graph:       {'ON' if enable_graph else 'OFF'}"
          f"{' (write sidecars)' if write_graph else ' (rank only)'}")
    print(f"  Digests:     {'ON' if write_modules else 'OFF'}")
    print(f"  Practices:   {'ON' if emit_practices_flag else 'OFF'}")
    print(f"  AI enrich:   {'ON (' + ai_provider + '/' + ai_model + ')' if use_ai else 'OFF (deterministic)'}")
    if use_ai:
        print(f"  AI folders:  max {ai_max_folders}")
    print(f"  Cursor .mdc: {'ON' if emit_cursor else 'OFF'}")
    print(f"  Dry-run:     {'yes' if dry_run else 'no'}")
    print()

    result = generate_codebase_context(
        project_root,
        enable_ast=enable_ast,
        enable_graph=enable_graph,
        write_graph=write_graph,
        write_modules=write_modules,
        emit_practices_flag=emit_practices_flag,
        use_ai=use_ai,
        ai_provider=ai_provider,
        ai_model=ai_model,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
        google_key=google_key,
        graph_token_budget=graph_token_budget,
        global_budget=global_budget,
        emit_cursor_rules=emit_cursor,
        dry_run=dry_run,
        ai_max_folders=ai_max_folders,
    )

    print()
    print("=" * 60)
    print("✓ Context generation complete" + (" (dry-run)" if dry_run else ""))
    print("=" * 60)
    print(f"  Languages: {', '.join(result['languages']) or '(none)'}")
    print(f"  Digests:   {result['modules']}")
    print(f"  Practices: {result.get('practices', 0)}")
    print(f"  Pack:      {project_root / '.ai-context' / 'CODEBASE.md'}")
    if result.get("agents_patched"):
        print("  Pointer:   AGENTS.md addendum updated")
    else:
        print("  Pointer:   skipped (constitution already rich / not additive)")
    print()
    print("Constitution (purpose/commands/off-limits) stays in AGENTS.md.")
    print("Edit packs: ai-rules-generator context for <path>")
    print("Folder digests: ai-rules-generator context show <path>")
    print("For identity bootstrap: Sync install-repo-identity.sh")
    print("=" * 60)


def cmd_context_show(args) -> None:
    """Print an on-demand folder digest."""
    # Ensure project-root is available for validate_and_resolve_paths
    if not hasattr(args, "project_root"):
        args.project_root = None
    _, project_root = validate_and_resolve_paths(args)
    folder = getattr(args, "folder", "") or ""
    full = bool(getattr(args, "full", False))
    enable_ast = not getattr(args, "no_ast", False)
    enable_graph = not getattr(args, "no_graph", False)

    text = show_folder_context(
        project_root,
        folder,
        full=full,
        enable_ast=enable_ast,
        enable_graph=enable_graph,
    )
    print(text)


def cmd_context_for(args) -> None:
    """Print a path-scoped edit pack (ancestors + neighborhood + AGENTS slices)."""
    if not hasattr(args, "project_root"):
        args.project_root = None
    _, project_root = validate_and_resolve_paths(args)
    paths = list(getattr(args, "paths", None) or [])
    budget = int(getattr(args, "budget", 2500) or 2500)
    as_json = bool(getattr(args, "json", False))
    do_write = bool(getattr(args, "write", False))
    enable_ast = not getattr(args, "no_ast", False)
    enable_graph = not getattr(args, "no_graph", False)

    result = assemble_edit_pack(
        project_root,
        paths,
        token_budget=budget,
        enable_graph=enable_graph,
        enable_ast=enable_ast,
        write_graph_cache=True,
    )
    if as_json:
        import json
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_markdown())
    if do_write:
        out = write_edit_pack(project_root, result, as_json=as_json)
        print(f"\nWrote {out.relative_to(project_root)}", flush=True)


def run_legacy_rules_setup(args) -> None:
    """Legacy path: write full AGENTS.md + .ai-rules skills + cursor rules."""
    from .cli import interactive_config
    from .scanner import scan_project

    user_config = load_user_config() or UserConfig()
    base_path, project_root = validate_and_resolve_paths(args)

    if getattr(args, "description", None) and getattr(args, "language", None):
        from .models import ProjectConfig
        config = ProjectConfig(
            description=args.description,
            is_monorepo=bool(getattr(args, "monorepo", False)),
            primary_language=args.language.lower(),
            frameworks=getattr(args, "frameworks", None) or [],
            project_root=project_root,
        )
    else:
        config = interactive_config()
        config.project_root = project_root

    use_ai = not getattr(args, "no_ai", False)
    ai_provider = user_config.ai_provider if use_ai else "none"
    ai_model = user_config.ai_model if use_ai else "template"
    openai_key = user_config.openai_api_key or os.getenv("OPENAI_API_KEY")
    anthropic_key = user_config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    enable_ast = not getattr(args, "no_ast", False)
    enable_graph = not getattr(args, "no_graph", False)
    link_mode = LinkMode.from_str(getattr(args, "link_mode", "symlink") or "symlink")
    enabled_tools = user_config.enabled_tools or ["cursor", "claude-code"]

    scan_ctx = None
    if enable_ast:
        try:
            scan_ctx = scan_project(project_root, config, extract_signatures=True)
        except Exception as exc:
            print(f"  (scan skipped: {exc})")

    kwargs = dict(
        google_key=google_key,
        scan_ctx=scan_ctx,
        enable_graph=enable_graph,
        enable_ast=enable_ast,
        graph_token_budget=int(getattr(args, "graph_budget", 0) or 1000),
        max_tier1_lines=getattr(args, "max_tier1_lines", None),
        global_budget=int(getattr(args, "token_budget", 0) or 1_000_000),
        link_mode=link_mode,
    )
    if config.is_monorepo:
        generate_monorepo_project_rules(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key, enabled_tools, **kwargs,
        )
    else:
        generate_single_project_rules_setup(
            config, base_path, project_root, use_ai, ai_provider, ai_model,
            openai_key, anthropic_key, enabled_tools, **kwargs,
        )
