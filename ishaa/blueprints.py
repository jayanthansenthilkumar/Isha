"""
Ishaa Blueprints - Modular route grouping (like Flask blueprints).
"""

from typing import Callable, List, Optional


class Blueprint:
    """
    A blueprint groups routes under a common prefix, enabling modular application design.
    
    Example:
        api = Blueprint("api", prefix="/api/v1")
        
        @api.route("/users")
        async def list_users(request):
            return JSONResponse({"users": []})
        
        app.register_blueprint(api)
    """

    def __init__(self, name: str, prefix: str = ""):
        self.name = name
        self.prefix = prefix.rstrip("/")
        self._routes = []
        self._before_hooks = []
        self._after_hooks = []
        self._error_handlers = {}

    def route(self, path: str, methods: List[str] = None, name: str = None):
        """Decorator to register a route on this blueprint."""
        def decorator(handler: Callable):
            route_name = name or f"{self.name}.{handler.__name__}"
            self._routes.append({
                "path": path,
                "handler": handler,
                "methods": methods,
                "name": route_name,
            })
            return handler
        return decorator

    def get(self, path: str, name: str = None):
        return self.route(path, methods=["GET"], name=name)

    def post(self, path: str, name: str = None):
        return self.route(path, methods=["POST"], name=name)

    def put(self, path: str, name: str = None):
        return self.route(path, methods=["PUT"], name=name)

    def delete(self, path: str, name: str = None):
        return self.route(path, methods=["DELETE"], name=name)

    def patch(self, path: str, name: str = None):
        return self.route(path, methods=["PATCH"], name=name)

    def before_request(self, func):
        """Register a before-request hook for this blueprint."""
        self._before_hooks.append(func)
        return func

    def after_request(self, func):
        """Register an after-request hook for this blueprint."""
        self._after_hooks.append(func)
        return func

    def error_handler(self, status_code: int):
        """Register an error handler for a specific status code."""
        def decorator(func):
            self._error_handlers[status_code] = func
            return func
        return decorator

    def get_routes(self):
        """Get all routes with the blueprint prefix applied."""
        routes = []
        for route_info in self._routes:
            full_path = self.prefix + route_info["path"]
            routes.append({
                **route_info,
                "path": full_path,
            })
        return routes

    def __repr__(self):
        return f"<Blueprint '{self.name}' prefix='{self.prefix}' routes={len(self._routes)}>"
