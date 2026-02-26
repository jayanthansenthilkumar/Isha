"""
Ishaa - A Modern Python Web Framework

Simplicity of Flask. Structure of Django. Performance mindset of FastAPI.
Clean. Powerful. Elegant. Self-Evolving.

Install:  pip install ishaa
Docs:     https://github.com/jayanthansenthilkumar/ISHAA_Framework
"""

__version__ = "1.2.0"
__author__ = "Jayanthan Senthilkumar"

from .app import Ishaa
from .request import Request
from .response import Response, JSONResponse, HTMLResponse, RedirectResponse
from .routing import Router, Route
from .middleware import Middleware
from .blueprints import Blueprint
from .sare import SARE
from .reality import RealityModeFramework
from .seqp import SelfEvolvingQualityPipeline

__all__ = [
    "Ishaa",
    "Request",
    "Response",
    "JSONResponse",
    "HTMLResponse",
    "RedirectResponse",
    "Router",
    "Route",
    "Middleware",
    "Blueprint",
    "SARE",
    "RealityModeFramework",
    "SelfEvolvingQualityPipeline",
    "__version__",
]
