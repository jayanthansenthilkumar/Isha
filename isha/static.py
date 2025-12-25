"""
ISHA Static Files - Serve CSS, JS, Images, etc.

Handles static file serving with proper MIME types.
"""

import mimetypes
from pathlib import Path
from typing import Optional
from .core import Request, Response


class StaticFiles:
    """
    Static file handler for serving CSS, JS, images, etc.
    
    Usage:
        app.mount_static("/static", "public")
    """
    
    MIME_TYPES = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'text/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject',
    }
    
    def __init__(self, url_prefix: str, directory: Path):
        """
        Initialize static file handler.
        
        Args:
            url_prefix: URL prefix (e.g., "/static")
            directory: Directory containing static files
        """
        self.url_prefix = url_prefix.rstrip('/')
        self.directory = Path(directory).resolve()
        
        if not self.directory.exists():
            self.directory.mkdir(parents=True, exist_ok=True)
    
    def serve(self, request: Request) -> Optional[Response]:
        """
        Serve a static file if the request matches.
        
        Args:
            request: The incoming request
            
        Returns:
            Response with file content or None if not a static file
        """
        # Check if request is for this static handler
        if not request.path.startswith(self.url_prefix):
            return None
        
        # Get the file path relative to static directory
        relative_path = request.path[len(self.url_prefix):].lstrip('/')
        
        if not relative_path:
            return None
        
        file_path = self.directory / relative_path
        
        # Security: prevent directory traversal
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.directory)):
                return Response("Forbidden", 403)
        except:
            return Response("Bad Request", 400)
        
        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return Response("Not Found", 404)
        
        # Read file
        try:
            # Determine content type
            content_type = self._get_content_type(file_path)
            
            # Read binary for images and other binary files
            if content_type.startswith(('image/', 'application/', 'font/')):
                content = file_path.read_bytes()
                response = Response("", content_type=content_type)
                response._binary_body = content
                return response
            else:
                content = file_path.read_text(encoding='utf-8')
                return Response(content, content_type=content_type)
                
        except Exception as e:
            return Response(f"Error reading file: {e}", 500)
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get MIME type for a file."""
        ext = file_path.suffix.lower()
        return self.MIME_TYPES.get(ext, 'application/octet-stream')
