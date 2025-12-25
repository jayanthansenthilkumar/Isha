"""
ISHA Session - Cookie-based Session Management

Simple session handling using signed cookies.
"""

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


class Session:
    """
    Session object for storing user data across requests.
    
    Usage:
        session = Session(secret_key="my-secret")
        session["user_id"] = 123
        session["username"] = "john"
        
        cookie_value = session.encode()
    """
    
    def __init__(self, secret_key: str, lifetime: int = 3600):
        """
        Initialize session.
        
        Args:
            secret_key: Secret key for signing cookies
            lifetime: Session lifetime in seconds (default: 1 hour)
        """
        self.secret_key = secret_key
        self.lifetime = lifetime
        self._data: Dict[str, Any] = {}
        self._modified = False
    
    def __getitem__(self, key: str) -> Any:
        """Get session value."""
        return self._data.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set session value."""
        self._data[key] = value
        self._modified = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get session value with default."""
        return self._data.get(key, default)
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return session value."""
        self._modified = True
        return self._data.pop(key, default)
    
    def clear(self) -> None:
        """Clear all session data."""
        self._data.clear()
        self._modified = True
    
    def encode(self) -> str:
        """
        Encode session data to a signed cookie value.
        
        Returns:
            Base64-encoded signed session data
        """
        # Add expiration timestamp
        data = self._data.copy()
        data["_expires"] = int(time.time()) + self.lifetime
        
        # Serialize to JSON
        json_data = json.dumps(data, separators=(',', ':'))
        
        # Create signature
        signature = self._sign(json_data)
        
        # Combine data and signature
        import base64
        combined = f"{json_data}.{signature}"
        return base64.urlsafe_b64encode(combined.encode()).decode()
    
    @classmethod
    def decode(cls, cookie_value: str, secret_key: str) -> Optional['Session']:
        """
        Decode and verify a session cookie.
        
        Args:
            cookie_value: The cookie value to decode
            secret_key: Secret key for verification
            
        Returns:
            Session object or None if invalid/expired
        """
        try:
            import base64
            
            # Decode base64
            combined = base64.urlsafe_b64decode(cookie_value.encode()).decode()
            
            # Split data and signature
            if '.' not in combined:
                return None
            
            json_data, signature = combined.rsplit('.', 1)
            
            # Verify signature
            session = cls(secret_key)
            expected_signature = session._sign(json_data)
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Parse JSON
            data = json.loads(json_data)
            
            # Check expiration
            expires = data.pop("_expires", 0)
            if time.time() > expires:
                return None
            
            # Create session object
            session._data = data
            return session
            
        except Exception:
            return None
    
    def _sign(self, data: str) -> str:
        """Create HMAC signature for data."""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
