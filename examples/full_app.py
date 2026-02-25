"""
Isha Framework — Comprehensive Example Application

Demonstrates all major features:
    - Routing (static, dynamic, method-based)
    - Middleware (CORS, rate limiting, security headers)
    - Request/Response handling
    - ORM with models
    - Authentication (JWT)
    - Background tasks
    - Template rendering
    - Plugin system
    - GraphQL
    - WebSocket
    - OpenAPI docs
    - Dependency injection
"""

from isha import Isha, JSONResponse, HTMLResponse, Response
from isha.middleware import CORSMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from isha.auth import JWT, PasswordHasher, SessionManager, login_required, role_required
from isha.orm import Database, Model, IntegerField, TextField, BooleanField, DateTimeField
from isha.tasks import TaskQueue
from isha.plugins import CachePlugin, StaticFilesPlugin, AdminPlugin
from isha.graphql import GraphQLSchema, mount_graphql
from isha.openapi import OpenAPIGenerator, mount_docs
from isha.websocket import websocket_route, WebSocketRoom
from isha.di import Depends, inject

# ── Initialize App ──────────────────────────────────────────────────

app = Isha("example_app", debug=True)

# ── Database Setup ──────────────────────────────────────────────────

Database.connect("example.db")


class User(Model):
    __tablename__ = "users"

    id = IntegerField(primary_key=True)
    name = TextField(nullable=False)
    email = TextField(unique=True, nullable=False)
    password = TextField(nullable=False)
    role = TextField(default="user")
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class Post(Model):
    __tablename__ = "posts"

    id = IntegerField(primary_key=True)
    title = TextField(nullable=False)
    content = TextField()
    author_id = IntegerField()
    published = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)


User.create_table()
Post.create_table()

# ── Auth Setup ──────────────────────────────────────────────────────

jwt = JWT(secret="super-secret-key-change-in-production", expiry_seconds=3600)
hasher = PasswordHasher()
sessions = SessionManager()

# ── Middleware ──────────────────────────────────────────────────────

app.add_middleware(CORSMiddleware(allow_origins=["*"]))
app.add_middleware(SecurityHeadersMiddleware())
app.add_middleware(RateLimitMiddleware(max_requests=100, window_seconds=60))

# ── Plugins ─────────────────────────────────────────────────────────

cache = CachePlugin(default_ttl=300)
app.register_plugin(cache)
app.register_plugin(StaticFilesPlugin(directory="static", prefix="/static"))

admin = AdminPlugin(prefix="/admin")
admin.register_model(User)
admin.register_model(Post)
app.register_plugin(admin)

# ── Background Tasks ────────────────────────────────────────────────

task_queue = TaskQueue(max_workers=4)


@task_queue.task
async def send_welcome_email(email, name):
    """Simulate sending a welcome email."""
    import asyncio
    await asyncio.sleep(1)  # Simulate email sending
    print(f"Welcome email sent to {name} <{email}>")
    return True


# ── Dependency Injection ────────────────────────────────────────────

async def get_current_user(request):
    """Extract and validate the current user from JWT token."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        from isha.di import HTTPException
        raise HTTPException(401, "Not authenticated")
    payload = jwt.decode(auth[7:])
    if not payload:
        from isha.di import HTTPException
        raise HTTPException(401, "Invalid token")
    return payload


# ── Routes ──────────────────────────────────────────────────────────

@app.route("/")
async def index(request):
    """Home page."""
    return HTMLResponse("""
    <html>
    <body style="font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem;">
        <h1>✦ Isha Framework — Example App</h1>
        <h2>Available Endpoints:</h2>
        <ul>
            <li><a href="/api/health">/api/health</a> — Health check</li>
            <li><a href="/api/hello/World">/api/hello/{name}</a> — Greeting</li>
            <li><a href="/docs">/docs</a> — API Documentation (Swagger UI)</li>
            <li><a href="/graphql">/graphql</a> — GraphQL IDE</li>
            <li><a href="/admin">/admin</a> — Admin Panel</li>
        </ul>
        <h2>Auth Endpoints:</h2>
        <ul>
            <li>POST /api/register — Register a user</li>
            <li>POST /api/login — Login and get JWT token</li>
            <li>GET /api/me — Get current user (requires auth)</li>
        </ul>
        <h2>CRUD Endpoints:</h2>
        <ul>
            <li>GET /api/users — List users</li>
            <li>GET /api/posts — List posts</li>
            <li>POST /api/posts — Create post (requires auth)</li>
        </ul>
    </body>
    </html>
    """)


@app.route("/api/health")
async def health(request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "framework": "Isha", "version": "1.0.0"})


@app.route("/api/hello/<str:name>")
async def hello(request, name="World"):
    """Greet a user by name."""
    return JSONResponse({"message": f"Hello, {name}!", "greeted_by": "Isha"})


# ── Auth Routes ─────────────────────────────────────────────────────

@app.post("/api/register")
async def register(request):
    """Register a new user."""
    data = await request.json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return JSONResponse({"error": "name, email, and password required"}, status_code=400)

    # Check if user exists
    existing = User.query().filter(email=email).first()
    if existing:
        return JSONResponse({"error": "Email already registered"}, status_code=409)

    # Create user
    hashed = hasher.hash(password)
    user = User.create(name=name, email=email, password=hashed)

    # Send welcome email in background
    await task_queue.enqueue(send_welcome_email, email, name)

    token = jwt.encode({"user_id": user.id, "email": email, "role": "user"})
    return JSONResponse({"user": user.to_dict(), "token": token}, status_code=201)


@app.post("/api/login")
async def login(request):
    """Login and receive a JWT token."""
    data = await request.json()
    email = data.get("email")
    password = data.get("password")

    user = User.query().filter(email=email).first()
    if not user or not hasher.verify(password, user.password):
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    token = jwt.encode({"user_id": user.id, "email": user.email, "role": user.role})
    return JSONResponse({"token": token, "user": user.to_dict()})


@app.get("/api/me")
@inject
async def get_me(request, user=Depends(get_current_user)):
    """Get current authenticated user profile."""
    db_user = User.get(user["user_id"])
    if not db_user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return JSONResponse({"user": db_user.to_dict()})


# ── CRUD Routes ─────────────────────────────────────────────────────

@app.get("/api/users")
async def list_users(request):
    """List all users."""
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 10))

    users = User.query().limit(per_page).offset((page - 1) * per_page).all()
    total = User.query().count()

    return JSONResponse({
        "users": [u.to_dict() for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.get("/api/users/<int:user_id>")
async def get_user(request, user_id):
    """Get a user by ID."""
    user = User.get(user_id)
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return JSONResponse({"user": user.to_dict()})


@app.get("/api/posts")
async def list_posts(request):
    """List all published posts."""
    posts = Post.query().filter(published=True).order_by("-created_at").all()
    return JSONResponse({"posts": [p.to_dict() for p in posts]})


@app.post("/api/posts")
@inject
async def create_post(request, user=Depends(get_current_user)):
    """Create a new post (requires authentication)."""
    data = await request.json()
    post = Post.create(
        title=data.get("title", ""),
        content=data.get("content", ""),
        author_id=user["user_id"],
        published=data.get("published", False),
    )
    return JSONResponse({"post": post.to_dict()}, status_code=201)


# ── Cached Route Example ────────────────────────────────────────────

@app.get("/api/stats")
@cache.cached(ttl=60)
async def get_stats(request):
    """Get app statistics (cached for 60 seconds)."""
    return JSONResponse({
        "total_users": User.query().count(),
        "total_posts": Post.query().count(),
        "published_posts": Post.query().filter(published=True).count(),
    })


# ── Background Task Status ──────────────────────────────────────────

@app.get("/api/tasks/<str:task_id>")
async def get_task_status(request, task_id):
    """Check the status of a background task."""
    result = task_queue.get_result(task_id)
    if not result:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return JSONResponse(result.to_dict())


# ── GraphQL ─────────────────────────────────────────────────────────

schema = GraphQLSchema()


@schema.query("hello")
def gql_hello(root, info, name="World"):
    return f"Hello, {name}!"


@schema.query("users")
def gql_users(root, info):
    users = User.all()
    return [u.to_dict() for u in users]


@schema.query("posts")
def gql_posts(root, info):
    posts = Post.query().filter(published=True).all()
    return [p.to_dict() for p in posts]


@schema.mutation("createUser")
def gql_create_user(root, info, name="", email="", password=""):
    hashed = hasher.hash(password)
    user = User.create(name=name, email=email, password=hashed)
    return user.to_dict()


mount_graphql(app, schema, path="/graphql")

# ── OpenAPI Docs ────────────────────────────────────────────────────

docs = OpenAPIGenerator(app, title="Isha Example API", version="1.0.0",
                        description="A comprehensive example of the Isha Framework")
mount_docs(app, docs)

# ── WebSocket ───────────────────────────────────────────────────────

chat_room = WebSocketRoom("chat")


@websocket_route(app, "/ws/chat")
async def chat_handler(ws):
    """WebSocket chat handler."""
    await ws.accept()
    chat_room.add(ws)
    try:
        await ws.send_json({"type": "system", "message": "Connected to chat!"})
        while True:
            data = await ws.receive_json()
            await chat_room.broadcast_json({
                "type": "message",
                "user": data.get("user", "Anonymous"),
                "message": data.get("message", ""),
            })
    except Exception:
        chat_room.remove(ws)


# ── Custom Error Handlers ───────────────────────────────────────────

@app.error_handler(404)
async def not_found(request):
    return JSONResponse({"error": "The resource you're looking for doesn't exist"}, status_code=404)


@app.error_handler(500)
async def server_error(request):
    return JSONResponse({"error": "Something went wrong on our end"}, status_code=500)


# ── Lifecycle Events ────────────────────────────────────────────────

@app.on_startup
async def startup():
    print("✦ Application starting up...")
    await task_queue.start_periodic()


@app.on_shutdown
async def shutdown():
    print("✦ Application shutting down...")
    task_queue.stop()
    Database.close()


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
