"""
Isha Framework — REST API Example

Demonstrates a clean REST API with CRUD operations.
"""

from isha import Isha, JSONResponse
from isha.blueprints import Blueprint
from isha.middleware import CORSMiddleware
from isha.orm import Database, Model, IntegerField, TextField, BooleanField, DateTimeField

# ── App Setup ───────────────────────────────────────────────────────

app = Isha("rest_api", debug=True)
app.add_middleware(CORSMiddleware(allow_origins=["*"]))

Database.connect("rest_api.db")


# ── Models ──────────────────────────────────────────────────────────

class Todo(Model):
    __tablename__ = "todos"

    id = IntegerField(primary_key=True)
    title = TextField(nullable=False)
    description = TextField(default="")
    completed = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)


Todo.create_table()


# ── API Blueprint ───────────────────────────────────────────────────

api = Blueprint("api", prefix="/api/v1")


@api.get("/todos")
async def list_todos(request):
    """List all todos with optional filtering."""
    completed = request.query_params.get("completed")
    query = Todo.query().order_by("-created_at")

    if completed is not None:
        query = query.filter(completed=(completed.lower() == "true"))

    todos = query.all()
    return JSONResponse({
        "todos": [t.to_dict() for t in todos],
        "count": len(todos),
    })


@api.get("/todos/<int:todo_id>")
async def get_todo(request, todo_id):
    """Get a single todo by ID."""
    todo = Todo.get(todo_id)
    if not todo:
        return JSONResponse({"error": "Todo not found"}, status_code=404)
    return JSONResponse({"todo": todo.to_dict()})


@api.post("/todos")
async def create_todo(request):
    """Create a new todo."""
    data = await request.json()
    if not data.get("title"):
        return JSONResponse({"error": "Title is required"}, status_code=400)

    todo = Todo.create(
        title=data["title"],
        description=data.get("description", ""),
    )
    return JSONResponse({"todo": todo.to_dict()}, status_code=201)


@api.put("/todos/<int:todo_id>")
async def update_todo(request, todo_id):
    """Update an existing todo."""
    todo = Todo.get(todo_id)
    if not todo:
        return JSONResponse({"error": "Todo not found"}, status_code=404)

    data = await request.json()
    if "title" in data:
        todo.title = data["title"]
    if "description" in data:
        todo.description = data["description"]
    if "completed" in data:
        todo.completed = data["completed"]

    todo.save()
    return JSONResponse({"todo": todo.to_dict()})


@api.delete("/todos/<int:todo_id>")
async def delete_todo(request, todo_id):
    """Delete a todo."""
    todo = Todo.get(todo_id)
    if not todo:
        return JSONResponse({"error": "Todo not found"}, status_code=404)

    todo.delete_record()
    return JSONResponse({"message": "Todo deleted"})


# Register blueprint
app.register_blueprint(api)


@app.route("/")
async def index(request):
    return JSONResponse({
        "name": "Todo API",
        "version": "1.0",
        "endpoints": {
            "list": "GET /api/v1/todos",
            "create": "POST /api/v1/todos",
            "read": "GET /api/v1/todos/{id}",
            "update": "PUT /api/v1/todos/{id}",
            "delete": "DELETE /api/v1/todos/{id}",
        },
    })


if __name__ == "__main__":
    app.run(port=8000, debug=True)
