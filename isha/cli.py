"""
ISHA CLI - Command Line Interface

The `isha` command for running ISHA applications.

Usage:
    isha run app.pyisha
    isha run app.pyisha --port 3000
    isha run app.pyisha --host 0.0.0.0 --port 8080
"""

import sys
import argparse
from .loader import load_pyisha, validate_app, IshaLoadError
from .server import Server


def print_banner():
    """Print the ISHA welcome banner."""
    print("""
  ╦╔═╗╦ ╦╔═╗
  ║╚═╗╠═╣╠═╣
  ╩╚═╝╩ ╩╩ ╩
  
  Simple. Human. Timeless.
    """)


def print_help():
    """Print help message."""
    print("""
ISHA Framework - Command Line Interface

Usage:
    isha run <file>.pyisha [options]

Commands:
    run         Run an ISHA application

Options:
    --host      Host address to bind to (default: 127.0.0.1)
    --port      Port number to listen on (default: 8000)
    --help      Show this help message

Examples:
    isha run app.pyisha
    isha run app.pyisha --port 3000
    isha run app.pyisha --host 0.0.0.0 --port 8080

Learn more: https://github.com/isha-framework/isha
    """)


def cmd_run(args):
    """Handle the 'run' command."""
    parser = argparse.ArgumentParser(
        prog="isha run",
        description="Run an ISHA application"
    )
    parser.add_argument(
        "file",
        help="The .pyisha file to run"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to listen on (default: 8000)"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load the .pyisha file
        print(f"  📂 Loading {parsed.file}...")
        module = load_pyisha(parsed.file)
        
        # Validate the app
        validate_app(module)
        
        # Create and run the server
        server = Server(
            app=module.app,
            host=parsed.host,
            port=parsed.port
        )
        server.run()
        
    except IshaLoadError as e:
        print(f"\n  ❌ Load Error:\n")
        for line in str(e).split("\n"):
            print(f"     {line}")
        print()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n  ❌ Error: {e}\n")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_banner()
        print_help()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "--help" or command == "-h":
        print_banner()
        print_help()
        sys.exit(0)
    
    if command == "--version" or command == "-v":
        from . import __version__
        print(f"ISHA Framework v{__version__}")
        sys.exit(0)
    
    if command == "run":
        print_banner()
        cmd_run(sys.argv[2:])
    
    else:
        print(f"\n  ❌ Unknown command: {command}")
        print("  Run 'isha --help' for usage information.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
