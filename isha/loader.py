"""
ISHA Loader - The .pyisha File Handler

Loads and executes .pyisha application files.
This is what makes ISHA unique — a custom file extension
with proper module loading.
"""

import importlib.util
import importlib.machinery
import sys
from pathlib import Path
from types import ModuleType


class IshaLoadError(Exception):
    """Raised when a .pyisha file cannot be loaded."""
    pass


def load_pyisha(file_path: str) -> ModuleType:
    """
    Load a .pyisha file as a Python module.
    
    This function:
    1. Validates the file extension
    2. Loads the file as a module
    3. Returns the module for execution
    
    Args:
        file_path: Path to the .pyisha file
        
    Returns:
        The loaded module containing the ISHA app
        
    Raises:
        IshaLoadError: If the file cannot be loaded
    """
    path = Path(file_path).resolve()
    
    # Validate extension
    if path.suffix != ".pyisha":
        raise IshaLoadError(
            f"ISHA apps must use .pyisha extension.\n"
            f"Got: {path.suffix}\n"
            f"Rename your file to: {path.stem}.pyisha"
        )
    
    # Check file exists
    if not path.exists():
        raise IshaLoadError(
            f"File not found: {path}\n"
            f"Make sure the file exists and the path is correct."
        )
    
    # Check file is readable
    if not path.is_file():
        raise IshaLoadError(
            f"Not a file: {path}\n"
            f"Please provide a valid .pyisha file."
        )
    
    try:
        # Add parent directory to path for imports
        parent_dir = str(path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Read the file content
        source_code = path.read_text(encoding="utf-8")
        
        # Create a loader for the .pyisha file (treat as Python)
        loader = importlib.machinery.SourceFileLoader("isha_app", str(path))
        spec = importlib.util.spec_from_loader(
            "isha_app",
            loader,
            origin=str(path)
        )
        
        if spec is None or spec.loader is None:
            raise IshaLoadError(f"Could not create module spec for: {path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules["isha_app"] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        return module
        
    except SyntaxError as e:
        raise IshaLoadError(
            f"Syntax error in {path.name}:\n"
            f"  Line {e.lineno}: {e.msg}\n"
            f"  {e.text}"
        )
    
    except ImportError as e:
        raise IshaLoadError(
            f"Import error in {path.name}:\n"
            f"  {e}\n"
            f"Make sure all dependencies are installed."
        )
    
    except Exception as e:
        raise IshaLoadError(
            f"Error loading {path.name}:\n"
            f"  {type(e).__name__}: {e}"
        )


def validate_app(module: ModuleType) -> bool:
    """
    Validate that a loaded module contains a valid ISHA app.
    
    Args:
        module: The loaded .pyisha module
        
    Returns:
        True if valid
        
    Raises:
        IshaLoadError: If validation fails
    """
    if not hasattr(module, "app"):
        raise IshaLoadError(
            "No `app` found in your .pyisha file.\n"
            "\n"
            "Your file should contain:\n"
            "  from isha import App\n"
            "  app = App()\n"
            "\n"
            "  @app.route('/')\n"
            "  def home(req):\n"
            "      return 'Hello!'"
        )
    
    from .core import App
    
    if not isinstance(module.app, App):
        raise IshaLoadError(
            f"`app` must be an ISHA App instance.\n"
            f"Got: {type(module.app).__name__}\n"
            f"\n"
            f"Make sure you create it like:\n"
            f"  from isha import App\n"
            f"  app = App()"
        )
    
    return True
