"""
Ishaa App - The core application class that ties everything together.
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

logger = logging.getLogger("ishaa")


class Ishaa:
    """
    The main Ishaa application class.
    
    Example:
        app = Ishaa()
        
        @app.route("/")
        async def index(request):
            return JSONResponse({"message": "Hello from Ishaa!"})
        
        app.run()
    """

    def __init__(self, name: str = "ishaa", debug: bool = False):
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

        # SARE - Self-Evolving Adaptive Routing Engine
        self.sare = None  # initialized via enable_sare()

        # RMF - Reality-Mode Framework
        self.rmf = None  # initialized via enable_rmf()

        # SEQP - Self-Evolving Quality Pipeline
        self.seqp = None  # initialized via enable_seqp()

        # Setup logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    # ── SARE - Self-Evolving Adaptive Routing Engine ────────────────

    def enable_sare(self, **kwargs):
        """
        Enable the Self-Evolving Adaptive Routing Engine.

        SARE autonomously optimizes routing, middleware ordering,
        response caching, and predicts traffic patterns - all in real time.

        Args:
            optimize_interval: Seconds between optimization cycles (default: 10)
            cache_size: Max memoized responses (default: 500)
            cache_ttl: Response cache TTL in seconds (default: 30)
            hot_route_slots: Max routes in hot cache (default: 20)
            middleware_reorder: Enable auto middleware reordering (default: True)
            predictor: Enable latency predictor (default: True)
            auto_memoize: Auto-enable caching for hot GET routes (default: True)

        Example:
            app = Ishaa()
            app.enable_sare(cache_ttl=60, hot_route_slots=30)
        """
        from .sare import SARE

        sare_kwargs = {
            "optimize_interval": kwargs.get("optimize_interval", 10.0),
            "cache_max_size": kwargs.get("cache_size", 500),
            "cache_default_ttl": kwargs.get("cache_ttl", 30.0),
            "hot_route_slots": kwargs.get("hot_route_slots", 20),
            "middleware_reorder": kwargs.get("middleware_reorder", True),
            "predictor_enabled": kwargs.get("predictor", True),
            "auto_memoize": kwargs.get("auto_memoize", True),
        }

        self.sare = SARE(**sare_kwargs)
        self.sare.attach(self)

        logger.info("SARE engine enabled - Self-Evolving Adaptive Routing Engine active")
        return self.sare

    # ── RMF - Reality-Mode Framework ────────────────────────────────

    def enable_rmf(self, **kwargs):
        """
        Enable the Reality-Mode Framework.

        RMF allows the same route to exist in multiple behavioral universes.
        Each request enters a different "reality" with different logic,
        middleware, caching, and security rules.

        Args:
            auto_promote_threshold: Requests before promotion (default: 1000)
            auto_promote_error_max: Max error rate for promotion (default: 0.02)
            auto_promote_latency_ratio: Max latency ratio vs stable (default: 1.5)
            enable_parallel_sim: Enable parallel simulation mode (default: False)
            enable_self_retiring: Enable self-retiring engine (default: True)

        Example:
            app = Ishaa()
            app.enable_rmf()

            @app.route("/recommend")
            @app.reality("stable")
            async def recommend_v1(request):
                return {"algo": "classic"}

            @app.route("/recommend")
            @app.reality("experimental", traffic_pct=20)
            async def recommend_v2(request):
                return {"algo": "neural"}
        """
        from .reality import RealityModeFramework

        self.rmf = RealityModeFramework(**kwargs)
        self.rmf.attach(self)

        logger.info("RMF engine enabled - Reality-Mode Framework active")
        return self.rmf

    def reality(self, name: str, **config):
        """
        Decorator to assign a route handler to a named reality.

        Args:
            name: Reality name (e.g. "stable", "experimental", "beta")
            traffic_pct: Percentage of traffic to route here (0-100)
            active_between: Time window ("09:00-17:00")
            auto_promote: Whether to auto-promote if proven stable
            middleware: List of middleware for this reality
            cache_ttl: Cache TTL override for this reality
            priority: Priority for reality selection (higher = preferred)
            tags: Metadata tags

        Example:
            @app.route("/api/data")
            @app.reality("experimental", traffic_pct=10, auto_promote=True)
            async def data_v2(request):
                return {"version": 2}
        """
        if self.rmf is None:
            raise RuntimeError(
                "RMF is not enabled. Call app.enable_rmf() before using @app.reality()"
            )
        return self.rmf.reality_decorator(name, **config)

    def rmf_behavior_rule(self, func: Callable):
        """
        Register a behavior-based reality selection rule.

        The function receives (request, available_realities) and returns
        a reality name or None.

        Example:
            @app.rmf_behavior_rule
            def route_by_header(request, realities):
                if request.headers.get("x-beta") == "1":
                    return "beta" if "beta" in realities else None
                return None
        """
        if self.rmf is None:
            raise RuntimeError(
                "RMF is not enabled. Call app.enable_rmf() before using @app.rmf_behavior_rule"
            )
        self.rmf.selector.add_behavior_rule(func)
        return func

    # ── SEQP - Self-Evolving Quality Pipeline ───────────────────────

    def enable_seqp(self, **kwargs):
        """
        Enable the Self-Evolving Quality Pipeline.

        SEQP continuously analyzes application code, generates adversarial
        tests, rewrites CI/CD pipelines, and enforces dynamic deployment
        policies based on code risk and runtime behavior.

        Args:
            scan_paths: List of paths to scan for risk analysis
            pipeline_platform: CI/CD platform ("github_actions", "gitlab_ci")
            pipeline_output: Path to write generated pipeline config
            latency_drift_tolerance: Max allowed latency increase (default: 0.20)
            error_rate_threshold: Max error rate for deployment (default: 0.02)
            auto_generate_tests: Auto-generate tests on evolve (default: True)
            auto_rewrite_pipeline: Auto-rewrite CI/CD config (default: True)

        Example:
            app = Ishaa()
            app.enable_seqp(pipeline_platform="github_actions")

            @app.route("/payment")
            @app.critical(level="financial_core")
            async def process_payment(request):
                ...
        """
        from .seqp import SelfEvolvingQualityPipeline

        self.seqp = SelfEvolvingQualityPipeline(**kwargs)
        self.seqp.attach(self)

        logger.info("SEQP engine enabled - Self-Evolving Quality Pipeline active")
        return self.seqp

    def critical(self, level: str = "standard", description: str = ""):
        """
        Decorator to tag a route handler with business criticality.

        Criticality levels affect SEQP test generation, coverage thresholds,
        deployment gates, and pipeline configuration.

        Levels:
            - "financial_core": Highest scrutiny (payment, billing)
            - "security_critical": Auth, encryption, token routes
            - "data_critical": Data mutation, migration routes
            - "standard": Normal routes (default)

        Example:
            @app.route("/payment")
            @app.critical(level="financial_core")
            async def process_payment(request):
                ...
        """
        if self.seqp is None:
            raise RuntimeError(
                "SEQP is not enabled. Call app.enable_seqp() before using @app.critical()"
            )
        return self.seqp.critical_decorator(level=level, description=description)

    # ── Routing ──────────────────────────────────────────────────────

    def route(self, path: str, methods: List[str] = None, name: str = None):
        """Decorator to register a route."""
        original_decorator = self.router.route(path, methods, name)

        def wrapper(func):
            result = original_decorator(func)
            # If RMF is enabled and handler has pending reality registrations
            if self.rmf is not None and hasattr(result, "_rmf_pending") and result._rmf_pending:
                self.rmf.finalize_route(path, result, methods)
            return result

        return wrapper

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
        1. SARE pre-route (cache check + optimization trigger)
        2. Run before_request middleware (with timing for SARE)
        3. RMF reality-mode routing (if active)
        4. Route resolution (hot-path aware)
        5. Call handler
        6. Run after_request middleware
        7. SARE post-route (record metrics + learn patterns)
        8. SEQP metrics recording
        9. Error handling
        """
        import time as _time
        request_start = _time.monotonic()
        matched_route = None

        try:
            # 1. SARE pre-route hook
            if self.sare is not None:
                sare_result = await self.sare.before_request(request)
                if sare_result is not None:
                    # Serve from SARE response cache
                    if isinstance(sare_result, dict) and "body" in sare_result:
                        return Response(
                            body=sare_result["body"],
                            status_code=sare_result.get("status_code", 200),
                            headers=sare_result.get("headers", {}),
                            content_type=sare_result.get("content_type", "text/plain"),
                        )
                    return self._ensure_response(sare_result)

            # 2. Run before-request middleware (with SARE timing)
            if self.sare is not None:
                early_response = await self._run_middleware_with_sare_timing(
                    request, phase="before"
                )
            else:
                early_response = await self.middleware.run_before(request)

            if early_response is not None:
                return self._ensure_response(early_response)

            # 3. RMF reality-mode routing
            if self.rmf is not None and self.rmf.has_reality_route(request.path):
                response = await self.rmf.handle_request(request, self._call_handler)
                if response is not None:
                    response = self._ensure_response(response)

                    # Run after-request middleware
                    if self.sare is not None:
                        response = await self._run_middleware_with_sare_timing(
                            request, phase="after", response=response
                        )
                    else:
                        response = await self.middleware.run_after(request, response)

                    # SEQP metrics recording
                    if self.seqp is not None:
                        latency_ms = (_time.monotonic() - request_start) * 1000
                        is_error = response.status_code >= 500
                        self.seqp.record_request_metrics(
                            request.path, latency_ms, error=is_error
                        )

                    return response

            # 4. Resolve route (normal flow)
            route, params = self.router.resolve(request.path, request.method)
            matched_route = route

            if route is None:
                if params.get("_method_not_allowed"):
                    allowed = params.get("_allowed", set())
                    response = await self._handle_error(request, 405, "Method Not Allowed")
                    response.headers["allow"] = ", ".join(sorted(allowed))
                    return response
                return await self._handle_error(request, 404, "Not Found")

            # 4. Set path params on request
            request.path_params = params

            # 5. Call the route handler
            response = await self._call_handler(route.handler, request, **params)

            # 6. Run after-request middleware
            if self.sare is not None:
                response = await self._run_middleware_with_sare_timing(
                    request, phase="after", response=response
                )
            else:
                response = await self.middleware.run_after(request, response)

            # 7. SARE post-route hook
            if self.sare is not None:
                latency = _time.monotonic() - request_start
                await self.sare.after_request(
                    request, response, route=matched_route, latency=latency
                )

            # 8. SEQP runtime metrics recording
            if self.seqp is not None:
                latency_ms = (_time.monotonic() - request_start) * 1000
                is_error = response.status_code >= 500
                self.seqp.record_request_metrics(
                    request.path, latency_ms, error=is_error
                )

            return response

        except Exception as exc:
            logger.error(f"Error handling {request.method} {request.path}: {exc}")
            if self.debug:
                logger.error(traceback.format_exc())

            # Record error in SARE
            if self.sare is not None and matched_route is not None:
                latency = _time.monotonic() - request_start
                self.sare.analyzer.record_request(
                    method=request.method,
                    path_pattern=matched_route.path,
                    latency=latency,
                    status_code=500,
                )

            # Record error in SEQP
            if self.seqp is not None:
                latency_ms = (_time.monotonic() - request_start) * 1000
                self.seqp.record_request_metrics(request.path, latency_ms, error=True)

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

    async def _run_middleware_with_sare_timing(self, request, phase="before", response=None):
        """
        Run middleware pipeline with per-middleware timing for SARE.
        Feeds execution cost data to the SARE optimizer.
        """
        import time as _time

        if phase == "before":
            # Time each middleware instance
            for mw in self.middleware._middleware_instances:
                mw_name = mw.__class__.__name__
                start = _time.monotonic()
                result = await mw.before_request(request)
                elapsed = _time.monotonic() - start
                short_circuited = result is not None
                self.sare.record_middleware_timing(mw_name, elapsed, short_circuited)
                if result is not None:
                    return result

            # Time function hooks
            for hook in self.middleware._before:
                hook_name = getattr(hook, "__name__", "hook")
                start = _time.monotonic()
                result = await hook(request)
                elapsed = _time.monotonic() - start
                self.sare.record_middleware_timing(f"hook:{hook_name}", elapsed, result is not None)
                if result is not None:
                    return result

            return None

        elif phase == "after":
            # Time function hooks
            for hook in self.middleware._after:
                hook_name = getattr(hook, "__name__", "hook")
                start = _time.monotonic()
                result = await hook(request, response)
                elapsed = _time.monotonic() - start
                self.sare.record_middleware_timing(f"hook:{hook_name}", elapsed)
                if result is not None:
                    response = result

            # Time middleware instances (reverse order)
            for mw in reversed(self.middleware._middleware_instances):
                mw_name = mw.__class__.__name__
                start = _time.monotonic()
                result = await mw.after_request(request, response)
                elapsed = _time.monotonic() - start
                self.sare.record_middleware_timing(mw_name, elapsed)
                if result is not None:
                    response = result

            return response

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
        print(f"""\n✦ Ishaa Framework v{__version__}""")
        print(f"  Running on: http://{host}:{port}")
        print(f"  Debug mode: {'ON' if self.debug else 'OFF'}")
        if self.sare is not None:
            print(f"  SARE:       ACTIVE (Self-Evolving Adaptive Routing Engine)")
        if self.rmf is not None:
            rmf_count = len(self.rmf._routes)
            print(f"  RMF:        ACTIVE (Reality-Mode Framework - {rmf_count} reality routes)")
        if self.seqp is not None:
            print(f"  SEQP:       ACTIVE (Self-Evolving Quality Pipeline)")
        print(f"  Press Ctrl+C to stop\n")

        try:
            from .server import run_server
            run_server(self, host, port)
        except KeyboardInterrupt:
            print("\n✦ Ishaa server stopped.")

    def __repr__(self):
        return f"<Ishaa '{self.name}' routes={len(self.router.routes)}>"
