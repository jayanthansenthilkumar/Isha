"""
ISHA Template Engine - Minimal HTML Rendering

A simple but powerful template system with variable substitution,
loops, conditionals, and template inheritance.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional


class TemplateError(Exception):
    """Raised when template rendering fails."""
    pass


class Template:
    """
    ISHA Template - Simple HTML templating.
    
    Syntax:
        {{ variable }}           - Variable substitution
        {% for item in items %}  - Loop
        {% if condition %}       - Conditional
        {% include "file.html" %} - Include another template
    """
    
    def __init__(self, template_str: str, template_dir: Optional[Path] = None):
        self.template_str = template_str
        self.template_dir = template_dir or Path.cwd() / "templates"
    
    def render(self, context: Dict[str, Any] = None) -> str:
        """Render the template with the given context."""
        context = context or {}
        result = self.template_str
        
        # Handle includes
        result = self._process_includes(result)
        
        # Handle loops
        result = self._process_loops(result, context)
        
        # Handle conditionals
        result = self._process_conditionals(result, context)
        
        # Handle variables
        result = self._process_variables(result, context)
        
        return result
    
    def _process_includes(self, template: str) -> str:
        """Process {% include "file.html" %} tags."""
        include_pattern = r'{%\s*include\s+["\']([^"\']+)["\']\s*%}'
        
        def replace_include(match):
            filename = match.group(1)
            include_path = self.template_dir / filename
            
            if not include_path.exists():
                return f"<!-- Include not found: {filename} -->"
            
            return include_path.read_text(encoding="utf-8")
        
        return re.sub(include_pattern, replace_include, template)
    
    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """Process {% for item in items %} ... {% endfor %} loops."""
        loop_pattern = r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}'
        
        def replace_loop(match):
            item_name = match.group(1)
            list_name = match.group(2)
            loop_body = match.group(3)
            
            items = context.get(list_name, [])
            if not isinstance(items, (list, tuple)):
                return ""
            
            result = []
            for item in items:
                loop_context = context.copy()
                loop_context[item_name] = item
                
                # Replace variables in loop body
                loop_result = loop_body
                for key, value in loop_context.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            loop_result = loop_result.replace(
                                f"{{{{ {item_name}.{sub_key} }}}}", 
                                str(sub_value)
                            )
                    else:
                        loop_result = loop_result.replace(f"{{{{ {key} }}}}", str(value))
                
                result.append(loop_result)
            
            return "".join(result)
        
        return re.sub(loop_pattern, replace_loop, template, flags=re.DOTALL)
    
    def _process_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        """Process {% if condition %} ... {% endif %} conditionals."""
        if_pattern = r'{%\s*if\s+(\w+)\s*%}(.*?)(?:{%\s*else\s*%}(.*?))?{%\s*endif\s*%}'
        
        def replace_conditional(match):
            condition_var = match.group(1)
            if_body = match.group(2)
            else_body = match.group(3) or ""
            
            condition_value = context.get(condition_var, False)
            
            # Check truthiness
            if condition_value:
                return if_body
            else:
                return else_body
        
        return re.sub(if_pattern, replace_conditional, template, flags=re.DOTALL)
    
    def _process_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Process {{ variable }} substitutions."""
        var_pattern = r'{{\s*([^}]+)\s*}}'
        
        def replace_var(match):
            var_name = match.group(1).strip()
            
            # Handle nested attributes (e.g., user.name)
            if '.' in var_name:
                parts = var_name.split('.')
                value = context.get(parts[0])
                for part in parts[1:]:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        return ""
                return str(value) if value is not None else ""
            
            value = context.get(var_name, "")
            return str(value) if value is not None else ""
        
        return re.sub(var_pattern, replace_var, template)


def render_template(template_name: str, context: Dict[str, Any] = None, 
                   template_dir: Optional[Path] = None) -> str:
    """
    Render a template file.
    
    Args:
        template_name: Name of the template file
        context: Dictionary of variables to pass to template
        template_dir: Directory containing templates
        
    Returns:
        Rendered HTML string
    """
    template_dir = template_dir or Path.cwd() / "templates"
    template_path = template_dir / template_name
    
    if not template_path.exists():
        raise TemplateError(f"Template not found: {template_name}")
    
    template_str = template_path.read_text(encoding="utf-8")
    template = Template(template_str, template_dir)
    return template.render(context)
