"""
ISHA Configuration - Application Settings

Centralized configuration management with environment support.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """
    Configuration manager for ISHA applications.
    
    Usage:
        config = Config()
        config.set("DATABASE_URL", "sqlite:///db.sqlite")
        url = config.get("DATABASE_URL")
        
        # Or use dictionary syntax
        config["API_KEY"] = "secret"
    """
    
    def __init__(self, defaults: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.
        
        Args:
            defaults: Default configuration values
        """
        self._config: Dict[str, Any] = defaults or {}
        self._loaded_files = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # Check environment variables first
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value
        
        # Check config dict
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style setting."""
        self.set(key, value)
    
    def load_from_file(self, file_path: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            file_path: Path to JSON config file
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            self._config.update(data)
            self._loaded_files.append(file_path)
    
    def load_from_env(self, prefix: str = "ISHA_") -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix (e.g., "ISHA_")
        """
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                self._config[config_key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return self._config.copy()
    
    def __repr__(self) -> str:
        return f"Config({len(self._config)} settings)"


# Default configuration
DEFAULT_CONFIG = {
    "DEBUG": False,
    "HOST": "127.0.0.1",
    "PORT": 8000,
    "SECRET_KEY": "change-this-secret-key-in-production",
    "TEMPLATE_DIR": "templates",
    "STATIC_DIR": "static",
    "DATABASE_URL": None,
    "SESSION_LIFETIME": 3600,  # 1 hour in seconds
}
