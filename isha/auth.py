"""
Isha Authentication — Session-based auth, JWT, password hashing.
"""

import hashlib
import hmac
import json
import secrets
import time
import base64
import logging
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("isha.auth")


# ── Password Hashing ────────────────────────────────────────────────

class PasswordHasher:
    """
    Secure password hashing using PBKDF2-HMAC-SHA256.
    For even stronger hashing, install bcrypt and use BcryptHasher.
    """

    @staticmethod
    def hash(password: str, iterations: int = 260000) -> str:
        """Hash a password with a random salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return f"pbkdf2_sha256${iterations}${salt}${hashed.hex()}"

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Verify a password against a stored hash."""
        try:
            algorithm, iterations, salt, hash_value = hashed.split("$")
            iterations = int(iterations)
            new_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
            )
            return secrets.compare_digest(new_hash.hex(), hash_value)
        except (ValueError, AttributeError):
            return False


class BcryptHasher:
    """Password hashing using bcrypt (requires bcrypt package)."""

    @staticmethod
    def hash(password: str, rounds: int = 12) -> str:
        try:
            import bcrypt
            salt = bcrypt.gensalt(rounds=rounds)
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except ImportError:
            logger.warning("bcrypt not installed. Falling back to PBKDF2.")
            return PasswordHasher.hash(password)

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ImportError:
            return PasswordHasher.verify(password, hashed)


# ── JWT (JSON Web Tokens) ───────────────────────────────────────────

class JWT:
    """
    Simple JWT implementation using HMAC-SHA256.
    
    Example:
        jwt = JWT(secret="my-secret-key")
        
        # Create token
        token = jwt.encode({"user_id": 1, "role": "admin"})
        
        # Verify and decode
        payload = jwt.decode(token)
    """

    def __init__(self, secret: str, algorithm: str = "HS256", expiry_seconds: int = 3600):
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_seconds = expiry_seconds

    def encode(self, payload: Dict[str, Any], expiry: int = None) -> str:
        """Create a JWT token."""
        header = {"alg": self.algorithm, "typ": "JWT"}
        
        # Add standard claims
        now = time.time()
        payload = dict(payload)  # Copy to avoid mutation
        payload.setdefault("iat", int(now))
        payload.setdefault("exp", int(now + (expiry or self.expiry_seconds)))

        # Encode header and payload
        header_b64 = self._base64url_encode(json.dumps(header))
        payload_b64 = self._base64url_encode(json.dumps(payload, default=str))

        # Create signature
        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message)
        sig_b64 = self._base64url_encode_bytes(signature)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def decode(self, token: str, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_sig = self._sign(message)
            actual_sig = self._base64url_decode_bytes(sig_b64)

            if not hmac.compare_digest(expected_sig, actual_sig):
                logger.warning("JWT signature verification failed")
                return None

            # Decode payload
            payload = json.loads(self._base64url_decode(payload_b64))

            # Check expiration
            if verify_exp and "exp" in payload:
                if time.time() > payload["exp"]:
                    logger.warning("JWT token expired")
                    return None

            return payload

        except Exception as e:
            logger.error(f"JWT decode error: {e}")
            return None

    def _sign(self, message: str) -> bytes:
        """Create HMAC-SHA256 signature."""
        return hmac.new(
            self.secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    @staticmethod
    def _base64url_encode(data: str) -> str:
        return base64.urlsafe_b64encode(data.encode("utf-8")).rstrip(b"=").decode("ascii")

    @staticmethod
    def _base64url_encode_bytes(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _base64url_decode(data: str) -> str:
        padding = 4 - len(data) % 4
        data += "=" * padding
        return base64.urlsafe_b64decode(data).decode("utf-8")

    @staticmethod
    def _base64url_decode_bytes(data: str) -> bytes:
        padding = 4 - len(data) % 4
        data += "=" * padding
        return base64.urlsafe_b64decode(data)


# ── Session Manager ─────────────────────────────────────────────────

class SessionManager:
    """
    In-memory session management.
    
    For production, extend with Redis or database-backed sessions.
    """

    def __init__(self, cookie_name="isha_session", max_age=3600, secret=None):
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secret = secret or secrets.token_hex(32)
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self) -> str:
        """Create a new session and return the session ID."""
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = {
            "_created": time.time(),
            "_expires": time.time() + self.max_age,
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Check expiry
        if time.time() > session.get("_expires", 0):
            self.destroy_session(session_id)
            return None

        return session

    def set(self, session_id: str, key: str, value: Any):
        """Set a value in the session."""
        session = self._sessions.get(session_id)
        if session is not None:
            session[key] = value

    def get(self, session_id: str, key: str, default=None):
        """Get a value from the session."""
        session = self._sessions.get(session_id)
        if session is not None:
            return session.get(key, default)
        return default

    def destroy_session(self, session_id: str):
        """Destroy a session."""
        self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        """Remove all expired sessions."""
        now = time.time()
        expired = [
            sid for sid, data in self._sessions.items()
            if now > data.get("_expires", 0)
        ]
        for sid in expired:
            del self._sessions[sid]


# ── Auth Middleware ──────────────────────────────────────────────────

class AuthMiddleware:
    """
    Authentication middleware that checks for JWT tokens or sessions.
    
    Usage:
        auth = AuthMiddleware(jwt=JWT(secret="secret"), exclude=["/login", "/register"])
        app.add_middleware(auth)
    """

    def __init__(
        self,
        jwt: JWT = None,
        session_manager: SessionManager = None,
        exclude: list = None,
        token_header: str = "authorization",
        token_prefix: str = "Bearer",
    ):
        self.jwt = jwt
        self.session_manager = session_manager
        self.exclude = exclude or []
        self.token_header = token_header
        self.token_prefix = token_prefix

    async def before_request(self, request):
        """Check authentication before handling the request."""
        # Skip excluded paths
        for path in self.exclude:
            if request.path.startswith(path):
                request.state["user"] = None
                return None

        # Try JWT auth
        if self.jwt:
            auth_header = request.headers.get(self.token_header, "")
            if auth_header.startswith(f"{self.token_prefix} "):
                token = auth_header[len(self.token_prefix) + 1:]
                payload = self.jwt.decode(token)
                if payload:
                    request.state["user"] = payload
                    return None

        # Try session auth
        if self.session_manager:
            session_id = request.cookies.get(self.session_manager.cookie_name)
            if session_id:
                session = self.session_manager.get_session(session_id)
                if session and "user" in session:
                    request.state["user"] = session["user"]
                    request.state["session_id"] = session_id
                    return None

        # No auth found — return 401
        from .response import JSONResponse
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    async def after_request(self, request, response):
        return response

    async def handle_exception(self, request, exc):
        return None


# ── Decorators ──────────────────────────────────────────────────────

def login_required(func):
    """Decorator to require authentication on a route."""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        user = request.state.get("user")
        if not user:
            from .response import JSONResponse
            return JSONResponse({"error": "Login required"}, status_code=401)
        return await func(request, *args, **kwargs) if __import__("asyncio").iscoroutinefunction(func) else func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    """Decorator to require specific roles."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.state.get("user", {})
            user_role = user.get("role", "")
            if user_role not in roles:
                from .response import JSONResponse
                return JSONResponse({"error": "Insufficient permissions"}, status_code=403)
            return await func(request, *args, **kwargs) if __import__("asyncio").iscoroutinefunction(func) else func(request, *args, **kwargs)
        return wrapper
    return decorator
