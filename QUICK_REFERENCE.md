# 🚀 ISHA Quick Reference - Enhanced Features

## URL Parameters

```python
@app.get("/users/{id}")
def get_user(req):
    user_id = req.params["id"]
    return f"User: {user_id}"
```

## JSON Body Parsing

```python
@app.post("/api/create")
def create(req):
    data = req.json_body  # Auto-parsed JSON
    name = data.get("name")
    return {"created": name}, 201
```

## CORS

```python
from isha.cors import enable_cors

enable_cors(app, origins=["*"])
```

## File Uploads

```python
from isha import FileUploadHandler

upload_handler = FileUploadHandler(upload_dir="uploads")

@app.before
def handle_uploads(req):
    upload_handler.process(req)

@app.post("/upload")
def upload(req):
    file = req.files['file']
    path = file.save("uploads")
    return {"path": path}
```

## Rate Limiting

```python
from isha.ratelimit import enable_rate_limiting

enable_rate_limiting(app, requests_per_minute=100)
```

## Caching

```python
from isha.cache import cached_route

@app.get("/data")
@cached_route(ttl=60)
def get_data(req):
    return expensive_operation()
```

## Logging

```python
from isha.logger import Logger, enable_request_logging

logger = Logger(name="app")
enable_request_logging(app, logger)

logger.info("Message", {"key": "value"})
```

## Run Demo

```bash
# Run the enhanced demo
python -m isha run demo_enhanced.pyisha

# Visit http://127.0.0.1:8000
```
