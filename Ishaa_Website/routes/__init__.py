"""
Route blueprints for Ishaa Framework Landing Page
"""

from ishaa import Blueprint

api = Blueprint("api", prefix="/api/v1")


@api.route("/ping")
async def ping(request):
    return {"pong": True}


@api.route("/stats")
async def stats(request):
    """Return framework stats for the landing page."""
    return {
        "version": "1.2.0",
        "stars": "Growing",
        "async_first": True,
        "built_in_orm": True,
        "middleware_count": 5,
    }
