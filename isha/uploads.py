"""
ISHA Uploads - File Upload Handling

Handle multipart/form-data file uploads.
"""

import os
from pathlib import Path


class UploadedFile:
    """
    Represents an uploaded file.
    
    Attributes:
        filename: Original filename
        content: File content as bytes
        content_type: MIME type
        size: File size in bytes
    """
    
    def __init__(self, filename: str, content: bytes, content_type: str = "application/octet-stream"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self.size = len(content)
    
    def save(self, destination: str):
        """
        Save the uploaded file to disk.
        
        Args:
            destination: Full path or directory to save the file
        
        Returns:
            Path to the saved file
        """
        dest_path = Path(destination)
        
        # If destination is a directory, use original filename
        if dest_path.is_dir():
            dest_path = dest_path / self.filename
        
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(dest_path, 'wb') as f:
            f.write(self.content)
        
        return str(dest_path)
    
    def __repr__(self):
        return f"<UploadedFile {self.filename} ({self.size} bytes)>"


def parse_multipart(request, upload_dir: str = None):
    """
    Parse multipart/form-data from request body.
    
    Args:
        request: Request object
        upload_dir: Optional directory to save files automatically
    
    Returns:
        Dictionary with form fields and files
        Example: {"name": "value", "file": UploadedFile(...)}
    """
    content_type = request.headers.get("Content-Type", "")
    
    if not content_type.startswith("multipart/form-data"):
        return {}
    
    # Extract boundary from Content-Type header
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part.split("=", 1)[1].strip('"')
            break
    
    if not boundary:
        return {}
    
    # Parse multipart data
    result = {}
    body_bytes = request.body.encode('utf-8') if isinstance(request.body, str) else request.body
    
    # Split by boundary
    boundary_bytes = f"--{boundary}".encode('utf-8')
    parts = body_bytes.split(boundary_bytes)
    
    for part in parts[1:-1]:  # Skip first and last (empty) parts
        if not part or part == b'--\r\n':
            continue
        
        # Split headers and content
        try:
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            
            headers_section = part[:header_end].decode('utf-8', errors='ignore')
            content = part[header_end + 4:]
            
            # Remove trailing \r\n
            if content.endswith(b'\r\n'):
                content = content[:-2]
            
            # Parse Content-Disposition header
            name = None
            filename = None
            content_type_field = "text/plain"
            
            for line in headers_section.split('\r\n'):
                if line.startswith('Content-Disposition:'):
                    # Parse name and filename
                    for item in line.split(';'):
                        item = item.strip()
                        if item.startswith('name='):
                            name = item.split('=', 1)[1].strip('"')
                        elif item.startswith('filename='):
                            filename = item.split('=', 1)[1].strip('"')
                
                elif line.startswith('Content-Type:'):
                    content_type_field = line.split(':', 1)[1].strip()
            
            if not name:
                continue
            
            # If it's a file upload
            if filename:
                uploaded_file = UploadedFile(filename, content, content_type_field)
                
                # Auto-save if upload_dir provided
                if upload_dir:
                    uploaded_file.save(upload_dir)
                
                result[name] = uploaded_file
            else:
                # Regular form field
                result[name] = content.decode('utf-8', errors='ignore')
        
        except Exception:
            continue
    
    return result


class FileUploadHandler:
    """
    Middleware to automatically handle file uploads.
    
    Usage:
        app = App()
        upload_handler = FileUploadHandler(upload_dir="uploads", max_size_mb=10)
        
        @app.before
        def handle_uploads(req):
            upload_handler.process(req)
        
        @app.post("/upload")
        def upload(req):
            file = req.files.get("file")
            if file:
                path = file.save("uploads")
                return {"uploaded": path}
    """
    
    def __init__(self, upload_dir: str = "uploads", max_size_mb: int = 10):
        """
        Initialize upload handler.
        
        Args:
            upload_dir: Directory to save uploaded files
            max_size_mb: Maximum file size in megabytes
        """
        self.upload_dir = Path(upload_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, request):
        """Process file uploads and attach to request."""
        if request.headers.get("Content-Type", "").startswith("multipart/form-data"):
            # Parse files and form data
            data = parse_multipart(request, upload_dir=None)
            
            # Separate files and form fields
            request.files = {}
            request.form_data = {}
            
            for key, value in data.items():
                if isinstance(value, UploadedFile):
                    # Check file size
                    if value.size > self.max_size_bytes:
                        continue  # Skip files that are too large
                    request.files[key] = value
                else:
                    request.form_data[key] = value
        else:
            request.files = {}
            request.form_data = {}
