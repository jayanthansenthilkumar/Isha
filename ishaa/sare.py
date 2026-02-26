"""
Ishaa SARE — Self-Evolving Adaptive Routing Engine

The world's first web framework feature that automatically rewrites and
optimizes its own routing + middleware execution flow based on real-time
traffic intelligence.

    Not monitoring. Not logging. Actually self-optimizing.

Architecture:
    Client Request
          ↓
    Traffic Analyzer          ← observes every request
          ↓
    Adaptive Optimizer Engine ← decides what to optimize
          ↓
    Dynamic Routing Layer     ← hot routes get fast-path
          ↓
    Middleware Execution Engine← reordered for best perf
          ↓
    Code Path Optimizer       ← memoization + fast JSON
          ↓
    Latency Predictor         ← predicts spikes + trends
          ↓
    Intelligence Reporter     ← generates self-improvement reports
          ↓
    Response

Usage:
    from ishaa import Ishaa

    app = Ishaa()
    app.enable_sare()           # one line to enable

    # Or with config:
    app.enable_sare(
        optimize_interval=10.0,
        cache_size=500,
        cache_ttl=30.0,
        hot_route_slots=20,
        middleware_reorder=True,
        predictor=True,
    )

    # Access intelligence report
    @app.route("/sare/report")
    async def sare_report(request):
        return app.sare.report()

    # Console report
    app.sare.print_report()
"""

import time
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .sare_traffic import TrafficAnalyzer, RouteMetrics
from .sare_optimizer import AdaptiveOptimizer
from .sare_predictor import LatencyPredictor
from .sare_codepath import CodePathOptimizer
from .sare_reporter import IntelligenceReporter

logger = logging.getLogger("ishaa.sare")


class SARE:
    """
    Self-Evolving Adaptive Routing Engine.

    Integrates all SARE components into a unified engine that plugs into
    the Ishaa request pipeline.

    The engine operates in three phases per request:
    1. PRE-ROUTE:  Check hot cache + response memoization
    2. POST-ROUTE: Record metrics + learn response structure
    3. PERIODIC:   Run optimization cycle + update predictions
    """

    def __init__(
        self,
        optimize_interval: float = 10.0,
        snapshot_interval: float = 5.0,
        cache_max_size: int = 500,
        cache_default_ttl: float = 30.0,
        hot_route_slots: int = 20,
        middleware_reorder: bool = True,
        predictor_enabled: bool = True,
        auto_memoize: bool = True,
        auto_memoize_rps_threshold: float = 5.0,
        auto_memoize_error_threshold: float = 0.02,
    ):
        # ── Core Components ──────────────────────────────────────
        self.analyzer = TrafficAnalyzer(
            window_size=1000,
            snapshot_interval=snapshot_interval,
        )

        self.optimizer = AdaptiveOptimizer(
            analyzer=self.analyzer,
            optimize_interval=optimize_interval,
            hot_route_slots=hot_route_slots,
        )
        self.optimizer.middleware_reorder_enabled = middleware_reorder

        self.predictor = LatencyPredictor(analyzer=self.analyzer)
        self.predictor_enabled = predictor_enabled

        self.codepath = CodePathOptimizer(
            cache_max_size=cache_max_size,
            cache_default_ttl=cache_default_ttl,
        )

        self.reporter = IntelligenceReporter(
            analyzer=self.analyzer,
            optimizer=self.optimizer,
            predictor=self.predictor,
            codepath=self.codepath,
        )

        # ── Auto-memoize Settings ────────────────────────────────
        self.auto_memoize = auto_memoize
        self.auto_memoize_rps_threshold = auto_memoize_rps_threshold
        self.auto_memoize_error_threshold = auto_memoize_error_threshold

        # ── State ────────────────────────────────────────────────
        self._enabled = True
        self._optimization_task: Optional[asyncio.Task] = None
        self._app = None  # set when integrated

        logger.info("SARE engine initialized — Self-Evolving Adaptive Routing Engine active")

    # ── Integration with Ishaa App ────────────────────────────────────

    def attach(self, app):
        """Attach SARE to an Ishaa application instance."""
        self._app = app
        logger.info("SARE attached to Ishaa application")

    # ── Request Pipeline Hooks ───────────────────────────────────────

    async def before_request(self, request) -> Optional[Any]:
        """
        SARE pre-route hook. Called before route resolution.

        1. Periodic optimization trigger
        2. Check response memo cache
        """
        if not self._enabled:
            return None

        # Trigger optimization cycle (non-blocking check)
        self.optimizer.maybe_optimize()

        # Auto-memoize candidates based on learned patterns
        if self.auto_memoize:
            self._auto_memoize_check()

        # Try serving from response cache
        route_id = f"{request.method} {request.path}"
        query_string = request.scope.get("query_string", b"")
        if isinstance(query_string, bytes):
            query_string = query_string.decode("utf-8", errors="replace")

        cached = self.codepath.try_cache_hit(
            route_id, request.method, request.path, query_string
        )
        if cached is not None:
            logger.debug(f"SARE cache hit: {route_id}")
            return cached  # Will be converted to response by app

        return None

    async def after_request(self, request, response, route=None, latency: float = 0.0):
        """
        SARE post-route hook. Called after response is generated.

        1. Record traffic metrics
        2. Record middleware metrics
        3. Store in response cache if enabled
        4. Learn JSON structure for pre-encoding
        5. Update predictor
        """
        if not self._enabled:
            return

        # Determine route pattern for tracking
        path_pattern = request.path
        if route is not None:
            path_pattern = route.path  # Use pattern, not concrete path

        route_id = f"{request.method} {path_pattern}"

        # 1. Record traffic metrics
        status_code = getattr(response, "status_code", 200)
        body = getattr(response, "body", b"")
        response_size = len(body) if isinstance(body, (bytes, bytearray)) else 0

        self.analyzer.record_request(
            method=request.method,
            path_pattern=path_pattern,
            latency=latency,
            status_code=status_code,
            response_size=response_size,
        )

        # 2. Store response in cache if memoization is enabled
        if status_code < 400:  # Only cache successful responses
            query_string = request.scope.get("query_string", b"")
            if isinstance(query_string, bytes):
                query_string = query_string.decode("utf-8", errors="replace")

            self.codepath.store_response(
                route_id=route_id,
                method=request.method,
                path=request.path,
                query_string=query_string,
                response_data={
                    "body": body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body),
                    "status_code": status_code,
                    "content_type": getattr(response, "content_type", "text/plain"),
                    "headers": dict(getattr(response, "headers", {})),
                },
            )

        # 3. Learn JSON structure
        if hasattr(response, "body") and status_code < 400:
            try:
                import json
                data = json.loads(body)
                if isinstance(data, dict):
                    self.codepath.try_fast_encode(route_id, data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # 4. Update predictor periodically
        if self.predictor_enabled:
            self.predictor.update()

    def record_middleware_timing(self, name: str, latency: float, short_circuited: bool = False):
        """Record middleware execution metrics."""
        if self._enabled:
            self.analyzer.record_middleware(name, latency, short_circuited)

    # ── Auto-Memoize Logic ───────────────────────────────────────────

    def _auto_memoize_check(self):
        """
        Automatically enable memoization for routes that meet criteria:
        - High RPS (hot)
        - Low error rate (stable)
        - GET method only
        """
        hot_routes = self.analyzer.get_hot_routes(20)
        for rm in hot_routes:
            if rm.method != "GET":
                continue
            route_id = f"{rm.method} {rm.path}"
            if route_id in self.codepath._memoized_routes:
                continue

            if (rm.requests_per_second >= self.auto_memoize_rps_threshold
                    and rm.error_rate <= self.auto_memoize_error_threshold
                    and rm.total_requests >= 50):
                self.codepath.enable_memoization(route_id)
                self.codepath.enable_preencoding(route_id)
                logger.info(f"SARE auto-memoize: Enabled for {route_id} "
                           f"(RPS={rm.requests_per_second:.1f}, err={rm.error_rate:.3f})")

    # ── Dynamic Middleware Reordering ─────────────────────────────────

    def get_optimized_middleware_order(self) -> Optional[List[str]]:
        """
        Return the optimizer's recommended middleware order.
        The MiddlewareStack can use this to reorder execution.
        """
        return self.optimizer.get_optimal_middleware_order()

    # ── Hot Route Query ──────────────────────────────────────────────

    def is_hot_route(self, method: str, path_pattern: str) -> bool:
        """Check if a route is in the optimizer's hot cache."""
        return self.optimizer.is_hot_route(method, path_pattern)

    # ── Reports ──────────────────────────────────────────────────────

    def report(self) -> Dict[str, Any]:
        """Generate a full intelligence report as a dict."""
        return self.reporter.generate_report()

    def print_report(self):
        """Print a formatted intelligence report to console."""
        return self.reporter.print_report()

    def report_json(self) -> str:
        """Generate a full intelligence report as JSON."""
        return self.reporter.to_json()

    # ── Control ──────────────────────────────────────────────────────

    def enable(self):
        """Enable SARE processing."""
        self._enabled = True
        logger.info("SARE engine enabled")

    def disable(self):
        """Disable SARE processing (pass-through mode)."""
        self._enabled = False
        logger.info("SARE engine disabled")

    def reset(self):
        """Reset all SARE state and caches."""
        self.analyzer.reset()
        self.codepath.response_cache.clear()
        logger.info("SARE engine reset")

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return combined stats from all SARE components."""
        return {
            "enabled": self._enabled,
            "traffic": self.analyzer.summary(),
            "optimizer": self.optimizer.get_stats(),
            "codepath": self.codepath.stats(),
            "predictions": (
                self.predictor.full_prediction_report()
                if self.predictor_enabled
                else {"status": "disabled"}
            ),
        }

    def __repr__(self):
        status = "active" if self._enabled else "disabled"
        reqs = self.analyzer.total_requests
        return f"<SARE engine={status} requests={reqs} optimizations={self.optimizer._optimization_count}>"
