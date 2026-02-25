"""
Tests for Isha ORM.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isha.orm import (
    Database, Model, IntegerField, TextField, BooleanField,
    FloatField, DateTimeField, JSONField, QueryBuilder,
)


# Use in-memory SQLite for tests
Database.connect(":memory:")


class TestUser(Model):
    __tablename__ = "test_users"
    id = IntegerField(primary_key=True)
    name = TextField(nullable=False)
    email = TextField(unique=True)
    age = IntegerField(default=0)
    active = BooleanField(default=True)
    score = FloatField(default=0.0)
    created_at = DateTimeField(auto_now_add=True)
    meta = JSONField(default=None)


class TestPost(Model):
    __tablename__ = "test_posts"
    id = IntegerField(primary_key=True)
    title = TextField(nullable=False)
    content = TextField()
    author_id = IntegerField()
    published = BooleanField(default=False)


def setup():
    """Setup test tables."""
    TestUser.create_table()
    TestPost.create_table()


def teardown():
    """Clean up."""
    Database.execute("DELETE FROM test_users")
    Database.execute("DELETE FROM test_posts")


def test_create_and_get():
    setup()
    user = TestUser.create(name="Alice", email="alice@test.com", age=30)
    assert user.id is not None
    assert user.name == "Alice"

    fetched = TestUser.get(user.id)
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.email == "alice@test.com"
    teardown()


def test_update():
    setup()
    user = TestUser.create(name="Bob", email="bob@test.com")
    user.age = 25
    user.save()

    fetched = TestUser.get(user.id)
    assert fetched.age == 25
    teardown()


def test_delete():
    setup()
    user = TestUser.create(name="Charlie", email="charlie@test.com")
    uid = user.id
    user.delete_record()

    fetched = TestUser.get(uid)
    assert fetched is None
    teardown()


def test_query_filter():
    setup()
    TestUser.create(name="Alice", email="a@test.com", active=True, age=25)
    TestUser.create(name="Bob", email="b@test.com", active=False, age=30)
    TestUser.create(name="Charlie", email="c@test.com", active=True, age=35)

    active_users = TestUser.query().filter(active=True).all()
    assert len(active_users) == 2

    bob = TestUser.query().filter(name="Bob").first()
    assert bob is not None
    assert bob.name == "Bob"
    teardown()


def test_query_operators():
    setup()
    TestUser.create(name="A", email="a1@test.com", age=20)
    TestUser.create(name="B", email="b1@test.com", age=30)
    TestUser.create(name="C", email="c1@test.com", age=40)

    over_25 = TestUser.query().filter(age__gt=25).all()
    assert len(over_25) == 2

    under_35 = TestUser.query().filter(age__lt=35).all()
    assert len(under_35) == 2

    exact_30 = TestUser.query().filter(age=30).first()
    assert exact_30.name == "B"
    teardown()


def test_query_order():
    setup()
    TestUser.create(name="Charlie", email="ch@test.com", age=30)
    TestUser.create(name="Alice", email="al@test.com", age=20)
    TestUser.create(name="Bob", email="bo@test.com", age=25)

    ascending = TestUser.query().order_by("age").all()
    assert ascending[0].name == "Alice"
    assert ascending[2].name == "Charlie"

    descending = TestUser.query().order_by("-age").all()
    assert descending[0].name == "Charlie"
    teardown()


def test_query_limit_offset():
    setup()
    for i in range(10):
        TestUser.create(name=f"User{i}", email=f"u{i}@test.com", age=20 + i)

    page1 = TestUser.query().order_by("age").limit(3).offset(0).all()
    assert len(page1) == 3
    assert page1[0].name == "User0"

    page2 = TestUser.query().order_by("age").limit(3).offset(3).all()
    assert len(page2) == 3
    assert page2[0].name == "User3"
    teardown()


def test_query_count():
    setup()
    TestUser.create(name="A", email="count_a@test.com")
    TestUser.create(name="B", email="count_b@test.com")
    TestUser.create(name="C", email="count_c@test.com")

    count = TestUser.query().count()
    assert count == 3
    teardown()


def test_query_exists():
    setup()
    TestUser.create(name="Exists", email="exists@test.com")

    assert TestUser.query().filter(name="Exists").exists()
    assert not TestUser.query().filter(name="NoSuch").exists()
    teardown()


def test_query_update():
    setup()
    TestUser.create(name="Old", email="update@test.com", age=20)
    TestUser.query().filter(name="Old").update(age=99)

    user = TestUser.query().filter(email="update@test.com").first()
    assert user.age == 99
    teardown()


def test_query_delete():
    setup()
    TestUser.create(name="Del1", email="del1@test.com")
    TestUser.create(name="Del2", email="del2@test.com")

    deleted = TestUser.query().filter(name="Del1").delete()
    assert deleted == 1
    assert TestUser.query().count() == 1
    teardown()


def test_boolean_field():
    setup()
    user = TestUser.create(name="Bool", email="bool@test.com", active=True)
    fetched = TestUser.get(user.id)
    assert fetched.active is True
    teardown()


def test_json_field():
    setup()
    user = TestUser.create(name="JSON", email="json@test.com", meta={"key": "value", "count": 42})
    fetched = TestUser.get(user.id)
    assert fetched.meta == {"key": "value", "count": 42}
    teardown()


def test_to_dict():
    setup()
    user = TestUser.create(name="Dict", email="dict@test.com", age=25)
    d = user.to_dict()
    assert d["name"] == "Dict"
    assert d["email"] == "dict@test.com"
    assert d["age"] == 25
    teardown()


def test_all():
    setup()
    TestUser.create(name="A", email="all_a@test.com")
    TestUser.create(name="B", email="all_b@test.com")

    users = TestUser.all()
    assert len(users) == 2
    teardown()


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
