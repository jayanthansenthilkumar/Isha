"""
ISHA Rate Limiting - Protect against abuse

Simple in-memory rate limiting for API endpoints.
"""

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Usage:
        limiter = RateLimiter(requests_per_minute=60)
        
        @app.before
        def check_rate_limit(req):
            if not limiter.allow(req):
                return "Rate limit exceeded", 429
    """
    
    def __init__(self, requests_per_minute: int = 60, burst: int = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Number of requests allowed per minute per IP
            burst: Maximum burst size (default: same as requests_per_minute)
        """
        self.rate = requests_per_minute / 60.0  # Requests per second
        self.burst = burst or requests_per_minute
        self.buckets = defaultdict(lambda: {'tokens': self.burst, 'last_update': time.time()})
        self.lock = Lock()
    
    def _get_client_id(self, request) -> str:
        """Get client identifier (IP address)."""
        # In production, you'd extract this from headers or socket
        return request.headers.get("X-Forwarded-For", "unknown")
    
    def allow(self, request) -> bool:
        """
        Check if request should be allowed.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        with self.lock:
            bucket = self.buckets[client_id]
            
            # Add tokens based on time elapsed
            time_elapsed = current_time - bucket['last_update']
            bucket['tokens'] = min(
                self.burst,
                bucket['tokens'] + time_elapsed * self.rate
            )
            bucket['last_update'] = current_time
            
            # Check if we have tokens available
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            
            return False
    
    def reset(self, request):
        """Reset rate limit for a specific client."""
        client_id = self._get_client_id(request)
        with self.lock:
            if client_id in self.buckets:
                del self.buckets[client_id]


class RouteRateLimiter:
    """
    Per-route rate limiting.
    
    Usage:
        limiter = RouteRateLimiter()
        
        @app.route("/api/expensive")
        @limiter.limit(requests_per_minute=10)
        def expensive_api(req):
            return {"data": "..."}
    """
    
    def __init__(self):
        self.limiters = {}
    
    def limit(self, requests_per_minute: int = 60, burst: int = None):
        """
        Decorator to apply rate limiting to a specific route.
        
        Args:
            requests_per_minute: Number of requests allowed per minute
            burst: Maximum burst size
        """
        def decorator(fn):
            # Create a rate limiter for this function
            limiter_key = f"{fn.__module__}.{fn.__name__}"
            self.limiters[limiter_key] = RateLimiter(requests_per_minute, burst)
            
            def wrapper(request):
                limiter = self.limiters[limiter_key]
                
                if not limiter.allow(request):
                    from .core import Response
                    return Response("Rate limit exceeded. Please try again later.", status=429)
                
                return fn(request)
            
            return wrapper
        return decorator


def enable_rate_limiting(app, requests_per_minute: int = 60):
    """
    Enable global rate limiting on an app.
    
    Usage:
        from isha import App
        from isha.ratelimit import enable_rate_limiting
        
        app = App()
        enable_rate_limiting(app, requests_per_minute=100)
    """
    limiter = RateLimiter(requests_per_minute)
    
    @app.before
    def check_rate_limit(req):
        if not limiter.allow(req):
            from .core import Response
            return Response("Rate limit exceeded", status=429)
    
    return limiter
