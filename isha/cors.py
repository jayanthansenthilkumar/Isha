"""
ISHA CORS - Cross-Origin Resource Sharing Support

Enable CORS headers for API endpoints.
"""


class CORS:
    """
    CORS middleware for handling cross-origin requests.
    
    Usage:
        app = App()
        cors = CORS(origins=["http://localhost:3000"])
        
        @app.before
        def add_cors(req):
            cors.add_headers(req)
        
        @app.after
        def apply_cors(req, res):
            return cors.apply(req, res)
    """
    
    def __init__(
        self,
        origins: list = None,
        methods: list = None,
        headers: list = None,
        allow_credentials: bool = False,
        max_age: int = 3600
    ):
        """
        Initialize CORS configuration.
        
        Args:
            origins: List of allowed origins (default: ["*"])
            methods: List of allowed HTTP methods
            headers: List of allowed headers
            allow_credentials: Whether to allow credentials
            max_age: Preflight cache duration in seconds
        """
        self.origins = origins or ["*"]
        self.methods = methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self.headers = headers or ["Content-Type", "Authorization", "X-Requested-With"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    def is_preflight(self, request) -> bool:
        """Check if request is a CORS preflight request."""
        return (
            request.method == "OPTIONS" and
            "Origin" in request.headers and
            "Access-Control-Request-Method" in request.headers
        )
    
    def apply(self, request, response):
        """Apply CORS headers to response."""
        origin = request.headers.get("Origin", "")
        
        # Check if origin is allowed
        if self.origins == ["*"] or origin in self.origins:
            allowed_origin = "*" if self.origins == ["*"] else origin
            response.set_header("Access-Control-Allow-Origin", allowed_origin)
            
            # Add other CORS headers
            response.set_header(
                "Access-Control-Allow-Methods",
                ", ".join(self.methods)
            )
            response.set_header(
                "Access-Control-Allow-Headers",
                ", ".join(self.headers)
            )
            response.set_header(
                "Access-Control-Max-Age",
                str(self.max_age)
            )
            
            if self.allow_credentials:
                response.set_header("Access-Control-Allow-Credentials", "true")
        
        return response
    
    def handle_preflight(self, request):
        """Handle CORS preflight request."""
        from .core import Response
        
        response = Response("", status=204)
        return self.apply(request, response)


def enable_cors(app, **kwargs):
    """
    Convenience function to enable CORS on an app.
    
    Usage:
        from isha import App
        from isha.cors import enable_cors
        
        app = App()
        enable_cors(app, origins=["http://localhost:3000"])
    """
    cors = CORS(**kwargs)
    
    @app.before
    def handle_cors_preflight(req):
        if cors.is_preflight(req):
            return cors.handle_preflight(req)
    
    @app.after
    def apply_cors_headers(req, res):
        return cors.apply(req, res)
    
    return cors
