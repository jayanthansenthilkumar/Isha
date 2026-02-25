"""
Tests for Isha Auth — Password hashing, JWT, sessions.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isha.auth import PasswordHasher, JWT, SessionManager


def test_password_hash_and_verify():
    hasher = PasswordHasher()
    hashed = hasher.hash("secret123")
    assert hasher.verify("secret123", hashed)
    assert not hasher.verify("wrong_password", hashed)


def test_password_different_hashes():
    hasher = PasswordHasher()
    h1 = hasher.hash("password")
    h2 = hasher.hash("password")
    assert h1 != h2  # Different salts


def test_jwt_encode_decode():
    jwt = JWT(secret="test-secret", expiry_seconds=3600)
    token = jwt.encode({"user_id": 1, "role": "admin"})
    payload = jwt.decode(token)
    assert payload is not None
    assert payload["user_id"] == 1
    assert payload["role"] == "admin"


def test_jwt_expired_token():
    jwt = JWT(secret="test-secret", expiry_seconds=1)
    token = jwt.encode({"user_id": 1}, expiry=-10)  # Already expired
    payload = jwt.decode(token)
    assert payload is None  # Should fail


def test_jwt_invalid_signature():
    jwt1 = JWT(secret="secret-1")
    jwt2 = JWT(secret="secret-2")
    token = jwt1.encode({"data": "test"})
    payload = jwt2.decode(token)
    assert payload is None  # Different secret should fail


def test_jwt_tampered_token():
    jwt = JWT(secret="test-secret")
    token = jwt.encode({"user_id": 1})
    # Tamper with the payload
    parts = token.split(".")
    parts[1] = parts[1] + "X"
    tampered = ".".join(parts)
    payload = jwt.decode(tampered)
    assert payload is None


def test_session_create_and_get():
    sm = SessionManager(max_age=60)
    sid = sm.create_session()
    assert sid is not None

    session = sm.get_session(sid)
    assert session is not None


def test_session_set_and_get():
    sm = SessionManager(max_age=60)
    sid = sm.create_session()
    sm.set(sid, "username", "alice")
    assert sm.get(sid, "username") == "alice"


def test_session_destroy():
    sm = SessionManager(max_age=60)
    sid = sm.create_session()
    sm.destroy_session(sid)
    assert sm.get_session(sid) is None


def test_session_expired():
    sm = SessionManager(max_age=0)  # Expires immediately
    sid = sm.create_session()
    time.sleep(0.1)
    assert sm.get_session(sid) is None


if __name__ == "__main__":
    test_funcs = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0

    for test in test_funcs:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
