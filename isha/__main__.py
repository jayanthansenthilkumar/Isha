"""
Allow running Isha as a module: python -m isha

This delegates to the CLI entry point.
"""

from isha.cli import main

if __name__ == "__main__":
    main()
