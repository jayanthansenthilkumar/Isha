"""
Isha Dependency Injection — Auto-inject dependencies into route handlers.

Example:
    from isha.di import Depends, inject

    async def get_db():
        db = Database.get_adapter()
        try:
            yield db
        finally:
            pass

    async def get_current_user(request):
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(401, "Not authenticated")
        return jwt.decode(token)

    @app.route("/users/me")
    @inject
    async def get_me(request, user=Depends(get_current_user), db=Depends(get_db)):
        return {"user": user}
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Optional
from functools import wraps

logger = logging.getLogger("isha.di")


class Depends:
    """
    Marks a parameter as a dependency to be injected.
    
    The dependency can be:
        - A regular function (called each request)
        - An async function
        - A generator (for setup/teardown patterns)
        - An async generator
    """

    def __init__(self, dependency: Callable, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self):
        return f"Depends({self.dependency.__name__})"


class HTTPException(Exception):
    """HTTP exception that can be raised from dependencies."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class DependencyInjector:
    """Resolves and injects dependencies for route handlers."""

    def __init__(self):
        self._singletons = {}

    async def resolve(self, dependency: Depends, request, cache: dict) -> Any:
        """Resolve a single dependency."""
        dep_func = dependency.dependency
        dep_id = id(dep_func)

        # Check cache
        if dependency.use_cache and dep_id in cache:
            return cache[dep_id]

        # Inspect the dependency function's parameters
        sig = inspect.signature(dep_func)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == "request":
                kwargs["request"] = request
            elif isinstance(param.default, Depends):
                # Recursive dependency resolution
                kwargs[param_name] = await self.resolve(param.default, request, cache)

        # Call the dependency
        if inspect.isasyncgenfunction(dep_func):
            gen = dep_func(**kwargs)
            value = await gen.__anext__()
            # Store generator for cleanup
            cache[f"_gen_{dep_id}"] = gen
        elif inspect.isgeneratorfunction(dep_func):
            gen = dep_func(**kwargs)
            value = next(gen)
            cache[f"_gen_{dep_id}"] = gen
        elif asyncio.iscoroutinefunction(dep_func):
            value = await dep_func(**kwargs)
        else:
            value = dep_func(**kwargs)

        if dependency.use_cache:
            cache[dep_id] = value

        return value

    async def cleanup(self, cache: dict):
        """Cleanup generator-based dependencies."""
        for key, gen in list(cache.items()):
            if isinstance(key, str) and key.startswith("_gen_"):
                try:
                    if hasattr(gen, "__anext__"):
                        try:
                            await gen.__anext__()
                        except StopAsyncIteration:
                            pass
                    else:
                        try:
                            next(gen)
                        except StopIteration:
                            pass
                except Exception as e:
                    logger.error(f"Dependency cleanup error: {e}")


_injector = DependencyInjector()


def inject(func: Callable) -> Callable:
    """
    Decorator that enables dependency injection on a route handler.
    
    Scans function parameters for Depends() defaults and resolves them.
    """
    sig = inspect.signature(func)
    dep_params = {}

    for param_name, param in sig.parameters.items():
        if isinstance(param.default, Depends):
            dep_params[param_name] = param.default

    if not dep_params:
        return func

    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        cache = {}
        try:
            # Resolve all dependencies
            for param_name, dep in dep_params.items():
                try:
                    kwargs[param_name] = await _injector.resolve(dep, request, cache)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Dependency resolution failed for {param_name}: {e}")
                    raise HTTPException(500, f"Dependency error: {e}")

            # Call the handler
            if asyncio.iscoroutinefunction(func):
                result = await func(request, *args, **kwargs)
            else:
                result = func(request, *args, **kwargs)

            return result

        except HTTPException as exc:
            from .response import JSONResponse
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

        finally:
            await _injector.cleanup(cache)

    return wrapper
