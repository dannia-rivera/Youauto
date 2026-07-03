"""YouAuto Preview — serve the finder and open it in a browser."""
import http.server
import os
import sys
import webbrowser
import threading
from pathlib import Path


PORT = 8080
DIR = Path(__file__).resolve().parent


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files with no-cache headers so refreshes always get fresh data."""
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    os.chdir(DIR)
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("", PORT), NoCacheHandler)
    threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}/preview.html")).start()
    print(f"Serving {DIR} on http://localhost:{PORT}/preview.html")
    print("  Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
