"""
Ishaa Template Engine — A mini template parser with Jinja-like syntax.

Supports:
    - Variable interpolation: {{ variable }}
    - Conditionals: {% if condition %} ... {% elif %} ... {% else %} ... {% endif %}
    - Loops: {% for item in items %} ... {% endfor %}
    - Template inheritance: {% extends "base.html" %} / {% block name %} ... {% endblock %}
    - Includes: {% include "partial.html" %}
    - Filters: {{ name|upper }} {{ price|format_currency }}
    - Comments: {# this is a comment #}
"""

import os
import re
import html
import logging
from typing import Any, Callable, Dict, Optional
from pathlib import Path

logger = logging.getLogger("ishaa.template")

# Regex patterns for template syntax
VARIABLE_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
TAG_RE = re.compile(r"\{%\s*(.+?)\s*%\}")
COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


class TemplateEngine:
    """
    The Ishaa template engine.
    
    Example:
        engine = TemplateEngine("templates/")
        html = engine.render("index.html", title="Home", items=[1, 2, 3])
    """

    def __init__(self, template_dir: str = "templates", auto_escape: bool = True):
        self.template_dir = Path(template_dir)
        self.auto_escape = auto_escape
        self._cache: Dict[str, str] = {}
        self._filters: Dict[str, Callable] = {}
        self._globals: Dict[str, Any] = {}

        # Register built-in filters
        self._register_builtin_filters()

    def _register_builtin_filters(self):
        """Register default template filters."""
        self._filters.update({
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "title": lambda x: str(x).title(),
            "strip": lambda x: str(x).strip(),
            "length": lambda x: len(x),
            "default": lambda x, d="": x if x else d,
            "escape": lambda x: html.escape(str(x)),
            "safe": lambda x: x,  # Mark as safe (no escaping)
            "int": lambda x: int(x),
            "float": lambda x: float(x),
            "str": lambda x: str(x),
            "join": lambda x, sep=", ": sep.join(str(i) for i in x),
            "first": lambda x: x[0] if x else "",
            "last": lambda x: x[-1] if x else "",
            "reverse": lambda x: list(reversed(x)) if isinstance(x, list) else str(x)[::-1],
            "truncate": lambda x, n=50: str(x)[:int(n)] + "..." if len(str(x)) > int(n) else str(x),
            "replace": lambda x, old, new: str(x).replace(old, new),
            "format_number": lambda x: f"{x:,}",
        })

    def add_filter(self, name: str, func: Callable):
        """Register a custom filter."""
        self._filters[name] = func

    def add_global(self, name: str, value: Any):
        """Add a global template variable."""
        self._globals[name] = value

    def _load_template(self, name: str) -> str:
        """Load a template file."""
        if name in self._cache:
            return self._cache[name]

        filepath = self.template_dir / name
        if not filepath.exists():
            raise FileNotFoundError(f"Template not found: {name}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        self._cache[name] = content
        return content

    def render(self, template_name: str, **context) -> str:
        """Render a template with the given context."""
        template = self._load_template(template_name)

        # Merge globals into context
        full_context = {**self._globals, **context}

        # Process template inheritance
        template = self._process_inheritance(template, full_context)

        # Process includes
        template = self._process_includes(template, full_context)

        # Remove comments
        template = COMMENT_RE.sub("", template)

        # Render the template
        return self._render_string(template, full_context)

    def render_string(self, template_string: str, **context) -> str:
        """Render a template from a string."""
        full_context = {**self._globals, **context}
        template_string = COMMENT_RE.sub("", template_string)
        return self._render_string(template_string, full_context)

    def _process_inheritance(self, template: str, context: dict) -> str:
        """Process {% extends %} and {% block %} tags."""
        extends_match = re.match(r'\{%\s*extends\s+["\'](.+?)["\']\s*%\}', template)
        if not extends_match:
            return template

        parent_name = extends_match.group(1)
        parent = self._load_template(parent_name)

        # Extract child blocks
        child_blocks = {}
        for match in re.finditer(
            r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}',
            template,
            re.DOTALL,
        ):
            child_blocks[match.group(1)] = match.group(2).strip()

        # Process parent recursively
        parent = self._process_inheritance(parent, context)

        # Replace parent blocks with child blocks
        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()
            return child_blocks.get(block_name, default_content)

        result = re.sub(
            r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}',
            replace_block,
            parent,
            flags=re.DOTALL,
        )

        return result

    def _process_includes(self, template: str, context: dict) -> str:
        """Process {% include %} tags."""
        def replace_include(match):
            include_name = match.group(1)
            try:
                included = self._load_template(include_name)
                return self._render_string(included, context)
            except FileNotFoundError:
                logger.warning(f"Include not found: {include_name}")
                return ""

        return re.sub(
            r'\{%\s*include\s+["\'](.+?)["\']\s*%\}',
            replace_include,
            template,
        )

    def _render_string(self, template: str, context: dict) -> str:
        """Core rendering: process control structures and variables."""
        # Process control structures (for, if)
        result = self._process_tags(template, context)

        # Process variable substitution
        result = self._process_variables(result, context)

        return result

    def _process_tags(self, template: str, context: dict) -> str:
        """Process {% %} control tags."""
        output = []
        pos = 0

        while pos < len(template):
            # Find next tag
            tag_match = TAG_RE.search(template, pos)
            if not tag_match:
                output.append(template[pos:])
                break

            # Add text before tag
            output.append(template[pos:tag_match.start()])
            tag_content = tag_match.group(1).strip()

            if tag_content.startswith("for "):
                # Process for loop
                block_end, rendered = self._process_for(template, tag_match.end(), tag_content, context)
                output.append(rendered)
                pos = block_end
            elif tag_content.startswith("if "):
                # Process if/elif/else
                block_end, rendered = self._process_if(template, tag_match.end(), tag_content, context)
                output.append(rendered)
                pos = block_end
            else:
                pos = tag_match.end()

        return "".join(output)

    def _process_for(self, template: str, start: int, tag: str, context: dict) -> tuple:
        """Process a for loop block."""
        # Parse: for item in items
        match = re.match(r'for\s+(\w+)\s+in\s+(.+)', tag)
        if not match:
            return start, ""

        var_name = match.group(1)
        iterable_expr = match.group(2).strip()

        # Find endfor
        depth = 1
        pos = start
        body_parts = []
        while pos < len(template) and depth > 0:
            next_tag = TAG_RE.search(template, pos)
            if not next_tag:
                break
            tag_text = next_tag.group(1).strip()
            if tag_text.startswith("for "):
                depth += 1
            elif tag_text == "endfor":
                depth -= 1
            if depth > 0:
                body_parts.append(template[pos:next_tag.end()])
                pos = next_tag.end()
            else:
                body_parts.append(template[pos:next_tag.start()])
                pos = next_tag.end()

        body = "".join(body_parts)

        # Evaluate iterable
        iterable = self._eval_expr(iterable_expr, context)
        if iterable is None:
            iterable = []

        # Render loop body
        result = []
        items = list(iterable)
        for i, item in enumerate(items):
            loop_context = dict(context)
            loop_context[var_name] = item
            loop_context["loop"] = {
                "index": i + 1,
                "index0": i,
                "first": i == 0,
                "last": i == len(items) - 1,
                "length": len(items),
            }
            rendered = self._render_string(body, loop_context)
            result.append(rendered)

        return pos, "".join(result)

    def _process_if(self, template: str, start: int, tag: str, context: dict) -> tuple:
        """Process an if/elif/else block."""
        condition_expr = tag[3:].strip()
        
        # Collect all branches: [(condition, body), ...]
        branches = []
        current_condition = condition_expr
        current_body_parts = []
        pos = start
        depth = 1

        while pos < len(template) and depth > 0:
            next_tag = TAG_RE.search(template, pos)
            if not next_tag:
                break

            tag_text = next_tag.group(1).strip()

            if tag_text.startswith("if ") and depth >= 1:
                # Nested if
                if tag_text.startswith("if ") and not (tag_text.startswith("ifdef") or tag_text.startswith("ifndef")):
                    depth += 1

            if depth == 1:
                if tag_text.startswith("elif "):
                    current_body_parts.append(template[pos:next_tag.start()])
                    branches.append((current_condition, "".join(current_body_parts)))
                    current_condition = tag_text[5:].strip()
                    current_body_parts = []
                    pos = next_tag.end()
                    continue
                elif tag_text == "else":
                    current_body_parts.append(template[pos:next_tag.start()])
                    branches.append((current_condition, "".join(current_body_parts)))
                    current_condition = "__else__"
                    current_body_parts = []
                    pos = next_tag.end()
                    continue
                elif tag_text == "endif":
                    depth -= 1
                    current_body_parts.append(template[pos:next_tag.start()])
                    branches.append((current_condition, "".join(current_body_parts)))
                    pos = next_tag.end()
                    continue

            if tag_text == "endif":
                depth -= 1
                if depth > 0:
                    current_body_parts.append(template[pos:next_tag.end()])
                    pos = next_tag.end()
                else:
                    current_body_parts.append(template[pos:next_tag.start()])
                    branches.append((current_condition, "".join(current_body_parts)))
                    pos = next_tag.end()
            else:
                current_body_parts.append(template[pos:next_tag.end()])
                pos = next_tag.end()

        # Evaluate branches
        for condition, body in branches:
            if condition == "__else__":
                return pos, self._render_string(body, context)
            if self._eval_condition(condition, context):
                return pos, self._render_string(body, context)

        return pos, ""

    def _process_variables(self, template: str, context: dict) -> str:
        """Process {{ variable }} expressions."""
        def replace_var(match):
            expr = match.group(1).strip()
            return self._eval_variable(expr, context)

        return VARIABLE_RE.sub(replace_var, template)

    def _eval_variable(self, expr: str, context: dict) -> str:
        """Evaluate a variable expression with optional filters."""
        parts = expr.split("|")
        value = self._eval_expr(parts[0].strip(), context)

        # Apply filters
        for filter_expr in parts[1:]:
            filter_expr = filter_expr.strip()
            # Parse filter name and arguments
            if "(" in filter_expr:
                fname = filter_expr[:filter_expr.index("(")]
                args_str = filter_expr[filter_expr.index("(") + 1:filter_expr.rindex(")")]
                args = [a.strip().strip("'\"") for a in args_str.split(",") if a.strip()]
            else:
                fname = filter_expr
                args = []

            filter_func = self._filters.get(fname)
            if filter_func:
                try:
                    value = filter_func(value, *args) if args else filter_func(value)
                except Exception as e:
                    logger.warning(f"Filter error ({fname}): {e}")

        # Auto-escape HTML
        if self.auto_escape and isinstance(value, str):
            # Don't escape if the 'safe' filter was used
            if "|safe" not in expr:
                value = html.escape(value)

        return str(value) if value is not None else ""

    def _eval_expr(self, expr: str, context: dict) -> Any:
        """Evaluate a simple expression (dot notation, index access)."""
        expr = expr.strip()

        # String literal
        if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]

        # Numeric literal
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Boolean/None
        if expr == "True":
            return True
        if expr == "False":
            return False
        if expr == "None":
            return None

        # Dot notation: obj.attr.subattr
        parts = expr.split(".")
        value = context.get(parts[0])

        for part in parts[1:]:
            if value is None:
                return None
            # Try index access for lists/dicts
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, (list, tuple)):
                try:
                    value = value[int(part)]
                except (ValueError, IndexError):
                    return None
            elif hasattr(value, part):
                value = getattr(value, part)
                if callable(value):
                    value = value()
            else:
                return None

        return value

    def _eval_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a conditional expression."""
        condition = condition.strip()

        # Handle 'not' prefix
        if condition.startswith("not "):
            return not self._eval_condition(condition[4:], context)

        # Handle 'and' / 'or'
        if " and " in condition:
            parts = condition.split(" and ", 1)
            return self._eval_condition(parts[0], context) and self._eval_condition(parts[1], context)
        if " or " in condition:
            parts = condition.split(" or ", 1)
            return self._eval_condition(parts[0], context) or self._eval_condition(parts[1], context)

        # Comparison operators
        for op, pyop in [("==", "=="), ("!=", "!="), (">=", ">="), ("<=", "<="), (">", ">"), ("<", "<"), (" in ", " in ")]:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._eval_expr(left.strip(), context)
                right_val = self._eval_expr(right.strip(), context)
                if op == " in ":
                    return left_val in right_val if right_val else False
                if op == "==":
                    return left_val == right_val
                if op == "!=":
                    return left_val != right_val
                if op == ">":
                    return left_val > right_val
                if op == "<":
                    return left_val < right_val
                if op == ">=":
                    return left_val >= right_val
                if op == "<=":
                    return left_val <= right_val

        # Truthiness check
        return bool(self._eval_expr(condition, context))

    def clear_cache(self):
        """Clear the template cache."""
        self._cache.clear()
