"""
Tests for Isha Template Engine.
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isha.template import TemplateEngine


# Create a temp directory for template files
TEMPLATE_DIR = tempfile.mkdtemp()


def write_template(name, content):
    """Helper: write a template file."""
    filepath = os.path.join(TEMPLATE_DIR, name)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


def test_variable_substitution():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render_string("Hello, {{ name }}!", name="World")
    assert result == "Hello, World!"


def test_nested_variable():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    user = {"name": "Alice", "age": 30}
    result = engine.render_string("{{ user.name }} is {{ user.age }}", user=user)
    assert result == "Alice is 30"


def test_filter_upper():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render_string("{{ name|upper }}", name="alice")
    assert result == "ALICE"


def test_filter_lower():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render_string("{{ name|lower }}", name="ALICE")
    assert result == "alice"


def test_filter_truncate():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render_string("{{ text|truncate(10) }}", text="Hello World, this is long")
    assert result == "Hello Worl..."


def test_for_loop():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% for item in items %}{{ item }} {% endfor %}"
    result = engine.render_string(template, items=["a", "b", "c"])
    assert "a" in result
    assert "b" in result
    assert "c" in result


def test_for_loop_index():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% for item in items %}{{ loop.index }}:{{ item }} {% endfor %}"
    result = engine.render_string(template, items=["x", "y"])
    assert "1:x" in result
    assert "2:y" in result


def test_if_true():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% if show %}Visible{% endif %}"
    result = engine.render_string(template, show=True)
    assert "Visible" in result


def test_if_false():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% if show %}Visible{% endif %}"
    result = engine.render_string(template, show=False)
    assert "Visible" not in result


def test_if_else():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% if logged_in %}Welcome{% else %}Login{% endif %}"
    result1 = engine.render_string(template, logged_in=True)
    assert "Welcome" in result1

    result2 = engine.render_string(template, logged_in=False)
    assert "Login" in result2


def test_if_comparison():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    template = "{% if age > 18 %}Adult{% else %}Minor{% endif %}"
    result = engine.render_string(template, age=25)
    assert "Adult" in result


def test_comment_removal():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render_string("Hello{# this is hidden #} World")
    assert result == "Hello World"


def test_template_inheritance():
    write_template("base.html", """
<html>
<head><title>{% block title %}Default{% endblock %}</title></head>
<body>{% block content %}Base Content{% endblock %}</body>
</html>
""")
    write_template("child.html", """
{% extends "base.html" %}
{% block title %}Child Page{% endblock %}
{% block content %}Child Content{% endblock %}
""")

    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render("child.html")
    assert "Child Page" in result
    assert "Child Content" in result
    assert "Base Content" not in result


def test_include():
    write_template("_header.html", "<header>My Header</header>")
    write_template("page.html", '{% include "_header.html" %}<main>Content</main>')

    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=False)
    result = engine.render("page.html")
    assert "My Header" in result
    assert "Content" in result


def test_auto_escape():
    engine = TemplateEngine(TEMPLATE_DIR, auto_escape=True)
    result = engine.render_string("{{ content }}", content="<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


# Cleanup
def cleanup():
    shutil.rmtree(TEMPLATE_DIR, ignore_errors=True)


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

    cleanup()
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
