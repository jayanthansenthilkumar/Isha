"""
Ishaa Routing Engine — Static routes, dynamic routes, and method-based routing.
"""

import re
from typing import Callable, Dict, List, Optional, Set, Tuple, Any


class Route:
    """
    Represents a single route in the framework.
    
    Supports:
        - Static routes: /home, /about
        - Dynamic routes: /user/<id>, /post/<slug>
        - Typed dynamic routes: /user/<int:id>, /post/<str:slug>
        - Wildcard routes: /files/<path:filepath>
    """

    PARAM_PATTERN = re.compile(r"<(?:(?P<type>\w+):)?(?P<name>\w+)>")

    TYPE_MAP = {
        "int": (r"(\d+)", int),
        "float": (r"([\d.]+)", float),
        "str": (r"([^/]+)", str),
        "path": (r"(.+)", str),
        "uuid": (r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", str),
        "slug": (r"([a-z0-9]+(?:-[a-z0-9]+)*)", str),
    }

    def __init__(self, path: str, handler: Callable, methods: Set[str] = None, name: str = None):
        self.path = path
        self.handler = handler
        self.methods = methods or {"GET"}
        self.name = name or handler.__name__
        self.is_dynamic = bool(self.PARAM_PATTERN.search(path))

        # Compile route pattern
        self.param_names = []
        self.param_converters = []
        self.pattern = self._compile_pattern(path)

    def _compile_pattern(self, path: str) -> re.Pattern:
        """Convert a route path to a regex pattern."""
        if not self.is_dynamic:
            return re.compile(f"^{re.escape(path)}$")

        regex = "^"
        last_end = 0

        for match in self.PARAM_PATTERN.finditer(path):
            # Add literal text before this param
            regex += re.escape(path[last_end:match.start()])

            param_type = match.group("type") or "str"
            param_name = match.group("name")

            self.param_names.append(param_name)

            if param_type in self.TYPE_MAP:
                pattern, converter = self.TYPE_MAP[param_type]
                self.param_converters.append(converter)
                regex += pattern
            else:
                self.param_converters.append(str)
                regex += r"([^/]+)"

            last_end = match.end()

        regex += re.escape(path[last_end:]) + "$"
        return re.compile(regex)

    def match(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Try to match this route against a given path.
        Returns extracted parameters dict or None.
        """
        m = self.pattern.match(path)
        if not m:
            return None

        if not self.is_dynamic:
            return {}

        params = {}
        for i, (name, converter) in enumerate(zip(self.param_names, self.param_converters)):
            try:
                params[name] = converter(m.group(i + 1))
            except (ValueError, TypeError):
                return None

        return params

    def __repr__(self):
        return f"<Route {self.methods} {self.path} -> {self.name}>"


class Router:
    """
    The routing engine for Ishaa.
    
    Manages route registration and URL matching with support for:
        - Static and dynamic routes
        - Method-based routing
        - Named routes for URL building
        - Route groups/prefixes
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix.rstrip("/")
        self.routes: List[Route] = []
        self._static_routes: Dict[str, Dict[str, Route]] = {}  # path -> {method: route}
        self._dynamic_routes: List[Route] = []
        self._named_routes: Dict[str, Route] = {}

    def add_route(self, path: str, handler: Callable, methods: List[str] = None, name: str = None):
        """Register a new route."""
        full_path = self.prefix + path if self.prefix else path
        if not full_path.startswith("/"):
            full_path = "/" + full_path

        method_set = {m.upper() for m in (methods or ["GET"])}

        # Automatically add HEAD for GET routes
        if "GET" in method_set:
            method_set.add("HEAD")

        route = Route(full_path, handler, method_set, name)
        self.routes.append(route)

        if name:
            self._named_routes[name] = route

        if route.is_dynamic:
            self._dynamic_routes.append(route)
        else:
            if full_path not in self._static_routes:
                self._static_routes[full_path] = {}
            for method in method_set:
                self._static_routes[full_path][method] = route

        return route

    def route(self, path: str, methods: List[str] = None, name: str = None):
        """Decorator for registering routes."""
        def decorator(handler: Callable):
            self.add_route(path, handler, methods, name)
            return handler
        return decorator

    def get(self, path: str, name: str = None):
        """Shortcut decorator for GET routes."""
        return self.route(path, methods=["GET"], name=name)

    def post(self, path: str, name: str = None):
        """Shortcut decorator for POST routes."""
        return self.route(path, methods=["POST"], name=name)

    def put(self, path: str, name: str = None):
        """Shortcut decorator for PUT routes."""
        return self.route(path, methods=["PUT"], name=name)

    def delete(self, path: str, name: str = None):
        """Shortcut decorator for DELETE routes."""
        return self.route(path, methods=["DELETE"], name=name)

    def patch(self, path: str, name: str = None):
        """Shortcut decorator for PATCH routes."""
        return self.route(path, methods=["PATCH"], name=name)

    def resolve(self, path: str, method: str = "GET") -> Tuple[Optional[Route], Dict[str, Any]]:
        """
        Resolve a path and method to a route.
        
        Returns:
            Tuple of (Route or None, path_params dict)
        """
        method = method.upper()

        # Check static routes first (O(1) lookup)
        if path in self._static_routes:
            route_map = self._static_routes[path]
            if method in route_map:
                return route_map[method], {}
            # Check if path exists but method not allowed
            if route_map:
                return None, {"_method_not_allowed": True, "_allowed": set().union(*(r.methods for r in route_map.values()))}

        # Check dynamic routes
        for route in self._dynamic_routes:
            params = route.match(path)
            if params is not None:
                if method in route.methods:
                    return route, params
                # Track method not allowed
                return None, {"_method_not_allowed": True, "_allowed": route.methods}

        return None, {}

    def url_for(self, name: str, **kwargs) -> str:
        """Build a URL for a named route."""
        route = self._named_routes.get(name)
        if not route:
            raise ValueError(f"No route named '{name}'")

        path = route.path
        for key, value in kwargs.items():
            # Replace <type:name> or <name> patterns
            path = re.sub(rf"<(?:\w+:)?{key}>", str(value), path)

        return path

    def merge(self, other_router: "Router"):
        """Merge another router's routes into this one."""
        for route in other_router.routes:
            full_path = self.prefix + route.path if self.prefix else route.path
            self.add_route(full_path, route.handler, list(route.methods), route.name)

    def __repr__(self):
        return f"<Router prefix='{self.prefix}' routes={len(self.routes)}>"
