"""
ISHA Forms - Form Handling and Validation

Simple form parsing and validation utilities.
"""

from typing import Dict, Any, List, Optional, Callable
from urllib.parse import parse_qs


class FormError(Exception):
    """Raised when form validation fails."""
    pass


class Field:
    """
    Base form field.
    
    Usage:
        name = Field(required=True, min_length=2)
        email = Field(required=True, validator=lambda v: '@' in v)
    """
    
    def __init__(self, required: bool = False, default: Any = None,
                 validator: Optional[Callable[[Any], bool]] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        """
        Initialize field.
        
        Args:
            required: Whether field is required
            default: Default value if not provided
            validator: Custom validation function
            min_length: Minimum string length
            max_length: Maximum string length
        """
        self.required = required
        self.default = default
        self.validator = validator
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate field value.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if required
        if self.required and (value is None or value == ""):
            return False, "This field is required"
        
        # If not required and empty, use default
        if (value is None or value == "") and not self.required:
            return True, None
        
        # Check length constraints
        if isinstance(value, str):
            if self.min_length and len(value) < self.min_length:
                return False, f"Must be at least {self.min_length} characters"
            if self.max_length and len(value) > self.max_length:
                return False, f"Must be at most {self.max_length} characters"
        
        # Custom validator
        if self.validator:
            try:
                if not self.validator(value):
                    return False, "Invalid value"
            except Exception as e:
                return False, str(e)
        
        return True, None


class Form:
    """
    Form handler with validation.
    
    Usage:
        class LoginForm(Form):
            username = Field(required=True, min_length=3)
            password = Field(required=True, min_length=8)
        
        form = LoginForm(request.body)
        if form.is_valid():
            print(form.data["username"])
    """
    
    def __init__(self, form_data: str = ""):
        """
        Initialize form with POST data.
        
        Args:
            form_data: URL-encoded form data from request body
        """
        self.raw_data = form_data
        self.data: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
        self._parse_data()
    
    def _parse_data(self) -> None:
        """Parse URL-encoded form data."""
        if not self.raw_data:
            return
        
        parsed = parse_qs(self.raw_data)
        
        # Get single values (not lists)
        for key, values in parsed.items():
            self.data[key] = values[0] if values else ""
    
    def is_valid(self) -> bool:
        """
        Validate all form fields.
        
        Returns:
            True if all fields are valid
        """
        self.errors.clear()
        
        # Get all field definitions from class
        fields = {}
        for name in dir(self.__class__):
            attr = getattr(self.__class__, name)
            if isinstance(attr, Field):
                fields[name] = attr
        
        # Validate each field
        for name, field in fields.items():
            value = self.data.get(name)
            
            # Use default if not provided
            if value is None and field.default is not None:
                value = field.default
                self.data[name] = value
            
            # Validate
            is_valid, error = field.validate(value)
            if not is_valid:
                self.errors[name] = error
        
        return len(self.errors) == 0
    
    def get_error(self, field: str) -> Optional[str]:
        """Get error message for a field."""
        return self.errors.get(field)


def parse_form_data(body: str) -> Dict[str, str]:
    """
    Parse URL-encoded form data.
    
    Args:
        body: Request body with form data
        
    Returns:
        Dictionary of form fields
    """
    if not body:
        return {}
    
    parsed = parse_qs(body)
    return {key: values[0] if values else "" for key, values in parsed.items()}
