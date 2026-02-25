<p align="center">
  <h1 align="center">🌟 Isha Framework</h1>
  <p align="center"><strong>A Modern Python Web Framework</strong></p>
  <p align="center">
    <em>Simplicity of Flask · Structure of Django · Performance mindset of FastAPI</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/version-1.0.0-orange.svg" alt="Version">
  <img src="https://img.shields.io/badge/ASGI-3.0-purple.svg" alt="ASGI 3.0">
</p>

---

**Isha** is a lightweight, modular, high-performance Python web framework built from scratch with **zero required external dependencies**. It features a complete ASGI-compatible architecture, a custom ORM, built-in authentication, a template engine, WebSocket support, GraphQL, dependency injection, and much more — all in pure Python.

---

## ✨ Features at a Glance

| Category | Features |
|----------|----------|
| **Core** | ASGI 3.0, async/sync handlers, middleware pipeline, blueprints |
| **Routing** | Typed params (`int`, `float`, `uuid`, `slug`, `path`), regex matching, named routes, `url_for()` |
| **ORM** | SQLite adapter, model metaclass, chainable QueryBuilder, migrations, field types |
| **Auth** | PBKDF2 password hashing, HMAC-SHA256 JWT, session management, decorators |
| **Templates** | Jinja-like syntax, inheritance, includes, filters, auto-escaping |
| **Middleware** | CORS, CSRF, rate limiting, security headers, custom middleware classes |
| **WebSocket** | Full duplex, rooms, broadcast, JSON messaging |
| **GraphQL** | Schema, queries, mutations, subscriptions, GraphiQL IDE |
| **Plugins** | Cache (TTL), static files, mail (SMTP), admin panel |
| **DI** | Dependency injection with `Depends()`, async support, generator cleanup |
| **CLI** | Project scaffolding, dev server, migrations, route listing, interactive shell |
| **Testing** | Built-in test client, assertion helpers, no server required |
| **Docs** | Auto-generated OpenAPI 3.0 spec, Swagger UI |

---

## 🚀 Quick Start

### Installation

```bash
# From source
git clone https://github.com/jayanthansenthilkumar/ISHA_Framework.git
cd ISHA_Framework
pip install -e .

# With optional dependencies
pip install -e ".[full]"    # uvicorn + bcrypt + jinja2
```

### Hello World

```python
from isha import Isha

app = Isha()

@app.route("/")
async def hello(request):
    return {"message": "Hello from Isha! 🌟"}

@app.route("/hello/<name>")
async def greet(request, name):
    return f"<h1>Hello, {name}!</h1>"

app.run()
```

Run it:
```bash
python app.py
# Server running at http://127.0.0.1:8000
```

---

## 📖 Documentation

### Table of Contents

- [Routing](#routing)
- [Request & Response](#request--response)
- [Middleware](#middleware)
- [Blueprints](#blueprints)
- [ORM (Database)](#orm-database)
- [Authentication](#authentication)
- [Template Engine](#template-engine)
- [WebSocket](#websocket)
- [Background Tasks](#background-tasks)
- [GraphQL](#graphql)
- [Dependency Injection](#dependency-injection)
- [Plugins](#plugins)
- [OpenAPI / Swagger](#openapi--swagger)
- [CLI Tool](#cli-tool)
- [Testing](#testing)

---

### Routing

Isha supports typed URL parameters, multiple HTTP methods, and named routes:

```python
from isha import Isha

app = Isha()

# Basic route
@app.route("/")
async def index(request):
    return "Welcome!"

# Typed parameters
@app.route("/users/<int:id>")
async def get_user(request, id):
    return {"user_id": id}  # id is already an int

# Multiple methods
@app.route("/items", methods=["GET", "POST"])
async def items(request):
    if request.method == "POST":
        data = await request.json()
        return {"created": data}
    return {"items": []}

# Method shortcuts
@app.get("/health")
async def health(request):
    return {"status": "ok"}

@app.post("/upload")
async def upload(request):
    body = await request.body()
    return {"size": len(body)}

# Named routes & url_for
@app.route("/profile/<username>", name="user_profile")
async def profile(request, username):
    return f"Profile: {username}"

url = app.router.url_for("user_profile", username="alice")
# => "/profile/alice"
```

**Supported param types:** `str` (default), `int`, `float`, `uuid`, `slug`, `path`

---

### Request & Response

#### Request Object

```python
@app.route("/example", methods=["POST"])
async def example(request):
    # Properties
    request.method          # "POST"
    request.path            # "/example"
    request.query_params    # {"key": "value"}
    request.headers         # {"content-type": "application/json"}
    request.cookies         # {"session_id": "abc123"}
    request.content_type    # "application/json"
    request.client          # ("127.0.0.1", 5000)
    
    # Body parsing
    body = await request.body()          # raw bytes
    text = await request.text()          # decoded string
    data = await request.json()          # parsed JSON dict
    form = await request.form()          # form data dict
```

#### Response Types

```python
from isha import Response, JSONResponse, HTMLResponse, RedirectResponse
from isha.response import StreamingResponse

# Auto-detection (return values from handlers)
return "Hello"                      # → HTMLResponse
return {"key": "value"}             # → JSONResponse
return [1, 2, 3]                    # → JSONResponse

# Explicit responses
return Response("Plain text", status=200, content_type="text/plain")
return JSONResponse({"ok": True}, status=201)
return HTMLResponse("<h1>Page</h1>")
return RedirectResponse("/login")

# Cookies
resp = JSONResponse({"logged_in": True})
resp.set_cookie("token", "abc123", max_age=3600, httponly=True, secure=True)
resp.delete_cookie("old_cookie")
return resp

# Streaming
async def generate():
    for i in range(10):
        yield f"data: {i}\n\n"
return StreamingResponse(generate(), content_type="text/event-stream")
```

---

### Middleware

```python
from isha.middleware import Middleware, CORSMiddleware, RateLimitMiddleware

app = Isha()

# Built-in CORS
app.add_middleware(CORSMiddleware(
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_credentials=True
))

# Rate limiting
app.add_middleware(RateLimitMiddleware(max_requests=100, window_seconds=60))

# Decorator-based
@app.before_request
async def log_request(request):
    print(f"{request.method} {request.path}")
    return None  # Continue processing; return a Response to short-circuit

@app.after_request
async def add_header(request, response):
    response.headers["X-Powered-By"] = "Isha"
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

### Blueprints

Organize your application into modular sections:

```python
from isha import Blueprint

# Create a blueprint
api = Blueprint("api", prefix="/api/v1")

@api.route("/users")
async def list_users(request):
    return {"users": []}

@api.route("/users/<int:id>")
async def get_user(request, id):
    return {"user": id}

# Register with app
app.register_blueprint(api)
# Routes: /api/v1/users, /api/v1/users/<int:id>
```

---

### ORM (Database)

A lightweight ORM with SQLite support:

```python
from isha.orm import Database, Model, IntegerField, TextField, BooleanField, DateTimeField

# Initialize database
db = Database("app.db")

# Define models
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
user.save()           # Update

user = User.get(1)    # Get by ID
users = User.all()    # Get all

# Chainable queries
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

### Authentication

Built-in password hashing, JWT, and session management:

```python
from isha.auth import PasswordHasher, JWT, SessionManager, login_required, role_required

# Password hashing (PBKDF2-HMAC-SHA256)
hasher = PasswordHasher()
hashed = hasher.hash("my_password")
is_valid = hasher.verify("my_password", hashed)  # True

# JWT tokens
jwt = JWT(secret="your-secret-key")
token = jwt.encode({"user_id": 1, "role": "admin"}, expires_in=3600)
payload = jwt.decode(token)  # {"user_id": 1, "role": "admin", "exp": ..., "iat": ...}

# Session management
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

### Template Engine

Jinja-like template syntax with inheritance, loops, conditionals, and filters:

```python
app = Isha(template_dir="templates")

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

### WebSocket

Full-duplex WebSocket communication with rooms:

```python
from isha.websocket import websocket_route, WebSocketRoom

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

### Background Tasks

Run tasks asynchronously with status tracking:

```python
from isha.tasks import TaskQueue, task

queue = TaskQueue(max_workers=4)

@task(queue)
async def send_email(to, subject, body):
    # Simulate sending email
    import asyncio
    await asyncio.sleep(2)
    return f"Email sent to {to}"

# Dispatch a task
result = await send_email.delay("user@example.com", "Hello", "Welcome!")
print(result.task_id)   # UUID
print(result.status)    # TaskStatus.PENDING → RUNNING → COMPLETED

# Check status later
status = queue.get_status(result.task_id)

# Periodic tasks
@queue.periodic(interval=300)  # Every 5 minutes
async def cleanup():
    print("Running cleanup...")
```

---

### GraphQL

Built-in GraphQL engine with GraphiQL IDE:

```python
from isha.graphql import GraphQLSchema, mount_graphql

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

# Mount at /graphql with GraphiQL IDE
mount_graphql(app, schema, path="/graphql")
```

Visit `http://localhost:8000/graphql` to use the interactive GraphiQL IDE.

---

### Dependency Injection

FastAPI-style dependency injection:

```python
from isha.di import Depends, inject

async def get_db():
    db = Database("app.db")
    yield db  # Generator dependencies are auto-cleaned up

async def get_current_user(request):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Not authenticated")
    return jwt.decode(token)

@app.route("/profile")
@inject
async def profile(request, user=Depends(get_current_user), db=Depends(get_db)):
    return {"user": user}
```

---

### Plugins

Extend Isha with a plugin system:

```python
from isha.plugins import CachePlugin, StaticFilesPlugin, AdminPlugin

# Caching
cache = CachePlugin(default_ttl=300)
app.register_plugin(cache)

@app.route("/expensive")
@cache.cached(ttl=60)
async def expensive_computation(request):
    return {"result": compute_something()}

# Static files
static = StaticFilesPlugin(directory="static", prefix="/static")
app.register_plugin(static)
# Serves files from ./static/ at /static/...

# Admin panel
admin = AdminPlugin(prefix="/admin")
admin.register_model(User)
admin.register_model(Post)
app.register_plugin(admin)
# Auto-generates list/detail views at /admin/users, /admin/posts
```

---

### OpenAPI / Swagger

Auto-generated API documentation:

```python
from isha.openapi import mount_docs

mount_docs(app, title="My API", version="1.0.0", description="My awesome API")
# Swagger UI at /docs
# OpenAPI JSON spec at /openapi.json
```

---

### CLI Tool

Isha includes a command-line tool for common tasks:

```bash
# Create a new project
isha create project myapp

# Start development server
isha run --host 0.0.0.0 --port 8000 --reload

# Database migrations
isha migrate run
isha migrate create add_users_table
isha migrate status

# List all registered routes
isha routes

# Interactive Python shell with app context
isha shell

# Show version
isha version
```

**Scaffolded project structure:**
```
myapp/
├── app.py              # Main application
├── config.py           # Configuration
├── models.py           # Database models
├── routes/
│   └── __init__.py     # Route blueprints
├── templates/
│   └── base.html       # Base template
├── static/
│   ├── css/
│   └── js/
└── tests/
    └── test_app.py     # Test suite
```

---

### Testing

Built-in test client — no running server needed:

```python
from isha.testing import TestClient

client = TestClient(app)

# Make requests
response = client.get("/")
assert response.ok
assert response.status == 200

response = client.post("/api/users", json={"name": "Alice"})
assert response.status == 201
assert response.json()["name"] == "Alice"

# Test with headers
response = client.get("/protected", headers={"Authorization": "Bearer <token>"})

# Test with cookies
response = client.get("/dashboard", cookies={"session_id": "abc123"})

# Assertion helpers
from isha.testing import assert_status, assert_json, assert_html, assert_redirect

assert_status(response, 200)
assert_json(response, {"ok": True})
assert_html(response, contains="<h1>")
assert_redirect(response, "/login")
```

---

## 🏗️ Architecture

```
isha/
├── __init__.py          # Package exports
├── app.py               # Core application (ASGI interface)
├── routing.py           # URL routing & pattern matching
├── request.py           # HTTP request parsing
├── response.py          # HTTP response types
├── middleware.py         # Middleware pipeline
├── blueprints.py        # Modular route grouping
├── server.py            # Built-in ASGI server
├── utils.py             # Configuration & utilities
├── orm.py               # Database ORM
├── auth.py              # Authentication (JWT, sessions, passwords)
├── template.py          # Template engine
├── tasks.py             # Background task queue
├── websocket.py         # WebSocket support
├── graphql.py           # GraphQL engine
├── openapi.py           # OpenAPI documentation
├── di.py                # Dependency injection
├── plugins.py           # Plugin system (cache, static, admin)
├── cli.py               # Command-line interface
└── testing.py           # Test client & helpers
```

**Design Principles:**

- **Zero dependencies** — Core runs on Python standard library only
- **ASGI-native** — Full async support, compatible with uvicorn/hypercorn
- **Modular** — Use only what you need
- **Convention over configuration** — Sensible defaults, easy overrides
- **Developer-first** — Clear errors, intuitive API, minimal boilerplate

---

## 🧪 Running Tests

```bash
# Run all tests
python tests/test_core.py
python tests/test_middleware.py
python tests/test_orm.py
python tests/test_auth.py
python tests/test_template.py

# Or with pytest (if installed)
pip install pytest
pytest tests/ -v
```

---

## 📦 Examples

See the [examples/](examples/) directory:

| Example | Description |
|---------|-------------|
| [minimal_app.py](examples/minimal_app.py) | Simplest possible Isha app — 3 routes |
| [rest_api.py](examples/rest_api.py) | REST API with Blueprint, ORM, and CRUD |
| [full_app.py](examples/full_app.py) | Complete app using all features |

---

## 📋 Requirements

- **Python 3.8+**
- No external dependencies for core functionality

**Optional dependencies:**
| Package | Purpose |
|---------|---------|
| `uvicorn` | Production ASGI server |
| `bcrypt` | Alternative password hashing |
| `jinja2` | Alternative template engine |
| `pytest` | Test runner |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with ❤️ — The Isha Framework</strong><br>
  <em>Simplicity · Structure · Performance</em>
</p>
