"""
Isha Utilities — Helper functions and common utilities.
"""

import os
import json
import hashlib
import secrets
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps


def get_timestamp():
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def generate_secret_key(length=64):
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(length)


def hash_password(password, salt=None):
    """Simple password hashing using SHA-256 with salt. For production, use bcrypt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(password, hashed):
    """Verify a password against a hash."""
    salt, hash_value = hashed.split("$", 1)
    new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return secrets.compare_digest(new_hash.hex(), hash_value)


def safe_join(directory, filename):
    """Safely join a directory and filename, preventing path traversal."""
    filename = os.path.normpath(filename)
    if filename.startswith(("../", "..\\")) or os.path.isabs(filename):
        raise ValueError("Path traversal detected")
    full_path = os.path.join(directory, filename)
    if not os.path.abspath(full_path).startswith(os.path.abspath(directory)):
        raise ValueError("Path traversal detected")
    return full_path


def get_mime_type(filename):
    """Get MIME type for a filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def import_string(dotted_path):
    """Import a module attribute given a dotted path string."""
    module_path, _, attr_name = dotted_path.rpartition(".")
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class cached_property:
    """A property that is computed once and then cached."""

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        val = self.func(instance)
        setattr(instance, self.attr_name, val)
        return val


class Config:
    """
    Application configuration management.
    
    Supports loading from:
        - Dictionary
        - Environment variables
        - JSON files
        - Python files
    """

    def __init__(self, defaults=None):
        self._config = {}
        if defaults:
            self._config.update(defaults)

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __contains__(self, key):
        return key in self._config

    def update(self, mapping):
        self._config.update(mapping)

    def from_dict(self, d):
        """Load config from a dictionary."""
        self._config.update(d)

    def from_env(self, prefix="ISHA_"):
        """Load config from environment variables with the given prefix."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                self._config[config_key] = value

    def from_json(self, filepath):
        """Load config from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self._config.update(data)

    def from_pyfile(self, filepath):
        """Load config from a Python file (uppercase variables only)."""
        config = {}
        with open(filepath) as f:
            exec(compile(f.read(), filepath, "exec"), config)
        for key, value in config.items():
            if key.isupper():
                self._config[key] = value

    def to_dict(self):
        return dict(self._config)

    def __repr__(self):
        return f"<Config {self._config}>"


def run_async(coro):
    """Run an async function synchronously."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)
