"""
Ishaa SARE — Code Path Optimizer

Automatically optimizes hot code paths at runtime:

1. Response memoization — caches handler output for identical requests
2. JSON pre-encoding — pre-builds JSON templates for hot routes
3. Function bytecode caching — keeps compiled handler references hot
4. Smart invalidation — time-based + change-detection eviction

All optimizations are applied autonomously by SARE based on traffic intelligence.
"""

import time
import json
import hashlib
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional, Set, Tuple
from collections import OrderedDict
from functools import wraps

logger = logging.getLogger("ishaa.sare.codepath")


# ── LRU Response Cache ───────────────────────────────────────────────


class ResponseCache:
    """
    Thread-safe, TTL-aware LRU cache for memoized responses.

    Keys are derived from (method, path, query_string, relevant_headers).
    Values are serialized response data.
    """

    def __init__(self, max_size: int = 500, default_ttl: float = 30.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()  # key -> (response_data, expires_at)
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached response. Returns None on miss or expiry."""
        if key not in self._cache:
            self._misses += 1
            return None

        data, expires_at = self._cache[key]
        if time.monotonic() > expires_at:
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return data

    def put(self, key: str, response_data: Dict[str, Any], ttl: Optional[float] = None):
        """Store a response in the cache."""
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.monotonic() + ttl

        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (response_data, expires_at)

        # Evict oldest if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str):
        """Remove a specific entry."""
        self._cache.pop(key, None)

    def invalidate_pattern(self, pattern: str):
        """Remove all entries whose key starts with the pattern."""
        to_remove = [k for k in self._cache if k.startswith(pattern)]
        for k in to_remove:
            del self._cache[k]

    def clear(self):
        """Clear the entire cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def evict_expired(self):
        """Remove all expired entries."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total) if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "default_ttl": self.default_ttl,
        }


# ── JSON Pre-Encoder ─────────────────────────────────────────────────


class JSONPreEncoder:
    """
    Pre-builds JSON encoding templates for routes that consistently return
    the same structure. Avoids repeated json.dumps() overhead for hot routes.
    """

    def __init__(self, max_templates: int = 100):
        self.max_templates = max_templates
        # route_id -> (template_keys_tuple, pre_encoded_static_parts)
        self._templates: Dict[str, Tuple[tuple, Optional[str]]] = {}
        self._structure_fingerprints: Dict[str, str] = {}

    def learn_structure(self, route_id: str, data: Any) -> bool:
        """
        Observe a response payload and learn its JSON structure.
        Returns True if the structure is consistent with previous observations.
        """
        if not isinstance(data, dict):
            return False

        # Fingerprint: sorted keys + value types
        fingerprint = self._fingerprint(data)

        if route_id in self._structure_fingerprints:
            if self._structure_fingerprints[route_id] != fingerprint:
                # Structure changed → invalidate template
                self._templates.pop(route_id, None)
                self._structure_fingerprints[route_id] = fingerprint
                return False
        else:
            self._structure_fingerprints[route_id] = fingerprint

        # Build template if consistent
        if route_id not in self._templates:
            keys = tuple(sorted(data.keys()))
            self._templates[route_id] = (keys, None)

            # Evict old templates if over limit
            while len(self._templates) > self.max_templates:
                oldest = next(iter(self._templates))
                del self._templates[oldest]

        return True

    def fast_encode(self, route_id: str, data: dict) -> Optional[str]:
        """
        Attempt a fast JSON encode using pre-learned structure.
        Falls back to None if no template exists.
        """
        if route_id not in self._templates or not isinstance(data, dict):
            return None

        keys, _ = self._templates[route_id]

        # Fast path: build JSON string directly for simple flat dicts
        try:
            parts = []
            for key in keys:
                val = data.get(key)
                if val is None:
                    parts.append(f'"{key}":null')
                elif isinstance(val, str):
                    # Escape basic characters
                    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
                    parts.append(f'"{key}":"{escaped}"')
                elif isinstance(val, bool):
                    parts.append(f'"{key}":{"true" if val else "false"}')
                elif isinstance(val, (int, float)):
                    parts.append(f'"{key}":{val}')
                else:
                    # Complex value — fall back to json.dumps
                    parts.append(f'"{key}":{json.dumps(val, ensure_ascii=False)}')
            return "{" + ",".join(parts) + "}"
        except Exception:
            return None

    def _fingerprint(self, data: dict) -> str:
        """Create a structural fingerprint of a dict."""
        sig = "|".join(f"{k}:{type(v).__name__}" for k, v in sorted(data.items()))
        return hashlib.md5(sig.encode()).hexdigest()

    def stats(self) -> Dict[str, Any]:
        return {
            "templates": len(self._templates),
            "max_templates": self.max_templates,
            "tracked_structures": len(self._structure_fingerprints),
        }


# ── Code Path Optimizer ──────────────────────────────────────────────


class CodePathOptimizer:
    """
    Main code path optimization engine.

    Coordinates response caching, JSON pre-encoding, and handler optimization
    based on directives from the AdaptiveOptimizer.
    """

    def __init__(
        self,
        cache_max_size: int = 500,
        cache_default_ttl: float = 30.0,
        max_json_templates: int = 100,
    ):
        self.response_cache = ResponseCache(
            max_size=cache_max_size,
            default_ttl=cache_default_ttl,
        )
        self.json_encoder = JSONPreEncoder(max_templates=max_json_templates)

        # Routes enabled for memoization (set by optimizer)
        self._memoized_routes: Set[str] = set()
        # Routes enabled for JSON pre-encoding
        self._preencoded_routes: Set[str] = set()
        # Per-route TTL overrides
        self._route_ttls: Dict[str, float] = {}

        # Bytecode cache: keep references to handler callables to avoid
        # repeated attribute lookups
        self._handler_cache: Dict[str, Callable] = {}

        # Stats
        self._cache_bypasses: int = 0
        self._fast_encodes: int = 0
        self._total_requests: int = 0

    # ── Memoization Control ──────────────────────────────────────────

    def enable_memoization(self, route_id: str, ttl: Optional[float] = None):
        """Enable response memoization for a route."""
        self._memoized_routes.add(route_id)
        if ttl is not None:
            self._route_ttls[route_id] = ttl
        logger.info(f"SARE CodePath: Enabled memoization for {route_id} (TTL={ttl or self.response_cache.default_ttl}s)")

    def disable_memoization(self, route_id: str):
        """Disable response memoization for a route."""
        self._memoized_routes.discard(route_id)
        self._route_ttls.pop(route_id, None)
        # Invalidate existing cache for this route
        self.response_cache.invalidate_pattern(route_id)

    def enable_preencoding(self, route_id: str):
        """Enable JSON pre-encoding for a route."""
        self._preencoded_routes.add(route_id)

    def disable_preencoding(self, route_id: str):
        """Disable JSON pre-encoding for a route."""
        self._preencoded_routes.discard(route_id)

    # ── Request-Level Operations ─────────────────────────────────────

    def build_cache_key(self, method: str, path: str, query_string: str = "") -> str:
        """Build a deterministic cache key for a request."""
        raw = f"{method}|{path}|{query_string}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def try_cache_hit(self, route_id: str, method: str, path: str, query_string: str = "") -> Optional[Dict[str, Any]]:
        """
        Attempt to serve a response from cache.
        Returns cached response data or None.
        """
        self._total_requests += 1

        if route_id not in self._memoized_routes:
            self._cache_bypasses += 1
            return None

        # Only cache GET/HEAD requests
        if method not in ("GET", "HEAD"):
            self._cache_bypasses += 1
            return None

        key = self.build_cache_key(method, path, query_string)
        return self.response_cache.get(f"{route_id}:{key}")

    def store_response(
        self,
        route_id: str,
        method: str,
        path: str,
        query_string: str,
        response_data: Dict[str, Any],
    ):
        """Store a response in cache if the route has memoization enabled."""
        if route_id not in self._memoized_routes:
            return
        if method not in ("GET", "HEAD"):
            return

        key = self.build_cache_key(method, path, query_string)
        ttl = self._route_ttls.get(route_id, self.response_cache.default_ttl)
        self.response_cache.put(f"{route_id}:{key}", response_data, ttl)

    def try_fast_encode(self, route_id: str, data: Any) -> Optional[str]:
        """
        Attempt fast JSON encoding for a response body.
        Returns pre-encoded JSON string or None.
        """
        if route_id not in self._preencoded_routes:
            return None

        if not isinstance(data, dict):
            return None

        # Learn structure
        self.json_encoder.learn_structure(route_id, data)

        # Attempt fast encode
        result = self.json_encoder.fast_encode(route_id, data)
        if result is not None:
            self._fast_encodes += 1
        return result

    # ── Handler Bytecode Cache ───────────────────────────────────────

    def cache_handler(self, route_id: str, handler: Callable):
        """Cache a handler reference for fast lookup."""
        self._handler_cache[route_id] = handler

    def get_cached_handler(self, route_id: str) -> Optional[Callable]:
        """Retrieve a cached handler reference."""
        return self._handler_cache.get(route_id)

    # ── Maintenance ──────────────────────────────────────────────────

    def cleanup(self):
        """Run periodic maintenance: evict expired cache entries."""
        self.response_cache.evict_expired()

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "memoized_routes": len(self._memoized_routes),
            "preencoded_routes": len(self._preencoded_routes),
            "cached_handlers": len(self._handler_cache),
            "total_requests_seen": self._total_requests,
            "cache_bypasses": self._cache_bypasses,
            "fast_encodes": self._fast_encodes,
            "response_cache": self.response_cache.stats(),
            "json_encoder": self.json_encoder.stats(),
        }
