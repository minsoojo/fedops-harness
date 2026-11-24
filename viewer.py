"""Loopback-only viewer for sanitized tool timelines."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing

import agent
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Viewer(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in {"/brief", "/ask"}:
            self.send_error(404)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384:
                raise ValueError()
            question = json.loads(self.rfile.read(size))
            if not isinstance(question, str) or not question.strip() or len(question) > 2000:
                raise ValueError()
        except (ValueError, UnicodeError):
            self.send_error(400)
            return
        if self.path == "/ask":
            try:
                folder = agent.run_folder("ask")
                process = multiprocessing.get_context("spawn").Process(
                    target=agent.run_turn, args=(folder, "ask", question.strip()))
                process.start()
            except OSError:
                self.send_error(503)
                return
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps({"run": folder.name}).encode())
            return
        try:
            body = subprocess.check_output([sys.executable, str(ROOT / "fedops.py"),
                                            "brief", "--", question.strip()], timeout=15)
        except (subprocess.SubprocessError, OSError):
            self.send_error(500)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "viewer.html").read_bytes()
            mime = "text/html"
        elif self.path == "/graph.html":
            body = (ROOT / "evidence/fedops-graph.html").read_bytes()
            mime = "text/html"
        elif self.path == "/vis-network.min.js":
            body = (ROOT / "ui-assets/vis-network.min.js").read_bytes()
            mime = "application/javascript"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
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
