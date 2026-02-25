"""
Isha OpenAPI Documentation Generator — Auto-generate API docs.
"""

import json
import inspect
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("isha.openapi")


class OpenAPIGenerator:
    """
    Generates OpenAPI 3.0 documentation from Isha routes.
    
    Example:
        docs = OpenAPIGenerator(app, title="My API", version="1.0.0")
        mount_docs(app, docs)
        
        # Access docs at /docs (Swagger UI) or /openapi.json
    """

    def __init__(self, app, title="Isha API", version="1.0.0", description=""):
        self.app = app
        self.title = title
        self.version = version
        self.description = description
        self._extra_schemas = {}
        self._tags = []

    def add_tag(self, name: str, description: str = ""):
        """Add a tag for grouping endpoints."""
        self._tags.append({"name": name, "description": description})

    def generate(self) -> Dict:
        """Generate the OpenAPI specification."""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": {},
            "components": {"schemas": dict(self._extra_schemas)},
        }

        if self._tags:
            spec["tags"] = self._tags

        for route in self.app.router.routes:
            path = self._convert_path(route.path)

            if path not in spec["paths"]:
                spec["paths"][path] = {}

            for method in route.methods:
                if method in ("HEAD",):
                    continue

                operation = self._build_operation(route, method)
                spec["paths"][path][method.lower()] = operation

        return spec

    def _convert_path(self, path: str) -> str:
        """Convert Isha path format to OpenAPI format: /user/<int:id> -> /user/{id}"""
        return re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", path)

    def _build_operation(self, route, method: str) -> Dict:
        """Build an OpenAPI operation object from a route."""
        handler = route.handler
        operation = {
            "summary": self._get_summary(handler),
            "description": self._get_description(handler),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {"schema": {"type": "object"}},
                    },
                },
            },
        }

        # Add parameters from dynamic path
        params = []
        for match in re.finditer(r"<(?:(\w+):)?(\w+)>", route.path):
            param_type = match.group(1) or "str"
            param_name = match.group(2)
            schema_type = {"int": "integer", "float": "number", "str": "string"}.get(param_type, "string")
            params.append({
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": {"type": schema_type},
            })

        if params:
            operation["parameters"] = params

        # Add request body for POST/PUT/PATCH
        if method in ("POST", "PUT", "PATCH"):
            operation["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                    },
                },
            }

        # Extract info from docstring
        if handler.__doc__:
            doc = handler.__doc__.strip()
            lines = doc.split("\n")
            operation["summary"] = lines[0].strip()
            if len(lines) > 1:
                operation["description"] = "\n".join(l.strip() for l in lines[1:]).strip()

        operation["operationId"] = route.name

        return operation

    def _get_summary(self, handler) -> str:
        """Get summary from handler function."""
        if handler.__doc__:
            return handler.__doc__.strip().split("\n")[0]
        return handler.__name__.replace("_", " ").title()

    def _get_description(self, handler) -> str:
        """Get description from handler docstring."""
        if handler.__doc__:
            lines = handler.__doc__.strip().split("\n")
            if len(lines) > 1:
                return "\n".join(l.strip() for l in lines[1:]).strip()
        return ""


def mount_docs(app, generator: OpenAPIGenerator = None, path: str = "/docs", json_path: str = "/openapi.json"):
    """
    Mount OpenAPI documentation on the app.
    
    Provides:
        - /docs — Swagger UI
        - /openapi.json — Raw OpenAPI spec
    """
    from .response import JSONResponse, HTMLResponse

    if generator is None:
        generator = OpenAPIGenerator(app)

    @app.route(json_path, methods=["GET"])
    async def openapi_json(request):
        """OpenAPI JSON specification."""
        return JSONResponse(generator.generate())

    @app.route(path, methods=["GET"])
    async def swagger_ui(request):
        """Swagger UI documentation page."""
        return HTMLResponse(_swagger_html(json_path, generator.title))


def _swagger_html(spec_url: str, title: str) -> str:
    """Generate Swagger UI HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} — API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
        body {{ margin: 0; background: #fafafa; }}
        .swagger-ui .topbar {{ display: none; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
            layout: "StandaloneLayout",
        }});
    </script>
</body>
</html>"""
