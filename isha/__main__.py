"""
ISHA Framework - Module Entry Point

Allows running ISHA as a module:
    python -m isha run app.pyisha

This will later become:
    isha run app.pyisha
"""

from .cli import main

if __name__ == "__main__":
    main()
