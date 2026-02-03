#!/usr/bin/env python3
"""
AI Rules Generator CLI
Generates comprehensive AI coding agent rules based on project configuration
and best practices from general guidelines and language/framework-specific rules.
"""

import sys

from .parser import create_parser


def main() -> None:
    """Main entry point."""
    try:
        parser = create_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(0)

        args.func(args)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
