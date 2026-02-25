"""
Isha App — The core application class that ties everything together.
"""

import asyncio
import inspect
import traceback
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from .routing import Router
from .request import Request
from .response import Response, JSONResponse, HTMLResponse
from .middleware import MiddlewareStack, Middleware
from .blueprints import Blueprint
from .utils import Config

logger = logging.getLogger("isha")


class Isha:
    """
    The main Isha application class.
    
    Example:
        app = Isha()
        
        @app.route("/")
        async def index(request):
            return JSONResponse({"message": "Hello from Isha!"})
        
        app.run()
    """

    def __init__(self, name: str = "isha", debug: bool = False):
        self.name = name
        self.debug = debug
        self.config = Config({
            "DEBUG": debug,
            "SECRET_KEY": "",
            "HOST": "127.0.0.1",
            "PORT": 8000,
            "STATIC_DIR": "static",
            "TEMPLATE_DIR": "templates",
        })

        self.router = Router()
        self.middleware = MiddlewareStack()
        self._error_handlers: Dict[int, Callable] = {}
        self._startup_handlers: List[Callable] = []
        self._shutdown_handlers: List[Callable] = []
        self._plugins: List[Any] = []
        self._state: Dict[str, Any] = {}
        self._template_engine = None
        self._blueprints: List[Blueprint] = []

        # Setup logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    # ── Routing ──────────────────────────────────────────────────────

    def route(self, path: str, methods: List[str] = None, name: str = None):
        """Decorator to register a route."""
        return self.router.route(path, methods, name)

    def get(self, path: str, name: str = None):
        """Shortcut for GET routes."""
        return self.router.get(path, name)

    def post(self, path: str, name: str = None):
        """Shortcut for POST routes."""
        return self.router.post(path, name)

    def put(self, path: str, name: str = None):
        """Shortcut for PUT routes."""
        return self.router.put(path, name)

    def delete(self, path: str, name: str = None):
        """Shortcut for DELETE routes."""
        return self.router.delete(path, name)

    def patch(self, path: str, name: str = None):
        """Shortcut for PATCH routes."""
        return self.router.patch(path, name)

    def url_for(self, name: str, **kwargs) -> str:
        """Build URL for a named route."""
        return self.router.url_for(name, **kwargs)

    # ── Blueprints ──────────────────────────────────────────────────

    def register_blueprint(self, blueprint: Blueprint):
        """Register a blueprint with the application."""
        self._blueprints.append(blueprint)
        for route_info in blueprint.get_routes():
            self.router.add_route(
                route_info["path"],
                route_info["handler"],
                route_info.get("methods"),
                route_info.get("name"),
            )
        logger.info(f"Registered blueprint: {blueprint.name}")

    # ── Middleware ───────────────────────────────────────────────────

    def add_middleware(self, middleware):
        """Add a middleware instance."""
        self.middleware.add(middleware)

    def before_request(self, func):
        """Decorator to register a before-request hook."""
        return self.middleware.before_request(func)

    def after_request(self, func):
        """Decorator to register an after-request hook."""
        return self.middleware.after_request(func)

    def exception_handler(self, func):
        """Decorator to register a global exception handler."""
        return self.middleware.exception_handler(func)

    # ── Error Handlers ──────────────────────────────────────────────

    def error_handler(self, status_code: int):
        """Decorator to register a custom error handler for a status code."""
        def decorator(func):
            self._error_handlers[status_code] = func
            return func
        return decorator

    async def _handle_error(self, request, status_code, message=None):
        """Handle an HTTP error."""
        if status_code in self._error_handlers:
            handler = self._error_handlers[status_code]
            return await self._call_handler(handler, request)

        error_body = {"error": message or f"HTTP {status_code}"}
        return JSONResponse(error_body, status_code=status_code)

    # ── Lifecycle Events ────────────────────────────────────────────

    def on_startup(self, func):
        """Register a startup handler."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func):
        """Register a shutdown handler."""
        self._shutdown_handlers.append(func)
        return func

    # ── Plugins ─────────────────────────────────────────────────────

    def register_plugin(self, plugin):
        """Register a plugin with the application."""
        self._plugins.append(plugin)
        if hasattr(plugin, "setup"):
            plugin.setup(self)
        logger.info(f"Registered plugin: {plugin.__class__.__name__}")

    # ── Template Engine ─────────────────────────────────────────────

    def set_template_engine(self, engine):
        """Set the template rendering engine."""
        self._template_engine = engine

    def render(self, template_name: str, **context) -> HTMLResponse:
        """Render a template with the given context. Returns an HTMLResponse."""
        if self._template_engine is None:
            from .template import TemplateEngine
            template_dir = self.config.get("TEMPLATE_DIR", "templates")
            self._template_engine = TemplateEngine(template_dir)

        html = self._template_engine.render(template_name, **context)
        return HTMLResponse(html)

    # ── Request Handling ────────────────────────────────────────────

    async def _call_handler(self, handler, request, **kwargs):
        """Call a route handler, supporting both sync and async."""
        if asyncio.iscoroutinefunction(handler):
            result = await handler(request, **kwargs)
        else:
            result = handler(request, **kwargs)

        return self._ensure_response(result)

    def _ensure_response(self, result):
        """Convert handler return value to a Response object."""
        if isinstance(result, (Response,)):
            return result

        # Check for StreamingResponse
        from .response import StreamingResponse
        if isinstance(result, StreamingResponse):
            return result

        if isinstance(result, dict):
            return JSONResponse(result)

        if isinstance(result, (list, tuple)):
            return JSONResponse(result)

        if isinstance(result, str):
            return HTMLResponse(result)

        if isinstance(result, bytes):
            return Response(result, content_type="application/octet-stream")

        if result is None:
            return Response("", status_code=204)

        return Response(str(result))

    async def handle_request(self, request: Request) -> Response:
        """
        Main request handling pipeline:
        1. Run before_request middleware
        2. Route resolution
        3. Call handler
        4. Run after_request middleware
        5. Error handling
        """
        try:
            # 1. Run before-request middleware
            early_response = await self.middleware.run_before(request)
            if early_response is not None:
                return self._ensure_response(early_response)

            # 2. Resolve route
            route, params = self.router.resolve(request.path, request.method)

            if route is None:
                if params.get("_method_not_allowed"):
                    allowed = params.get("_allowed", set())
                    response = await self._handle_error(request, 405, "Method Not Allowed")
                    response.headers["allow"] = ", ".join(sorted(allowed))
                    return response
                return await self._handle_error(request, 404, "Not Found")

            # 3. Set path params on request
            request.path_params = params

            # 4. Call the route handler
            response = await self._call_handler(route.handler, request, **params)

            # 5. Run after-request middleware
            response = await self.middleware.run_after(request, response)

            return response

        except Exception as exc:
            logger.error(f"Error handling {request.method} {request.path}: {exc}")
            if self.debug:
                logger.error(traceback.format_exc())

            # Try exception middleware
            error_response = await self.middleware.run_exception(request, exc)
            if error_response is not None:
                return self._ensure_response(error_response)

            # Default 500
            if self.debug:
                return JSONResponse(
                    {"error": str(exc), "traceback": traceback.format_exc()},
                    status_code=500,
                )
            return await self._handle_error(request, 500, "Internal Server Error")

    # ── ASGI Interface ──────────────────────────────────────────────

    async def __call__(self, scope, receive, send):
        """ASGI application interface."""
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
            return

        if scope["type"] == "http":
            request = Request(scope, receive)
            await request.read_body()
            response = await self.handle_request(request)
            await response.send(send)
            return

        if scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)
            return

    async def _handle_lifespan(self, scope, receive, send):
        """Handle ASGI lifespan events."""
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    for handler in self._startup_handlers:
                        if asyncio.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as exc:
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return

            elif message["type"] == "lifespan.shutdown":
                try:
                    for handler in self._shutdown_handlers:
                        if asyncio.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception:
                    await send({"type": "lifespan.shutdown.complete"})
                return

    async def _handle_websocket(self, scope, receive, send):
        """Handle WebSocket connections (delegated to WebSocket handler)."""
        try:
            from .websocket import WebSocketHandler
            ws_handler = WebSocketHandler(self, scope, receive, send)
            await ws_handler.handle()
        except ImportError:
            await send({"type": "websocket.close", "code": 1000})

    # ── Development Server ──────────────────────────────────────────

    def run(self, host: str = None, port: int = None, debug: bool = None, workers: int = 1):
        """
        Run the development server.
        
        For production, use: uvicorn app:app --host 0.0.0.0 --port 8000
        """
        host = host or self.config.get("HOST", "127.0.0.1")
        port = port or self.config.get("PORT", 8000)
        if debug is not None:
            self.debug = debug

        from . import __version__
        print(f"""\n✦ Isha Framework v{__version__}""")
        print(f"  Running on: http://{host}:{port}")
        print(f"  Debug mode: {'ON' if self.debug else 'OFF'}")
        print(f"  Press Ctrl+C to stop\n")

        try:
            from .server import run_server
            run_server(self, host, port)
        except KeyboardInterrupt:
            print("\n✦ Isha server stopped.")

    def __repr__(self):
        return f"<Isha '{self.name}' routes={len(self.router.routes)}>"
