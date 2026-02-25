"""
Isha SARE — Intelligence Reporter

Generates comprehensive self-improvement reports showing:

- Optimization suggestions and auto-applied patches
- Performance deltas (before vs after)
- Code path evolution history
- Traffic predictions and spike warnings
- Middleware reorder history

Output format: structured dict (can be serialized to JSON, rendered as
HTML, or printed to console).
"""

import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("isha.sare.reporter")


class IntelligenceReporter:
    """
    Generates real-time self-improvement reports for the SARE engine.

    Aggregates data from all SARE components to produce a unified
    intelligence dashboard.
    """

    def __init__(self, analyzer, optimizer, predictor, codepath):
        """
        Args:
            analyzer: TrafficAnalyzer instance
            optimizer: AdaptiveOptimizer instance
            predictor: LatencyPredictor instance
            codepath: CodePathOptimizer instance
        """
        self.analyzer = analyzer
        self.optimizer = optimizer
        self.predictor = predictor
        self.codepath = codepath
        self._start_time = time.monotonic()
        self._report_count = 0

    # ── Full Report ──────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive SARE Intelligence Report.

        This is the main output — a complete picture of the framework's
        self-optimization state.
        """
        self._report_count += 1
        now = time.time()
        uptime = time.monotonic() - self._start_time

        report = {
            "header": {
                "title": "Isha SARE Intelligence Report",
                "generated_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                "report_number": self._report_count,
                "uptime_seconds": round(uptime, 1),
                "engine": "Self-Evolving Adaptive Routing Engine v1.0",
            },
            "traffic_overview": self._traffic_section(),
            "route_intelligence": self._route_intelligence_section(),
            "middleware_intelligence": self._middleware_section(),
            "predictions": self._prediction_section(),
            "optimizations_applied": self._optimizations_section(),
            "code_path_optimization": self._codepath_section(),
            "evolution_history": self._evolution_section(),
            "recommendations": self._recommendations_section(),
            "performance_delta": self._performance_delta_section(),
        }

        return report

    # ── Sections ─────────────────────────────────────────────────────

    def _traffic_section(self) -> Dict[str, Any]:
        """Traffic overview."""
        summary = self.analyzer.summary()
        return {
            "total_requests": summary["total_requests"],
            "total_errors": summary["total_errors"],
            "global_rps": summary["global_rps"],
            "tracked_routes": summary["tracked_routes"],
            "tracked_middleware": summary["tracked_middleware"],
            "error_rate": round(
                summary["total_errors"] / max(summary["total_requests"], 1), 4
            ),
        }

    def _route_intelligence_section(self) -> Dict[str, Any]:
        """Per-route intelligence."""
        hot_routes = self.analyzer.get_hot_routes(10)
        slow_routes = self.analyzer.get_slow_routes()
        error_routes = self.analyzer.get_error_prone_routes()

        routes = {}
        for rm in self.analyzer.get_all_route_metrics().values():
            route_id = f"{rm.method} {rm.path}"
            routes[route_id] = {
                "requests": rm.total_requests,
                "rps": round(rm.requests_per_second, 2),
                "avg_latency_ms": round(rm.avg_latency * 1000, 2),
                "p50_ms": round(rm.p50_latency * 1000, 2),
                "p95_ms": round(rm.p95_latency * 1000, 2),
                "p99_ms": round(rm.p99_latency * 1000, 2),
                "error_rate": round(rm.error_rate, 4),
                "heat_score": round(rm.heat_score, 4),
                "is_hot": rm in hot_routes,
                "is_slow": rm in slow_routes,
                "is_error_prone": rm in error_routes,
            }

        return {
            "routes": routes,
            "hot_count": len(hot_routes),
            "slow_count": len(slow_routes),
            "error_prone_count": len(error_routes),
        }

    def _middleware_section(self) -> Dict[str, Any]:
        """Middleware intelligence."""
        mw_metrics = self.analyzer.get_middleware_metrics()
        optimal_order = self.optimizer.get_optimal_middleware_order()

        middleware = {}
        for name, mm in mw_metrics.items():
            middleware[name] = {
                "total_calls": mm.total_calls,
                "avg_latency_ms": round(mm.avg_latency * 1000, 2),
                "short_circuit_rate": round(mm.short_circuit_rate, 4),
                "short_circuits": mm.short_circuit_count,
            }

        return {
            "middleware": middleware,
            "optimal_order": optimal_order,
            "total_tracked": len(mw_metrics),
        }

    def _prediction_section(self) -> Dict[str, Any]:
        """Predictions from the latency predictor."""
        return self.predictor.full_prediction_report()

    def _optimizations_section(self) -> Dict[str, Any]:
        """Summary of auto-applied optimizations."""
        optimizer_stats = self.optimizer.get_stats()
        evolution_log = self.optimizer.get_evolution_log()

        # Count by type
        action_counts: Dict[str, int] = {}
        for entry in evolution_log:
            for action in entry["actions"]:
                atype = action["type"]
                action_counts[atype] = action_counts.get(atype, 0) + 1

        return {
            "total_cycles": optimizer_stats["optimization_cycles"],
            "total_actions": optimizer_stats["total_actions"],
            "actions_by_type": action_counts,
            "hot_routes_cached": optimizer_stats["hot_routes_cached"],
            "middleware_reorders": optimizer_stats["middleware_reorders"],
            "auto_patches": self._list_auto_patches(evolution_log),
        }

    def _list_auto_patches(self, evolution_log: List[Dict]) -> List[Dict[str, Any]]:
        """Extract the most recent auto-applied changes."""
        patches = []
        for entry in evolution_log[-10:]:  # last 10 cycles
            for action in entry["actions"]:
                patches.append({
                    "cycle": entry["cycle"],
                    "timestamp": datetime.fromtimestamp(
                        entry["ts"], tz=timezone.utc
                    ).isoformat(),
                    "type": action["type"],
                    "detail": action["detail"],
                })
        return patches

    def _codepath_section(self) -> Dict[str, Any]:
        """Code path optimization stats."""
        return self.codepath.stats()

    def _evolution_section(self) -> Dict[str, Any]:
        """Evolution history summary."""
        log = self.optimizer.get_evolution_log()
        return {
            "total_evolution_cycles": len(log),
            "recent_evolutions": [
                {
                    "cycle": e["cycle"],
                    "actions_count": len(e["actions"]),
                    "timestamp": datetime.fromtimestamp(
                        e["ts"], tz=timezone.utc
                    ).isoformat(),
                }
                for e in log[-20:]
            ],
        }

    def _recommendations_section(self) -> List[Dict[str, Any]]:
        """Actionable recommendations."""
        suggestions = self.optimizer.get_optimization_suggestions()

        # Add prediction-based recommendations
        pred_report = self.predictor.full_prediction_report()
        for route_id, data in pred_report.get("routes", {}).items():
            spike = data.get("spike_prediction", {})
            if spike.get("likely"):
                suggestions.append({
                    "route": route_id,
                    "type": "spike_warning",
                    "probability": spike["probability"],
                    "recommendations": [
                        f"Traffic spike likely ({spike['probability']:.0%} probability)",
                        "Consider enabling auto-scaling or rate limiting",
                        spike.get("reason", ""),
                    ],
                })

            strategy = data.get("recommended_strategy", {})
            if strategy.get("confidence", 0) > 0.5:
                suggestions.append({
                    "route": route_id,
                    "type": "strategy_recommendation",
                    "strategy": strategy["strategy"],
                    "confidence": strategy["confidence"],
                    "recommendations": [strategy.get("reason", "")],
                })

        return suggestions

    def _performance_delta_section(self) -> Dict[str, Any]:
        """
        Compute performance deltas from historical data.
        Shows improvement trends.
        """
        history = self.analyzer.get_history()

        if len(history) < 2:
            return {"status": "insufficient data", "data_points": len(history)}

        first = history[0]
        latest = history[-1]

        # Global RPS change
        rps_delta = latest["rps_global"] - first["rps_global"]

        # Per-route latency improvements
        route_deltas = {}
        for route_id in latest.get("routes", {}):
            if route_id in first.get("routes", {}):
                old_lat = first["routes"][route_id]["avg_lat"]
                new_lat = latest["routes"][route_id]["avg_lat"]
                if old_lat > 0:
                    pct_change = ((new_lat - old_lat) / old_lat) * 100
                    route_deltas[route_id] = {
                        "old_avg_latency_ms": round(old_lat * 1000, 2),
                        "new_avg_latency_ms": round(new_lat * 1000, 2),
                        "change_pct": round(pct_change, 1),
                        "improved": pct_change < 0,
                    }

        return {
            "status": "ok",
            "data_points": len(history),
            "time_span_seconds": round(latest["ts"] - first["ts"], 1),
            "global_rps_delta": round(rps_delta, 2),
            "route_latency_deltas": route_deltas,
            "routes_improved": sum(1 for d in route_deltas.values() if d["improved"]),
            "routes_degraded": sum(1 for d in route_deltas.values() if not d["improved"]),
        }

    # ── Console Output ───────────────────────────────────────────────

    def print_report(self):
        """Print a human-readable intelligence report to console."""
        report = self.generate_report()
        header = report["header"]
        traffic = report["traffic_overview"]
        opts = report["optimizations_applied"]
        delta = report["performance_delta"]
        recs = report["recommendations"]

        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║           Isha SARE — Intelligence Report                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            f"║  Generated: {header['generated_at'][:19]}                       ║",
            f"║  Report #{header['report_number']:>4}   Uptime: {header['uptime_seconds']:>8.1f}s                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  TRAFFIC OVERVIEW                                              ║",
            f"║    Total Requests: {traffic['total_requests']:>10}                                ║",
            f"║    Global RPS:     {traffic['global_rps']:>10.2f}                                ║",
            f"║    Error Rate:     {traffic['error_rate']:>10.4f}                                ║",
            f"║    Tracked Routes: {traffic['tracked_routes']:>10}                                ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  OPTIMIZATIONS APPLIED                                         ║",
            f"║    Optimization Cycles:  {opts['total_cycles']:>6}                                ║",
            f"║    Total Actions:        {opts['total_actions']:>6}                                ║",
            f"║    Hot Routes Cached:    {opts['hot_routes_cached']:>6}                                ║",
            f"║    Middleware Reorders:  {opts['middleware_reorders']:>6}                                ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  PERFORMANCE DELTA                                             ║",
        ]

        if delta["status"] == "ok":
            lines.append(f"║    Data Points:          {delta['data_points']:>6}                                ║")
            lines.append(f"║    Routes Improved:      {delta['routes_improved']:>6}                                ║")
            lines.append(f"║    Routes Degraded:      {delta['routes_degraded']:>6}                                ║")
        else:
            lines.append("║    Collecting data...                                          ║")

        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  RECOMMENDATIONS                                               ║")

        if recs:
            for rec in recs[:5]:
                route = rec.get("route", "global")[:30]
                rtype = rec.get("type", "")[:20]
                lines.append(f"║    [{rtype}] {route:<40}║")
        else:
            lines.append("║    No recommendations at this time.                            ║")

        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        lines.append("")

        output = "\n".join(lines)
        print(output)
        return output

    # ── JSON Export ───────────────────────────────────────────────────

    def to_json(self) -> str:
        """Export the full report as a JSON string."""
        import json
        return json.dumps(self.generate_report(), indent=2, default=str)
