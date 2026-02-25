"""
Isha CLI — Command-line interface for creating and managing projects.

Commands:
    isha create project <name>  - Create a new Isha project
    isha run                    - Run the development server
    isha migrate                - Run database migrations
    isha routes                 - List all registered routes
    isha shell                  - Start interactive shell
"""

import argparse
import os
import sys
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="isha",
        description="Isha Framework CLI — Build elegant web applications",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── create ──
    create_parser = subparsers.add_parser("create", help="Create a new project or component")
    create_sub = create_parser.add_subparsers(dest="create_type")
    
    project_parser = create_sub.add_parser("project", help="Create a new Isha project")
    project_parser.add_argument("name", help="Project name")
    project_parser.add_argument("--minimal", action="store_true", help="Create minimal project")

    # ── run ──
    run_parser = subparsers.add_parser("run", help="Run the development server")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("app", nargs="?", default="app:app", help="Application module (default: app:app)")

    # ── migrate ──
    migrate_parser = subparsers.add_parser("migrate", help="Database migrations")
    migrate_parser.add_argument("action", nargs="?", default="run", choices=["run", "create", "status"])
    migrate_parser.add_argument("--name", help="Migration name (for create)")
    migrate_parser.add_argument("--sql", help="SQL for migration (for create)")

    # ── routes ──
    routes_parser = subparsers.add_parser("routes", help="List all registered routes")
    routes_parser.add_argument("app", nargs="?", default="app:app", help="Application module")

    # ── shell ──
    subparsers.add_parser("shell", help="Start interactive Python shell with app context")

    # ── version ──
    subparsers.add_parser("version", help="Show Isha version")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "create": cmd_create,
        "run": cmd_run,
        "migrate": cmd_migrate,
        "routes": cmd_routes,
        "shell": cmd_shell,
        "version": cmd_version,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


def cmd_create(args):
    """Create a new Isha project."""
    if args.create_type != "project":
        print("Usage: isha create project <name>")
        return

    name = args.name
    project_dir = Path(name)

    if project_dir.exists():
        print(f"Error: Directory '{name}' already exists.")
        sys.exit(1)

    print(f"✦ Creating Isha project: {name}")

    # Create directories
    dirs = [
        project_dir,
        project_dir / "static" / "css",
        project_dir / "static" / "js",
        project_dir / "static" / "img",
        project_dir / "templates",
        project_dir / "migrations",
        project_dir / "tests",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create app.py
    app_content = f'''"""
{name} — Built with Isha Framework
"""

from isha import Isha, JSONResponse, HTMLResponse
from isha.plugins import StaticFilesPlugin

app = Isha("{name}", debug=True)

# Register plugins
app.register_plugin(StaticFilesPlugin(directory="static", prefix="/static"))


@app.route("/")
async def index(request):
    return await app.render("index.html", title="{name}", message="Welcome to Isha!")


@app.route("/api/health")
async def health(request):
    return JSONResponse({{"status": "ok", "framework": "Isha"}})


@app.route("/api/hello/<str:name>")
async def hello(request, name="World"):
    return JSONResponse({{"message": f"Hello, {{name}}!"}})


if __name__ == "__main__":
    app.run(debug=True)
'''
    (project_dir / "app.py").write_text(app_content)

    # Create base template
    base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}''' + name + '''{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <a href="/" class="brand">''' + name + '''</a>
    </nav>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    <footer class="footer">
        <p>Built with ✦ Isha Framework</p>
    </footer>
    {% block scripts %}{% endblock %}
</body>
</html>
'''
    (project_dir / "templates" / "base.html").write_text(base_template)

    # Create index template
    index_template = '''{% extends "base.html" %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<div class="hero">
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
    <a href="/api/health" class="btn">Check API Health</a>
</div>
{% endblock %}
'''
    (project_dir / "templates" / "index.html").write_text(index_template)

    # Create CSS
    css_content = '''/* ''' + name + ''' — Isha Framework */
:root {
    --primary: #6366f1;
    --bg: #0f172a;
    --text: #e2e8f0;
    --card: #1e293b;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.navbar {
    padding: 1rem 2rem;
    background: var(--card);
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.brand {
    color: var(--primary);
    font-weight: 700;
    font-size: 1.25rem;
    text-decoration: none;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    flex: 1;
}

.hero {
    text-align: center;
    padding: 4rem 0;
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, var(--primary), #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero p {
    font-size: 1.25rem;
    color: #94a3b8;
    margin-bottom: 2rem;
}

.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    background: var(--primary);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-weight: 600;
    transition: opacity 0.2s;
}

.btn:hover { opacity: 0.9; }

.footer {
    padding: 2rem;
    text-align: center;
    color: #64748b;
    border-top: 1px solid rgba(255,255,255,0.05);
}
'''
    (project_dir / "static" / "css" / "style.css").write_text(css_content)

    # Create test file
    test_content = f'''"""Tests for {name}"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from isha.testing import TestClient


def test_health():
    from app import app
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_hello():
    from app import app
    client = TestClient(app)
    response = client.get("/api/hello/Isha")
    assert response.status_code == 200
    data = response.json()
    assert "Hello" in data["message"]


if __name__ == "__main__":
    test_health()
    test_hello()
    print("All tests passed!")
'''
    (project_dir / "tests" / "test_app.py").write_text(test_content)

    # Create requirements.txt
    (project_dir / "requirements.txt").write_text("isha>=1.0.0\nuvicorn>=0.20.0\n")

    # Create .gitignore
    (project_dir / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n*.pyo\n.env\n*.db\nvenv/\n.venv/\n*.egg-info/\ndist/\nbuild/\n"
    )

    print(f"""
✦ Project '{name}' created successfully!

  cd {name}
  pip install isha
  python app.py

  Your app will be running at http://127.0.0.1:8000
""")


def cmd_run(args):
    """Run the development server."""
    module_path, _, attr_name = args.app.partition(":")
    attr_name = attr_name or "app"

    sys.path.insert(0, os.getcwd())
    try:
        module = __import__(module_path)
        app = getattr(module, attr_name)
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not load '{args.app}': {e}")
        sys.exit(1)

    if args.reload:
        try:
            import uvicorn
            uvicorn.run(
                args.app,
                host=args.host,
                port=args.port,
                reload=True,
                log_level="debug" if args.debug else "info",
            )
        except ImportError:
            print("Auto-reload requires uvicorn: pip install uvicorn")
            app.run(host=args.host, port=args.port, debug=args.debug)
    else:
        app.run(host=args.host, port=args.port, debug=args.debug)


def cmd_migrate(args):
    """Run database migrations."""
    from .orm import Database, MigrationManager

    if args.action == "run":
        print("✦ Running migrations...")
        MigrationManager.run_migrations()
        print("✦ Migrations complete.")

    elif args.action == "create":
        if not args.name:
            print("Error: --name required for creating migrations")
            sys.exit(1)
        sql = args.sql or "-- Add your SQL here"
        filepath = MigrationManager.create_migration(args.name, sql)
        print(f"✦ Created migration: {filepath}")

    elif args.action == "status":
        MigrationManager.init()
        rows = Database.fetchall(f"SELECT name, applied_at FROM {MigrationManager.MIGRATION_TABLE} ORDER BY id")
        if rows:
            print("Applied migrations:")
            for row in rows:
                print(f"  ✓ {row['name']} ({row['applied_at']})")
        else:
            print("No migrations applied yet.")


def cmd_routes(args):
    """List all registered routes."""
    module_path, _, attr_name = args.app.partition(":")
    attr_name = attr_name or "app"

    sys.path.insert(0, os.getcwd())
    try:
        module = __import__(module_path)
        app = getattr(module, attr_name)
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not load '{args.app}': {e}")
        sys.exit(1)

    print(f"\n✦ Routes for '{app.name}':\n")
    print(f"  {'Methods':<30} {'Path':<30} {'Handler':<20}")
    print(f"  {'─' * 30} {'─' * 30} {'─' * 20}")
    for route in app.router.routes:
        methods = ", ".join(sorted(route.methods - {"HEAD"}))
        print(f"  {methods:<30} {route.path:<30} {route.name:<20}")
    print()


def cmd_shell(args):
    """Start an interactive shell."""
    sys.path.insert(0, os.getcwd())

    context = {}
    try:
        import app as user_app
        context["app"] = getattr(user_app, "app", None)
    except ImportError:
        pass

    try:
        from .orm import Database, Model
        context["Database"] = Database
        context["Model"] = Model
    except ImportError:
        pass

    banner = "✦ Isha Interactive Shell\nContext: " + ", ".join(context.keys())

    try:
        from IPython import embed
        embed(banner1=banner, user_ns=context)
    except ImportError:
        import code
        code.interact(banner=banner, local=context)


def cmd_version(args):
    """Show version."""
    from . import __version__
    print(f"Isha Framework v{__version__}")


if __name__ == "__main__":
    main()
