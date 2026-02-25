"""
Isha Server — Built-in ASGI development server and raw socket server.
"""

import asyncio
import logging
import signal
import sys

logger = logging.getLogger("isha.server")


def run_server(app, host="127.0.0.1", port=8000):
    """
    Run the Isha application using asyncio-based ASGI server.
    For production, use Uvicorn or Gunicorn with UvicornWorker.
    """
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info" if not app.debug else "debug")
    except ImportError:
        logger.info("Uvicorn not found. Using built-in development server.")
        asyncio.run(_run_builtin_server(app, host, port))


async def _run_builtin_server(app, host, port):
    """
    A minimal async HTTP/1.1 server for development.
    Translates raw HTTP into ASGI scope/receive/send.
    """
    server = await asyncio.start_server(
        lambda r, w: _handle_connection(app, r, w),
        host, port,
    )

    logger.info(f"Built-in server listening on {host}:{port}")

    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        pass


async def _handle_connection(app, reader, writer):
    """Handle a single HTTP connection."""
    try:
        # Read the request (up to 64KB for headers + body)
        data = b""
        while True:
            chunk = await asyncio.wait_for(reader.read(65536), timeout=30.0)
            data += chunk
            if not chunk or b"\r\n\r\n" in data:
                break

        if not data:
            writer.close()
            return

        # Check for Content-Length and read remaining body
        header_end = data.find(b"\r\n\r\n")
        if header_end != -1:
            headers_section = data[:header_end].decode("utf-8", errors="replace")
            for line in headers_section.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
                    body_received = len(data) - header_end - 4
                    while body_received < content_length:
                        chunk = await asyncio.wait_for(reader.read(65536), timeout=30.0)
                        if not chunk:
                            break
                        data += chunk
                        body_received += len(chunk)
                    break

        # Parse raw HTTP into ASGI scope
        scope, body = _parse_http_to_scope(data)
        if scope is None:
            writer.close()
            return

        # Create ASGI receive/send callables
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        response_started = False
        response_headers = []
        response_status = 200
        response_body = b""

        async def send(message):
            nonlocal response_started, response_headers, response_status, response_body

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message["status"]
                response_headers = message.get("headers", [])

            elif message["type"] == "http.response.body":
                body_chunk = message.get("body", b"")
                response_body_parts = [response_body, body_chunk]

                if not message.get("more_body", False):
                    # Write the complete response
                    full_body = b"".join(response_body_parts)
                    status_text = _get_status_text(response_status)
                    response_line = f"HTTP/1.1 {response_status} {status_text}\r\n"

                    header_lines = []
                    has_content_length = False
                    for h_name, h_value in response_headers:
                        name = h_name.decode("latin-1") if isinstance(h_name, bytes) else h_name
                        value = h_value.decode("latin-1") if isinstance(h_value, bytes) else h_value
                        header_lines.append(f"{name}: {value}")
                        if name.lower() == "content-length":
                            has_content_length = True

                    if not has_content_length:
                        header_lines.append(f"content-length: {len(full_body)}")

                    header_lines.append("connection: close")

                    raw_response = response_line + "\r\n".join(header_lines) + "\r\n\r\n"
                    writer.write(raw_response.encode("utf-8") + full_body)
                    await writer.drain()

        # Call the ASGI app
        try:
            await app(scope, receive, send)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = f"HTTP/1.1 500 Internal Server Error\r\ncontent-type: text/plain\r\n\r\n500 Internal Server Error"
            writer.write(error_response.encode("utf-8"))
            await writer.drain()

    except asyncio.TimeoutError:
        pass
    except ConnectionResetError:
        pass
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _parse_http_to_scope(raw_data):
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

        # Parse request line
        parts = lines[0].split(" ", 2)
        if len(parts) < 2:
            return None, b""

        method = parts[0]
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
            "server": ("127.0.0.1", 8000),
        }

        return scope, body

    except Exception as e:
        logger.error(f"Failed to parse HTTP request: {e}")
        return None, b""


def _get_status_text(status_code):
    """Get HTTP status text for a code."""
    from .response import HTTP_STATUS_CODES
    return HTTP_STATUS_CODES.get(status_code, "Unknown")
