"""Tests for Ishaa Framework Landing Page"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ishaa.testing import TestClient
from app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.ok
    data = response.json()
    assert data["status"] == "ok"
    assert data["framework"] == "Ishaa"


def test_hello():
    response = client.get("/api/hello/World")
    assert response.ok
    data = response.json()
    assert "Hello" in data["message"]
    assert "Ishaa Framework" in data["message"]


def test_landing_page():
    response = client.get("/")
    assert response.ok
    assert "Ishaa Framework" in response.text
    assert "Lightning Speed" in response.text


def test_not_found():
    response = client.get("/nonexistent")
    assert response.status_code == 404


if __name__ == "__main__":
    for name_key, fn in list(globals().items()):
        if name_key.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name_key}")
            except Exception as e:
                print(f"  FAIL  {name_key}: {e}")
