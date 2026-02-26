"""
Configuration for Ishaa Framework Landing Page
"""

import os


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    DEBUG = False
    HOST = "127.0.0.1"
    PORT = 8000


class DevConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProdConfig(Config):
    """Production configuration."""
    DEBUG = False
    HOST = "0.0.0.0"
