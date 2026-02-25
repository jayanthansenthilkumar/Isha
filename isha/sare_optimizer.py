"""
Isha SARE — Adaptive Optimizer Engine

The decision-making core of SARE. Consumes traffic intelligence from the
TrafficAnalyzer and applies real-time optimizations:

1. Dynamic route prioritization (hot routes get O(1) fast-path)
2. Middleware auto-reordering based on execution cost & short-circuit rates
3. Coordination with CodePathOptimizer for memoization / caching decisions

This module operates autonomously — no human tuning required.
"""

import time
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict

from .sare_traffic import TrafficAnalyzer, RouteMetrics, MiddlewareMetrics

logger = logging.getLogger("isha.sare.optimizer")


class AdaptiveOptimizer:
    """
    The brain of SARE.

    Periodically evaluates traffic patterns and applies optimizations
    to the routing and middleware layers.
    """

    def __init__(
        self,
        analyzer: TrafficAnalyzer,
        optimize_interval: float = 10.0,
        hot_route_slots: int = 20,
        reorder_threshold: float = 0.15,
    ):
        self.analyzer = analyzer
        self.optimize_interval = optimize_interval
        self.hot_route_slots = hot_route_slots
        self.reorder_threshold = reorder_threshold

        # Optimized lookup caches
        self._hot_route_cache: OrderedDict = OrderedDict()  # path_pattern -> handler
        self._optimal_mw_order: Optional[List[str]] = None
        self._mw_order_changed: bool = False

        # Evolution log — records every optimization decision
        self._evolution_log: list = []
        self._optimization_count: int = 0

        self._lock = threading.Lock()
        self._last_optimize = 0.0

        # Configuration flags
        self.route_caching_enabled: bool = True
        self.middleware_reorder_enabled: bool = True

    # ── Optimization Cycle ───────────────────────────────────────────

    def maybe_optimize(self):
        """Run optimization cycle if the interval has elapsed."""
        now = time.monotonic()
        if now - self._last_optimize < self.optimize_interval:
            return
        self.run_optimization_cycle()

    def run_optimization_cycle(self):
        """Execute a full optimization cycle."""
        with self._lock:
            self._last_optimize = time.monotonic()
            self._optimization_count += 1

            cycle_actions = []

            # 1. Route heat optimization
            if self.route_caching_enabled:
                actions = self._optimize_hot_routes()
                cycle_actions.extend(actions)

            # 2. Middleware reordering
            if self.middleware_reorder_enabled:
                actions = self._optimize_middleware_order()
                cycle_actions.extend(actions)

            if cycle_actions:
                self._evolution_log.append({
                    "cycle": self._optimization_count,
                    "ts": time.time(),
                    "actions": cycle_actions,
                })
                for action in cycle_actions:
                    logger.info(f"SARE optimization: {action['type']} — {action['detail']}")

    # ── Route Optimization ───────────────────────────────────────────

    def _optimize_hot_routes(self) -> List[Dict[str, Any]]:
        """
        Identify hot routes and promote them to the fast-path cache.

        Hot routes are resolved in O(1) via a pre-built dict lookup instead
        of walking the route list.
        """
        actions = []
        hot_routes = self.analyzer.get_hot_routes(self.hot_route_slots)

        new_cache: OrderedDict = OrderedDict()
        for rm in hot_routes:
            if rm.heat_score > 0.1:  # minimum threshold
                key = (rm.method, rm.path)
                new_cache[key] = rm.heat_score

        # Detect promotions and demotions
        old_keys = set(self._hot_route_cache.keys())
        new_keys = set(new_cache.keys())

        promoted = new_keys - old_keys
        demoted = old_keys - new_keys

        if promoted:
            actions.append({
                "type": "route_promote",
                "detail": f"Promoted {len(promoted)} routes to hot cache: "
                          + ", ".join(f"{m} {p}" for m, p in promoted),
            })

        if demoted:
            actions.append({
                "type": "route_demote",
                "detail": f"Demoted {len(demoted)} routes from hot cache: "
                          + ", ".join(f"{m} {p}" for m, p in demoted),
            })

        self._hot_route_cache = new_cache
        return actions

    def is_hot_route(self, method: str, path_pattern: str) -> bool:
        """Check if a route is in the hot cache (for fast-path routing)."""
        return (method.upper(), path_pattern) in self._hot_route_cache

    def get_hot_route_keys(self) -> List[Tuple[str, str]]:
        """Return the current hot route keys in priority order."""
        return list(self._hot_route_cache.keys())

    # ── Middleware Reordering ────────────────────────────────────────

    def _optimize_middleware_order(self) -> List[Dict[str, Any]]:
        """
        Analyze middleware execution costs and short-circuit rates to
        determine the optimal execution order.

        Strategy:
        - Middleware with HIGH short-circuit rate should run FIRST
          (they save the most downstream work).
        - Among remaining, cheaper middleware runs first.
        - Never reorder if the delta is below reorder_threshold.
        """
        actions = []
        mw_metrics = self.analyzer.get_middleware_metrics()

        if len(mw_metrics) < 2:
            return actions

        # Score each middleware: higher = should run earlier
        scored: List[Tuple[str, float]] = []
        for name, mm in mw_metrics.items():
            # Short-circuit bonus: high SC rate means it often prevents downstream work
            sc_bonus = mm.short_circuit_rate * 3.0
            # Speed bonus: faster middleware should run first
            speed_bonus = max(0, 1.0 - mm.avg_latency * 10.0)  # penalize slow mw
            score = sc_bonus + speed_bonus
            scored.append((name, score))

        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)
        new_order = [name for name, _ in scored]

        if self._optimal_mw_order is None:
            self._optimal_mw_order = new_order
            self._mw_order_changed = True
            actions.append({
                "type": "middleware_initial_order",
                "detail": f"Initial middleware order: {' → '.join(new_order)}",
            })
        elif new_order != self._optimal_mw_order:
            # Check if the change is significant
            old_scores = {name: i for i, name in enumerate(self._optimal_mw_order)}
            max_shift = max(
                abs(new_idx - old_scores.get(name, new_idx))
                for new_idx, name in enumerate(new_order)
            )
            normalized_shift = max_shift / max(len(new_order), 1)

            if normalized_shift >= self.reorder_threshold:
                self._mw_order_changed = True
                actions.append({
                    "type": "middleware_reorder",
                    "detail": f"Reordered middleware: {' → '.join(self._optimal_mw_order)} "
                              f"→ {' → '.join(new_order)} (shift={normalized_shift:.2f})",
                })
                self._optimal_mw_order = new_order
            else:
                self._mw_order_changed = False

        return actions

    def get_optimal_middleware_order(self) -> Optional[List[str]]:
        """Return the optimized middleware execution order, or None if no reorder needed."""
        return self._optimal_mw_order

    def did_middleware_order_change(self) -> bool:
        """Check if the last optimization cycle changed the middleware order."""
        changed = self._mw_order_changed
        self._mw_order_changed = False
        return changed

    # ── Slow Endpoint Detection ──────────────────────────────────────

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """
        Return actionable suggestions for routes that could benefit from
        code path optimization (caching, memoization, async conversion).
        """
        suggestions = []

        slow = self.analyzer.get_slow_routes(threshold_ms=100.0)
        for rm in slow:
            suggestion = {
                "route": f"{rm.method} {rm.path}",
                "type": "slow_endpoint",
                "p95_ms": round(rm.p95_latency * 1000, 2),
                "recommendations": [],
            }

            if rm.p95_latency > 0.5:
                suggestion["recommendations"].append("Consider async execution or background task offload")
            if rm.requests_per_second > 5 and rm.p95_latency > 0.2:
                suggestion["recommendations"].append("Enable response memoization for this endpoint")
            if rm.error_rate > 0.1:
                suggestion["recommendations"].append("High error rate detected — investigate handler logic")

            suggestions.append(suggestion)

        error_prone = self.analyzer.get_error_prone_routes()
        for rm in error_prone:
            if not any(s["route"] == f"{rm.method} {rm.path}" for s in suggestions):
                suggestions.append({
                    "route": f"{rm.method} {rm.path}",
                    "type": "error_prone",
                    "error_rate": round(rm.error_rate, 4),
                    "recommendations": ["Investigate error patterns", "Add circuit breaker"],
                })

        return suggestions

    # ── Evolution Log ────────────────────────────────────────────────

    def get_evolution_log(self) -> List[Dict[str, Any]]:
        """Return the full evolution history of optimization decisions."""
        return list(self._evolution_log)

    def get_stats(self) -> Dict[str, Any]:
        """Return optimizer statistics."""
        return {
            "optimization_cycles": self._optimization_count,
            "hot_routes_cached": len(self._hot_route_cache),
            "middleware_reorders": sum(
                1 for entry in self._evolution_log
                for action in entry["actions"]
                if action["type"] == "middleware_reorder"
            ),
            "total_actions": sum(len(e["actions"]) for e in self._evolution_log),
            "route_caching_enabled": self.route_caching_enabled,
            "middleware_reorder_enabled": self.middleware_reorder_enabled,
        }
