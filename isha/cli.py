"""
Isha CLI — Command-line interface for creating and managing Isha projects.

Usage:
    isha create project <name>  - Scaffold a new Isha project
    isha run [app:app]          - Run the development server
    isha routes [app:app]       - List all registered routes
    isha shell                  - Start interactive shell
    isha version                - Show Isha version
"""

import argparse
import os
import sys
import importlib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="isha",
        description="Isha — A Modern Python Web Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  isha create project myapp     Create a new project
  isha run                      Run dev server (loads app:app)
  isha run myapp.main:app       Run a specific app module
  isha routes                   Show all registered routes
  isha version                  Print framework version
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── create ──
    create_parser = subparsers.add_parser("create", help="Create a new project or component")
    create_sub = create_parser.add_subparsers(dest="create_type")

    project_parser = create_sub.add_parser("project", help="Scaffold a new Isha project")
    project_parser.add_argument("name", help="Project name")
    project_parser.add_argument("--minimal", action="store_true", help="Minimal project (single file)")

    # ── run ──
    run_parser = subparsers.add_parser("run", help="Run the development server")
    run_parser.add_argument("app", nargs="?", default=None, help="App import path (default: auto-detect or app:app)")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    run_parser.add_argument("--port", "-p", type=int, default=8000, help="Port to bind to (default: 8000)")
    run_parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode")
    run_parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload on code changes")
    run_parser.add_argument("--workers", type=int, default=1, help="Number of workers (uvicorn only)")

    # ── routes ──
    routes_parser = subparsers.add_parser("routes", help="List all registered routes")
    routes_parser.add_argument("app", nargs="?", default=None, help="App import path")

    # ── shell ──
    subparsers.add_parser("shell", help="Start interactive Python shell with Isha imports")

    # ── version ──
    subparsers.add_parser("version", help="Show Isha framework version")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "create": cmd_create,
        "run": cmd_run,
        "routes": cmd_routes,
        "shell": cmd_shell,
        "version": cmd_version,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n✦ Stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


def _resolve_app(app_path=None):
    """
    Resolve an application import path like 'app:app' or 'mypackage.main:application'.
    Auto-detects if app_path is None by looking for common patterns.

    Returns (app_instance, app_path_string).
    """
    # Add cwd to sys.path for local imports
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if app_path is None:
        # Auto-detect: try common patterns
        candidates = [
            ("app", "app"),
            ("main", "app"),
            ("wsgi", "app"),
            ("asgi", "app"),
            ("server", "app"),
        ]
        for module_name, attr_name in candidates:
            module_file = Path(cwd) / f"{module_name}.py"
            if module_file.exists():
                app_path = f"{module_name}:{attr_name}"
                break

        if app_path is None:
            print("Error: Could not auto-detect application.", file=sys.stderr)
            print("Provide the app path explicitly: isha run mymodule:app", file=sys.stderr)
            sys.exit(1)

    # Parse module:attribute
    if ":" in app_path:
        module_path, attr_name = app_path.rsplit(":", 1)
    else:
        module_path = app_path
        attr_name = "app"

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error: Could not import module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)

    app = getattr(module, attr_name, None)
    if app is None:
        print(f"Error: Module '{module_path}' has no attribute '{attr_name}'.", file=sys.stderr)
        available = [a for a in dir(module) if not a.startswith("_")]
        if available:
            print(f"  Available: {', '.join(available[:10])}", file=sys.stderr)
        sys.exit(1)

    return app, app_path


def cmd_run(args):
    """Run the development server."""
    app, app_path = _resolve_app(args.app)

    host = args.host
    port = args.port
    debug = args.debug

    if debug and hasattr(app, "debug"):
        app.debug = True

    if args.reload:
        # Use uvicorn for auto-reload support
        try:
            import uvicorn
            print(f"\n✦ Isha Dev Server (uvicorn + auto-reload)")
            print(f"  App:    {app_path}")
            print(f"  URL:    http://{host}:{port}")
            print(f"  Reload: ON")
            print(f"  Press Ctrl+C to stop\n")
            uvicorn.run(
                app_path,
                host=host,
                port=port,
                reload=True,
                log_level="debug" if debug else "info",
                workers=args.workers if args.workers > 1 else 1,
            )
        except ImportError:
            print("Warning: Auto-reload requires uvicorn. Install with: pip install isha[uvicorn]", file=sys.stderr)
            print("Running without reload...\n")
            app.run(host=host, port=port, debug=debug)
    else:
        # Try uvicorn first for production-quality serving, fall back to built-in
        try:
            import uvicorn
            print(f"\n✦ Isha Server (uvicorn)")
            print(f"  App:    {app_path}")
            print(f"  URL:    http://{host}:{port}")
            print(f"  Press Ctrl+C to stop\n")
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="debug" if debug else "info",
                workers=args.workers if args.workers > 1 else 1,
            )
        except ImportError:
            # Use built-in server
            app.run(host=host, port=port, debug=debug)


def cmd_create(args):
    """Create a new Isha project."""
    if args.create_type != "project":
        print("Usage: isha create project <name>")
        return

    name = args.name
    safe_name = name.replace("-", "_").replace(" ", "_")
    project_dir = Path(name)

    if project_dir.exists():
        print(f"Error: Directory '{name}' already exists.", file=sys.stderr)
        sys.exit(1)

    print(f"\n✦ Creating Isha project: {name}\n")

    if args.minimal:
        _create_minimal_project(project_dir, name, safe_name)
    else:
        _create_full_project(project_dir, name, safe_name)

    print(f"""✦ Project '{name}' created successfully!

  Next steps:
    cd {name}
    pip install isha
    python app.py

  Your app will be running at http://127.0.0.1:8000
""")


def _create_full_project(project_dir, name, safe_name):
    """Scaffold a full Isha project."""
    dirs = [
        project_dir,
        project_dir / "routes",
        project_dir / "models",
        project_dir / "static" / "css",
        project_dir / "static" / "js",
        project_dir / "static" / "img",
        project_dir / "templates",
        project_dir / "tests",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created {d}/")

    # ── app.py ──
    (project_dir / "app.py").write_text(f'''"""
{name} — Built with Isha Framework
"""

from isha import Isha, JSONResponse, HTMLResponse
from isha.middleware import CORSMiddleware, SecurityHeadersMiddleware
from isha.plugins import StaticFilesPlugin

app = Isha("{safe_name}", debug=True)

# Middleware
app.add_middleware(CORSMiddleware(allow_origins=["*"]))
app.add_middleware(SecurityHeadersMiddleware())

# Static files
app.register_plugin(StaticFilesPlugin(directory="static", prefix="/static"))


# ── Routes ──────────────────────────────────────────────

@app.route("/")
async def index(request):
    """Serve the home page."""
    return app.render("index.html", title="{name}", message="Welcome to {name}!")


@app.route("/api/health")
async def health(request):
    """API health check endpoint."""
    return {{"status": "ok", "app": "{safe_name}", "framework": "Isha"}}


@app.route("/api/hello/<name>")
async def hello(request, name):
    """Greeting endpoint."""
    return {{"message": f"Hello, {{name}}! Welcome to {name}."}}


# ── Startup / Shutdown ──────────────────────────────────

@app.on_startup
async def startup():
    print("✦ {name} started!")


@app.on_shutdown
async def shutdown():
    print("✦ {name} shutting down...")


# ── Run ─────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
''', encoding="utf-8")
    print(f"  Created {project_dir / 'app.py'}")

    # ── config.py ──
    (project_dir / "config.py").write_text(f'''"""
Configuration for {name}
"""

import os


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    DEBUG = False
    HOST = "127.0.0.1"
    PORT = 8000


class DevConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProdConfig(Config):
    """Production configuration."""
    DEBUG = False
    HOST = "0.0.0.0"
''', encoding="utf-8")
    print(f"  Created {project_dir / 'config.py'}")

    # ── routes/__init__.py ──
    (project_dir / "routes" / "__init__.py").write_text(f'''"""
Route blueprints for {name}
"""

from isha import Blueprint

api = Blueprint("api", prefix="/api/v1")


@api.route("/ping")
async def ping(request):
    return {{"pong": True}}
''', encoding="utf-8")
    print(f"  Created {project_dir / 'routes' / '__init__.py'}")

    # ── models/__init__.py ──
    (project_dir / "models" / "__init__.py").write_text(f'''"""
Database models for {name}
"""

# Uncomment to use the built-in ORM:
#
# from isha.orm import Database, Model, TextField, IntegerField, BooleanField
#
# db = Database("{safe_name}.db")
#
# class User(Model):
#     _table = "users"
#     _db = db
#     name = TextField()
#     email = TextField()
''', encoding="utf-8")
    print(f"  Created {project_dir / 'models' / '__init__.py'}")

    # ── templates/base.html ──
    (project_dir / "templates" / "base.html").write_text('''<!DOCTYPE html>
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
        <div class="nav-container">
            <a href="/" class="brand">''' + name + '''</a>
            <div class="nav-links">
                <a href="/">Home</a>
                <a href="/api/health">API</a>
            </div>
        </div>
    </nav>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer class="footer">
        <p>Built with <a href="https://github.com/jayanthansenthilkumar/ISHA_Framework">Isha Framework</a></p>
    </footer>

    {% block scripts %}{% endblock %}
</body>
</html>
''', encoding="utf-8")
    print(f"  Created {project_dir / 'templates' / 'base.html'}")

    # ── templates/index.html ──
    (project_dir / "templates" / "index.html").write_text('''{% extends "base.html" %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<div class="hero">
    <h1>{{ title }}</h1>
    <p class="subtitle">{{ message }}</p>
    <div class="cta-group">
        <a href="/api/health" class="btn btn-primary">API Health</a>
        <a href="/api/hello/World" class="btn btn-secondary">Try API</a>
    </div>
</div>

<div class="features">
    <div class="feature-card">
        <h3>Fast</h3>
        <p>Async-first ASGI architecture for high performance.</p>
    </div>
    <div class="feature-card">
        <h3>Modular</h3>
        <p>Blueprints, plugins, and middleware — use only what you need.</p>
    </div>
    <div class="feature-card">
        <h3>Secure</h3>
        <p>Built-in JWT auth, CORS, CSRF, rate limiting, and security headers.</p>
    </div>
</div>
{% endblock %}
''', encoding="utf-8")
    print(f"  Created {project_dir / 'templates' / 'index.html'}")

    # ── static/css/style.css ──
    (project_dir / "static" / "css" / "style.css").write_text('''/* ''' + name + ''' — Built with Isha Framework */
:root {
    --primary: #6366f1;
    --primary-hover: #4f46e5;
    --bg: #0f172a;
    --surface: #1e293b;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --border: rgba(255, 255, 255, 0.08);
    --radius: 12px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    line-height: 1.6;
}

a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.navbar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 2rem;
}
.nav-container {
    max-width: 1000px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 60px;
}
.brand {
    color: var(--primary) !important;
    font-weight: 700;
    font-size: 1.2rem;
    text-decoration: none !important;
}
.nav-links a {
    color: var(--text-muted);
    margin-left: 1.5rem;
    font-size: 0.9rem;
}
.nav-links a:hover { color: var(--text); text-decoration: none; }

.container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
    flex: 1;
}

.hero {
    text-align: center;
    padding: 5rem 0 3rem;
}
.hero h1 {
    font-size: 3.5rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    background: linear-gradient(135deg, var(--primary), #a78bfa, #f472b6);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.subtitle {
    font-size: 1.25rem;
    color: var(--text-muted);
    margin-bottom: 2rem;
}
.cta-group { display: flex; gap: 1rem; justify-content: center; }
.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
}
.btn-primary {
    background: var(--primary);
    color: white;
}
.btn-primary:hover { background: var(--primary-hover); text-decoration: none; }
.btn-secondary {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
}
.btn-secondary:hover { border-color: var(--primary); text-decoration: none; }

.features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    padding: 2rem 0;
}
.feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem;
}
.feature-card:hover { border-color: var(--primary); }
.feature-card h3 { margin-bottom: 0.5rem; font-size: 1.1rem; }
.feature-card p { color: var(--text-muted); font-size: 0.9rem; }

.footer {
    padding: 2rem;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
    border-top: 1px solid var(--border);
}
''', encoding="utf-8")
    print(f"  Created {project_dir / 'static' / 'css' / 'style.css'}")

    # ── tests ──
    (project_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (project_dir / "tests" / "test_app.py").write_text(f'''"""Tests for {name}"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from isha.testing import TestClient
from app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.ok
    data = response.json()
    assert data["status"] == "ok"


def test_hello():
    response = client.get("/api/hello/World")
    assert response.ok
    data = response.json()
    assert "Hello" in data["message"]


def test_not_found():
    response = client.get("/nonexistent")
    assert response.status_code == 404


if __name__ == "__main__":
    for name_key, fn in list(globals().items()):
        if name_key.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {{name_key}}")
            except Exception as e:
                print(f"  FAIL  {{name_key}}: {{e}}")
''', encoding="utf-8")
    print(f"  Created {project_dir / 'tests' / 'test_app.py'}")

    # ── requirements.txt ──
    (project_dir / "requirements.txt").write_text("isha>=1.0.0\n", encoding="utf-8")
    print(f"  Created {project_dir / 'requirements.txt'}")

    # ── .gitignore ──
    (project_dir / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n*.pyo\n.env\n*.db\nvenv/\n.venv/\n*.egg-info/\ndist/\nbuild/\n.pytest_cache/\n",
        encoding="utf-8",
    )
    print(f"  Created {project_dir / '.gitignore'}")


def _create_minimal_project(project_dir, name, safe_name):
    """Scaffold a minimal single-file project."""
    project_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Created {project_dir}/")

    (project_dir / "app.py").write_text(f'''"""
{name} — Built with Isha Framework (minimal)
"""

from isha import Isha

app = Isha("{safe_name}")


@app.route("/")
async def index(request):
    return "<h1>Hello from {name}!</h1>"


@app.route("/api/health")
async def health(request):
    return {{"status": "ok"}}


@app.route("/hello/<name>")
async def hello(request, name):
    return {{"message": f"Hello, {{name}}!"}}


if __name__ == "__main__":
    app.run(debug=True)
''', encoding="utf-8")
    print(f"  Created {project_dir / 'app.py'}")

    (project_dir / "requirements.txt").write_text("isha>=1.0.0\n", encoding="utf-8")
    (project_dir / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.env\n*.db\nvenv/\n",
        encoding="utf-8",
    )


def cmd_routes(args):
    """List all registered routes."""
    app, _ = _resolve_app(args.app)

    print(f"\n✦ Routes for '{app.name}':\n")
    print(f"  {'METHOD':<20} {'PATH':<35} {'HANDLER':<20}")
    print(f"  {'─' * 20} {'─' * 35} {'─' * 20}")

    for route in app.router.routes:
        methods = ", ".join(sorted(route.methods - {"HEAD"}))
        print(f"  {methods:<20} {route.path:<35} {route.name:<20}")
    print()


def cmd_shell(args):
    """Start an interactive shell with Isha imports."""
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    context = {}
    try:
        from isha import Isha, Request, Response, JSONResponse, HTMLResponse
        context.update({
            "Isha": Isha,
            "Request": Request,
            "Response": Response,
            "JSONResponse": JSONResponse,
            "HTMLResponse": HTMLResponse,
        })
    except ImportError:
        pass

    # Try loading user's app
    try:
        import app as user_app
        if hasattr(user_app, "app"):
            context["app"] = user_app.app
    except ImportError:
        pass

    names = ", ".join(context.keys())
    banner = f"✦ Isha Interactive Shell\n  Available: {names}\n"

    try:
        from IPython import embed
        embed(banner1=banner, user_ns=context)
    except ImportError:
        import code
        code.interact(banner=banner, local=context)


def cmd_version(args):
    """Show Isha framework version."""
    from . import __version__
    print(f"Isha Framework v{__version__}")


if __name__ == "__main__":
    main()
