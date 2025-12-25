# 🌱 ISHA Framework

**Simple. Human. Timeless.**

A framework that doesn't shout — it endures.

---

## ✨ Features

- **Zero Dependencies** — Pure Python, nothing else
- **Custom File Extension** — `.pyisha` files for clear intent
- **Clean CLI** — `isha run app.pyisha`
- **Minimal Core** — App, Request, Response — that's it
- **Human DX** — Professional, corporate-ready developer experience

---

## 🚀 Quick Start

### Installation

```bash
pip install isha
```

Or install from source:

```bash
git clone https://github.com/isha-framework/isha
cd isha
pip install -e .
```

### Create Your First App

Create a file named `app.pyisha`:

```python
from isha import App

app = App()

@app.route("/")
def home(req):
    return "Hello from ISHA 🌱"

@app.route("/health")
def health(req):
    return "OK"
```

### Run It

```bash
isha run app.pyisha
```

Or with Python directly:

```bash
python -m isha run app.pyisha
```

Visit `http://127.0.0.1:8000` — you're live!

---

## 📚 Documentation

### The App

```python
from isha import App

app = App(name="my-app")
```

### Routes

```python
@app.route("/")
def home(req):
    return "Hello!"

@app.route("/users", methods=["GET", "POST"])
def users(req):
    if req.method == "POST":
        return "Created!", 201
    return "List of users"

# Shorthand decorators
@app.get("/items")
def get_items(req):
    return "Items"

@app.post("/items")
def create_item(req):
    return "Created!", 201
```

### Request Object

```python
@app.route("/api")
def api(req):
    print(req.method)   # "GET", "POST", etc.
    print(req.path)     # "/api"
    print(req.headers)  # {"Content-Type": "application/json", ...}
    print(req.body)     # Request body content
    return "OK"
```

### Response Types

```python
# String response
@app.route("/text")
def text(req):
    return "Plain text"

# JSON response (automatic serialization)
@app.route("/json")
def json(req):
    return {"message": "Hello", "status": "ok"}

# Tuple for custom status
@app.route("/created")
def created(req):
    return "Created!", 201

# Full Response object
from isha import Response

@app.route("/custom")
def custom(req):
    res = Response("Custom", status=200, content_type="text/html")
    res.set_header("X-Custom", "value")
    return res
```

### Middleware

```python
# Before request
@app.before
def log_request(req):
    print(f"Incoming: {req.method} {req.path}")

# After request
@app.after
def add_headers(req, res):
    res.set_header("X-Powered-By", "ISHA")
    return res
```

### Error Handlers

```python
@app.error(404)
def not_found(req):
    return f"Page {req.path} not found", 404

@app.error(500)
def server_error(req):
    return "Something went wrong", 500
```

### CLI Options

```bash
# Default (localhost:8000)
isha run app.pyisha

# Custom port
isha run app.pyisha --port 3000

# Custom host and port (accessible externally)
isha run app.pyisha --host 0.0.0.0 --port 8080

# Help
isha --help

# Version
isha --version
```

---

## 🏗️ Project Structure

```
isha/
├── __init__.py     # Package exports
├── core.py         # App, Request, Response
├── server.py       # HTTP server
├── loader.py       # .pyisha file loader
├── cli.py          # CLI commands
└── __main__.py     # Module entry point
```

---

## 🎯 Philosophy

ISHA is built on three principles:

1. **Simple** — No magic, no hidden complexity
2. **Human** — Readable code, clear intentions
3. **Timeless** — Patterns that last, not trends that fade

---

## 📦 Why `.pyisha`?

The custom file extension:

- **Differentiates** your framework
- **Signals intent** — this is an ISHA app
- **Creates brand gravity**
- **Enables clean tooling** — syntax highlighting, linting

Your IDE will treat `.pyisha` files as Python (same syntax), but the extension tells the story.

---

## 🛣️ Roadmap

- [ ] 🔐 Middleware system (v0.2)
- [ ] 🎨 HTML templates (v0.3)
- [ ] ⚡ ASGI upgrade (v0.4)
- [ ] 📦 PyPI release (v0.5)
- [ ] 🧭 Project generator: `isha new` (v0.6)

---

## 🤝 Contributing

ISHA is open to contributions. Keep it simple, keep it human.

```bash
# Clone
git clone https://github.com/isha-framework/isha
cd isha

# Install in development mode
pip install -e .

# Run the example
isha run app.pyisha
```

---

## 📄 License

MIT License — Use freely, build boldly.

---

<p align="center">
  <strong>ISHA</strong><br>
  Simple. Human. Timeless.
</p>
