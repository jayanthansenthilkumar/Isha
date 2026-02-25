"""
Tests for Isha Middleware System.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isha import Isha, JSONResponse
from isha.middleware import CORSMiddleware, SecurityHeadersMiddleware, Middleware
from isha.testing import TestClient


def test_before_request_middleware():
    app = Isha("test")

    @app.before_request
    def add_custom_header(request):
        request.state["custom"] = "hello"
        return None

    @app.route("/check")
    async def check(request):
        return JSONResponse({"custom": request.state.get("custom")})

    client = TestClient(app)
    response = client.get("/check")
    assert response.json()["custom"] == "hello"


def test_after_request_middleware():
    app = Isha("test")

    @app.after_request
    def add_header(request, response):
        response.headers["x-custom"] = "test-value"
        return response

    @app.route("/check")
    async def check(request):
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/check")
    assert response.headers.get("x-custom") == "test-value"


def test_cors_middleware():
    app = Isha("test")
    app.add_middleware(CORSMiddleware(allow_origins=["*"]))

    @app.route("/api")
    async def api(request):
        return JSONResponse({"data": True})

    client = TestClient(app)
    response = client.get("/api", headers={"origin": "http://example.com"})
    assert "access-control-allow-origin" in response.headers


def test_cors_preflight():
    app = Isha("test")
    app.add_middleware(CORSMiddleware(allow_origins=["*"]))

    @app.route("/api", methods=["POST"])
    async def api(request):
        return JSONResponse({"data": True})

    client = TestClient(app)
    # OPTIONS request should be handled by CORS middleware
    # Note: our router may not have a route for OPTIONS on /api specifically,
    # but the middleware should handle it
    response = client._request("OPTIONS", "/api", headers={"origin": "http://example.com"})
    assert response.status_code == 204


def test_security_headers_middleware():
    app = Isha("test")
    app.add_middleware(SecurityHeadersMiddleware())

    @app.route("/secure")
    async def secure(request):
        return JSONResponse({"secure": True})

    client = TestClient(app)
    response = client.get("/secure")
    assert "x-content-type-options" in response.headers
    assert "x-frame-options" in response.headers


def test_custom_middleware_class():
    class CounterMiddleware(Middleware):
        def __init__(self):
            self.count = 0

        async def before_request(self, request):
            self.count += 1
            request.state["request_count"] = self.count
            return None

    app = Isha("test")
    counter = CounterMiddleware()
    app.add_middleware(counter)

    @app.route("/count")
    async def count(request):
        return JSONResponse({"count": request.state["request_count"]})

    client = TestClient(app)
    client.get("/count")
    client.get("/count")
    response = client.get("/count")
    assert response.json()["count"] == 3


def test_middleware_short_circuit():
    app = Isha("test")

    @app.before_request
    def block_all(request):
        if request.path == "/blocked":
            return JSONResponse({"error": "Blocked"}, status_code=403)
        return None

    @app.route("/blocked")
    async def blocked(request):
        return JSONResponse({"should": "not reach"})

    @app.route("/allowed")
    async def allowed(request):
        return JSONResponse({"allowed": True})

    client = TestClient(app)
    resp1 = client.get("/blocked")
    assert resp1.status_code == 403

    resp2 = client.get("/allowed")
    assert resp2.status_code == 200
    assert resp2.json()["allowed"] is True


def test_exception_handler():
    app = Isha("test")

    @app.exception_handler
    async def handle_exception(request, exc):
        return JSONResponse({"error": "Caught!", "detail": str(exc)}, status_code=500)

    @app.route("/crash")
    async def crash(request):
        raise ValueError("Something broke")

    client = TestClient(app)
    response = client.get("/crash")
    assert response.status_code == 500
    assert response.json()["error"] == "Caught!"


if __name__ == "__main__":
    test_funcs = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0

    for test in test_funcs:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
