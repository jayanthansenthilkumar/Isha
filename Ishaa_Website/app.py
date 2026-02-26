"""
Ishaa Framework - Official Landing Page
The modern async Python web framework.
"""

import mimetypes

# Fix Windows MIME type registry (Windows may serve .js as text/plain)
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")

from ishaa import Ishaa, JSONResponse, HTMLResponse
from ishaa.middleware import CORSMiddleware, SecurityHeadersMiddleware
from ishaa.plugins import StaticFilesPlugin

app = Ishaa("isha_framework", debug=True)

# Middleware
app.add_middleware(CORSMiddleware(allow_origins=["*"]))
app.add_middleware(SecurityHeadersMiddleware())

# Static files
app.register_plugin(StaticFilesPlugin(directory="static", prefix="/static"))


# ── Routes ──────────────────────────────────────────────

@app.route("/")
async def index(request):
    """Serve the Ishaa Framework landing page."""
    return app.render(
        "index.html",
        title="Ishaa Framework",
        tagline="The Modern Async Python Web Framework",
        description="Build blazing-fast web applications with an elegant, batteries-included framework designed for developer happiness.",
    )


@app.route("/docs")
async def docs(request):
    """Serve the Ishaa Framework documentation page."""
    return app.render(
        "docs.html",
        title="Documentation",
    )


@app.route("/api/health")
async def health(request):
    """API health check endpoint."""
    return {"status": "ok", "app": "isha_framework", "framework": "Ishaa"}


@app.route("/api/hello/<name>")
async def hello(request, name):
    """Greeting endpoint - a live demo of Ishaa routing."""
    return {"message": f"Hello, {name}! Welcome to Ishaa Framework."}


# ── Startup / Shutdown ──────────────────────────────────

@app.on_startup
async def startup():
    print("✦ Ishaa Framework landing page started!")


@app.on_shutdown
async def shutdown():
    print("✦ Ishaa Framework landing page shutting down...")


# ── Run ─────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
