"""Keyless Claude Code tool-loop test. HTTP responses are scripted."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

if Path("/opt/fedops/worker.py").exists():
    sys.path.insert(0, "/opt/fedops")
import worker


def replay(work, emit=None, wait_first=False):
    first_request = True
    class Messages(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            nonlocal first_request
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "count_tokens" in self.path:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"input_tokens":10}')
                return
            if first_request and wait_first:
                first_request = False
                print("모의 서버가 첫 모델 요청을 받았습니다. 응답을 10초 보류합니다.", file=sys.stderr, flush=True)
                time.sleep(10)
                print("모의 서버가 첫 응답 전송을 시작합니다.", file=sys.stderr, flush=True)
            results = [b for m in request["messages"] for b in m["content"]
                       if isinstance(b, dict) and b.get("type") == "tool_result"]
            path = str(work / worker.TARGET)
            message = dict(id="msg_replay", type="message", role="assistant", model=request["model"],
                           content=[], stop_reason=None, stop_sequence=None,
                           usage={"input_tokens": 10, "output_tokens": 1})
            reason = "end_turn"
            block = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": "Scripted tool replay completed."}
            if len(results) < 2:
                name = "Read" if not results else "Edit"
                args = {"file_path": path}
                if results:
                    line = "        weighted_performance = sum(performances)"
                    args.update(old_string=line, new_string=
                                "        total_examples = sum(n for n, m in metrics if key in m)\n" + line)
                block = dict(type="tool_use", id="toolu_" + name, name=name, input={})
                delta = dict(type="input_json_delta", partial_json=json.dumps(args))
                reason = "tool_use"
            events = [
                dict(type="message_start", message=message),
                dict(type="content_block_start", index=0, content_block=block),
                dict(type="content_block_delta", index=0, delta=delta),
                dict(type="content_block_stop", index=0),
                dict(type="message_delta", delta={"stop_reason": reason, "stop_sequence": None},
                     usage={"output_tokens": 3}),
                dict(type="message_stop"),
            ]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for event in events:
                self.wfile.write(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode())

    with ThreadingHTTPServer(("127.0.0.1", 0), Messages) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        real_run = subprocess.Popen

        def local_transport(argv, **kwargs):
            if argv[0] == "claude":
                kwargs["env"].update(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{server.server_port}",
                                     NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
            return real_run(argv, **kwargs)

        try:
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "offline-test-value"}), \
                    patch.object(subprocess, "Popen", local_transport):
                report = worker.execute({"mode": "edit", "model": "anthropic/claude-sonnet-4.6",
                                         "brief": "Run the FedOps tool replay."}, work, emit)
        finally:
            server.shutdown()
    if (report["before"]["code"] != 1 or report["after"]["code"] != 0 or
            [e["tool"] for e in report["trace"] if e["event"] == "tool_use"] != ["Read", "Edit"]):
        raise SystemExit("Replay failed")
    if emit is None:
        print("PASS · Claude Read → Edit · 기존 2개 실패 → 7개 통과 · 로컬 모의 응답")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        def emit(item):
            print(json.dumps(item), flush=True)
        replay(Path(folder), emit if "--timeline" in sys.argv else None, "--wait-first" in sys.argv)
