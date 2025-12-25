# 🎨 ISHA Fullstack Framework - Complete Guide

## ✨ What's New in the Fullstack Version

ISHA has evolved from a simple web framework into a **complete fullstack solution** with:

### 🚀 Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **🔧 Zero Dependencies** | Pure Python, no external packages | ✅ |
| **🎨 Template Engine** | Variable substitution, loops, conditionals | ✅ |
| **💾 Database Support** | SQLite wrapper with ORM-like API | ✅ |
| **📝 Form Validation** | Declarative forms with validators | ✅ |
| **🔐 Session Management** | Signed cookie sessions | ✅ |
| **📁 Static Files** | Serve CSS, JS, images automatically | ✅ |
| **🔌 RESTful APIs** | JSON responses out of the box | ✅ |
| **⚙️ Configuration** | Environment-aware settings | ✅ |
| **🍪 Cookie Support** | Request/response cookies | ✅ |
| **🎯 Middleware** | Before/after request hooks | ✅ |
| **❌ Error Handling** | Custom error pages | ✅ |

---

## 📚 Complete API Documentation

### 1. Configuration Management

```python
from isha import Config, DEFAULT_CONFIG

# Create configuration
config = Config(DEFAULT_CONFIG)

# Set values
config.set("DATABASE_URL", "sqlite:///app.db")
config.set("SECRET_KEY", "your-secret-key")

# Get values (checks environment variables first)
db_url = config.get("DATABASE_URL")

# Dictionary-style access
config["DEBUG"] = True
debug = config["DEBUG"]

# Load from JSON file
config.load_from_file("config.json")

# Load from environment variables
config.load_from_env(prefix="ISHA_")
```

**Default Configuration:**
```python
{
    "DEBUG": False,
    "HOST": "127.0.0.1",
    "PORT": 8000,
    "SECRET_KEY": "change-this-secret-key-in-production",
    "TEMPLATE_DIR": "templates",
    "STATIC_DIR": "static",
    "DATABASE_URL": None,
    "SESSION_LIFETIME": 3600,  # 1 hour
}
```

---

### 2. Database Operations

```python
from isha import Database

# Connect to database
db = Database("app.db")  # or ":memory:" for in-memory

# Create table
db.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        email TEXT
    )
''')

# Insert data
user_id = db.insert("users", {
    "username": "alice",
    "email": "alice@example.com"
})

# Query data
users = db.query("SELECT * FROM users WHERE username = ?", ("alice",))
# Returns: [{"id": 1, "username": "alice", "email": "alice@example.com"}]

# Query single result
user = db.query_one("SELECT * FROM users WHERE id = ?", (1,))

# Update data
db.update("users", 
    {"email": "newemail@example.com"},
    "id = ?",
    (1,)
)

# Delete data
db.delete("users", "id = ?", (1,))

# Use as context manager
with Database("app.db") as db:
    users = db.query("SELECT * FROM users")
```

---

### 3. Template Rendering

```python
from isha import Template, render_template

# Inline template
template = Template('''
    <h1>Hello, {{ name }}!</h1>
    
    {% if is_admin %}
        <p>Welcome, admin!</p>
    {% else %}
        <p>Welcome, user!</p>
    {% endif %}
    
    <ul>
    {% for item in items %}
        <li>{{ item.name }} - ${{ item.price }}</li>
    {% endfor %}
    </ul>
''')

html = template.render({
    "name": "Alice",
    "is_admin": True,
    "items": [
        {"name": "Apple", "price": 1.99},
        {"name": "Banana", "price": 0.99}
    ]
})

# Render from file
html = render_template("index.html", {
    "title": "Home",
    "users": users
})

# In app routes
@app.route("/")
def home(req):
    return app.render_template("home.html", {
        "title": "Welcome"
    })
```

**Template Syntax:**
- `{{ variable }}` - Variable substitution
- `{{ user.name }}` - Nested attributes
- `{% if condition %} ... {% endif %}` - Conditionals
- `{% if condition %} ... {% else %} ... {% endif %}` - If-else
- `{% for item in items %} ... {% endfor %}` - Loops
- `{% include "partial.html" %}` - Include other templates

---

### 4. Form Handling & Validation

```python
from isha import Form, Field, parse_form_data

# Define form class
class RegistrationForm(Form):
    username = Field(required=True, min_length=3, max_length=20)
    email = Field(
        required=True,
        validator=lambda v: '@' in v and '.' in v.split('@')[1]
    )
    age = Field(
        required=False,
        validator=lambda v: int(v) >= 18
    )

# Use in route
@app.post("/register")
def register(req):
    form = RegistrationForm(req.body)
    
    if form.is_valid():
        # Access validated data
        username = form.data["username"]
        email = form.data["email"]
        
        # Save to database
        db.insert("users", {
            "username": username,
            "email": email
        })
        
        return {"success": True, "message": "User registered!"}
    else:
        return {"success": False, "errors": form.errors}, 400

# Parse form data manually
@app.post("/submit")
def submit(req):
    data = parse_form_data(req.body)
    name = data.get("name")
    return f"Hello, {name}!"
```

**Field Validators:**
```python
Field(
    required=True,           # Field must be present
    default="value",         # Default value if not provided
    min_length=3,           # Minimum string length
    max_length=20,          # Maximum string length
    validator=custom_fn     # Custom validation function
)
```

---

### 5. Session Management

```python
from isha import Session

# Create session in middleware
@app.before
def add_session(req):
    session = Session.decode(
        req.cookies.get("session", ""),
        app.config.get("SECRET_KEY")
    )
    req.session = session or Session(
        app.config.get("SECRET_KEY"),
        lifetime=3600  # 1 hour
    )

# Use session in routes
@app.route("/login")
def login(req):
    req.session["user_id"] = 123
    req.session["username"] = "alice"
    return "Logged in!"

@app.route("/profile")
def profile(req):
    user_id = req.session.get("user_id")
    if not user_id:
        return "Not logged in", 401
    return f"User ID: {user_id}"

@app.route("/logout")
def logout(req):
    req.session.clear()
    return "Logged out!"

# Save session in middleware
@app.after
def save_session(req, res):
    if hasattr(req, 'session') and req.session._modified:
        res.set_cookie("session", req.session.encode(), max_age=3600)
    return res
```

---

### 6. Static File Serving

```python
# Mount static directory
app.mount_static("/static", "public")
# Now files in public/ are accessible at /static/*

# Multiple static directories
app.mount_static("/css", "assets/styles")
app.mount_static("/js", "assets/scripts")
app.mount_static("/images", "assets/images")

# In HTML:
# <link rel="stylesheet" href="/static/style.css">
# <script src="/static/app.js"></script>
# <img src="/static/logo.png">
```

**Supported File Types:**
- HTML, CSS, JavaScript
- Images: PNG, JPG, GIF, SVG, ICO
- Fonts: WOFF, WOFF2, TTF, EOT
- Documents: PDF, ZIP
- JSON, TXT

---

### 7. Enhanced Request Object

```python
@app.route("/search")
def search(req):
    # Query parameters
    query = req.query_params.get("q")
    page = req.query_params.get("page", 1)
    
    # Cookies
    session_id = req.cookies.get("session")
    
    # Headers
    user_agent = req.headers.get("User-Agent")
    
    # Body (POST data)
    username = parse_form_data(req.body).get("username")
    
    # Method
    if req.method == "POST":
        return "Processing..."
    
    return f"Search for: {query}"
```

---

### 8. Enhanced Response Object

```python
from isha import Response

@app.route("/custom")
def custom(req):
    res = Response("Hello!", status=200, content_type="text/html")
    
    # Set headers
    res.set_header("Cache-Control", "no-cache")
    res.set_header("X-Custom", "value")
    
    # Set cookies
    res.set_cookie("user_id", "123", max_age=3600, http_only=True)
    
    # Redirect
    res.redirect("/home", status=302)
    
    return res

# Shorthand responses
@app.route("/json")
def json_response(req):
    return {"message": "Hello"}  # Auto JSON

@app.route("/text")
def text_response(req):
    return "Plain text"  # Auto text/plain

@app.route("/with_status")
def with_status(req):
    return "Created!", 201  # Tuple: (body, status)
```

---

### 9. Middleware

```python
# Before request
@app.before
def authenticate(req):
    token = req.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401
    # Continue to route if return None

@app.before
def add_timestamp(req):
    import time
    req.timestamp = time.time()

# After request
@app.after
def add_headers(req, res):
    res.set_header("X-Powered-By", "ISHA")
    res.set_header("X-Request-Time", str(req.timestamp))
    return res

@app.after
def log_response(req, res):
    print(f"Response: {res.status}")
    return res
```

---

### 10. Error Handling

```python
# Custom error pages
@app.error(404)
def not_found(req):
    return f"Page {req.path} not found", 404

@app.error(500)
def server_error(req):
    return {"error": "Something went wrong"}, 500

@app.error(403)
def forbidden(req):
    return "Access denied", 403

# All error responses go through these handlers
```

---

## 🎯 Complete Example Application

See [`app.pyisha`](app.pyisha) for a production-ready fullstack application featuring:

✅ **8 HTML Pages** with modern responsive design  
✅ **4 API Endpoints** with JSON responses  
✅ **Database Integration** with SQLite  
✅ **Session Management** with secure cookies  
✅ **Form Validation** for user input  
✅ **Static File Serving** ready to use  
✅ **Custom Error Pages** with beautiful UI  
✅ **Middleware Pipeline** for security headers  

---

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Run the fullstack demo
isha run app.pyisha

# Visit
# http://127.0.0.1:8000/          - Homepage
# http://127.0.0.1:8000/users     - User directory
# http://127.0.0.1:8000/posts     - Blog posts
# http://127.0.0.1:8000/dashboard - Dashboard
# http://127.0.0.1:8000/api/status - API status
```

---

## 📦 Project Structure

```
your-project/
├── app.pyisha              # Main application
├── templates/              # HTML templates
│   ├── base.html
│   ├── home.html
│   └── about.html
├── static/                 # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── images/
│       └── logo.png
├── config.json             # Configuration
└── app_database.db         # SQLite database
```

---

## 🎨 Framework Philosophy

**Simple. Human. Timeless.**

ISHA is designed to be:
- **Explicit over magical** - No hidden behavior
- **Readable over clever** - Code should be clear
- **Flexible over prescriptive** - Use what you need
- **Stable over trendy** - Patterns that last

---

## 📄 License

MIT License - Use freely, build boldly.

---

<p align="center">
  <strong>ISHA Framework v0.1.0</strong><br>
  A framework that doesn't shout — it endures.
</p>
