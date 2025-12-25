"""
ISHA Cache - Response Caching

Simple in-memory caching for expensive operations.
"""

import time
import hashlib
from threading import Lock


class Cache:
    """
    Simple in-memory cache with TTL support.
    
    Usage:
        cache = Cache(ttl=300)  # 5 minutes
        
        @app.get("/expensive")
        def expensive(req):
            result = cache.get("expensive_key")
            if result is None:
                result = do_expensive_operation()
                cache.set("expensive_key", result)
            return result
    """
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            ttl: Time to live in seconds (default: 5 minutes)
            max_size: Maximum number of items to cache
        """
        self.ttl = ttl
        self.max_size = max_size
        self.store = {}
        self.lock = Lock()
    
    def get(self, key: str):
        """Get value from cache."""
        with self.lock:
            if key in self.store:
                value, expiry = self.store[key]
                if time.time() < expiry:
                    return value
                else:
                    del self.store[key]
        return None
    
    def set(self, key: str, value, ttl: int = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL for this item
        """
        expiry_time = time.time() + (ttl or self.ttl)
        
        with self.lock:
            # Evict oldest item if cache is full
            if len(self.store) >= self.max_size and key not in self.store:
                oldest_key = min(self.store.keys(), key=lambda k: self.store[k][1])
                del self.store[oldest_key]
            
            self.store[key] = (value, expiry_time)
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self.lock:
            if key in self.store:
                del self.store[key]
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.store.clear()
    
    def cleanup(self):
        """Remove expired entries."""
        current_time = time.time()
        with self.lock:
            expired = [k for k, (_, expiry) in self.store.items() if current_time >= expiry]
            for key in expired:
                del self.store[key]


class ResponseCache:
    """
    Automatically cache HTTP responses.
    
    Usage:
        response_cache = ResponseCache(ttl=60)
        
        @app.get("/data")
        @response_cache.cached()
        def get_data(req):
            return expensive_database_query()
    """
    
    def __init__(self, ttl: int = 300, cache_instance: Cache = None):
        """
        Initialize response cache.
        
        Args:
            ttl: Default TTL for cached responses
            cache_instance: Optional Cache instance to use
        """
        self.cache = cache_instance or Cache(ttl=ttl)
        self.ttl = ttl
    
    def _make_cache_key(self, request) -> str:
        """Generate cache key from request."""
        # Use method, path, and query string for key
        key_parts = [request.method, request.path, request.query_string]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def cached(self, ttl: int = None, key_func=None):
        """
        Decorator to cache route responses.
        
        Args:
            ttl: Custom TTL for this route
            key_func: Custom function to generate cache key from request
        """
        def decorator(fn):
            def wrapper(request):
                # Only cache GET requests
                if request.method != "GET":
                    return fn(request)
                
                # Generate cache key
                if key_func:
                    cache_key = key_func(request)
                else:
                    cache_key = self._make_cache_key(request)
                
                # Try to get from cache
                cached_response = self.cache.get(cache_key)
                if cached_response is not None:
                    return cached_response
                
                # Call original function
                response = fn(request)
                
                # Cache the response
                self.cache.set(cache_key, response, ttl=ttl or self.ttl)
                
                return response
            
            return wrapper
        return decorator
    
    def invalidate(self, request):
        """Invalidate cache for a specific request."""
        cache_key = self._make_cache_key(request)
        self.cache.delete(cache_key)


def cached_route(ttl: int = 300):
    """
    Simple decorator for caching routes.
    
    Usage:
        from isha.cache import cached_route
        
        @app.get("/expensive")
        @cached_route(ttl=60)
        def expensive(req):
            return {"data": calculate_expensive_data()}
    """
    cache = Cache(ttl=ttl)
    response_cache = ResponseCache(cache_instance=cache)
    return response_cache.cached(ttl=ttl)
