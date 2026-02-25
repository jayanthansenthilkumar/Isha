"""
Isha Plugin System — Extensible plugin architecture.

Supports:
    - Plugin registration and lifecycle
    - Plugin configuration
    - Built-in plugins: Cache, Static Files, etc.
"""

import os
import time
import logging
import mimetypes
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("isha.plugin")


class Plugin:
    """
    Base plugin class. Subclass this to create plugins.
    
    Example:
        class MyPlugin(Plugin):
            name = "my_plugin"
            
            def setup(self, app):
                app.config["MY_SETTING"] = True
                
                @app.route("/my-plugin")
                async def plugin_route(request):
                    return {"plugin": "active"}
    """

    name: str = "base_plugin"
    version: str = "1.0.0"

    def setup(self, app):
        """Called when the plugin is registered with the app."""
        pass

    def teardown(self, app):
        """Called when the app shuts down."""
        pass


class CachePlugin(Plugin):
    """
    Simple in-memory cache plugin.
    
    Example:
        cache = CachePlugin(default_ttl=300)
        app.register_plugin(cache)
        
        # Use in routes
        cache.set("key", "value", ttl=60)
        value = cache.get("key")
    """

    name = "cache"

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, tuple] = {}  # key -> (value, expiry)

    def setup(self, app):
        app._state["cache"] = self
        logger.info(f"Cache plugin initialized (TTL={self.default_ttl}s, max={self.max_size})")

    def get(self, key: str, default=None) -> Any:
        """Get a cached value."""
        if key in self._store:
            value, expiry = self._store[key]
            if expiry is None or time.time() < expiry:
                return value
            # Expired
            del self._store[key]
        return default

    def set(self, key: str, value: Any, ttl: int = None):
        """Set a cached value."""
        if len(self._store) >= self.max_size:
            self._evict()

        expiry = None
        if ttl is not None:
            expiry = time.time() + ttl
        elif self.default_ttl:
            expiry = time.time() + self.default_ttl

        self._store[key] = (value, expiry)

    def delete(self, key: str):
        """Delete a cached key."""
        self._store.pop(key, None)

    def clear(self):
        """Clear all cached data."""
        self._store.clear()

    def has(self, key: str) -> bool:
        """Check if a key is cached and not expired."""
        return self.get(key) is not None

    def _evict(self):
        """Evict expired and oldest entries."""
        now = time.time()
        # Remove expired
        expired = [k for k, (v, exp) in self._store.items() if exp and now >= exp]
        for k in expired:
            del self._store[k]

        # If still over max, remove oldest
        while len(self._store) >= self.max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

    def cached(self, ttl: int = None, key_func=None):
        """Decorator to cache route responses."""
        def decorator(func):
            import asyncio
            from functools import wraps

            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                if key_func:
                    cache_key = key_func(request)
                else:
                    cache_key = f"{request.method}:{request.path}:{request.scope.get('query_string', b'').decode()}"

                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                if asyncio.iscoroutinefunction(func):
                    result = await func(request, *args, **kwargs)
                else:
                    result = func(request, *args, **kwargs)

                self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper
        return decorator


class StaticFilesPlugin(Plugin):
    """
    Static file serving plugin.
    
    Example:
        static = StaticFilesPlugin(directory="static", prefix="/static")
        app.register_plugin(static)
    """

    name = "static_files"

    def __init__(self, directory: str = "static", prefix: str = "/static"):
        self.directory = Path(directory)
        self.prefix = prefix.rstrip("/")

    def setup(self, app):
        from .response import Response

        prefix = self.prefix
        directory = self.directory

        @app.route(f"{prefix}/<path:filepath>", methods=["GET"])
        async def serve_static(request, filepath=""):
            try:
                # Prevent path traversal
                safe_path = os.path.normpath(filepath)
                if safe_path.startswith(".."):
                    return Response("Forbidden", status_code=403)

                file_path = directory / safe_path
                if not file_path.exists() or not file_path.is_file():
                    return Response("Not Found", status_code=404)

                mime_type, _ = mimetypes.guess_type(str(file_path))
                mime_type = mime_type or "application/octet-stream"

                with open(file_path, "rb") as f:
                    content = f.read()

                return Response(
                    body=content,
                    status_code=200,
                    content_type=mime_type,
                    headers={"cache-control": "public, max-age=3600"},
                )

            except Exception as e:
                logger.error(f"Static file error: {e}")
                return Response("Internal Server Error", status_code=500)

        logger.info(f"Static files: {prefix}/ -> {directory}/")


class MailPlugin(Plugin):
    """
    Email sending plugin (SMTP).
    
    Example:
        mail = MailPlugin(
            host="smtp.gmail.com",
            port=587,
            username="you@gmail.com",
            password="app-password",
        )
        app.register_plugin(mail)
        
        await mail.send(
            to="user@example.com",
            subject="Hello",
            body="Welcome to Isha!",
        )
    """

    name = "mail"

    def __init__(self, host="localhost", port=587, username="", password="", use_tls=True, default_sender=""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.default_sender = default_sender or username

    def setup(self, app):
        app._state["mail"] = self
        logger.info(f"Mail plugin initialized ({self.host}:{self.port})")

    async def send(self, to, subject, body, html_body=None, sender=None):
        """Send an email."""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_sync, to, subject, body, html_body, sender)

    def _send_sync(self, to, subject, body, html_body=None, sender=None):
        """Synchronous email sending."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        sender = sender or self.default_sender
        if isinstance(to, str):
            to = [to]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(to)

        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(sender, to, msg.as_string())
            logger.info(f"Email sent to {to}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise


class AdminPlugin(Plugin):
    """
    Basic admin dashboard plugin.
    Serves a simple admin interface for managing data.
    """

    name = "admin"

    def __init__(self, prefix="/admin", title="Isha Admin"):
        self.prefix = prefix.rstrip("/")
        self.title = title
        self._models = []

    def register_model(self, model_class):
        """Register a model for the admin interface."""
        self._models.append(model_class)

    def setup(self, app):
        from .response import HTMLResponse, JSONResponse

        prefix = self.prefix
        models = self._models
        title = self.title

        @app.route(f"{prefix}", methods=["GET"])
        async def admin_index(request):
            model_links = "".join(
                f'<li><a href="{prefix}/{m.__tablename__}">{m.__name__}</a></li>'
                for m in models
            )
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>{title}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; background: #f5f5f5; }}
                h1 {{ color: #333; }} .card {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                a {{ color: #0066cc; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
                ul {{ list-style: none; padding: 0; }} li {{ padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
            </style></head>
            <body>
                <h1>{title}</h1>
                <div class="card">
                    <h2>Models</h2>
                    <ul>{model_links}</ul>
                </div>
            </body></html>
            """
            return HTMLResponse(html_content)

        @app.route(f"{prefix}/<str:table>", methods=["GET"])
        async def admin_list(request, table=""):
            model = next((m for m in models if m.__tablename__ == table), None)
            if not model:
                return JSONResponse({"error": "Model not found"}, status_code=404)

            records = model.all()
            data = [r.to_dict() for r in records]
            return JSONResponse({"model": model.__name__, "count": len(data), "records": data})

        logger.info(f"Admin plugin mounted at {prefix}")
