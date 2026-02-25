"""
Isha Testing Framework — Built-in test client and utilities.

Example:
    from isha.testing import TestClient
    from app import app
    
    client = TestClient(app)
    
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger("isha.testing")


class TestResponse:
    """Wraps a response for easy testing assertions."""

    def __init__(self, status_code=200, headers=None, body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self._json = None

    def json(self) -> Any:
        """Parse response body as JSON."""
        if self._json is None:
            self._json = json.loads(self.body.decode("utf-8"))
        return self._json

    @property
    def text(self) -> str:
        """Response body as string."""
        return self.body.decode("utf-8")

    @property
    def content_type(self) -> str:
        """Get content-type header."""
        return self.headers.get("content-type", "")

    @property
    def is_json(self) -> bool:
        return "application/json" in self.content_type

    @property
    def is_html(self) -> bool:
        return "text/html" in self.content_type

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def __repr__(self):
        return f"<TestResponse {self.status_code}>"


class TestClient:
    """
    Test client for making requests to an Isha app without a real server.
    
    Example:
        client = TestClient(app)
        
        # GET request
        response = client.get("/api/users")
        
        # POST with JSON
        response = client.post("/api/users", json={"name": "Alice"})
        
        # With headers
        response = client.get("/api/protected", headers={"Authorization": "Bearer token"})
    """

    def __init__(self, app):
        self.app = app
        self.cookies: Dict[str, str] = {}
        self.default_headers: Dict[str, str] = {}

    def get(self, path, headers=None, params=None, **kwargs):
        return self._request("GET", path, headers=headers, params=params, **kwargs)

    def post(self, path, headers=None, data=None, json=None, json_data=None, **kwargs):
        return self._request("POST", path, headers=headers, data=data, json_data=json or json_data, **kwargs)

    def put(self, path, headers=None, data=None, json=None, json_data=None, **kwargs):
        return self._request("PUT", path, headers=headers, data=data, json_data=json or json_data, **kwargs)

    def delete(self, path, headers=None, **kwargs):
        return self._request("DELETE", path, headers=headers, **kwargs)

    def patch(self, path, headers=None, data=None, json=None, json_data=None, **kwargs):
        return self._request("PATCH", path, headers=headers, data=data, json_data=json or json_data, **kwargs)

    def _request(
        self,
        method,
        path,
        headers=None,
        data=None,
        json_data=None,
        params=None,
        cookies=None,
    ):
        """Make a request to the app."""
        # Build query string
        if params:
            qs = urlencode(params)
            if "?" in path:
                path += "&" + qs
            else:
                path += "?" + qs

        query_string = ""
        if "?" in path:
            path, query_string = path.split("?", 1)

        # Build headers
        all_headers = dict(self.default_headers)
        if headers:
            all_headers.update(headers)

        # Build body
        body = b""
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            all_headers.setdefault("content-type", "application/json")
        elif data is not None:
            if isinstance(data, dict):
                body = urlencode(data).encode("utf-8")
                all_headers.setdefault("content-type", "application/x-www-form-urlencoded")
            elif isinstance(data, str):
                body = data.encode("utf-8")
            elif isinstance(data, bytes):
                body = data

        all_headers["content-length"] = str(len(body))

        # Build cookies
        all_cookies = dict(self.cookies)
        if cookies:
            all_cookies.update(cookies)
        if all_cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
            all_headers["cookie"] = cookie_str

        # Build ASGI scope
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": query_string.encode("utf-8"),
            "root_path": "",
            "scheme": "http",
            "headers": [
                [k.lower().encode("latin-1"), v.encode("latin-1")]
                for k, v in all_headers.items()
            ],
            "server": ("testclient", 80),
            "client": ("127.0.0.1", 0),
        }

        body_sent = False
        response_started = False
        response_status = 200
        response_headers = {}
        response_body = b""

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal response_started, response_status, response_headers, response_body

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message["status"]
                for h_name, h_value in message.get("headers", []):
                    name = h_name.decode("latin-1") if isinstance(h_name, bytes) else h_name
                    value = h_value.decode("latin-1") if isinstance(h_value, bytes) else h_value
                    response_headers[name.lower()] = value

                    # Track set-cookie
                    if name.lower() == "set-cookie":
                        self._parse_set_cookie(value)

            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")

        # Run the ASGI app
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        async def run():
            nonlocal response_body
            response_body = b""
            await self.app(scope, receive, send)

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, run())
                future.result()
        else:
            asyncio.run(run())

        return TestResponse(
            status_code=response_status,
            headers=response_headers,
            body=response_body,
        )

    def _parse_set_cookie(self, cookie_str):
        """Parse a Set-Cookie header and store the cookie."""
        if "=" in cookie_str:
            parts = cookie_str.split(";")[0]
            key, value = parts.split("=", 1)
            self.cookies[key.strip()] = value.strip()


# ── Assertion Helpers ────────────────────────────────────────────────

def assert_status(response, expected_status):
    """Assert response has the expected status code."""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. Body: {response.text[:200]}"
    )


def assert_json(response, expected_data=None, key=None, value=None):
    """Assert response is JSON and optionally check content."""
    assert response.is_json, f"Expected JSON response, got {response.content_type}"
    data = response.json()

    if expected_data is not None:
        assert data == expected_data, f"Expected {expected_data}, got {data}"

    if key is not None:
        assert key in data, f"Key '{key}' not found in response"
        if value is not None:
            assert data[key] == value, f"Expected {key}={value}, got {key}={data[key]}"


def assert_html(response, contains=None):
    """Assert response is HTML and optionally check content."""
    assert response.is_html, f"Expected HTML response, got {response.content_type}"
    if contains:
        assert contains in response.text, f"Expected '{contains}' in HTML response"


def assert_redirect(response, location=None):
    """Assert response is a redirect."""
    assert 300 <= response.status_code < 400, (
        f"Expected redirect status, got {response.status_code}"
    )
    if location:
        actual = response.headers.get("location", "")
        assert actual == location, f"Expected redirect to '{location}', got '{actual}'"
