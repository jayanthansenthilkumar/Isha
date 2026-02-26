"""
Allow running Ishaa as a module: python -m ishaa

This delegates to the CLI entry point.
"""

from ishaa.cli import main

if __name__ == "__main__":
    main()
