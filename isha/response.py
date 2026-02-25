"""
Isha Response Objects — Build and send HTTP responses.
"""

import json
from http.cookies import SimpleCookie
from datetime import datetime, timezone


class Response:
    """
    Represents an HTTP response.
    
    Attributes:
        body: Response body content
        status_code: HTTP status code
        headers: Response headers
        content_type: Content-Type header value
    """

    def __init__(self, body="", status_code=200, headers=None, content_type="text/plain"):
        if isinstance(body, str):
            self.body = body.encode("utf-8")
        elif isinstance(body, bytes):
            self.body = body
        else:
            self.body = str(body).encode("utf-8")

        self.status_code = status_code
        self.headers = headers or {}
        self.content_type = content_type
        self._cookies = SimpleCookie()

        # Ensure content-type is set
        if "content-type" not in {k.lower() for k in self.headers}:
            self.headers["content-type"] = self.content_type

    def set_cookie(
        self, key, value="", max_age=None, expires=None,
        path="/", domain=None, secure=False, httponly=True,
        samesite="Lax"
    ):
        """Set a cookie on the response."""
        self._cookies[key] = value
        if max_age is not None:
            self._cookies[key]["max-age"] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            self._cookies[key]["expires"] = expires
        if path:
            self._cookies[key]["path"] = path
        if domain:
            self._cookies[key]["domain"] = domain
        if secure:
            self._cookies[key]["secure"] = True
        if httponly:
            self._cookies[key]["httponly"] = True
        if samesite:
            self._cookies[key]["samesite"] = samesite

    def delete_cookie(self, key, path="/", domain=None):
        """Delete a cookie by setting it to expire."""
        self.set_cookie(key, "", max_age=0, path=path, domain=domain)

    def _build_headers(self):
        """Build headers list for ASGI response."""
        headers = []
        for key, value in self.headers.items():
            if isinstance(key, str):
                key = key.encode("latin-1")
            if isinstance(value, str):
                value = value.encode("latin-1")
            headers.append([key, value])

        # Add cookie headers
        for morsel in self._cookies.values():
            cookie_val = morsel.OutputString()
            headers.append([b"set-cookie", cookie_val.encode("latin-1")])

        return headers

    async def send(self, send):
        """Send the response via ASGI send channel."""
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self._build_headers(),
        })
        await send({
            "type": "http.response.body",
            "body": self.body,
        })

    def to_http(self):
        """Convert to raw HTTP response bytes (for built-in server)."""
        status_text = HTTP_STATUS_CODES.get(self.status_code, "Unknown")
        lines = [f"HTTP/1.1 {self.status_code} {status_text}"]

        all_headers = dict(self.headers)
        all_headers["content-length"] = str(len(self.body))

        for key, value in all_headers.items():
            lines.append(f"{key}: {value}")

        # Add cookies
        for morsel in self._cookies.values():
            lines.append(f"set-cookie: {morsel.OutputString()}")

        header_block = "\r\n".join(lines) + "\r\n\r\n"
        return header_block.encode("utf-8") + self.body

    def __repr__(self):
        return f"<Response {self.status_code}>"


class JSONResponse(Response):
    """JSON response with proper content type."""

    def __init__(self, data, status_code=200, headers=None, **json_kwargs):
        body = json.dumps(data, ensure_ascii=False, **json_kwargs)
        super().__init__(
            body=body,
            status_code=status_code,
            headers=headers,
            content_type="application/json; charset=utf-8",
        )


class HTMLResponse(Response):
    """HTML response with proper content type."""

    def __init__(self, body, status_code=200, headers=None):
        super().__init__(
            body=body,
            status_code=status_code,
            headers=headers,
            content_type="text/html; charset=utf-8",
        )


class RedirectResponse(Response):
    """HTTP redirect response."""

    def __init__(self, url, status_code=302, headers=None):
        headers = headers or {}
        headers["location"] = url
        super().__init__(
            body=f"Redirecting to {url}",
            status_code=status_code,
            headers=headers,
            content_type="text/plain",
        )


class StreamingResponse:
    """Streaming response for large payloads or server-sent events."""

    def __init__(self, generator, status_code=200, headers=None, content_type="application/octet-stream"):
        self.generator = generator
        self.status_code = status_code
        self.headers = headers or {}
        self.content_type = content_type
        if "content-type" not in {k.lower() for k in self.headers}:
            self.headers["content-type"] = self.content_type

    def _build_headers(self):
        headers = []
        for key, value in self.headers.items():
            if isinstance(key, str):
                key = key.encode("latin-1")
            if isinstance(value, str):
                value = value.encode("latin-1")
            headers.append([key, value])
        return headers

    async def send(self, send):
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self._build_headers(),
        })
        if hasattr(self.generator, "__aiter__"):
            async for chunk in self.generator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                })
        else:
            for chunk in self.generator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                })
        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        })


# Standard HTTP status codes
HTTP_STATUS_CODES = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    413: "Payload Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}
