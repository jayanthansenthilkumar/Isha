"""
Isha SARE — Traffic Analyzer

Real-time traffic intelligence engine that tracks per-route metrics:
request frequency, latency, error rates, and resource usage.
Forms the observation layer of the Self-Evolving Adaptive Routing Engine.
"""

import time
import logging
import threading
import statistics
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger("isha.sare.traffic")

# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class RouteMetrics:
    """Live metrics for a single route + method combination."""

    path: str
    method: str
    # Rolling windows (configurable size)
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_codes: deque = field(default_factory=lambda: deque(maxlen=500))
    response_sizes: deque = field(default_factory=lambda: deque(maxlen=500))

    # Counters
    total_requests: int = 0
    total_errors: int = 0
    total_5xx: int = 0

    # Snapshot values (updated periodically)
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    heat_score: float = 0.0  # composite score for prioritization

    def record(self, latency: float, status_code: int, response_size: int = 0):
        """Record a single request's metrics."""
        now = time.monotonic()
        self.latencies.append(latency)
        self.timestamps.append(now)
        self.response_sizes.append(response_size)
        self.total_requests += 1

        if status_code >= 400:
            self.error_codes.append(status_code)
            self.total_errors += 1
        if status_code >= 500:
            self.total_5xx += 1

    def compute_snapshot(self):
        """Recompute derived metrics from rolling windows."""
        if not self.latencies:
            return

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        self.avg_latency = statistics.mean(sorted_latencies)
        self.p50_latency = sorted_latencies[n // 2]
        self.p95_latency = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
        self.p99_latency = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]

        # RPS from timestamps in the last 60 seconds
        now = time.monotonic()
        recent = [t for t in self.timestamps if now - t <= 60.0]
        self.requests_per_second = len(recent) / 60.0 if recent else 0.0

        # Error rate
        self.error_rate = (self.total_errors / self.total_requests) if self.total_requests > 0 else 0.0

        # Heat score: composite of frequency and inverse latency
        # Higher RPS + lower latency = hotter route
        freq_score = min(self.requests_per_second / 10.0, 1.0)  # normalize
        latency_score = max(0, 1.0 - (self.avg_latency / 2.0))  # penalize slow
        error_penalty = 1.0 - min(self.error_rate * 2, 1.0)
        self.heat_score = (freq_score * 0.5 + latency_score * 0.3 + error_penalty * 0.2)


@dataclass
class MiddlewareMetrics:
    """Tracks per-middleware execution cost."""

    name: str
    latencies: deque = field(default_factory=lambda: deque(maxlen=500))
    short_circuit_count: int = 0
    total_calls: int = 0
    avg_latency: float = 0.0

    def record(self, latency: float, short_circuited: bool = False):
        self.latencies.append(latency)
        self.total_calls += 1
        if short_circuited:
            self.short_circuit_count += 1

    def compute_snapshot(self):
        if self.latencies:
            self.avg_latency = statistics.mean(self.latencies)

    @property
    def short_circuit_rate(self) -> float:
        return (self.short_circuit_count / self.total_calls) if self.total_calls > 0 else 0.0


# ── Traffic Analyzer ─────────────────────────────────────────────────


class TrafficAnalyzer:
    """
    Core observation engine of SARE.

    Tracks real-time per-route and per-middleware metrics, maintains rolling
    windows, and provides APIs for the optimizer to query traffic intelligence.

    Thread-safe: uses a lock for snapshot computation; individual deque appends
    are atomic in CPython.
    """

    def __init__(self, window_size: int = 1000, snapshot_interval: float = 5.0):
        self.window_size = window_size
        self.snapshot_interval = snapshot_interval

        # route_key = (method, path_pattern)
        self._routes: Dict[Tuple[str, str], RouteMetrics] = {}
        self._middleware: Dict[str, MiddlewareMetrics] = {}
        self._global_timestamps: deque = deque(maxlen=10000)

        # Global counters
        self.total_requests: int = 0
        self.total_errors: int = 0

        self._lock = threading.Lock()
        self._last_snapshot = 0.0

        # Historical snapshots for trend analysis (kept for predictor)
        self._history: deque = deque(maxlen=360)  # ~30 min at 5s intervals

    # ── Recording ────────────────────────────────────────────────────

    def record_request(
        self,
        method: str,
        path_pattern: str,
        latency: float,
        status_code: int,
        response_size: int = 0,
    ):
        """Record metrics for a completed request."""
        key = (method.upper(), path_pattern)

        if key not in self._routes:
            self._routes[key] = RouteMetrics(
                path=path_pattern,
                method=method.upper(),
                latencies=deque(maxlen=self.window_size),
                timestamps=deque(maxlen=self.window_size),
                error_codes=deque(maxlen=self.window_size // 2),
                response_sizes=deque(maxlen=self.window_size // 2),
            )

        self._routes[key].record(latency, status_code, response_size)
        self._global_timestamps.append(time.monotonic())
        self.total_requests += 1
        if status_code >= 400:
            self.total_errors += 1

    def record_middleware(self, name: str, latency: float, short_circuited: bool = False):
        """Record a middleware execution event."""
        if name not in self._middleware:
            self._middleware[name] = MiddlewareMetrics(name=name)
        self._middleware[name].record(latency, short_circuited)

    # ── Snapshot / Query ─────────────────────────────────────────────

    def maybe_refresh(self):
        """Recompute snapshots if snapshot_interval has elapsed."""
        now = time.monotonic()
        if now - self._last_snapshot < self.snapshot_interval:
            return
        self._refresh_snapshots()

    def _refresh_snapshots(self):
        """Recompute all derived metrics."""
        with self._lock:
            for rm in self._routes.values():
                rm.compute_snapshot()
            for mm in self._middleware.values():
                mm.compute_snapshot()
            self._last_snapshot = time.monotonic()

            # Store history point
            self._history.append(self._build_history_point())

    def _build_history_point(self) -> Dict[str, Any]:
        """Build a lightweight history snapshot for trend analysis."""
        return {
            "ts": time.time(),
            "rps_global": self.global_rps,
            "routes": {
                f"{rm.method} {rm.path}": {
                    "rps": rm.requests_per_second,
                    "avg_lat": rm.avg_latency,
                    "err_rate": rm.error_rate,
                    "heat": rm.heat_score,
                }
                for rm in self._routes.values()
            },
        }

    # ── Public Queries ───────────────────────────────────────────────

    @property
    def global_rps(self) -> float:
        now = time.monotonic()
        recent = sum(1 for t in self._global_timestamps if now - t <= 60.0)
        return recent / 60.0

    def get_route_metrics(self, method: str, path_pattern: str) -> Optional[RouteMetrics]:
        return self._routes.get((method.upper(), path_pattern))

    def get_all_route_metrics(self) -> Dict[Tuple[str, str], RouteMetrics]:
        return dict(self._routes)

    def get_hot_routes(self, top_n: int = 10) -> List[RouteMetrics]:
        """Return routes sorted by heat score (descending)."""
        self.maybe_refresh()
        sorted_routes = sorted(self._routes.values(), key=lambda r: r.heat_score, reverse=True)
        return sorted_routes[:top_n]

    def get_slow_routes(self, threshold_ms: float = 200.0) -> List[RouteMetrics]:
        """Return routes whose p95 latency exceeds the threshold."""
        self.maybe_refresh()
        return [
            rm for rm in self._routes.values()
            if rm.p95_latency * 1000 > threshold_ms
        ]

    def get_error_prone_routes(self, threshold: float = 0.05) -> List[RouteMetrics]:
        """Return routes with error rate above threshold."""
        self.maybe_refresh()
        return [
            rm for rm in self._routes.values()
            if rm.error_rate > threshold and rm.total_requests >= 10
        ]

    def get_middleware_metrics(self) -> Dict[str, MiddlewareMetrics]:
        self.maybe_refresh()
        return dict(self._middleware)

    def get_history(self) -> List[Dict[str, Any]]:
        """Return historical snapshots for trend analysis."""
        return list(self._history)

    # ── Summaries ────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """High-level traffic summary."""
        self.maybe_refresh()
        hot = self.get_hot_routes(5)
        slow = self.get_slow_routes()
        errors = self.get_error_prone_routes()

        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "global_rps": round(self.global_rps, 2),
            "tracked_routes": len(self._routes),
            "tracked_middleware": len(self._middleware),
            "hot_routes": [
                {"route": f"{r.method} {r.path}", "heat": round(r.heat_score, 4), "rps": round(r.requests_per_second, 2)}
                for r in hot
            ],
            "slow_routes": [
                {"route": f"{r.method} {r.path}", "p95_ms": round(r.p95_latency * 1000, 2)}
                for r in slow
            ],
            "error_routes": [
                {"route": f"{r.method} {r.path}", "error_rate": round(r.error_rate, 4)}
                for r in errors
            ],
        }

    def reset(self):
        """Reset all tracked metrics."""
        self._routes.clear()
        self._middleware.clear()
        self._global_timestamps.clear()
        self._history.clear()
        self.total_requests = 0
        self.total_errors = 0
        self._last_snapshot = 0.0
