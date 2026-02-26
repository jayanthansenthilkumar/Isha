"""
Ishaa SARE — AI-Assisted Latency Predictor

Lightweight, zero-dependency prediction engine that uses reinforcement-style
heuristics and pattern-based analysis to predict:

- Traffic spikes per route
- Memory/latency trends
- Optimal execution strategy (sync vs async hints)

No external ML libraries required — pure Python statistical learning.
"""

import math
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field

from .sare_traffic import TrafficAnalyzer

logger = logging.getLogger("ishaa.sare.predictor")


# ── Exponential Weighted Moving Average ──────────────────────────────


class EWMA:
    """Exponentially Weighted Moving Average with configurable decay."""

    __slots__ = ("alpha", "value", "initialized")

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value: float = 0.0
        self.initialized: bool = False

    def update(self, sample: float) -> float:
        if not self.initialized:
            self.value = sample
            self.initialized = True
        else:
            self.value = self.alpha * sample + (1 - self.alpha) * self.value
        return self.value

    def predict(self) -> float:
        return self.value


# ── Trend Detector ───────────────────────────────────────────────────


class TrendDetector:
    """
    Detects upward/downward trends using simple linear regression
    over a sliding window of observations.
    """

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.values: deque = deque(maxlen=window_size)
        self.timestamps: deque = deque(maxlen=window_size)

    def add(self, value: float, ts: Optional[float] = None):
        self.values.append(value)
        self.timestamps.append(ts or time.monotonic())

    def slope(self) -> float:
        """Return the slope of the trend line. Positive = increasing."""
        n = len(self.values)
        if n < 3:
            return 0.0

        # Simple linear regression: y = mx + b
        x_vals = list(range(n))
        y_vals = list(self.values)

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def trend_direction(self) -> str:
        """Return 'rising', 'falling', or 'stable'."""
        s = self.slope()
        if s > 0.01:
            return "rising"
        elif s < -0.01:
            return "falling"
        return "stable"

    def predict_next(self, steps_ahead: int = 1) -> float:
        """Predict the value N steps in the future using linear extrapolation."""
        n = len(self.values)
        if n == 0:
            return 0.0
        if n < 3:
            return self.values[-1]

        s = self.slope()
        return self.values[-1] + s * steps_ahead


# ── Spike Detector ───────────────────────────────────────────────────


class SpikeDetector:
    """
    Detects anomalous spikes using a z-score approach over a rolling window.
    """

    def __init__(self, window_size: int = 100, z_threshold: float = 2.5):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.values: deque = deque(maxlen=window_size)

    def add(self, value: float) -> bool:
        """Add a value and return True if it's a spike."""
        is_spike = self.is_spike(value)
        self.values.append(value)
        return is_spike

    def is_spike(self, value: float) -> bool:
        if len(self.values) < 10:
            return False

        mean = sum(self.values) / len(self.values)
        variance = sum((v - mean) ** 2 for v in self.values) / len(self.values)
        std = math.sqrt(variance) if variance > 0 else 0.001

        z_score = (value - mean) / std
        return abs(z_score) > self.z_threshold


# ── Reinforcement Heuristic ──────────────────────────────────────────


@dataclass
class RouteStrategy:
    """Tracks which execution strategy works best for a route."""

    route_key: str
    # Reward signals for different strategies
    cache_reward: float = 0.0
    async_reward: float = 0.0
    precompile_reward: float = 0.0
    # Exploration counter
    observations: int = 0

    def best_strategy(self) -> str:
        """Return the strategy with the highest cumulative reward."""
        strategies = {
            "cache": self.cache_reward,
            "async_priority": self.async_reward,
            "precompile": self.precompile_reward,
        }
        return max(strategies, key=strategies.get)

    def update_reward(self, strategy: str, reward: float, learning_rate: float = 0.1):
        """Update the reward for a strategy using exponential smoothing."""
        self.observations += 1
        if strategy == "cache":
            self.cache_reward += learning_rate * (reward - self.cache_reward)
        elif strategy == "async_priority":
            self.async_reward += learning_rate * (reward - self.async_reward)
        elif strategy == "precompile":
            self.precompile_reward += learning_rate * (reward - self.precompile_reward)


# ── Main Predictor ───────────────────────────────────────────────────


class LatencyPredictor:
    """
    AI-Assisted Latency Predictor.

    Combines EWMA, trend detection, spike detection, and reinforcement-style
    heuristics to provide predictive intelligence about route behavior.
    """

    def __init__(self, analyzer: TrafficAnalyzer):
        self.analyzer = analyzer

        # Per-route predictors
        self._rps_ewma: Dict[str, EWMA] = {}          # route -> EWMA for RPS
        self._latency_ewma: Dict[str, EWMA] = {}      # route -> EWMA for latency
        self._rps_trend: Dict[str, TrendDetector] = {}
        self._latency_trend: Dict[str, TrendDetector] = {}
        self._spike_detectors: Dict[str, SpikeDetector] = {}

        # Strategy learning
        self._strategies: Dict[str, RouteStrategy] = {}

        # Prediction history
        self._predictions: deque = deque(maxlen=200)
        self._prediction_accuracy: deque = deque(maxlen=100)

    # ── Update from Traffic Data ─────────────────────────────────────

    def update(self):
        """
        Pull latest data from the TrafficAnalyzer and update all predictors.
        Should be called periodically (e.g., every optimization cycle).
        """
        route_metrics = self.analyzer.get_all_route_metrics()

        for key, rm in route_metrics.items():
            route_id = f"{rm.method} {rm.path}"

            # Initialize predictors if new
            if route_id not in self._rps_ewma:
                self._rps_ewma[route_id] = EWMA(alpha=0.3)
                self._latency_ewma[route_id] = EWMA(alpha=0.3)
                self._rps_trend[route_id] = TrendDetector(window_size=30)
                self._latency_trend[route_id] = TrendDetector(window_size=30)
                self._spike_detectors[route_id] = SpikeDetector()
                self._strategies[route_id] = RouteStrategy(route_key=route_id)

            # Feed data
            self._rps_ewma[route_id].update(rm.requests_per_second)
            self._latency_ewma[route_id].update(rm.avg_latency)
            self._rps_trend[route_id].add(rm.requests_per_second)
            self._latency_trend[route_id].add(rm.avg_latency)

            # Spike detection on RPS
            is_spike = self._spike_detectors[route_id].add(rm.requests_per_second)
            if is_spike:
                logger.warning(f"SARE: Traffic spike detected on {route_id} "
                               f"(RPS={rm.requests_per_second:.1f})")

            # Update strategy rewards based on current behavior
            self._update_strategy_rewards(route_id, rm)

    def _update_strategy_rewards(self, route_id: str, rm):
        """Update reinforcement rewards based on observed behavior."""
        strategy = self._strategies[route_id]

        # If route is cache-friendly (low error rate, stable responses) → reward caching
        if rm.error_rate < 0.01 and rm.requests_per_second > 2:
            strategy.update_reward("cache", 1.0)
        else:
            strategy.update_reward("cache", -0.2)

        # If route is latency-heavy → reward async priority
        if rm.avg_latency > 0.1:
            strategy.update_reward("async_priority", 0.8)
        else:
            strategy.update_reward("async_priority", -0.1)

        # If route is very hot → reward precompilation
        if rm.heat_score > 0.5:
            strategy.update_reward("precompile", 1.0)
        elif rm.heat_score > 0.2:
            strategy.update_reward("precompile", 0.3)
        else:
            strategy.update_reward("precompile", -0.3)

    # ── Predictions ──────────────────────────────────────────────────

    def predict_rps(self, route_id: str, steps_ahead: int = 6) -> Optional[float]:
        """Predict future RPS for a route (steps are in snapshot intervals)."""
        trend = self._rps_trend.get(route_id)
        ewma = self._rps_ewma.get(route_id)

        if trend is None or ewma is None:
            return None

        # Blend trend extrapolation with EWMA for stability
        trend_pred = trend.predict_next(steps_ahead)
        ewma_pred = ewma.predict()

        # Weighted blend: trend gets more weight for long-term, EWMA for short
        weight = min(steps_ahead / 12.0, 0.7)
        prediction = trend_pred * weight + ewma_pred * (1 - weight)
        return max(0, prediction)

    def predict_latency(self, route_id: str, steps_ahead: int = 6) -> Optional[float]:
        """Predict future average latency for a route."""
        trend = self._latency_trend.get(route_id)
        ewma = self._latency_ewma.get(route_id)

        if trend is None or ewma is None:
            return None

        trend_pred = trend.predict_next(steps_ahead)
        ewma_pred = ewma.predict()

        weight = min(steps_ahead / 12.0, 0.7)
        prediction = trend_pred * weight + ewma_pred * (1 - weight)
        return max(0, prediction)

    def predict_spike(self, route_id: str) -> Dict[str, Any]:
        """
        Predict whether a traffic spike is likely in the near future.

        Uses trend slope and acceleration to estimate spike probability.
        """
        trend = self._rps_trend.get(route_id)
        if trend is None or len(trend.values) < 5:
            return {"likely": False, "probability": 0.0, "reason": "insufficient data"}

        slope = trend.slope()
        direction = trend.trend_direction()

        # Check acceleration (change in slope over recent values)
        recent_half = list(trend.values)[len(trend.values) // 2:]
        first_half = list(trend.values)[:len(trend.values) // 2]

        if len(first_half) >= 2 and len(recent_half) >= 2:
            early_avg = sum(first_half) / len(first_half)
            late_avg = sum(recent_half) / len(recent_half)
            acceleration = (late_avg - early_avg) / max(early_avg, 0.001)
        else:
            acceleration = 0.0

        # Probability heuristic
        probability = 0.0
        reasons = []

        if slope > 0.05:
            probability += 0.3
            reasons.append(f"rising trend (slope={slope:.4f})")
        if acceleration > 0.5:
            probability += 0.4
            reasons.append(f"accelerating traffic ({acceleration:.1%})")
        if direction == "rising" and slope > 0.1:
            probability += 0.2
            reasons.append("strong upward momentum")

        probability = min(probability, 0.95)

        return {
            "likely": probability > 0.5,
            "probability": round(probability, 3),
            "direction": direction,
            "slope": round(slope, 6),
            "acceleration": round(acceleration, 4),
            "reason": "; ".join(reasons) if reasons else "stable traffic pattern",
        }

    def recommend_strategy(self, route_id: str) -> Dict[str, Any]:
        """
        Recommend the best execution strategy for a route based on
        reinforcement learning signals.
        """
        strategy = self._strategies.get(route_id)
        if strategy is None:
            return {"strategy": "default", "confidence": 0.0, "reason": "no data"}

        best = strategy.best_strategy()
        confidence = max(strategy.cache_reward, strategy.async_reward, strategy.precompile_reward)
        confidence = min(max(confidence, 0), 1.0)

        descriptions = {
            "cache": "Enable response memoization — route is cache-friendly",
            "async_priority": "Prioritize async execution — route is latency-heavy",
            "precompile": "Pre-compile response templates — route is hot and stable",
        }

        return {
            "strategy": best,
            "confidence": round(confidence, 3),
            "reason": descriptions.get(best, ""),
            "scores": {
                "cache": round(strategy.cache_reward, 3),
                "async_priority": round(strategy.async_reward, 3),
                "precompile": round(strategy.precompile_reward, 3),
            },
            "observations": strategy.observations,
        }

    # ── Full Prediction Report ───────────────────────────────────────

    def full_prediction_report(self) -> Dict[str, Any]:
        """Generate a full prediction report for all tracked routes."""
        report = {"routes": {}, "global": {}}

        for route_id in self._rps_ewma:
            route_report = {
                "predicted_rps_30s": self.predict_rps(route_id, steps_ahead=6),
                "predicted_rps_60s": self.predict_rps(route_id, steps_ahead=12),
                "predicted_latency_30s": self.predict_latency(route_id, steps_ahead=6),
                "spike_prediction": self.predict_spike(route_id),
                "recommended_strategy": self.recommend_strategy(route_id),
                "rps_trend": self._rps_trend[route_id].trend_direction(),
                "latency_trend": self._latency_trend[route_id].trend_direction(),
            }
            report["routes"][route_id] = route_report

        # Global predictions
        global_rps = self.analyzer.global_rps
        report["global"] = {
            "current_rps": round(global_rps, 2),
            "tracked_routes": len(self._rps_ewma),
            "routes_with_rising_traffic": sum(
                1 for t in self._rps_trend.values() if t.trend_direction() == "rising"
            ),
            "routes_with_rising_latency": sum(
                1 for t in self._latency_trend.values() if t.trend_direction() == "rising"
            ),
        }

        return report
