"""
ISHA Server - The HTTP Layer

A lightweight, threaded HTTP server built on raw sockets.
Simple. Reliable. No dependencies.
"""

import socket
import threading
from typing import Optional
from .core import App, Request, Response


class Server:
    """
    ISHA HTTP Server.
    
    A minimal HTTP/1.1 server that handles requests using
    Python's socket library with threading support.
    
    Usage:
        from isha.core import App
        from isha.server import Server
        
        app = App()
        
        @app.route("/")
        def home(req):
            return "Hello!"
        
        server = Server(app)
        server.run()
    """
    
    def __init__(self, app: App, host: str = "127.0.0.1", port: int = 8000):
        """
        Initialize the ISHA server.
        
        Args:
            app: The ISHA App instance
            host: Host address to bind to (default: 127.0.0.1)
            port: Port number to listen on (default: 8000)
        """
        self.app = app
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
    
    def handle(self, conn: socket.socket, addr: tuple):
        """
        Handle a single client connection.
        
        Args:
            conn: Client socket connection
            addr: Client address tuple (host, port)
        """
        try:
            # Receive request data
            raw = conn.recv(4096).decode("utf-8", errors="ignore")
            
            if not raw:
                conn.close()
                return
            
            # Parse request and get response
            request = Request(raw)
            response = self.app.handle_request(request)
            
            # Send response
            conn.send(response.build())
            
        except Exception as e:
            # Send error response
            error_response = Response(f"Internal Server Error: {str(e)}", 500)
            try:
                conn.send(error_response.build())
            except:
                pass
            print(f"⚠️  Error handling connection from {addr}: {e}")
        
        finally:
            conn.close()
    
    def run(self):
        """
        Start the HTTP server.
        
        This method blocks and runs forever until interrupted.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print()
            print("  ╔═══════════════════════════════════════════╗")
            print("  ║                                           ║")
            print("  ║   ✨ ISHA Framework v0.1.0                ║")
            print("  ║   Simple. Human. Timeless.                ║")
            print("  ║                                           ║")
            print(f"  ║   🌐 Running at http://{self.host}:{self.port}".ljust(46) + "║")
            print("  ║   📝 Press Ctrl+C to stop                 ║")
            print("  ║                                           ║")
            print("  ╚═══════════════════════════════════════════╝")
            print()
            
            while self.running:
                try:
                    conn, addr = self.socket.accept()
                    thread = threading.Thread(
                        target=self.handle,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                except OSError:
                    break
                    
        except KeyboardInterrupt:
            print("\n  🛑 Shutting down ISHA server...")
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop the HTTP server."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        print("  ✅ Server stopped gracefully.")
