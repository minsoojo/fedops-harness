"""Loopback-only viewer for sanitized tool timelines."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Viewer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "viewer.html").read_bytes()
            mime = "text/html"
        elif self.path == "/runs":
            runs = {}
            for file in sorted((ROOT / "runs").glob("**/timeline.jsonl"),
                               key=lambda path: path.stat().st_mtime, reverse=True):
                events = []
                for line in file.read_text().splitlines():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        break  # Writer may still be appending the last line.
                runs[str(file.parent.relative_to(ROOT / "runs"))] = events
            body = json.dumps(runs).encode()
            mime = "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8765), Viewer) as server:
        print("http://127.0.0.1:8765", flush=True)
        server.serve_forever()
