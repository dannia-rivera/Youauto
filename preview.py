"""YouAuto Preview — serve the finder and open it in a browser."""
import csv
import http.server
import os
import sys
import time
import webbrowser
import threading
from pathlib import Path
from urllib.parse import parse_qs


PORT = 8080
DIR = Path(__file__).resolve().parent
REPORTS_CSV = DIR / "reports.csv"

# Ensure reports CSV exists with header
if not REPORTS_CSV.exists():
    with open(REPORTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "location", "comment"])


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve static files with no-cache headers and handle /report POST."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_POST(self):
        if self.path != "/report":
            self.send_error(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)
        location = params.get("location", [""])[0].strip()
        comment = params.get("comment", [""])[0].strip()

        if not comment:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Comment is required.")
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(REPORTS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, location, comment])

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Report submitted. Thank you!")


def main():
    os.chdir(DIR)
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("", PORT), Handler)
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
