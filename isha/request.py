"""
Isha Request Object — Parses and wraps incoming HTTP requests.
"""

import json
from urllib.parse import parse_qs, urlparse, unquote
from http.cookies import SimpleCookie


class Request:
    """
    Represents an incoming HTTP request.
    
    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
        path: Request path
        headers: Dictionary of request headers
        query_params: Parsed query string parameters
        path_params: Dynamic route parameters
        body: Raw request body bytes
        _json: Cached parsed JSON body
        cookies: Parsed cookies
        scope: ASGI scope (when running under ASGI)
    """

    __slots__ = (
        "method", "path", "headers", "query_params", "path_params",
        "body", "_json", "_form", "cookies", "scope", "state",
        "content_type", "client", "_receive",
    )

    def __init__(self, scope=None, receive=None):
        self.method = "GET"
        self.path = "/"
        self.headers = {}
        self.query_params = {}
        self.path_params = {}
        self.body = b""
        self._json = None
        self._form = None
        self.cookies = {}
        self.scope = scope or {}
        self.state = {}
        self.content_type = ""
        self.client = ("127.0.0.1", 0)
        self._receive = receive

        if scope:
            self._parse_scope(scope)

    def _parse_scope(self, scope):
        """Parse ASGI scope into request attributes."""
        self.method = scope.get("method", "GET").upper()
        self.path = scope.get("path", "/")
        self.client = scope.get("client", ("127.0.0.1", 0))

        # Parse headers
        raw_headers = scope.get("headers", [])
        self.headers = {}
        for key, value in raw_headers:
            header_name = key.decode("latin-1").lower() if isinstance(key, bytes) else key.lower()
            header_value = value.decode("latin-1") if isinstance(value, bytes) else value
            self.headers[header_name] = header_value

        self.content_type = self.headers.get("content-type", "")

        # Parse query string
        qs = scope.get("query_string", b"")
        if isinstance(qs, bytes):
            qs = qs.decode("utf-8")
        self.query_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(qs).items()}

        # Parse cookies
        cookie_header = self.headers.get("cookie", "")
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            self.cookies = {key: morsel.value for key, morsel in cookie.items()}

    async def read_body(self):
        """Read the full request body from ASGI receive channel."""
        if self._receive is None:
            return self.body

        if self.body:
            return self.body

        chunks = []
        while True:
            message = await self._receive()
            chunk = message.get("body", b"")
            if chunk:
                chunks.append(chunk)
            if not message.get("more_body", False):
                break

        self.body = b"".join(chunks)
        return self.body

    async def json(self):
        """Parse the request body as JSON."""
        if self._json is not None:
            return self._json
        body = await self.read_body()
        if body:
            self._json = json.loads(body.decode("utf-8"))
        else:
            self._json = {}
        return self._json

    async def form(self):
        """Parse the request body as form data (application/x-www-form-urlencoded)."""
        if self._form is not None:
            return self._form
        body = await self.read_body()
        if body:
            decoded = body.decode("utf-8")
            self._form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(decoded).items()}
        else:
            self._form = {}
        return self._form

    async def text(self):
        """Return the request body as a string."""
        body = await self.read_body()
        return body.decode("utf-8") if body else ""

    def get_header(self, name, default=None):
        """Get a specific header value."""
        return self.headers.get(name.lower(), default)

    @property
    def is_json(self):
        """Check if the request content type is JSON."""
        return "application/json" in self.content_type

    @property
    def is_form(self):
        """Check if the request content type is form data."""
        return "application/x-www-form-urlencoded" in self.content_type

    @property
    def host(self):
        """Get the Host header."""
        return self.headers.get("host", "")

    @property
    def url(self):
        """Reconstruct the full URL."""
        scheme = self.scope.get("scheme", "http")
        qs = self.scope.get("query_string", b"")
        if isinstance(qs, bytes):
            qs = qs.decode("utf-8")
        query = f"?{qs}" if qs else ""
        return f"{scheme}://{self.host}{self.path}{query}"

    @property
    def content_length(self):
        """Get the Content-Length header as int."""
        cl = self.headers.get("content-length", "0")
        try:
            return int(cl)
        except (ValueError, TypeError):
            return 0

    @classmethod
    def from_raw(cls, raw_data, client_addr=("127.0.0.1", 0)):
        """
        Create a Request from raw HTTP bytes (for the built-in server).
        """
        request = cls()
        try:
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8", errors="replace")

            lines = raw_data.split("\r\n")
            if not lines:
                return request

            # Parse request line
            request_line = lines[0].split(" ")
            if len(request_line) >= 2:
                request.method = request_line[0].upper()
                full_path = request_line[1]

                parsed = urlparse(full_path)
                request.path = unquote(parsed.path)
                request.query_params = {
                    k: v[0] if len(v) == 1 else v
                    for k, v in parse_qs(parsed.query).items()
                }

            # Parse headers
            i = 1
            while i < len(lines) and lines[i]:
                if ":" in lines[i]:
                    key, value = lines[i].split(":", 1)
                    request.headers[key.strip().lower()] = value.strip()
                i += 1

            request.content_type = request.headers.get("content-type", "")
            request.client = client_addr

            # Parse cookies
            cookie_header = request.headers.get("cookie", "")
            if cookie_header:
                cookie = SimpleCookie()
                cookie.load(cookie_header)
                request.cookies = {key: morsel.value for key, morsel in cookie.items()}

            # Parse body
            body_start = raw_data.find("\r\n\r\n")
            if body_start != -1:
                request.body = raw_data[body_start + 4:].encode("utf-8")

        except Exception:
            pass

        return request

    def __repr__(self):
        return f"<Request {self.method} {self.path}>"
