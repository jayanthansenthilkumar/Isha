"""
Isha — A Modern Python Web Framework

Simplicity of Flask. Structure of Django. Performance mindset of FastAPI.
Clean. Powerful. Elegant.
"""

__version__ = "1.0.0"
__author__ = "Isha Framework Contributors"

from .app import Isha
from .request import Request
from .response import Response, JSONResponse, HTMLResponse, RedirectResponse
from .routing import Router, Route
from .middleware import Middleware
from .blueprints import Blueprint

__all__ = [
    "Isha",
    "Request",
    "Response",
    "JSONResponse",
    "HTMLResponse",
    "RedirectResponse",
    "Router",
    "Route",
    "Middleware",
    "Blueprint",
    "__version__",
]
