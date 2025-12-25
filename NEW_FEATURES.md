# 🚀 ISHA Framework - New Features Guide

## Version 0.2.0 - Enhanced Edition

This document covers all the new features added to the ISHA framework.

---

## 📚 Table of Contents

1. [URL Parameters (Dynamic Routes)](#url-parameters)
2. [JSON Body Parsing](#json-body-parsing)
3. [CORS Support](#cors-support)
4. [File Upload Handling](#file-uploads)
5. [Rate Limiting](#rate-limiting)
6. [Response Caching](#response-caching)
7. [Structured Logging](#structured-logging)

---

## 🎯 URL Parameters (Dynamic Routes) {#url-parameters}

Define routes with dynamic parameters using `{param}` syntax.

### Basic Usage

```python
from isha import App

app = App()

@app.get("/users/{id}")
def get_user(req):
    user_id = req.params.get("id")
    return f"User ID: {user_id}"

@app.get("/posts/{post_id}/comments/{comment_id}")
def get_comment(req):
    post_id = req.params["post_id"]
    comment_id = req.params["comment_id"]
    return f"Post {post_id}, Comment {comment_id}"
```

### Features

- ✅ Multiple parameters in one route
- ✅ Automatic regex matching
- ✅ Parameters accessible via `req.params` dictionary
- ✅ Works with all HTTP methods (GET, POST, PUT, DELETE)

### Example

```python
@app.get("/api/products/{category}/{id}")
def get_product(req):
    category = req.params["category"]
    product_id = req.params["id"]
    
    # Query database
    product = db.query(
        "SELECT * FROM products WHERE category = ? AND id = ?",
        (category, product_id)
    )
    
    return {"product": product}
```

---

## 📦 JSON Body Parsing {#json-body-parsing}

Automatic JSON parsing for POST/PUT requests with `Content-Type: application/json`.

### Basic Usage

```python
@app.post("/api/users")
def create_user(req):
    # JSON is automatically parsed
    data = req.json_body
    
    if not data:
        return {"error": "JSON body required"}, 400
    
    username = data.get("username")
    email = data.get("email")
    
    # Create user...
    return {"message": "User created", "username": username}, 201
```

### Request Example

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com"}'
```

### Features

- ✅ Automatic detection of JSON content type
- ✅ Parsed JSON available as `req.json_body`
- ✅ Returns `None` if JSON is invalid
- ✅ Original body still available as `req.body`

---

## 🌐 CORS Support {#cors-support}

Enable Cross-Origin Resource Sharing for your APIs.

### Quick Setup

```python
from isha import App
from isha.cors import enable_cors

app = App()

# Enable CORS with default settings
enable_cors(app)
```

### Custom Configuration

```python
from isha.cors import enable_cors

enable_cors(
    app,
    origins=["http://localhost:3000", "https://example.com"],
    methods=["GET", "POST", "PUT", "DELETE"],
    headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age=3600
)
```

### Manual CORS Setup

```python
from isha.cors import CORS

cors = CORS(origins=["*"])

@app.before
def handle_cors_preflight(req):
    if cors.is_preflight(req):
        return cors.handle_preflight(req)

@app.after
def apply_cors_headers(req, res):
    return cors.apply(req, res)
```

### Features

- ✅ Automatic preflight request handling
- ✅ Configurable allowed origins, methods, and headers
- ✅ Credential support
- ✅ Preflight caching with `max_age`

---

## 📤 File Upload Handling {#file-uploads}

Handle multipart/form-data file uploads with ease.

### Basic Setup

```python
from isha import App, FileUploadHandler

app = App()
upload_handler = FileUploadHandler(upload_dir="uploads", max_size_mb=10)

@app.before
def handle_uploads(req):
    upload_handler.process(req)
```

### Upload Route

```python
@app.post("/upload")
def upload_file(req):
    if 'file' not in req.files:
        return "No file uploaded", 400
    
    uploaded_file = req.files['file']
    
    # Access file properties
    print(f"Filename: {uploaded_file.filename}")
    print(f"Size: {uploaded_file.size} bytes")
    print(f"Type: {uploaded_file.content_type}")
    
    # Save file
    save_path = uploaded_file.save("uploads")
    
    return {"message": "File uploaded", "path": save_path}
```

### HTML Form

```html
<form method="POST" action="/upload" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button type="submit">Upload</button>
</form>
```

### Manual Parsing

```python
from isha.uploads import parse_multipart

@app.post("/custom-upload")
def custom_upload(req):
    data = parse_multipart(req)
    
    # Access uploaded files
    if 'file' in data:
        file = data['file']
        file.save("custom_directory")
    
    # Access form fields
    name = data.get('name', '')
    
    return "Upload complete"
```

### Features

- ✅ Automatic file parsing
- ✅ File size limits
- ✅ Multiple file uploads
- ✅ Access to file metadata
- ✅ Simple save API

---

## ⚡ Rate Limiting {#rate-limiting}

Protect your API from abuse with token bucket rate limiting.

### Global Rate Limiting

```python
from isha import App
from isha.ratelimit import enable_rate_limiting

app = App()

# 100 requests per minute per IP
enable_rate_limiting(app, requests_per_minute=100)
```

### Per-Route Rate Limiting

```python
from isha.ratelimit import RouteRateLimiter

limiter = RouteRateLimiter()

@app.get("/api/expensive")
@limiter.limit(requests_per_minute=10)
def expensive_api(req):
    # This route allows only 10 requests per minute per IP
    return {"data": "expensive operation result"}

@app.get("/api/cheap")
@limiter.limit(requests_per_minute=100)
def cheap_api(req):
    # This route allows 100 requests per minute per IP
    return {"data": "cheap operation result"}
```

### Manual Rate Limiter

```python
from isha.ratelimit import RateLimiter

limiter = RateLimiter(requests_per_minute=60, burst=100)

@app.before
def check_rate_limit(req):
    if not limiter.allow(req):
        return "Rate limit exceeded. Please try again later.", 429
```

### Features

- ✅ Token bucket algorithm
- ✅ Per-IP rate limiting
- ✅ Configurable burst size
- ✅ Global and per-route limits
- ✅ Returns 429 status code when limit exceeded

---

## 💾 Response Caching {#response-caching}

Cache expensive operations with in-memory caching.

### Decorator-Based Caching

```python
from isha import App
from isha.cache import cached_route

app = App()

@app.get("/expensive")
@cached_route(ttl=300)  # Cache for 5 minutes
def expensive_operation(req):
    # This will only execute once every 5 minutes
    result = perform_expensive_database_query()
    return {"result": result}
```

### Response Cache Class

```python
from isha.cache import ResponseCache

cache = ResponseCache(ttl=60)

@app.get("/data")
@cache.cached(ttl=30)  # Override default TTL
def get_data(req):
    return {"data": fetch_data()}
```

### Manual Caching

```python
from isha.cache import Cache

cache = Cache(ttl=300, max_size=1000)

@app.get("/products")
def get_products(req):
    # Check cache first
    cached = cache.get("products")
    if cached:
        return cached
    
    # Fetch from database
    products = db.query("SELECT * FROM products")
    
    # Store in cache
    cache.set("products", {"products": products})
    
    return {"products": products}
```

### Cache Invalidation

```python
# Clear specific cache entry
cache.delete("products")

# Clear all cache entries
cache.clear()

# Clean up expired entries
cache.cleanup()
```

### Features

- ✅ TTL-based expiration
- ✅ LRU eviction when max size reached
- ✅ Automatic cache key generation
- ✅ Per-route TTL configuration
- ✅ Manual cache control

---

## 📝 Structured Logging {#structured-logging}

Beautiful, colorful logging for development and production.

### Basic Logger

```python
from isha.logger import Logger, LogLevel

logger = Logger(name="my-app", min_level=LogLevel.INFO)

logger.debug("Debug message")
logger.info("Server started")
logger.warning("Disk space low", {"available_gb": 5})
logger.error("Database connection failed", {"error": str(e)})
logger.critical("System failure!")
```

### Request Logging

```python
from isha import App
from isha.logger import enable_request_logging

app = App()

# Enable automatic request/response logging
enable_request_logging(app)
```

### Custom Request Logger

```python
from isha.logger import Logger, RequestLogger

logger = Logger(name="api", min_level=LogLevel.DEBUG)
request_logger = RequestLogger(logger)

@app.before
def log_request(req):
    request_logger.log_request(req)

@app.after
def log_response(req, res):
    request_logger.log_response(req, res)
    return res
```

### Log Levels

- `DEBUG` - Detailed debug information (cyan)
- `INFO` - General informational messages (green)
- `WARNING` - Warning messages (yellow)
- `ERROR` - Error messages (red)
- `CRITICAL` - Critical errors (magenta)

### Example Output

```
[2025-12-25 10:30:45] INFO     [my-app] Server started
[2025-12-25 10:30:46] INFO     [http] GET /api/users | query=None | content_type=None
[2025-12-25 10:30:46] INFO     [http] GET /api/users → 200 | duration_ms=15.32 | content_type=application/json
[2025-12-25 10:30:50] WARNING  [my-app] Rate limit approaching | client=192.168.1.1
[2025-12-25 10:30:55] ERROR    [http] POST /api/users → 400 | duration_ms=5.21 | content_type=application/json
```

### Features

- ✅ Colored output for better readability
- ✅ Structured context logging
- ✅ Automatic request/response logging
- ✅ Configurable log levels
- ✅ Duration tracking for requests

---

## 🎯 Complete Example

Here's a complete example using all new features:

```python
from isha import App, Database
from isha.cors import enable_cors
from isha.ratelimit import enable_rate_limiting
from isha.logger import enable_request_logging, Logger
from isha.cache import cached_route
from isha import FileUploadHandler

# Initialize
app = App(name="my-api")
db = Database("app.db")
logger = Logger(name="my-api")

# Enable features
enable_cors(app, origins=["*"])
enable_rate_limiting(app, requests_per_minute=100)
enable_request_logging(app, logger)

upload_handler = FileUploadHandler(upload_dir="uploads")

@app.before
def handle_uploads(req):
    upload_handler.process(req)

# URL parameters
@app.get("/users/{id}")
def get_user(req):
    user_id = req.params["id"]
    user = db.query("SELECT * FROM users WHERE id = ?", (user_id,))
    return {"user": user[0] if user else None}

# JSON body parsing
@app.post("/api/users")
def create_user(req):
    if not req.json_body:
        return {"error": "JSON required"}, 400
    
    username = req.json_body.get("username")
    db.insert("users", {"username": username})
    return {"message": "Created"}, 201

# Cached route
@app.get("/expensive")
@cached_route(ttl=60)
def expensive(req):
    # Only runs once per minute
    return {"data": expensive_operation()}

# File upload
@app.post("/upload")
def upload(req):
    if 'file' in req.files:
        file = req.files['file']
        path = file.save("uploads")
        logger.info(f"File uploaded: {file.filename}")
        return {"path": path}
    return {"error": "No file"}, 400

if __name__ == "__main__":
    logger.info("🚀 Server starting on http://127.0.0.1:8000")
```

---

## 🎉 Summary

The ISHA framework now includes:

✅ **7 Major New Features**
✅ **5 New Modules** (cors, uploads, ratelimit, cache, logger)
✅ **Enhanced Core** (URL params, JSON parsing)
✅ **Production-Ready** (Security, performance, observability)
✅ **Still Zero Dependencies** (Pure Python)

Happy coding with ISHA! 🌱
