"""
ISHA Logger - Structured Logging

Simple, colorful logging for development and production.
"""

import sys
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log levels."""
    DEBUG = ("DEBUG", "\033[36m")      # Cyan
    INFO = ("INFO", "\033[32m")        # Green
    WARNING = ("WARNING", "\033[33m")  # Yellow
    ERROR = ("ERROR", "\033[31m")      # Red
    CRITICAL = ("CRITICAL", "\033[35m") # Magenta


class Logger:
    """
    Simple structured logger with colors.
    
    Usage:
        logger = Logger(name="my-app")
        logger.info("Server started")
        logger.error("Something went wrong", {"error": str(e)})
    """
    
    def __init__(self, name: str = "isha", use_colors: bool = True, min_level: LogLevel = LogLevel.INFO):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            use_colors: Whether to use colored output
            min_level: Minimum log level to display
        """
        self.name = name
        self.use_colors = use_colors
        self.min_level = min_level
        self._reset = "\033[0m" if use_colors else ""
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level."""
        levels_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return levels_order.index(level) >= levels_order.index(self.min_level)
    
    def _format_message(self, level: LogLevel, message: str, context: dict = None) -> str:
        """Format log message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_name, color = level.value
        
        # Build message
        parts = [
            f"[{timestamp}]",
            f"{color if self.use_colors else ''}{level_name:8}{self._reset}",
            f"[{self.name}]",
            message
        ]
        
        log_line = " ".join(parts)
        
        # Add context if provided
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            log_line += f" | {context_str}"
        
        return log_line
    
    def _log(self, level: LogLevel, message: str, context: dict = None):
        """Internal log method."""
        if not self._should_log(level):
            return
        
        formatted = self._format_message(level, message, context)
        
        # Write to stderr for errors, stdout otherwise
        stream = sys.stderr if level in [LogLevel.ERROR, LogLevel.CRITICAL] else sys.stdout
        print(formatted, file=stream)
    
    def debug(self, message: str, context: dict = None):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, context: dict = None):
        """Log info message."""
        self._log(LogLevel.INFO, message, context)
    
    def warning(self, message: str, context: dict = None):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, context: dict = None):
        """Log error message."""
        self._log(LogLevel.ERROR, message, context)
    
    def critical(self, message: str, context: dict = None):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, context)


class RequestLogger:
    """
    Middleware for logging HTTP requests.
    
    Usage:
        app = App()
        request_logger = RequestLogger()
        
        @app.before
        def log_request(req):
            request_logger.log_request(req)
        
        @app.after
        def log_response(req, res):
            request_logger.log_response(req, res)
            return res
    """
    
    def __init__(self, logger: Logger = None):
        """
        Initialize request logger.
        
        Args:
            logger: Optional Logger instance to use
        """
        self.logger = logger or Logger(name="http")
        self.start_times = {}
    
    def log_request(self, request):
        """Log incoming request."""
        import time
        
        # Store start time for this request
        request_id = id(request)
        self.start_times[request_id] = time.time()
        
        self.logger.info(
            f"{request.method} {request.path}",
            {
                "query": request.query_string if request.query_string else None,
                "content_type": request.headers.get("Content-Type"),
            }
        )
    
    def log_response(self, request, response):
        """Log response."""
        import time
        
        request_id = id(request)
        start_time = self.start_times.get(request_id)
        
        if start_time:
            duration_ms = (time.time() - start_time) * 1000
            del self.start_times[request_id]
        else:
            duration_ms = 0
        
        # Choose log level based on status code
        if response.status < 400:
            log_func = self.logger.info
        elif response.status < 500:
            log_func = self.logger.warning
        else:
            log_func = self.logger.error
        
        log_func(
            f"{request.method} {request.path} → {response.status}",
            {
                "duration_ms": f"{duration_ms:.2f}",
                "content_type": response.content_type,
            }
        )


def enable_request_logging(app, logger: Logger = None):
    """
    Enable request logging on an app.
    
    Usage:
        from isha import App
        from isha.logger import enable_request_logging
        
        app = App()
        enable_request_logging(app)
    """
    request_logger = RequestLogger(logger)
    
    @app.before
    def log_request(req):
        request_logger.log_request(req)
    
    @app.after
    def log_response(req, res):
        request_logger.log_response(req, res)
        return res
    
    return request_logger


# Create a default logger instance
default_logger = Logger()
