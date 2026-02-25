"""
Isha Middleware System — Before/after request hooks and exception handlers.
"""

import asyncio
import traceback
from typing import Callable, List, Optional
from functools import wraps


class Middleware:
    """
    Base middleware class.
    
    Subclass this and implement before_request, after_request,
    or handle_exception to create custom middleware.
    """

    async def before_request(self, request):
        """Called before the route handler. Return a Response to short-circuit."""
        return None

    async def after_request(self, request, response):
        """Called after the route handler. Can modify the response."""
        return response

    async def handle_exception(self, request, exc):
        """Called when an exception occurs. Return a Response to handle it."""
        return None


class MiddlewareStack:
    """
    Manages the ordered middleware pipeline.
    """

    def __init__(self):
        self._before: List[Callable] = []
        self._after: List[Callable] = []
        self._exception: List[Callable] = []
        self._middleware_instances: List[Middleware] = []

    def add(self, middleware):
        """Add a middleware instance or class."""
        if isinstance(middleware, type):
            middleware = middleware()

        if isinstance(middleware, Middleware):
            self._middleware_instances.append(middleware)
            return

        raise TypeError(f"Expected Middleware instance, got {type(middleware)}")

    def before_request(self, func):
        """Decorator to register a before-request hook."""
        if asyncio.iscoroutinefunction(func):
            self._before.append(func)
        else:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            self._before.append(async_wrapper)
        return func

    def after_request(self, func):
        """Decorator to register an after-request hook."""
        if asyncio.iscoroutinefunction(func):
            self._after.append(func)
        else:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            self._after.append(async_wrapper)
        return func

    def exception_handler(self, func):
        """Decorator to register an exception handler."""
        if asyncio.iscoroutinefunction(func):
            self._exception.append(func)
        else:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            self._exception.append(async_wrapper)
        return func

    async def run_before(self, request):
        """Run all before-request middleware. Returns response to short-circuit or None."""
        # Run middleware instances
        for mw in self._middleware_instances:
            result = await mw.before_request(request)
            if result is not None:
                return result

        # Run function hooks
        for hook in self._before:
            result = await hook(request)
            if result is not None:
                return result

        return None

    async def run_after(self, request, response):
        """Run all after-request middleware. Returns the (possibly modified) response."""
        # Run function hooks
        for hook in self._after:
            result = await hook(request, response)
            if result is not None:
                response = result

        # Run middleware instances (reverse order)
        for mw in reversed(self._middleware_instances):
            result = await mw.after_request(request, response)
            if result is not None:
                response = result

        return response

    async def run_exception(self, request, exc):
        """Run exception handlers. Returns response or None."""
        # Run middleware instances
        for mw in self._middleware_instances:
            result = await mw.handle_exception(request, exc)
            if result is not None:
                return result

        # Run function hooks
        for hook in self._exception:
            result = await hook(request, exc)
            if result is not None:
                return result

        return None


class CORSMiddleware(Middleware):
    """
    Cross-Origin Resource Sharing (CORS) middleware.
    """

    def __init__(
        self,
        allow_origins=None,
        allow_methods=None,
        allow_headers=None,
        expose_headers=None,
        allow_credentials=False,
        max_age=600,
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.expose_headers = expose_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def before_request(self, request):
        """Handle preflight OPTIONS requests."""
        if request.method == "OPTIONS":
            from .response import Response
            response = Response("", status_code=204)
            self._add_cors_headers(request, response)
            return response
        return None

    async def after_request(self, request, response):
        """Add CORS headers to all responses."""
        self._add_cors_headers(request, response)
        return response

    def _add_cors_headers(self, request, response):
        origin = request.headers.get("origin", "")

        if "*" in self.allow_origins:
            response.headers["access-control-allow-origin"] = "*"
        elif origin in self.allow_origins:
            response.headers["access-control-allow-origin"] = origin

        response.headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allow_headers)

        if self.expose_headers:
            response.headers["access-control-expose-headers"] = ", ".join(self.expose_headers)

        if self.allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"

        response.headers["access-control-max-age"] = str(self.max_age)


class RateLimitMiddleware(Middleware):
    """
    Simple in-memory rate limiting middleware.
    """

    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = {}  # ip -> [(timestamp, ...)]

    async def before_request(self, request):
        import time

        client_ip = request.client[0] if request.client else "unknown"
        now = time.time()

        if client_ip not in self._requests:
            self._requests[client_ip] = []

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip]
            if now - t < self.window_seconds
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            from .response import JSONResponse
            return JSONResponse(
                {"error": "Too Many Requests", "retry_after": self.window_seconds},
                status_code=429,
            )

        self._requests[client_ip].append(now)
        return None


class CSRFMiddleware(Middleware):
    """
    CSRF protection middleware using token validation.
    """

    def __init__(self, secret=None, exempt_methods=None, token_header="x-csrf-token"):
        import secrets
        self.secret = secret or secrets.token_hex(32)
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}
        self.token_header = token_header

    def generate_token(self):
        """Generate a CSRF token."""
        import hmac
        import hashlib
        import secrets as sec
        nonce = sec.token_hex(16)
        sig = hmac.new(self.secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()
        return f"{nonce}.{sig}"

    def validate_token(self, token):
        """Validate a CSRF token."""
        import hmac
        import hashlib
        if not token or "." not in token:
            return False
        nonce, sig = token.rsplit(".", 1)
        expected = hmac.new(self.secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)

    async def before_request(self, request):
        if request.method.upper() in self.exempt_methods:
            return None

        token = request.headers.get(self.token_header, "")
        if not self.validate_token(token):
            from .response import JSONResponse
            return JSONResponse(
                {"error": "CSRF token missing or invalid"},
                status_code=403,
            )
        return None


class SecurityHeadersMiddleware(Middleware):
    """
    Adds common security headers to all responses.
    """

    async def after_request(self, request, response):
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("x-xss-protection", "1; mode=block")
        response.headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "content-security-policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        return response
