"""
ISHA Core - The Heart of the Framework

Contains the fundamental building blocks:
- Request: Handles incoming HTTP requests
- Response: Builds HTTP responses
- App: The application router
"""


class Request:
    """
    Represents an incoming HTTP request.
    
    Attributes:
        raw: The raw HTTP request string
        method: HTTP method (GET, POST, etc.)
        path: Request path
        query_string: Query string from URL
        query_params: Parsed query parameters
        headers: Dictionary of request headers
        cookies: Dictionary of request cookies
        body: Request body content
    """
    
    def __init__(self, raw: str):
        self.raw = raw
        self.method = ""
        self.path = ""
        self.query_string = ""
        self.query_params = {}
        self.headers = {}
        self.cookies = {}
        self.body = ""
        self.json_body = None  # Parsed JSON body
        self.params = {}  # URL path parameters like {id}
        self._parse()
    
    def _parse(self):
        """Parse the raw HTTP request."""
        if not self.raw:
            return
        
        lines = self.raw.split("\r\n")
        
        # Parse request line
        if lines:
            request_line = lines[0].split()
            if len(request_line) >= 2:
                self.method = request_line[0]
                full_path = request_line[1]
                
                # Split path and query string
                if "?" in full_path:
                    self.path, self.query_string = full_path.split("?", 1)
                    self._parse_query_params()
                else:
                    self.path = full_path
        
        # Parse headers
        header_section = True
        body_lines = []
        
        for line in lines[1:]:
            if header_section:
                if line == "":
                    header_section = False
                elif ":" in line:
                    key, value = line.split(":", 1)
                    self.headers[key.strip()] = value.strip()
            else:
                body_lines.append(line)
        
        self.body = "\r\n".join(body_lines)
        
        # Parse cookies from headers
        if "Cookie" in self.headers:
            self._parse_cookies()
        
        # Parse JSON body if content-type is application/json
        if self.headers.get("Content-Type", "").startswith("application/json"):
            self._parse_json_body()
    
    def _parse_query_params(self):
        """Parse URL query parameters."""
        from urllib.parse import parse_qs
        parsed = parse_qs(self.query_string)
        self.query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    
    def _parse_cookies(self):
        """Parse cookies from Cookie header."""
        cookie_header = self.headers.get("Cookie", "")
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                key, value = cookie.strip().split("=", 1)
                self.cookies[key] = value
    
    def _parse_json_body(self):
        """Parse JSON from request body."""
        if self.body:
            try:
                import json
                self.json_body = json.loads(self.body)
            except (json.JSONDecodeError, ValueError):
                self.json_body = None


class Response:
    """
    Represents an HTTP response.
    
    Attributes:
        body: Response body content
        status: HTTP status code
        content_type: Content-Type header value
        headers: Additional response headers
        cookies: Response cookies
    """
    
    STATUS_PHRASES = {
        200: "OK",
        201: "Created",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }
    
    def __init__(self, body: str = "", status: int = 200, content_type: str = "text/plain"):
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = {}
        self.cookies = {}
        self._binary_body = None  # For binary content (images, etc.)
    
    def set_header(self, key: str, value: str):
        """Set a custom response header."""
        self.headers[key] = value
        return self
    
    def set_cookie(self, name: str, value: str, max_age: int = None, path: str = "/", 
                   http_only: bool = True, secure: bool = False):
        """Set a cookie."""
        cookie_parts = [f"{name}={value}"]
        if max_age:
            cookie_parts.append(f"Max-Age={max_age}")
        cookie_parts.append(f"Path={path}")
        if http_only:
            cookie_parts.append("HttpOnly")
        if secure:
            cookie_parts.append("Secure")
        
        self.cookies[name] = "; ".join(cookie_parts)
        return self
    
    def redirect(self, location: str, status: int = 302):
        """Set redirect headers."""
        self.status = status
        self.set_header("Location", location)
        return self
    
    def build(self) -> bytes:
        """Build the raw HTTP response bytes."""
        phrase = self.STATUS_PHRASES.get(self.status, "OK")
        
        # Use binary body if available
        if self._binary_body:
            body_bytes = self._binary_body
        else:
            body_bytes = self.body.encode('utf-8')
        
        # Build headers
        headers = [
            f"HTTP/1.1 {self.status} {phrase}",
            f"Content-Type: {self.content_type}",
            f"Content-Length: {len(body_bytes)}",
            "Connection: close",
        ]
        
        # Add custom headers
        for key, value in self.headers.items():
            headers.append(f"{key}: {value}")
        
        # Add cookies
        for cookie_value in self.cookies.values():
            headers.append(f"Set-Cookie: {cookie_value}")
        
        header_str = "\r\n".join(headers)
        return header_str.encode('utf-8') + b"\r\n\r\n" + body_bytes


class App:
    """
    The ISHA Application.
    
    A minimal, elegant router that maps paths to handlers.
    
    Usage:
        app = App()
        
        @app.route("/")
        def home(req):
            return "Hello, ISHA!"
    """
    
    def __init__(self, name: str = "isha"):
        self.name = name
        self.routes = {}
        self.dynamic_routes = []  # For routes with {param} patterns
        self.before_request_handlers = []
        self.after_request_handlers = []
        self.error_handlers = {}
        self.static_handlers = []  # For serving static files
        self.config = None  # Will hold Config object
        self.template_dir = None  # Template directory path
    
    def route(self, path: str, methods: list = None):
        """
        Decorator to register a route handler.
        
        Args:
            path: The URL path to match
            methods: List of allowed HTTP methods (default: ["GET"])
        
        Usage:
            @app.route("/")
            def home(req):
                return "Hello!"
                
            @app.route("/api/data", methods=["GET", "POST"])
            def api(req):
                return "API Response"
        """
        if methods is None:
            methods = ["GET"]
        
        def wrapper(fn):
            # Check if path has dynamic parameters {param}
            if "{" in path and "}" in path:
                self.dynamic_routes.append({
                    "pattern": path,
                    "handler": fn,
                    "methods": methods
                })
            else:
                self.routes[path] = {
                    "handler": fn,
                    "methods": methods
                }
            return fn
        return wrapper
    
    def get(self, path: str):
        """Shortcut for @app.route(path, methods=["GET"])"""
        return self.route(path, methods=["GET"])
    
    def post(self, path: str):
        """Shortcut for @app.route(path, methods=["POST"])"""
        return self.route(path, methods=["POST"])
    
    def before(self, fn):
        """Register a before-request handler."""
        self.before_request_handlers.append(fn)
        return fn
    
    def after(self, fn):
        """Register an after-request handler."""
        self.after_request_handlers.append(fn)
        return fn
    
    def error(self, status_code: int):
        """Register a custom error handler for a status code."""
        def wrapper(fn):
            self.error_handlers[status_code] = fn
            return fn
        return wrapper
    
    def mount_static(self, url_prefix: str, directory: str):
        """Mount a static file directory."""
        from .static import StaticFiles
        from pathlib import Path
        
        static_handler = StaticFiles(url_prefix, Path(directory))
        self.static_handlers.append(static_handler)
    
    def render_template(self, template_name: str, context: dict = None):
        """Render a template file."""
        from .template import render_template
        from pathlib import Path
        
        template_dir = self.template_dir or Path.cwd() / "templates"
        return render_template(template_name, context, template_dir)
    
    def handle_request(self, request: Request) -> Response:
        """
        Process a request and return a response.
        
        This is the core request handling logic.
        """
        # Check static file handlers first
        for static_handler in self.static_handlers:
            response = static_handler.serve(request)
            if response is not None:
                return response
        
        # Run before-request handlers
        for handler in self.before_request_handlers:
            result = handler(request)
            if result is not None:
                return self._make_response(result)
        
        # Find route - check static routes first
        route_info = self.routes.get(request.path)
        
        # If no static route, check dynamic routes
        if route_info is None:
            route_info, params = self._match_dynamic_route(request.path)
            if route_info:
                request.params = params
        
        if route_info is None:
            return self._handle_error(404, request)
        
        if request.method not in route_info["methods"]:
            return self._handle_error(405, request)
        
        try:
            result = route_info["handler"](request)
            response = self._make_response(result)
        except Exception as e:
            print(f"⚠️  Error handling request: {e}")
            return self._handle_error(500, request)
        
        # Run after-request handlers
        for handler in self.after_request_handlers:
            response = handler(request, response) or response
        
        return response
    
    def _make_response(self, result) -> Response:
        """Convert a handler result to a Response object."""
        if isinstance(result, Response):
            return result
        if isinstance(result, str):
            return Response(result)
        if isinstance(result, dict):
            import json
            return Response(json.dumps(result), content_type="application/json")
        if isinstance(result, tuple):
            body, status = result
            return Response(body, status)
        return Response(str(result))
    
    def _match_dynamic_route(self, path: str):
        """Match a path against dynamic route patterns."""
        import re
        
        for route in self.dynamic_routes:
            pattern = route["pattern"]
            # Convert {param} to regex capturing group
            regex_pattern = re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", pattern)
            regex_pattern = "^" + regex_pattern + "$"
            
            match = re.match(regex_pattern, path)
            if match:
                return route, match.groupdict()
        
        return None, {}
    
    def _handle_error(self, status_code: int, request: Request) -> Response:
        """Handle error responses."""
        if status_code in self.error_handlers:
            result = self.error_handlers[status_code](request)
            return self._make_response(result)
        
        messages = {
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }
        return Response(messages.get(status_code, "Error"), status_code)
