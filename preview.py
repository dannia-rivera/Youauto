"""YouAuto Preview — serve the finder and open it in a browser."""
import http.server
import os
import sys
import webbrowser
import threading
from pathlib import Path


PORT = 8080
DIR = Path(__file__).resolve().parent


def main():
    os.chdir(DIR)
    server = http.server.HTTPServer(
        ("", PORT),
        http.server.SimpleHTTPRequestHandler,
    )
    # Open browser after a tiny delay so the server is listening
    threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}/preview.html")).start()
    print(f"✓ Serving {DIR} on http://localhost:{PORT}/preview.html")
    print("  Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✗ Shutting down.")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
