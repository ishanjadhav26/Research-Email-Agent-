import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from scheduler import run_on_interval
from utils.logger import get_logger

logger = get_logger("app")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Render expects a 200 OK response on the configured health check path
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "healthy"}')

    def log_message(self, format, *args):
        # Suppress logging standard health check requests to keep logs clean
        pass

def start_http_server(port):
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Health check server listening on port {port}...")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

if __name__ == "__main__":
    # Get port from environment (Render sets this automatically)
    port = int(os.environ.get("PORT", 10000))
    
    # Start the HTTP health check server in a background thread
    server_thread = threading.Thread(target=start_http_server, args=(port,), daemon=True)
    server_thread.start()
    
    # Run the scheduler on the main thread (runs forever, executing every 24 hours)
    run_on_interval(
        topic="latest developments in artificial intelligence",
        interval_seconds=86400,  # 24 hours
    )
