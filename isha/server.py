"""
Isha Server — Built-in async HTTP/1.1 development server.

For production, use uvicorn or hypercorn:
    uvicorn app:app --host 0.0.0.0 --port 8000
    hypercorn app:app --bind 0.0.0.0:8000
"""

import asyncio
import logging
import sys

logger = logging.getLogger("isha.server")


def run_server(app, host="127.0.0.1", port=8000):
    """
    Run the Isha application.
    Tries uvicorn first (production-quality), falls back to built-in dev server.
    """
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info" if not getattr(app, "debug", False) else "debug")
    except ImportError:
        logger.info("uvicorn not installed — using built-in development server.")
        logger.info("For production, install uvicorn: pip install isha[uvicorn]")
        try:
            asyncio.run(_run_builtin_server(app, host, port))
        except KeyboardInterrupt:
            pass


async def _run_builtin_server(app, host, port):
    """
    Minimal async HTTP/1.1 development server.
    Translates raw HTTP into ASGI scope/receive/send.
    """
    server = await asyncio.start_server(
        lambda r, w: _handle_connection(app, r, w),
        host, port,
    )

    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"  Listening on: {addrs}")
    print(f"  (built-in dev server — not for production)\n")

    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        pass


async def _handle_connection(app, reader, writer):
    """Handle a single HTTP connection."""
    try:
        # Read headers first
        data = b""
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(65536), timeout=30.0)
            except asyncio.TimeoutError:
                writer.close()
                return
            if not chunk:
                writer.close()
                return
            data += chunk
            if b"\r\n\r\n" in data:
                break

        # Find where headers end and body begins
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            writer.close()
            return

        # Check Content-Length for remaining body data
        headers_section = data[:header_end].decode("utf-8", errors="replace")
        content_length = 0
        for line in headers_section.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                break

        body_start = header_end + 4
        body_received = len(data) - body_start

        # Read remaining body if needed
        while body_received < content_length:
            try:
                chunk = await asyncio.wait_for(reader.read(65536), timeout=30.0)
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            data += chunk
            body_received += len(chunk)

        # Extract peer info
        try:
            peername = writer.get_extra_info("peername", ("127.0.0.1", 0))
        except Exception:
            peername = ("127.0.0.1", 0)

        # Extract server socket info
        try:
            sockname = writer.get_extra_info("sockname", ("127.0.0.1", 8000))
        except Exception:
            sockname = ("127.0.0.1", 8000)

        # Parse raw HTTP into ASGI scope
        scope, body = _parse_http_to_scope(data, client=peername, server=sockname)
        if scope is None:
            writer.close()
            return

        # Create ASGI receive callable
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            # After body is sent, just wait (simulates client still connected)
            await asyncio.sleep(3600)
            return {"type": "http.disconnect"}

        # Create ASGI send callable
        response_started = False
        response_status = 200
        response_headers = []
        response_body_parts = []

        async def send(message):
            nonlocal response_started, response_status, response_headers

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message["status"]
                response_headers = message.get("headers", [])

            elif message["type"] == "http.response.body":
                body_chunk = message.get("body", b"")
                if body_chunk:
                    response_body_parts.append(body_chunk)

                if not message.get("more_body", False):
                    # Build and send the complete HTTP response
                    full_body = b"".join(response_body_parts)

                    status_text = _get_status_text(response_status)
                    response_line = f"HTTP/1.1 {response_status} {status_text}\r\n"

                    header_lines = []
                    has_content_length = False
                    has_connection = False

                    for h_name, h_value in response_headers:
                        name = h_name.decode("latin-1") if isinstance(h_name, bytes) else h_name
                        value = h_value.decode("latin-1") if isinstance(h_value, bytes) else h_value
                        header_lines.append(f"{name}: {value}")
                        if name.lower() == "content-length":
                            has_content_length = True
                        if name.lower() == "connection":
                            has_connection = True

                    if not has_content_length:
                        header_lines.append(f"content-length: {len(full_body)}")
                    if not has_connection:
                        header_lines.append("connection: close")

                    raw_response = response_line + "\r\n".join(header_lines) + "\r\n\r\n"
                    writer.write(raw_response.encode("utf-8") + full_body)
                    await writer.drain()

        # Call the ASGI application
        try:
            await app(scope, receive, send)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            if not response_started:
                error_body = b"500 Internal Server Error"
                error_response = (
                    b"HTTP/1.1 500 Internal Server Error\r\n"
                    b"content-type: text/plain; charset=utf-8\r\n"
                    b"content-length: " + str(len(error_body)).encode() + b"\r\n"
                    b"connection: close\r\n"
                    b"\r\n" + error_body
                )
                writer.write(error_response)
                await writer.drain()

        # Log the request
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        logger.info(f"{peername[0]} - {method} {path} → {response_status}")

    except ConnectionResetError:
        pass
    except BrokenPipeError:
        pass
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _parse_http_to_scope(raw_data, client=("127.0.0.1", 0), server=("127.0.0.1", 8000)):
    """Parse raw HTTP data into an ASGI HTTP scope."""
    try:
        header_end = raw_data.find(b"\r\n\r\n")
        if header_end == -1:
            return None, b""

        header_section = raw_data[:header_end].decode("utf-8", errors="replace")
        body = raw_data[header_end + 4:]

        lines = header_section.split("\r\n")
        if not lines:
            return None, b""

        # Parse request line: METHOD PATH HTTP/VERSION
        parts = lines[0].split(" ", 2)
        if len(parts) < 2:
            return None, b""

        method = parts[0].upper()
        full_path = parts[1]
        http_version = parts[2] if len(parts) > 2 else "HTTP/1.1"

        # Split path and query string
        if "?" in full_path:
            path, query_string = full_path.split("?", 1)
        else:
            path, query_string = full_path, ""

        # Parse headers
        headers = []
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers.append([
                    key.strip().lower().encode("latin-1"),
                    value.strip().encode("latin-1"),
                ])

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": http_version.split("/")[-1] if "/" in http_version else "1.1",
            "method": method,
            "path": path,
            "query_string": query_string.encode("utf-8"),
            "root_path": "",
            "scheme": "http",
            "headers": headers,
            "server": server,
            "client": client,
        }

        return scope, body

    except Exception as e:
        logger.error(f"Failed to parse HTTP request: {e}")
        return None, b""


def _get_status_text(status_code):
    """Get HTTP status text for a status code."""
    from .response import HTTP_STATUS_CODES
    return HTTP_STATUS_CODES.get(status_code, "Unknown")
