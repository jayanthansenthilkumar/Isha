"""
Ishaa Reality-Mode Framework (RMF) — One Codebase. Multiple Realities.

World-first execution-layer abstraction that allows the same route to exist
in multiple behavioral universes. Each request can enter a different "reality"
with different logic, middleware, caching, and security rules — without
conditional clutter or branching code.

Features:
    - Reality decorators: @app.reality("stable"), @app.reality("experimental")
    - Reality Selector Engine: route users by %, behavior, risk, time window
    - Parallel Simulation Mode: run multiple realities, compare outputs
    - Time-Bound Realities: auto-activate/deactivate on schedule
    - Self-Retiring Realities: auto-promote proven experimental logic
    - Reality-scoped middleware, caching, and security

Usage:
    from ishaa import Ishaa

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

    app.run()
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ishaa.rmf")


# ─── Reality Configuration ──────────────────────────────────────────────

class RealityConfig:
    """Configuration for a single reality layer."""

    def __init__(
        self,
        name: str,
        traffic_pct: float = 100.0,
        active_between: Optional[str] = None,
        sticky: bool = True,
        auto_promote: bool = False,
        promote_after_requests: int = 1000,
        promote_error_threshold: float = 0.02,
        promote_latency_ratio: float = 1.1,
        middleware: Optional[List[Any]] = None,
        cache_ttl: Optional[float] = None,
        priority: int = 0,
        tags: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.traffic_pct = traffic_pct
        self.active_between = active_between
        self.sticky = sticky
        self.auto_promote = auto_promote
        self.promote_after_requests = promote_after_requests
        self.promote_error_threshold = promote_error_threshold
        self.promote_latency_ratio = promote_latency_ratio
        self.middleware = middleware or []
        self.cache_ttl = cache_ttl
        self.priority = priority
        self.tags = tags or {}

        # Parsed time window
        self._time_start: Optional[datetime] = None
        self._time_end: Optional[datetime] = None
        if active_between:
            self._parse_time_window(active_between)

    def _parse_time_window(self, spec: str):
        """Parse 'Mon DD - Mon DD' or 'YYYY-MM-DD - YYYY-MM-DD' time windows."""
        try:
            parts = [p.strip() for p in spec.split("-", 1)]
            if len(parts) == 2:
                for fmt in ("%b %d", "%Y-%m-%d", "%B %d", "%m/%d"):
                    try:
                        now = datetime.now(timezone.utc)
                        start = datetime.strptime(parts[0].strip(), fmt)
                        end = datetime.strptime(parts[1].strip(), fmt)
                        start = start.replace(year=now.year, tzinfo=timezone.utc)
                        end = end.replace(year=now.year, tzinfo=timezone.utc)
                        if end < start:
                            end = end.replace(year=now.year + 1)
                        self._time_start = start
                        self._time_end = end
                        return
                    except ValueError:
                        continue
        except Exception:
            logger.warning(f"RMF: Could not parse time window: {spec}")

    def is_time_active(self) -> bool:
        """Check if this reality is currently active based on time window."""
        if self._time_start is None:
            return True
        now = datetime.now(timezone.utc)
        return self._time_start <= now <= self._time_end


# ─── Reality Handler ────────────────────────────────────────────────────

class RealityHandler:
    """Wraps a handler with its reality configuration."""

    def __init__(self, handler: Callable, config: RealityConfig):
        self.handler = handler
        self.config = config
        self.name = config.name

        # Metrics
        self.total_requests = 0
        self.total_errors = 0
        self.latency_sum = 0.0
        self.latency_count = 0
        self._created_at = time.monotonic()

    @property
    def avg_latency(self) -> float:
        if self.latency_count == 0:
            return 0.0
        return self.latency_sum / self.latency_count

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests

    def record_success(self, latency: float):
        self.total_requests += 1
        self.latency_sum += latency
        self.latency_count += 1

    def record_error(self, latency: float):
        self.total_requests += 1
        self.total_errors += 1
        self.latency_sum += latency
        self.latency_count += 1


# ─── Reality Route ──────────────────────────────────────────────────────

class RealityRoute:
    """
    A multi-reality route: same path, multiple handlers in different realities.
    """

    def __init__(self, path: str, methods: Set[str]):
        self.path = path
        self.methods = methods
        self.realities: Dict[str, RealityHandler] = {}
        self.default_reality: Optional[str] = None

    def add_reality(self, handler: Callable, config: RealityConfig):
        """Register a handler for a specific reality."""
        rh = RealityHandler(handler, config)
        self.realities[config.name] = rh
        if config.name == "stable" or self.default_reality is None:
            self.default_reality = config.name
        logger.debug(f"RMF: Added reality '{config.name}' for {self.path}")

    def get_reality_names(self) -> List[str]:
        return list(self.realities.keys())


# ─── Reality Selector Engine ────────────────────────────────────────────

class RealitySelectorEngine:
    """
    Determines which reality a request enters.

    Selection criteria (in priority order):
    1. Explicit header: X-Reality
    2. Cookie-based sticky session
    3. User behavior/risk profile (via tags)
    4. Time-bound window check
    5. Traffic percentage allocation
    """

    def __init__(self, sticky_cookie: str = "_ishaa_reality"):
        self.sticky_cookie = sticky_cookie
        self._user_assignments: Dict[str, Dict[str, str]] = {}  # path -> {user_id: reality}
        self._behavior_rules: List[Callable] = []

    def add_behavior_rule(self, rule_fn: Callable):
        """
        Add a custom behavior rule for reality selection.
        rule_fn(request, available_realities) -> Optional[str]
        """
        self._behavior_rules.append(rule_fn)

    def select(self, request, route: RealityRoute) -> str:
        """Select the appropriate reality for this request."""
        available = route.realities

        # 1. Explicit header override
        explicit = request.headers.get("x-reality")
        if explicit and explicit in available:
            return explicit

        # 2. Cookie-based sticky session
        cookie_key = f"{self.sticky_cookie}_{route.path}"
        cookie_val = request.cookies.get(cookie_key.replace("/", "_"))
        if cookie_val and cookie_val in available:
            return cookie_val

        # 3. Custom behavior rules
        for rule_fn in self._behavior_rules:
            try:
                result = rule_fn(request, list(available.keys()))
                if result and result in available:
                    return result
            except Exception:
                continue

        # 4. Filter by time-bound window
        active_realities = {
            name: rh for name, rh in available.items()
            if rh.config.is_time_active()
        }
        if not active_realities:
            active_realities = available

        # 5. Traffic percentage allocation (deterministic hash-based)
        return self._traffic_select(request, route, active_realities)

    def _traffic_select(
        self, request, route: RealityRoute, realities: Dict[str, RealityHandler]
    ) -> str:
        """Select reality based on traffic percentage using deterministic hashing."""
        # Create a stable hash for this user/request
        seed = self._get_request_seed(request, route.path)

        # Sort realities by priority, then name for determinism
        sorted_realities = sorted(
            realities.values(),
            key=lambda r: (-r.config.priority, r.name),
        )

        # Weighted selection
        total_pct = sum(r.config.traffic_pct for r in sorted_realities)
        if total_pct <= 0:
            return route.default_reality or sorted_realities[0].name

        # Normalize to 0-1 range using hash
        hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16) % 10000
        position = hash_val / 10000.0

        cumulative = 0.0
        for rh in sorted_realities:
            cumulative += rh.config.traffic_pct / total_pct
            if position < cumulative:
                return rh.name

        return sorted_realities[-1].name

    def _get_request_seed(self, request, path: str) -> str:
        """Generate a deterministic seed for consistent reality assignment."""
        # Use client IP + user-agent for sticky assignment
        ip = ""
        if hasattr(request, "client") and request.client:
            ip = str(request.client[0]) if isinstance(request.client, tuple) else str(request.client)
        ua = request.headers.get("user-agent", "")
        return f"{ip}:{ua}:{path}"


# ─── Parallel Simulation Engine ─────────────────────────────────────────

class ParallelSimulationEngine:
    """
    Runs multiple realities in parallel for the same request.
    User sees the primary reality's response; other realities run silently
    in the background for comparison and drift measurement.
    """

    def __init__(self, enabled: bool = False, max_parallel: int = 3):
        self.enabled = enabled
        self.max_parallel = max_parallel
        self._comparison_log: List[Dict[str, Any]] = []
        self._max_log_size = 500

    async def simulate(
        self,
        request,
        primary_reality: str,
        route: RealityRoute,
        call_handler_fn: Callable,
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Execute the primary reality and background realities in parallel.

        Returns:
            (primary_response, comparison_results)
        """
        if not self.enabled:
            rh = route.realities[primary_reality]
            start = time.monotonic()
            response = await call_handler_fn(rh.handler, request)
            latency = time.monotonic() - start
            rh.record_success(latency)
            return response, []

        # Run primary + shadow realities in parallel
        shadow_realities = [
            name for name in route.realities
            if name != primary_reality
        ][:self.max_parallel - 1]

        primary_rh = route.realities[primary_reality]
        tasks = {}

        # Primary task
        async def run_reality(rh_: RealityHandler):
            start_ = time.monotonic()
            try:
                resp = await call_handler_fn(rh_.handler, request)
                lat = time.monotonic() - start_
                rh_.record_success(lat)
                return {"reality": rh_.name, "latency": lat, "status": "ok", "response": resp}
            except Exception as e:
                lat = time.monotonic() - start_
                rh_.record_error(lat)
                return {"reality": rh_.name, "latency": lat, "status": "error", "error": str(e)}

        # Create all tasks
        all_tasks = [run_reality(primary_rh)]
        for sname in shadow_realities:
            all_tasks.append(run_reality(route.realities[sname]))

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        primary_result = results[0] if not isinstance(results[0], Exception) else {
            "reality": primary_reality, "status": "error", "error": str(results[0])
        }

        comparisons = []
        for r in results[1:]:
            if isinstance(r, Exception):
                comparisons.append({"status": "error", "error": str(r)})
            else:
                drift = self._measure_drift(primary_result, r)
                comparison = {
                    "shadow_reality": r.get("reality"),
                    "shadow_latency": r.get("latency", 0),
                    "primary_latency": primary_result.get("latency", 0),
                    "drift_score": drift,
                    "shadow_status": r.get("status"),
                }
                comparisons.append(comparison)

        # Log comparison
        if comparisons:
            entry = {
                "timestamp": time.time(),
                "path": route.path,
                "primary": primary_reality,
                "comparisons": comparisons,
            }
            self._comparison_log.append(entry)
            if len(self._comparison_log) > self._max_log_size:
                self._comparison_log = self._comparison_log[-self._max_log_size:]

        return primary_result.get("response"), comparisons

    def _measure_drift(self, primary: Dict, shadow: Dict) -> float:
        """
        Measure behavioral drift between primary and shadow reality.
        Returns a 0.0-1.0 drift score (0 = identical, 1 = completely different).
        """
        drift = 0.0
        weights = 0.0

        # Latency drift
        p_lat = primary.get("latency", 0)
        s_lat = shadow.get("latency", 0)
        if p_lat > 0:
            lat_ratio = abs(s_lat - p_lat) / max(p_lat, 0.001)
            drift += min(lat_ratio, 2.0) * 0.3
            weights += 0.3

        # Status drift
        if primary.get("status") != shadow.get("status"):
            drift += 0.5
        weights += 0.5

        # Response body drift (if both have responses)
        p_resp = primary.get("response")
        s_resp = shadow.get("response")
        if p_resp is not None and s_resp is not None:
            try:
                p_body = str(getattr(p_resp, "body", p_resp))
                s_body = str(getattr(s_resp, "body", s_resp))
                if p_body != s_body:
                    # Simple length-based heuristic
                    max_len = max(len(p_body), len(s_body), 1)
                    diff_len = abs(len(p_body) - len(s_body))
                    drift += min(diff_len / max_len, 1.0) * 0.2
                weights += 0.2
            except Exception:
                pass

        return min(drift / max(weights, 0.01), 1.0)

    def get_comparison_log(self) -> List[Dict[str, Any]]:
        """Get the simulation comparison history."""
        return list(self._comparison_log)


# ─── Self-Retiring Engine ───────────────────────────────────────────────

class SelfRetiringEngine:
    """
    Monitors experimental realities and automatically promotes them to stable
    when they prove reliable. Retired realities are cleaned up automatically.
    """

    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self._last_check = time.monotonic()
        self._promotion_history: List[Dict[str, Any]] = []
        self._retired: List[Dict[str, Any]] = []

    def check_promotions(self, reality_routes: Dict[str, "RealityRoute"]):
        """Check all routes for realities ready for promotion."""
        now = time.monotonic()
        if now - self._last_check < self.check_interval:
            return
        self._last_check = now

        for path, route in reality_routes.items():
            stable_rh = route.realities.get("stable")
            for name, rh in list(route.realities.items()):
                if name == "stable":
                    continue
                if not rh.config.auto_promote:
                    continue
                if self._should_promote(rh, stable_rh):
                    self._promote(route, name)

    def _should_promote(
        self, candidate: RealityHandler, stable: Optional[RealityHandler]
    ) -> bool:
        """Determine if a candidate reality should be promoted to stable."""
        cfg = candidate.config

        # Must meet minimum request count
        if candidate.total_requests < cfg.promote_after_requests:
            return False

        # Error rate must be below threshold
        if candidate.error_rate > cfg.promote_error_threshold:
            return False

        # If there's a stable version, compare latency
        if stable and stable.avg_latency > 0:
            latency_ratio = candidate.avg_latency / max(stable.avg_latency, 0.001)
            if latency_ratio > cfg.promote_latency_ratio:
                return False

        return True

    def _promote(self, route: RealityRoute, reality_name: str):
        """Promote a reality to stable, retiring the old stable."""
        old_stable = route.realities.get("stable")
        candidate = route.realities.get(reality_name)

        if not candidate:
            return

        # Record history
        entry = {
            "timestamp": time.time(),
            "path": route.path,
            "promoted": reality_name,
            "old_stable_requests": old_stable.total_requests if old_stable else 0,
            "new_stable_requests": candidate.total_requests,
            "new_stable_error_rate": candidate.error_rate,
            "new_stable_avg_latency": candidate.avg_latency,
        }

        # Retire old stable
        if old_stable:
            self._retired.append({
                "timestamp": time.time(),
                "path": route.path,
                "reality": "stable",
                "requests": old_stable.total_requests,
                "error_rate": old_stable.error_rate,
            })

        # Promote: swap handler
        route.realities["stable"] = RealityHandler(
            candidate.handler, RealityConfig(name="stable")
        )
        route.default_reality = "stable"

        # Retire the experimental
        self._retired.append({
            "timestamp": time.time(),
            "path": route.path,
            "reality": reality_name,
            "action": "promoted_to_stable",
        })
        del route.realities[reality_name]

        self._promotion_history.append(entry)
        logger.info(
            f"RMF: Auto-promoted '{reality_name}' → 'stable' for {route.path} "
            f"(requests={candidate.total_requests}, error_rate={candidate.error_rate:.4f})"
        )


# ─── Reality-Mode Framework (Main Engine) ───────────────────────────────

class RealityModeFramework:
    """
    The Reality-Mode Framework engine.

    One route. Multiple parallel realities. Each request can exist in a
    different behavioral universe — with different logic, middleware,
    caching, and security rules — without branching code.

    Architecture:
        Incoming Request
              ↓
        Reality Selector Engine
              ↓
        Execution Universe Loader
              ↓
        Route + Middleware (Reality Scoped)
              ↓
        Response
    """

    def __init__(
        self,
        sticky_cookie: str = "_ishaa_reality",
        parallel_simulation: bool = False,
        max_parallel: int = 3,
        auto_retire_check: float = 60.0,
    ):
        self.selector = RealitySelectorEngine(sticky_cookie=sticky_cookie)
        self.simulator = ParallelSimulationEngine(
            enabled=parallel_simulation, max_parallel=max_parallel
        )
        self.retiree = SelfRetiringEngine(check_interval=auto_retire_check)

        # Reality routes: path -> RealityRoute
        self._reality_routes: Dict[str, RealityRoute] = {}
        self._app = None

        logger.info("RMF: Reality-Mode Framework initialized")

    def attach(self, app):
        """Attach the RMF engine to an Ishaa application."""
        self._app = app
        logger.info("RMF: Attached to Ishaa application")

    # ── Registration ────────────────────────────────────────────────

    def register_reality(
        self,
        path: str,
        handler: Callable,
        reality_name: str,
        methods: Optional[List[str]] = None,
        **kwargs,
    ):
        """Register a handler for a specific reality on a route."""
        method_set = {m.upper() for m in (methods or ["GET"])}
        if "GET" in method_set:
            method_set.add("HEAD")

        route_key = path
        if route_key not in self._reality_routes:
            self._reality_routes[route_key] = RealityRoute(path, method_set)

        config = RealityConfig(name=reality_name, **kwargs)
        self._reality_routes[route_key].add_reality(handler, config)

    def reality_decorator(
        self,
        reality_name: str,
        traffic_pct: float = 100.0,
        active_between: Optional[str] = None,
        sticky: bool = True,
        auto_promote: bool = False,
        promote_after_requests: int = 1000,
        promote_error_threshold: float = 0.02,
        promote_latency_ratio: float = 1.1,
        middleware: Optional[List[Any]] = None,
        cache_ttl: Optional[float] = None,
        priority: int = 0,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator factory to register a handler for a reality.

        Usage:
            @app.route("/recommend")
            @app.reality("stable")
            async def recommend_v1(request):
                return {"algo": "classic"}

            @app.route("/recommend")
            @app.reality("experimental", traffic_pct=20, auto_promote=True)
            async def recommend_v2(request):
                return {"algo": "neural"}
        """
        def decorator(func):
            # The route path is extracted from the function's _rmf_route if set
            # Otherwise deferred until route() is called
            if not hasattr(func, "_rmf_pending"):
                func._rmf_pending = []
            func._rmf_pending.append({
                "reality_name": reality_name,
                "traffic_pct": traffic_pct,
                "active_between": active_between,
                "sticky": sticky,
                "auto_promote": auto_promote,
                "promote_after_requests": promote_after_requests,
                "promote_error_threshold": promote_error_threshold,
                "promote_latency_ratio": promote_latency_ratio,
                "middleware": middleware,
                "cache_ttl": cache_ttl,
                "priority": priority,
                "tags": tags or {},
            })
            return func
        return decorator

    def finalize_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None):
        """Called by the app's route() to finalize pending reality registrations."""
        if hasattr(handler, "_rmf_pending") and handler._rmf_pending:
            for pending in handler._rmf_pending:
                self.register_reality(
                    path=path,
                    handler=handler,
                    methods=methods,
                    **pending,
                )
            handler._rmf_pending = []
            return True
        return False

    # ── Request Handling ────────────────────────────────────────────

    def has_reality_route(self, path: str) -> bool:
        """Check if a path has reality-mode handlers."""
        return path in self._reality_routes

    async def handle_request(self, request, call_handler_fn: Callable):
        """
        Handle a request through the reality pipeline.

        1. Find reality route
        2. Select reality via selector engine
        3. Run parallel simulation if enabled
        4. Apply reality-scoped middleware
        5. Check for auto-promotions
        """
        path = request.path
        route = self._reality_routes.get(path)

        if route is None:
            return None

        # Check method
        if request.method.upper() not in route.methods:
            return None

        # Select reality
        selected = self.selector.select(request, route)
        rh = route.realities.get(selected)
        if rh is None:
            selected = route.default_reality
            rh = route.realities.get(selected)
        if rh is None:
            return None

        # Tag the request
        request._reality = selected
        request._reality_route = route

        # Apply reality-scoped middleware (before)
        for mw in rh.config.middleware:
            if hasattr(mw, "before_request"):
                result = await mw.before_request(request)
                if result is not None:
                    return result

        # Run through simulation engine
        response, comparisons = await self.simulator.simulate(
            request, selected, route, call_handler_fn
        )

        # Apply reality-scoped middleware (after)
        for mw in rh.config.middleware:
            if hasattr(mw, "after_request"):
                result = await mw.after_request(request, response)
                if result is not None:
                    response = result

        # Add reality header to response
        if hasattr(response, "headers"):
            response.headers["X-Ishaa-Reality"] = selected
            if comparisons:
                response.headers["X-Ishaa-Simulation"] = json.dumps(
                    [{"reality": c.get("shadow_reality"), "drift": round(c.get("drift_score", 0), 4)}
                     for c in comparisons]
                )

        # Set sticky cookie
        if rh.config.sticky and hasattr(response, "set_cookie"):
            cookie_key = f"{self.selector.sticky_cookie}_{path}".replace("/", "_")
            response.set_cookie(cookie_key, selected, max_age=86400)

        # Check auto-promotions periodically
        self.retiree.check_promotions(self._reality_routes)

        return response

    # ── Behavior Rules ──────────────────────────────────────────────

    def add_behavior_rule(self, rule_fn: Callable):
        """
        Add a custom reality selection rule.

        Example:
            @app.rmf_behavior_rule
            def beta_users(request, realities):
                if request.headers.get("X-Beta") == "true":
                    return "experimental"
                return None
        """
        self.selector.add_behavior_rule(rule_fn)

    # ── Status & Reporting ──────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get RMF statistics."""
        routes = {}
        for path, route in self._reality_routes.items():
            realities = {}
            for name, rh in route.realities.items():
                realities[name] = {
                    "requests": rh.total_requests,
                    "errors": rh.total_errors,
                    "error_rate": round(rh.error_rate, 4),
                    "avg_latency_ms": round(rh.avg_latency * 1000, 2),
                    "traffic_pct": rh.config.traffic_pct,
                    "auto_promote": rh.config.auto_promote,
                    "time_active": rh.config.is_time_active(),
                }
            routes[path] = {
                "realities": realities,
                "default": route.default_reality,
            }

        return {
            "total_reality_routes": len(self._reality_routes),
            "parallel_simulation": self.simulator.enabled,
            "routes": routes,
            "promotions": self.retiree._promotion_history[-20:],
            "retired": self.retiree._retired[-20:],
            "simulation_log": self.simulator.get_comparison_log()[-10:],
        }

    def report(self) -> Dict[str, Any]:
        """Generate a full RMF intelligence report."""
        stats = self.stats()
        report_data = {
            "title": "Ishaa RMF Intelligence Report",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_routes": stats["total_reality_routes"],
                "parallel_simulation": stats["parallel_simulation"],
                "total_promotions": len(self.retiree._promotion_history),
                "total_retired": len(self.retiree._retired),
            },
            "routes": stats["routes"],
            "recent_promotions": stats["promotions"],
            "recent_simulations": stats["simulation_log"],
        }
        return report_data

    def print_report(self):
        """Print RMF report to console."""
        report = self.report()
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║           Ishaa RMF — Reality-Mode Framework Report            ║",
            "╚══════════════════════════════════════════════════════════════════╝",
            "",
            f"  Reality Routes:       {report['summary']['total_routes']}",
            f"  Parallel Simulation:  {'ON' if report['summary']['parallel_simulation'] else 'OFF'}",
            f"  Auto-Promotions:      {report['summary']['total_promotions']}",
            f"  Retired Realities:    {report['summary']['total_retired']}",
            "",
        ]
        for path, info in report["routes"].items():
            lines.append(f"  Route: {path}")
            lines.append(f"    Default Reality: {info['default']}")
            for name, r in info["realities"].items():
                lines.append(
                    f"    [{name}] requests={r['requests']}, "
                    f"errors={r['errors']}, "
                    f"latency={r['avg_latency_ms']}ms, "
                    f"traffic={r['traffic_pct']}%"
                )
            lines.append("")

        print("\n".join(lines))

    # ── Configuration ───────────────────────────────────────────────

    def enable_parallel_simulation(self, max_parallel: int = 3):
        """Enable parallel simulation mode."""
        self.simulator.enabled = True
        self.simulator.max_parallel = max_parallel
        logger.info(f"RMF: Parallel simulation enabled (max_parallel={max_parallel})")

    def disable_parallel_simulation(self):
        """Disable parallel simulation mode."""
        self.simulator.enabled = False

    def reset(self):
        """Reset all RMF state and metrics."""
        for route in self._reality_routes.values():
            for rh in route.realities.values():
                rh.total_requests = 0
                rh.total_errors = 0
                rh.latency_sum = 0.0
                rh.latency_count = 0
        self.simulator._comparison_log.clear()
        self.retiree._promotion_history.clear()
        self.retiree._retired.clear()
        logger.info("RMF: All state reset")
