<p align="center">
  <h1 align="center">✦ Ishaa Framework</h1>
  <p align="center"><strong>A Modern, High-Performance Python Web Framework</strong></p>
  <p align="center">
    <em>Simplicity of Flask · Structure of Django · Performance mindset of FastAPI</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/version-1.2.0-orange.svg" alt="Version 1.2.0">
  <img src="https://img.shields.io/badge/ASGI-3.0-purple.svg" alt="ASGI 3.0">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/SARE-Self--Evolving-ff69b4.svg" alt="SARE Engine">
  <img src="https://img.shields.io/badge/RMF-Multiple--Realities-blueviolet.svg" alt="RMF Engine">
  <img src="https://img.shields.io/badge/SEQP-Quality--Pipeline-critical.svg" alt="SEQP Engine">
</p>

---

## What is Ishaa?

**Ishaa** is a lightweight, modular, high-performance Python web framework built from scratch with **zero required external dependencies**. It provides a complete ASGI-compatible architecture including a custom ORM, built-in authentication, a Jinja-like template engine, WebSocket support, GraphQL, dependency injection, background tasks, and a CLI - all implemented in pure Python standard library.

Ishaa v1.2.0 introduces **three world-first engines**:
- **SARE** - Self-Evolving Adaptive Routing Engine (self-optimizing routing & middleware)
- **RMF** - Reality-Mode Framework: One Codebase, Multiple Realities (parallel behavioral universes per route)
- **SEQP** - Self-Evolving Quality Pipeline (auto risk analysis, test generation, CI/CD rewriting)

---

## Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Routing](#-routing)
- [Request & Response](#-request--response)
- [Middleware](#-middleware)
- [Blueprints](#-blueprints)
- [ORM (Database)](#-orm-database)
- [Authentication](#-authentication)
- [Template Engine](#-template-engine)
- [WebSocket](#-websocket)
- [Background Tasks](#-background-tasks)
- [GraphQL](#-graphql)
- [Dependency Injection](#-dependency-injection)
- [Plugins](#-plugins)
- [OpenAPI / Swagger](#-openapi--swagger)
- [CLI Tool](#-cli-tool)
- [Testing](#-testing)
- [SARE Engine](#-sare--self-evolving-adaptive-routing-engine)
- [RMF - Reality-Mode Framework](#-rmf--reality-mode-framework)
- [SEQP - Self-Evolving Quality Pipeline](#-seqp--self-evolving-quality-pipeline)
- [Architecture](#-architecture)
- [Version History](#-version-history)
- [Requirements](#-requirements)
- [License](#-license)

---

## ✨ Features

| Category | What You Get |
|----------|-------------|
| **Core** | ASGI 3.0 interface, async/sync handler support, full middleware pipeline, modular blueprints |
| **SARE Engine** | Self-evolving routing, traffic heat mapping, middleware auto-reordering, AI latency prediction, code path optimization, intelligence reports |
| **RMF Engine** | Reality-Mode Framework: same route in multiple realities, traffic-based selection, time-bound realities, parallel simulation, self-retiring experiments |
| **SEQP Engine** | Self-Evolving Quality Pipeline: risk analysis, auto test generation, CI/CD pipeline rewriting, deployment guards, drift intelligence |
| **Routing** | Typed parameters (`int`, `float`, `uuid`, `slug`, `path`), regex matching, named routes, `url_for()` reverse lookup |
| **ORM** | SQLite adapter, model metaclass, chainable QueryBuilder, auto-migrations, field types (Text, Integer, Boolean, DateTime, Float) |
| **Auth** | PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 JWT tokens, session management, `@login_required` and `@role_required` decorators |
| **Templates** | Jinja-like syntax with `{% extends %}`, `{% block %}`, `{% include %}`, `{% for %}`, `{% if %}`, 16+ built-in filters, auto-escaping |
| **Middleware** | CORS, CSRF protection, rate limiting, security headers, custom middleware classes with before/after hooks |
| **WebSocket** | Full-duplex communication, rooms, broadcast, JSON messaging protocol |
| **GraphQL** | Schema definition, queries, mutations, subscriptions, built-in GraphiQL IDE |
| **Plugins** | Cache (TTL-based), static file serving, mail (SMTP), admin panel scaffold |
| **DI** | FastAPI-style `Depends()`, async support, generator cleanup |
| **CLI** | Project scaffolding, dev server with auto-reload, migration management, route listing, interactive shell |
| **Testing** | Built-in `TestClient`, assertion helpers, no running server required |
| **Docs** | Auto-generated OpenAPI 3.0 specification, Swagger UI endpoint |

---

## 🚀 Quick Start

### Installation

```bash
# From source
git clone https://github.com/jayanthansenthilkumar/ISHAA_Framework.git
cd ISHAA_Framework
pip install -e .

# With all optional dependencies
pip install -e ".[full]"    # uvicorn + bcrypt + jinja2
```

### Hello World

```python
from ishaa import Ishaa

app = Ishaa()

@app.route("/")
async def hello(request):
    return {"message": "Hello from Ishaa! ✦"}

@app.route("/hello/<name>")
async def greet(request, name):
    return f"<h1>Hello, {name}!</h1>"

app.run()
```

```bash
python app.py
# ✦ Ishaa Framework v1.1.0
# Server running at http://127.0.0.1:8000
```

---

## 🛤️ Routing

Ishaa supports typed URL parameters, multiple HTTP methods, named routes, and reverse URL generation.

```python
from ishaa import Ishaa

app = Ishaa()

# Basic route
@app.route("/")
async def index(request):
    return "Welcome to Ishaa!"

# Typed URL parameters (auto-converted)
@app.route("/users/<int:id>")
async def get_user(request, id):
    return {"user_id": id}  # id is already an int

# Multiple HTTP methods
@app.route("/items", methods=["GET", "POST"])
async def items(request):
    if request.method == "POST":
        data = await request.json()
        return {"created": data}
    return {"items": []}

# Method shortcut decorators
@app.get("/health")
async def health(request):
    return {"status": "ok"}

@app.post("/upload")
async def upload(request):
    body = await request.body()
    return {"size": len(body)}

# Named routes with url_for() reverse lookup
@app.route("/profile/<username>", name="user_profile")
async def profile(request, username):
    return f"Profile: {username}"

url = app.router.url_for("user_profile", username="alice")
# => "/profile/alice"
```

**Supported parameter types:** `str` (default), `int`, `float`, `uuid`, `slug`, `path`

---

## 📨 Request & Response

### Request Object

Every handler receives a `Request` object with parsed HTTP data:

```python
@app.route("/example", methods=["POST"])
async def example(request):
    # Request properties
    request.method          # "POST"
    request.path            # "/example"
    request.query_params    # {"key": "value"}
    request.headers         # {"content-type": "application/json", ...}
    request.cookies         # {"session_id": "abc123"}
    request.content_type    # "application/json"
    request.client          # ("127.0.0.1", 5000)
    
    # Async body parsing
    body = await request.body()          # raw bytes
    text = await request.text()          # decoded string
    data = await request.json()          # parsed JSON dict
    form = await request.form()          # form data dict
```

### Response Types

Ishaa auto-detects response types from return values, or you can use explicit response classes:

```python
from ishaa import Response, JSONResponse, HTMLResponse, RedirectResponse
from ishaa.response import StreamingResponse

# Auto-detection (just return from handlers)
return "Hello"                      # → HTMLResponse
return {"key": "value"}             # → JSONResponse
return [1, 2, 3]                    # → JSONResponse

# Explicit response classes
return Response("Plain text", status=200, content_type="text/plain")
return JSONResponse({"ok": True}, status=201)
return HTMLResponse("<h1>Page</h1>")
return RedirectResponse("/login")

# Cookie management
resp = JSONResponse({"logged_in": True})
resp.set_cookie("token", "abc123", max_age=3600, httponly=True, secure=True)
resp.delete_cookie("old_cookie")
return resp

# Server-Sent Events / Streaming
async def event_stream():
    for i in range(10):
        yield f"data: {i}\n\n"
return StreamingResponse(event_stream(), content_type="text/event-stream")
```

---

## 🔗 Middleware

Ishaa provides a middleware pipeline with built-in CORS, rate limiting, security headers, and CSRF protection.

```python
from ishaa.middleware import Middleware, CORSMiddleware, RateLimitMiddleware

app = Ishaa()

# Built-in CORS middleware
app.add_middleware(CORSMiddleware(
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_credentials=True
))

# Rate limiting (per-client IP)
app.add_middleware(RateLimitMiddleware(max_requests=100, window_seconds=60))

# Decorator-based hooks
@app.before_request
async def log_request(request):
    print(f"{request.method} {request.path}")
    return None  # Continue; return a Response to short-circuit

@app.after_request
async def add_header(request, response):
    response.headers["X-Powered-By"] = "Ishaa"
    return response

# Custom middleware class
class TimingMiddleware(Middleware):
    async def before_request(self, request):
        import time
        request._start = time.time()
        return None

    async def after_request(self, request, response):
        import time
        elapsed = time.time() - request._start
        response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
        return response

app.add_middleware(TimingMiddleware())
```

---

## 📦 Blueprints

Organize your application into modular, reusable sections:

```python
from ishaa import Blueprint

# Create a blueprint with a URL prefix
api = Blueprint("api", prefix="/api/v1")

@api.route("/users")
async def list_users(request):
    return {"users": []}

@api.route("/users/<int:id>")
async def get_user(request, id):
    return {"user": id}

# Register with the app
app.register_blueprint(api)
# Routes: /api/v1/users, /api/v1/users/<int:id>
```

---

## 🗄️ ORM (Database)

A lightweight ORM with SQLite support, model definitions, chainable queries, and migrations:

```python
from ishaa.orm import Database, Model, IntegerField, TextField, BooleanField, DateTimeField

# Initialize database
db = Database("app.db")

# Define models with typed fields
class User(Model):
    _table = "users"
    _db = db
    
    name = TextField()
    email = TextField()
    age = IntegerField(default=0)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now=True)

# Create tables
User.create_table()

# CRUD operations
user = User.create(name="Alice", email="alice@example.com", age=30)
print(user.id)       # Auto-generated ID
print(user.name)     # "Alice"

user.age = 31
user.save()           # Update existing record

user = User.get(1)    # Fetch by primary key
users = User.all()    # Fetch all records

# Chainable QueryBuilder
active_users = (User.query()
    .filter(is_active=True)
    .filter(age__gt=18)
    .order_by("name")
    .limit(10)
    .all())

count = User.query().filter(is_active=True).count()
exists = User.query().filter(email="alice@example.com").exists()

# Bulk operations
User.query().filter(is_active=False).delete()
User.query().filter(age__lt=18).update(is_active=False)

# Query operators: __gt, __lt, __gte, __lte, __ne, __like, __in
results = User.query().filter(name__like="%Ali%").all()
results = User.query().filter(age__in=[25, 30, 35]).all()
```

---

## 🔐 Authentication

Built-in password hashing (PBKDF2), JWT tokens, session management, and route protection decorators:

```python
from ishaa.auth import PasswordHasher, JWT, SessionManager, login_required, role_required

# Password hashing (PBKDF2-HMAC-SHA256, 260000 iterations)
hasher = PasswordHasher()
hashed = hasher.hash("my_password")
is_valid = hasher.verify("my_password", hashed)  # True

# JWT tokens (HMAC-SHA256)
jwt = JWT(secret="your-secret-key")
token = jwt.encode({"user_id": 1, "role": "admin"}, expires_in=3600)
payload = jwt.decode(token)  # {"user_id": 1, "role": "admin", "exp": ..., "iat": ...}

# Session management (server-side, auto-expiry)
sessions = SessionManager(max_age=3600)
session_id = sessions.create({"user_id": 1})
session = sessions.get(session_id)
session.set("theme", "dark")
value = session.get("theme")  # "dark"
sessions.destroy(session_id)

# Route protection decorators
@app.route("/dashboard")
@login_required(jwt_instance=jwt)
async def dashboard(request):
    return f"Welcome, user {request.user['user_id']}!"

@app.route("/admin")
@role_required(jwt_instance=jwt, roles=["admin"])
async def admin_panel(request):
    return "Admin area"
```

---

## 📝 Template Engine

A Jinja-like template engine with inheritance, loops, conditionals, includes, and 16+ built-in filters:

```python
app = Ishaa(template_dir="templates")

@app.route("/page")
async def page(request):
    return app.render("page.html", title="Home", items=["a", "b", "c"])
```

**templates/base.html:**
```html
<!DOCTYPE html>
<html>
<head><title>{% block title %}Default{% endblock %}</title></head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

**templates/page.html:**
```html
{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
  <h1>{{ title|upper }}</h1>
  
  {% for item in items %}
    <p>{{ loop.index }}. {{ item }}</p>
  {% endfor %}
  
  {% if user %}
    <p>Welcome, {{ user.name }}!</p>
  {% else %}
    <p>Please log in.</p>
  {% endif %}
  
  {# This is a comment #}
  {% include "_footer.html" %}
{% endblock %}
```

**Built-in filters:** `upper`, `lower`, `title`, `capitalize`, `strip`, `length`, `default`, `int`, `float`, `str`, `join`, `first`, `last`, `reverse`, `truncate`, `replace`, `format_number`

---

## 🔌 WebSocket

Full-duplex WebSocket communication with rooms and broadcast:

```python
from ishaa.websocket import websocket_route, WebSocketRoom

chat_room = WebSocketRoom("chat")

@app.route("/ws")
@websocket_route
async def websocket_handler(ws):
    await ws.accept()
    chat_room.add(ws)
    
    try:
        while True:
            data = await ws.receive_json()
            await chat_room.broadcast(f"{data['user']}: {data['message']}")
    except Exception:
        chat_room.remove(ws)
        await ws.close()
```

---

## ⏱️ Background Tasks

Async task queue with status tracking and periodic scheduling:

```python
from ishaa.tasks import TaskQueue, task

queue = TaskQueue(max_workers=4)

@task(queue)
async def send_email(to, subject, body):
    import asyncio
    await asyncio.sleep(2)     # Simulate I/O
    return f"Email sent to {to}"

# Dispatch a task (non-blocking)
result = await send_email.delay("user@example.com", "Hello", "Welcome!")
print(result.task_id)   # UUID
print(result.status)    # TaskStatus.PENDING → RUNNING → COMPLETED

# Check status later
status = queue.get_status(result.task_id)

# Periodic tasks (every 5 minutes)
@queue.periodic(interval=300)
async def cleanup():
    print("Running scheduled cleanup...")
```

---

## 🔮 GraphQL

Built-in GraphQL engine with query/mutation/subscription support and GraphiQL IDE:

```python
from ishaa.graphql import GraphQLSchema, mount_graphql

schema = GraphQLSchema()

@schema.query("hello")
async def resolve_hello(name: str = "World"):
    return f"Hello, {name}!"

@schema.query("users")
async def resolve_users():
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@schema.mutation("createUser")
async def create_user(name: str, email: str):
    return {"id": 3, "name": name, "email": email}

# Mount at /graphql with interactive GraphiQL IDE
mount_graphql(app, schema, path="/graphql")
```

Visit `http://localhost:8000/graphql` to use the interactive GraphiQL IDE.

---

## 💉 Dependency Injection

FastAPI-style dependency injection with `Depends()`:

```python
from ishaa.di import Depends, inject

async def get_db():
    db = Database("app.db")
    yield db  # Generator dependencies are auto-cleaned up

async def get_current_user(request):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        return None
    return jwt.decode(token)

@app.route("/profile")
@inject
async def profile(request, user=Depends(get_current_user), db=Depends(get_db)):
    return {"user": user}
```

---

## 🧩 Plugins

Extend Ishaa with the built-in plugin system:

```python
from ishaa.plugins import CachePlugin, StaticFilesPlugin, AdminPlugin

# In-memory caching with TTL
cache = CachePlugin(default_ttl=300)
app.register_plugin(cache)

@app.route("/expensive")
@cache.cached(ttl=60)
async def expensive_computation(request):
    return {"result": compute_something()}

# Static file serving
static = StaticFilesPlugin(directory="static", prefix="/static")
app.register_plugin(static)
# Serves ./static/ files at /static/...

# Admin panel scaffold
admin = AdminPlugin(prefix="/admin")
admin.register_model(User)
admin.register_model(Post)
app.register_plugin(admin)
# Auto-generates CRUD views at /admin/users, /admin/posts
```

---

## 📄 OpenAPI / Swagger

Auto-generated API documentation:

```python
from ishaa.openapi import mount_docs

mount_docs(app, title="My API", version="1.0.0", description="My awesome API")
# Swagger UI at:       http://localhost:8000/docs
# OpenAPI JSON spec at: http://localhost:8000/openapi.json
```

---

## 🛠️ CLI Tool

Ishaa includes a command-line tool for project scaffolding, development, and management:

```bash
# Create a new project with full structure
ishaa create project myapp

# Start development server with auto-reload
ishaa run --host 0.0.0.0 --port 8000 --reload

# Database migrations
ishaa migrate run
ishaa migrate create add_users_table
ishaa migrate status

# List all registered routes
ishaa routes

# Interactive Python shell with app context
ishaa shell

# Show version
ishaa version
```

**Scaffolded project structure:**
```
myapp/
├── app.py              # Main application entry point
├── config.py           # Configuration settings
├── models.py           # Database models
├── requirements.txt    # Dependencies (ishaa>=1.0.0)
├── routes/
│   └── __init__.py     # Route blueprints
├── templates/
│   └── base.html       # Base HTML template
├── static/
│   ├── css/
│   └── js/
└── tests/
    └── test_app.py     # Test suite
```

---

## 🧪 Testing

Built-in test client - make requests without a running server:

```python
from ishaa.testing import TestClient

client = TestClient(app)

# Make requests
response = client.get("/")
assert response.ok
assert response.status == 200

response = client.post("/api/users", json={"name": "Alice"})
assert response.status == 201
assert response.json()["name"] == "Alice"

# Test with authentication headers
response = client.get("/protected", headers={"Authorization": "Bearer <token>"})

# Test with cookies
response = client.get("/dashboard", cookies={"session_id": "abc123"})

# Assertion helpers
from ishaa.testing import assert_status, assert_json, assert_html, assert_redirect

assert_status(response, 200)
assert_json(response, {"ok": True})
assert_html(response, contains="<h1>")
assert_redirect(response, "/login")
```

```bash
# Run tests with pytest
pip install pytest
pytest tests/ -v
```

---

## 🧬 SARE - Self-Evolving Adaptive Routing Engine

> **The world's first web framework with self-optimizing routing and middleware intelligence.**

SARE automatically **observes**, **decides**, **adapts**, and **evolves** your application's routing and middleware execution based on real-time traffic patterns.

### Enable SARE

```python
from ishaa import Ishaa

app = Ishaa("myapp")
app.enable_sare()  # One line - self-optimization begins immediately

@app.route("/api/data")
async def data(request):
    return {"items": await fetch_items()}

@app.route("/sare/report")
async def intelligence(request):
    return app.sare.report()  # Full intelligence dashboard

app.run()
```

### SARE Architecture (5 Layers)

| Layer | Module | What It Does |
|-------|--------|-------------|
| **Observation** | `sare_traffic.py` | Tracks per-route latency (p50/p95/p99), requests per second, error rates, and computes heat scores |
| **Decision** | `sare_optimizer.py` | Promotes hot routes to O(1) fast-path cache; reorders middleware by measured efficiency ratios |
| **Prediction** | `sare_predictor.py` | EWMA + linear regression forecasting, z-score spike detection, reinforcement-based heuristics |
| **Execution** | `sare_codepath.py` | Response memoization, JSON pre-encoding, handler result caching - all applied automatically |
| **Reporting** | `sare_reporter.py` | Generates intelligence reports: performance deltas, evolution history, optimization recommendations |

### Configuration Options

```python
app.enable_sare(
    optimize_interval=10,    # Seconds between optimization cycles
    cache_size=500,          # Max response cache entries
    cache_ttl=30,            # Default cache TTL (seconds)
    hot_route_slots=20,      # Number of hot route fast-path slots
    middleware_reorder=True,  # Enable middleware auto-reordering
    predictor=True,           # Enable AI latency predictor
    auto_memoize=True,        # Auto-enable memoization for hot GET routes
)
```

### Auto-Memoization Criteria

Routes are automatically memoized when all conditions are met:
- HTTP method is **GET**
- Requests per second ≥ **5.0**
- Error rate ≤ **2%**
- Total request count ≥ **50**

### Runtime Control

```python
app.sare.disable()       # Pause SARE optimization
app.sare.enable()        # Resume optimization
app.sare.reset()         # Reset all collected data
app.sare.print_report()  # Print report to console
app.sare.stats()         # Get quick stats dict
```

---

## 🌐 RMF - Reality-Mode Framework

> **One Codebase. Multiple Realities. The world's first execution-layer abstraction for web frameworks.**

RMF allows the **same route** to exist in **multiple behavioral universes**. Each request can enter a different "reality" with different logic, middleware, caching, and security rules - without conditional clutter or branching code.

### Enable RMF

```python
from ishaa import Ishaa

app = Ishaa("myapp")
app.enable_rmf()

@app.route("/recommend")
@app.reality("stable")
async def recommend_v1(request):
    return {"algo": "classic", "version": 1}

@app.route("/recommend")
@app.reality("experimental", traffic_pct=20, auto_promote=True)
async def recommend_v2(request):
    return {"algo": "neural_v2", "version": 2}

app.run()
```

80% of users see `stable`, 20% see `experimental`. When the experimental reality proves stable (low error rate, acceptable latency), it auto-promotes to become the new default.

### Reality Selection Engine

Requests are routed to realities using a priority chain:

| Priority | Method | Description |
|----------|--------|-------------|
| 1 | **Header** | `X-Reality: experimental` forces a specific reality |
| 2 | **Cookie** | Sticky session remembers the user's assigned reality |
| 3 | **Behavior Rules** | Custom functions evaluate request properties |
| 4 | **Time Window** | Realities active only during specified hours |
| 5 | **Traffic %** | Deterministic hash-based traffic splitting |

### Behavior Rules

```python
@app.rmf_behavior_rule
def route_premium_users(request, realities):
    if request.headers.get("x-user-tier") == "premium":
        return "premium" if "premium" in realities else None
    return None
```

### Time-Bound Realities

```python
@app.route("/api/feed")
@app.reality("night_mode", active_between="22:00-06:00")
async def feed_night(request):
    return {"theme": "dark", "content": "curated_night"}
```

### Parallel Simulation Mode

```python
app.enable_rmf(enable_parallel_sim=True, sim_sample_rate=0.1)
```

Runs **shadow realities** alongside the primary one, compares outputs, and logs drift without affecting the user's response.

### Self-Retiring Realities

```python
@app.route("/api/search")
@app.reality("experimental", auto_promote=True,
             promote_after_requests=500,
             promote_error_threshold=0.01,
             promote_latency_ratio=1.1)
async def search_v2(request):
    return {"engine": "semantic"}
```

When the experimental reality completes 500+ requests with <1% error rate and latency within 110% of stable, it automatically promotes to default.

### Configuration

```python
app.enable_rmf(
    auto_promote_threshold=1000,      # Min requests before promotion
    auto_promote_error_max=0.02,      # Max error rate for promotion
    auto_promote_latency_ratio=1.5,   # Max latency ratio vs stable
    enable_parallel_sim=False,        # Enable parallel simulation
    enable_self_retiring=True,        # Enable self-retiring engine
)
```

### RMF Reports

```python
app.rmf.print_report()  # Console report
app.rmf.stats()          # Stats dict

@app.route("/rmf/report")
async def rmf_report(request):
    return app.rmf.report()  # JSON report
```

### RMF Architecture

| Component | What It Does |
|-----------|-------------|
| **RealityConfig** | Per-reality configuration: traffic %, time windows, middleware, caching |
| **RealityHandler** | Wraps handler with config + live metrics (requests, errors, latency) |
| **RealityRoute** | Multi-reality container: same path, multiple handlers |
| **RealitySelectorEngine** | Selects reality per request via header → cookie → behavior → time → traffic |
| **ParallelSimulationEngine** | Runs shadow realities, measures drift (latency/status/body comparison) |
| **SelfRetiringEngine** | Auto-promotes experimental realities when proven stable |

---

## 🔬 SEQP - Self-Evolving Quality Pipeline

> **Ishaa doesn't just run your app. It evolves your delivery system.**

SEQP continuously analyzes your application code, generates adversarial tests, rewrites CI/CD pipeline configurations, and enforces dynamic deployment policies - all based on code risk analysis and runtime behavior.

### Enable SEQP

```python
from ishaa import Ishaa

app = Ishaa("myapp")
app.enable_seqp(pipeline_platform="github_actions")

@app.route("/payment")
@app.critical(level="financial_core")
async def process_payment(request):
    data = await request.json()
    # ... payment logic ...
    return {"status": "ok"}

# Run full evolution cycle
result = app.seqp.evolve(output_dir="./generated")
app.seqp.print_report()
```

### Business Criticality Tagging

Tag routes with business criticality to enforce stronger quality gates:

```python
@app.route("/transfer")
@app.critical(level="financial_core", description="Inter-bank wire transfer")
async def transfer(request):
    ...

@app.route("/auth/login")
@app.critical(level="security_critical")
async def login(request):
    ...

@app.route("/data/migrate")
@app.critical(level="data_critical")
async def migrate(request):
    ...
```

| Criticality Level | Coverage Threshold | Extra Test Types |
|---|---|---|
| `financial_core` | 95% | load_burst, mutation_testing, concurrency, security |
| `security_critical` | 92% | security_audit, mutation_testing |
| `data_critical` | 90% | schema_drift, integration |
| `standard` | 75-85% | unit, boundary (if complex) |

### Layer 1: Risk Analyzer

Analyzes Python source code to produce risk profiles:

```python
from ishaa.seqp import RiskAnalyzer

ra = RiskAnalyzer()
metrics = ra.analyze_file("app.py")
print(f"Risk: {metrics.risk_score:.2f} [{metrics.risk_level}]")
print(f"Complexity: {metrics.cyclomatic_complexity}")
print(f"DB interactions: {metrics.db_interactions}")
print(f"Security sensitive: {metrics.security_sensitive}")
```

**Metrics measured:** Branch density, cyclomatic complexity, nesting depth, state mutations, DB interactions, concurrency indicators, external calls, input parsing surface, security sensitivity.

### Layer 2: Auto Test Generator

Risk-targeted test generation - not random fuzzing:

| Risk Signal | Test Types Generated |
|---|---|
| High branch density | Boundary value tests (empty, null, oversized, negative, unicode) |
| Concurrency indicators | Race condition simulation (20 concurrent requests) |
| Input parsing | Security payloads (SQL injection, XSS, command injection, path traversal) |
| DB interactions | Schema drift validation |
| Financial criticality | Load burst + mutation testing |

```python
# Generate tests for all routes
test_code = app.seqp.generate_tests(output_path="tests/test_seqp_auto.py")
```

### Layer 3: Pipeline Rewriter Engine

Auto-generates CI/CD configurations based on risk analysis:

```python
# Generate GitHub Actions workflow
pipeline = app.seqp.rewrite_pipeline(
    output_path=".github/workflows/seqp_pipeline.yml"
)
```

**Supported platforms:** GitHub Actions, GitLab CI, Generic YAML.

Stages are dynamically added/removed based on detected risk:
- Always: lint, unit tests, build, deploy
- If DB interactions: schema drift validation
- If concurrency: race condition simulation
- If input parsing/security: security scan
- If high risk: mutation testing, deep logical tests
- If financial: load testing, shadow deployment

### Layer 4: Deployment Guard

Dynamic deployment policies that adapt to code risk:

```python
result = app.seqp.check_deployment_readiness(
    current_latency=45.2,
    baseline_latency=40.0,
    current_error_rate=0.01,
)
print(result["allowed"])         # True/False
print(result["recommendation"])  # "proceed" / "block_latency_regression" / "immediate_rollback"
```

### Layer 5: Drift Intelligence

Tracks trends over time to detect instability patterns:

```python
trends = app.seqp.drift_intelligence.detect_trends()
actions = app.seqp.drift_intelligence.recommend_actions()
```

**Tracked metrics:** Latency drift, error rate trends, test pass rate decline.
**Actions:** Add regression replay, enable strict rollback, activate shadow deployment, pipeline freeze.

### Full Evolution Cycle

```python
result = app.seqp.evolve(output_dir="./generated")
# Returns: profiles_count, tests_generated, pipeline_generated, policy, trends, actions
```

### SEQP Configuration

```python
app.enable_seqp(
    scan_paths=[".", "src/"],           # Paths to analyze
    pipeline_platform="github_actions", # CI/CD platform
    latency_drift_tolerance=0.20,       # 20% max latency regression
    error_rate_threshold=0.02,          # 2% max error rate
    auto_generate_tests=True,           # Auto-generate test files
    auto_rewrite_pipeline=True,         # Auto-rewrite CI/CD config
)
```

### SEQP Architecture

| Layer | Component | What It Does |
|-------|-----------|-------------|
| **Analysis** | `RiskAnalyzer` | AST-based code analysis: branch density, complexity, mutation risk, DB/concurrency/security detection |
| **Generation** | `AutoTestGenerator` | Risk-targeted test creation: boundary, concurrency, security, load, mutation tests |
| **Pipeline** | `PipelineRewriterEngine` | Auto-generates CI/CD YAML configs based on detected risk levels |
| **Guard** | `DeploymentGuard` | Dynamic deployment policies: latency budget, error rate, rollback triggers |
| **Intelligence** | `DriftIntelligence` | Trend analysis: latency drift, error frequency, test pass rate decline detection |

---

## 🏗️ Architecture

```
ishaa/
├── __init__.py          # Package exports & version
├── __main__.py          # python -m ishaa support
├── app.py               # Core Ishaa application class (ASGI interface)
├── routing.py           # URL routing engine & pattern matching
├── request.py           # HTTP request parsing
├── response.py          # HTTP response types (JSON, HTML, Redirect, Streaming)
├── middleware.py         # Middleware pipeline (CORS, CSRF, Rate Limit, Security)
├── blueprints.py        # Modular route grouping
├── server.py            # Built-in async HTTP/1.1 development server
├── utils.py             # Configuration & utility helpers
├── orm.py               # Database ORM (SQLite, Models, QueryBuilder, Migrations)
├── auth.py              # Authentication (JWT, Sessions, Password Hashing)
├── template.py          # Jinja-like template engine
├── tasks.py             # Background task queue & scheduler
├── websocket.py         # WebSocket support (rooms, broadcast)
├── graphql.py           # GraphQL engine & GraphiQL IDE
├── openapi.py           # OpenAPI 3.0 documentation generator
├── di.py                # Dependency injection container
├── plugins.py           # Plugin system (Cache, Static Files, Admin)
├── cli.py               # Command-line interface
├── testing.py           # Test client & assertion helpers
├── sare.py              # SARE unified engine (integration layer)
├── sare_traffic.py      # SARE: Traffic analyzer (observation)
├── sare_optimizer.py    # SARE: Adaptive optimizer (decision)
├── sare_predictor.py    # SARE: AI latency predictor (prediction)
├── sare_codepath.py     # SARE: Code path optimizer (execution)
├── sare_reporter.py     # SARE: Intelligence reporter (reporting)
├── reality.py           # RMF: Reality-Mode Framework engine
└── seqp.py              # SEQP: Self-Evolving Quality Pipeline engine
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Zero Dependencies** | Core runs entirely on Python standard library - no pip installs required |
| **ASGI-Native** | Full async support, compatible with uvicorn, hypercorn, and any ASGI server |
| **Modular** | Import and use only what you need - each module is self-contained |
| **Convention over Configuration** | Sensible defaults with easy overrides |
| **Developer-First** | Clear error messages, intuitive API, minimal boilerplate |
| **Self-Evolving** | SARE optimizes routing, RMF enables parallel realities, SEQP evolves your CI/CD |

---

## 📋 Version History

### v1.2.0 (Current)
- **RMF Engine** - Reality-Mode Framework: One Codebase, Multiple Realities
  - Same route exists in multiple behavioral universes simultaneously
  - Reality Selector Engine: header → cookie → behavior → time → traffic % routing
  - Time-bound realities with automatic schedule-based activation
  - Self-retiring realities that auto-promote when proven stable
  - Parallel simulation mode for shadow testing without user impact
  - Reality-scoped middleware, caching, and security rules
  - `@app.reality()` decorator with traffic splitting and behavior rules
  - Live stats, reports, and intelligence dashboard
- **SEQP Engine** - Self-Evolving Quality Pipeline
  - Risk Analyzer: AST-based code analysis (branch density, complexity, mutation risk)
  - Auto Test Generator: risk-targeted test creation (boundary, concurrency, security, load)
  - Pipeline Rewriter Engine: auto-generates GitHub Actions / GitLab CI configs
  - Deployment Guard: dynamic coverage thresholds and rollback policies
  - Drift Intelligence: trend detection for latency, error rate, and test pass rate
  - Business criticality tagging: `@app.critical(level="financial_core")`
  - Full evolution cycle: `app.seqp.evolve()` runs analysis → tests → pipeline → policy

### v1.1.0
- **SARE Engine** - Self-Evolving Adaptive Routing Engine with 5-layer architecture
  - Traffic heat mapping and per-route latency tracking (p50/p95/p99)
  - Adaptive middleware reordering based on efficiency measurements
  - AI-assisted latency prediction with EWMA and linear regression
  - Automatic response memoization and code path optimization
  - Intelligence reporting with performance deltas and recommendations
- Project renamed from **Isha** to **Ishaa**
- CLI command updated to `ishaa`
- Package name updated to `ishaa` on PyPI

### v1.0.0
- Initial release with full framework core
- ASGI 3.0 application class with async/sync handler support
- URL routing with typed parameters and named routes
- Request/Response objects with auto-detection
- Middleware pipeline (CORS, CSRF, Rate Limiting, Security Headers)
- Blueprint system for modular applications
- SQLite ORM with Model metaclass, QueryBuilder, and migrations
- Authentication: PBKDF2 password hashing, HMAC-SHA256 JWT, sessions
- Jinja-like template engine with inheritance, includes, and filters
- WebSocket support with rooms and broadcast
- Background task queue with periodic scheduling
- GraphQL engine with GraphiQL IDE
- Dependency injection with `Depends()`
- Plugin system (Cache, Static Files, Admin Panel)
- OpenAPI 3.0 specification generator with Swagger UI
- CLI tool for scaffolding, dev server, migrations, and shell
- Built-in test client with assertion helpers

---

## 📦 Requirements

- **Python 3.8+** (tested on 3.8 through 3.13)
- **Zero external dependencies** for core functionality

### Optional Dependencies

| Package | Install Command | Purpose |
|---------|----------------|---------|
| `uvicorn` | `pip install ishaa[uvicorn]` | Production-grade ASGI server |
| `bcrypt` | `pip install bcrypt` | Alternative password hashing backend |
| `jinja2` | `pip install jinja2` | Alternative template engine |
| `pytest` | `pip install ishaa[dev]` | Test runner and async test support |

Install everything at once:
```bash
pip install ishaa[full]
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with ❤️ by Jayanthan Senthilkumar</strong><br>
  <strong>The Ishaa Framework</strong> - Simplicity · Structure · Performance · Self-Evolution · Multiple Realities<br>
  <a href="https://github.com/jayanthansenthilkumar/ISHAA_Framework">GitHub</a>
</p>
