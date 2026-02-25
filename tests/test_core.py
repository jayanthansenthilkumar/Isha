"""
Tests for Isha Core — App, Routing, Request, Response.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isha import Isha, JSONResponse, HTMLResponse, Response
from isha.routing import Router, Route
from isha.request import Request
from isha.response import RedirectResponse, StreamingResponse
from isha.testing import TestClient


# ── Route Matching Tests ────────────────────────────────────────────

def test_static_route_matching():
    router = Router()

    @router.route("/home")
    def home(request):
        return "Home"

    route, params = router.resolve("/home", "GET")
    assert route is not None
    assert params == {}
    assert route.name == "home"


def test_dynamic_route_matching():
    router = Router()

    @router.route("/user/<int:id>")
    def get_user(request, id):
        return f"User {id}"

    route, params = router.resolve("/user/42", "GET")
    assert route is not None
    assert params == {"id": 42}


def test_string_param_route():
    router = Router()

    @router.route("/hello/<str:name>")
    def hello(request, name):
        return f"Hello, {name}"

    route, params = router.resolve("/hello/Alice", "GET")
    assert route is not None
    assert params == {"name": "Alice"}


def test_multiple_params():
    router = Router()

    @router.route("/post/<int:year>/<str:slug>")
    def post(request, year, slug):
        return f"{year}: {slug}"

    route, params = router.resolve("/post/2025/hello-world", "GET")
    assert route is not None
    assert params == {"year": 2025, "slug": "hello-world"}


def test_method_not_allowed():
    router = Router()

    @router.route("/data", methods=["GET"])
    def data(request):
        return "data"

    route, params = router.resolve("/data", "POST")
    assert route is None
    assert params.get("_method_not_allowed") is True


def test_not_found():
    router = Router()

    @router.route("/exists")
    def exists(request):
        return "exists"

    route, params = router.resolve("/does-not-exist", "GET")
    assert route is None


def test_url_for():
    router = Router()

    @router.route("/user/<int:id>", name="user_detail")
    def user(request, id):
        return f"User {id}"

    url = router.url_for("user_detail", id=5)
    assert url == "/user/5"


# ── App and Request Handling Tests ──────────────────────────────────

def test_basic_get():
    app = Isha("test")

    @app.route("/")
    async def index(request):
        return JSONResponse({"hello": "world"})

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["hello"] == "world"


def test_post_with_json():
    app = Isha("test")

    @app.route("/echo", methods=["POST"])
    async def echo(request):
        data = await request.json()
        return JSONResponse({"received": data})

    client = TestClient(app)
    response = client.post("/echo", json_data={"name": "Isha"})
    assert response.status_code == 200
    assert response.json()["received"]["name"] == "Isha"


def test_dynamic_route_handler():
    app = Isha("test")

    @app.route("/greet/<str:name>")
    async def greet(request, name):
        return JSONResponse({"message": f"Hello, {name}!"})

    client = TestClient(app)
    response = client.get("/greet/Alice")
    assert response.status_code == 200
    assert "Alice" in response.json()["message"]


def test_query_params():
    app = Isha("test")

    @app.route("/search")
    async def search(request):
        q = request.query_params.get("q", "")
        return JSONResponse({"query": q})

    client = TestClient(app)
    response = client.get("/search", params={"q": "isha"})
    assert response.status_code == 200
    assert response.json()["query"] == "isha"


def test_404_handler():
    app = Isha("test")

    @app.route("/exists")
    async def exists(request):
        return "OK"

    client = TestClient(app)
    response = client.get("/nope")
    assert response.status_code == 404


def test_method_not_allowed():
    app = Isha("test")

    @app.route("/only-get", methods=["GET"])
    async def only_get(request):
        return "OK"

    client = TestClient(app)
    response = client.post("/only-get")
    assert response.status_code == 405


def test_html_response():
    app = Isha("test")

    @app.route("/page")
    async def page(request):
        return HTMLResponse("<h1>Hello</h1>")

    client = TestClient(app)
    response = client.get("/page")
    assert response.status_code == 200
    assert "<h1>Hello</h1>" in response.text
    assert response.is_html


def test_redirect_response():
    app = Isha("test")

    @app.route("/old")
    async def old(request):
        return RedirectResponse("/new")

    client = TestClient(app)
    response = client.get("/old")
    assert response.status_code == 302
    assert response.headers.get("location") == "/new"


def test_dict_auto_json():
    app = Isha("test")

    @app.route("/data")
    async def data(request):
        return {"key": "value"}

    client = TestClient(app)
    response = client.get("/data")
    assert response.status_code == 200
    assert response.json()["key"] == "value"


def test_string_auto_html():
    app = Isha("test")

    @app.route("/text")
    async def text(request):
        return "Hello World"

    client = TestClient(app)
    response = client.get("/text")
    assert response.status_code == 200
    assert response.text == "Hello World"


def test_sync_handler():
    app = Isha("test")

    @app.route("/sync")
    def sync_handler(request):
        return {"sync": True}

    client = TestClient(app)
    response = client.get("/sync")
    assert response.status_code == 200
    assert response.json()["sync"] is True


def test_custom_error_handler():
    app = Isha("test")

    @app.error_handler(404)
    async def custom_404(request):
        return JSONResponse({"custom": "not found"}, status_code=404)

    client = TestClient(app)
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["custom"] == "not found"


# ── Response Object Tests ───────────────────────────────────────────

def test_response_cookie():
    resp = Response("OK")
    resp.set_cookie("session", "abc123", httponly=True)
    headers = resp._build_headers()
    cookie_headers = [h for h in headers if h[0] == b"set-cookie"]
    assert len(cookie_headers) == 1


def test_json_response():
    resp = JSONResponse({"a": 1})
    assert b'"a": 1' in resp.body
    assert resp.status_code == 200


# ── Request Object Tests ────────────────────────────────────────────

def test_request_from_raw():
    raw = b"GET /test?q=hello HTTP/1.1\r\nHost: localhost\r\nCookie: sid=abc\r\n\r\n"
    req = Request.from_raw(raw)
    assert req.method == "GET"
    assert req.path == "/test"
    assert req.query_params.get("q") == "hello"
    assert req.headers.get("host") == "localhost"
    assert req.cookies.get("sid") == "abc"


# ── Runner ──────────────────────────────────────────────────────────

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

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")

    if failed > 0:
        sys.exit(1)
