"""One fresh Claude Code process per request. Runs inside the OpenShell sandbox."""
import ast
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from queue import Queue
from stream_loop import messages

APP = Path(__file__).resolve().parent
TARGET = "src/python/fedops/simulation/fl_strategy/aggregation.py"
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "current": {"type": "number"}, "agreed": {"type": ["number", "null"]},
        "reported_zero": {"type": ["number", "null"]}, "source": {"type": ["string", "null"]},
    },
    "required": ["current", "agreed", "reported_zero", "source"],
}


def tests(target):
    result = subprocess.run([sys.executable, "-I", "-B", str(APP / "check.py"), str(target)],
                            capture_output=True, text=True, timeout=30)
    return {"code": result.returncode, "log": result.stdout + result.stderr}


class RoundRecorder:
    """Publish completed top-level messages and correlate tool returns by call ID."""

    def __init__(self, emit):
        self.emit = emit
        self.lock = threading.Lock()
        self.requests = Queue()
        self.sent = 0
        self.current = None
        self.blocks = []
        self.calls = {}

    def publish(self, event, **fields):
        with self.lock:
            self.emit(dict(event=event, **fields))

    def observe_request(self, line):
        if line.rstrip().partition(" ")[2] == "[DEBUG] [API REQUEST] /v1/messages source=sdk":
            self.sent += 1
            self.publish("model_request", round=self.sent)
            self.requests.put(self.sent)

    def observe(self, packet):
        if packet.get("parent_tool_use_id"):
            return
        kind = packet.get("type")
        stream = packet.get("event", {})
        if kind == "stream_event" and stream.get("type") == "message_start":
            # stdout and stderr are drained independently. Consume starts in send order.
            self.current = self.requests.get(timeout=5)
            self.blocks = []
        elif kind == "assistant" and self.current is not None:
            for block in packet.get("message", {}).get("content", []):
                if block["type"] == "text":
                    self.blocks.append({"type": "text", "text": block["text"]})
                elif block["type"] == "tool_use":
                    self.blocks.append({key: block[key] for key in ("type", "id", "name", "input")})
                    self.calls[block["id"]] = self.current
        elif kind == "stream_event" and stream.get("type") == "message_stop" and self.current is not None:
            self.publish("model_response", round=self.current, blocks=self.blocks)
            self.current = None

    def tool_event(self, item):
        number = self.calls.get(item["id"])
        self.publish(**item, **({"round": number} if number is not None else {}))


def execute(request, work, emit=None):
    mode = request["mode"]
    if mode not in {"ask", "recall", "edit"}:
        raise ValueError("unknown task")
    env = os.environ.copy()
    token = env.pop("OPENROUTER_API_KEY", "")
    if not token:
        raise ValueError("OpenRouter provider credential missing")
    model = request["model"]
    env.update(ANTHROPIC_BASE_URL="https://openrouter.ai/api", ANTHROPIC_AUTH_TOKEN=token,
               ANTHROPIC_API_KEY="", ANTHROPIC_DEFAULT_HAIKU_MODEL=model,
               ANTHROPIC_DEFAULT_SONNET_MODEL=model, ANTHROPIC_DEFAULT_OPUS_MODEL=model,
               CLAUDE_CONFIG_DIR=str(work / ".claude-config"), DISABLE_AUTOUPDATER="1",
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
    target = work / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(APP / "evidence/aggregation.py", target)
    shutil.copyfile(APP / "check.py", work / "check.py")
    prompt = request["brief"] + "\n작업 복사본의 집계 코드 위치: " + TARGET
    toolset = "Read"
    report = {}
    if mode == "edit":
        report["before"] = tests(target)
        if report["before"]["code"] != 1 or "FAILED (failures=2)" not in report["before"]["log"]:
            raise ValueError("unexpected baseline test result")
        # The independent grader is baked into the image. The agent may run a copy.
        toolset = "Read,Edit,Bash"
        prompt += ("\nweighted_average 본문만 수정하고, python3 -I -B check.py " + TARGET
                   + " 로 검사하세요. 실패하면 고치고 다시 검사하세요.")
    args = ["claude", "-p", "--no-session-persistence", "--output-format", "stream-json", "--verbose",
            "--model", model, "--tools", toolset, "--permission-mode", "dontAsk",
            "--allowedTools", "Read"]
    if mode == "edit":
        args += ["Edit", "Bash(python3 -I -B check.py " + TARGET + ")"]
    if mode == "recall":
        args += ["--json-schema", json.dumps(SCHEMA)]
        prompt += "\ncurrent는 현재 구현, agreed는 합의 결과, reported_zero는 B가 0을 보고할 때 합의 결과입니다. 저장된 결정이 없으면 합의 관련 필드와 source는 null로 답하세요."
    answer = None
    trace = []
    recorder = RoundRecorder(emit) if emit else None
    if recorder:
        args.extend(["--debug-to-stderr", "--include-partial-messages"])
    for event in messages(args, prompt, 300, cwd=work, env=env, stderr=subprocess.DEVNULL,
                          on_stderr=recorder.observe_request if recorder else None):
        if recorder:
            recorder.observe(event)
        if event.get("type") == "result":
            answer = event
        previous = len(trace)
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                trace.append({"event": "tool_use", "id": block.get("id"), "tool": block.get("name")})
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                trace.append({"event": "tool_result", "id": block.get("tool_use_id"),
                              "error": bool(block.get("is_error"))})
        if emit:
            for item in trace[previous:]:
                recorder.tool_event(item)
    if answer is None:
        raise RuntimeError("Claude 최종 결과 이벤트가 없습니다.")
    report["trace"] = trace
    if answer.get("is_error"):
        raise RuntimeError(str(answer.get("result", "Claude error")).replace(token, "[redacted]"))
    report.update(result=answer.get("result"), structured=answer.get("structured_output"),
                  usage=answer.get("usage"), session=answer.get("session_id"))
    if mode == "edit":
        base = APP / "evidence/aggregation.py"
        old, new = base.read_text(), target.read_text()
        def surrounding(code):
            lines = code.splitlines(keepends=True)
            definitions = [node for node in ast.parse(code).body
                           if isinstance(node, ast.FunctionDef) and node.name == "weighted_average"]
            if len(definitions) != 1:
                raise ValueError("weighted_average 정의 개수 오류")
            func = definitions[0]
            return "".join(lines[:func.lineno]), "".join(lines[func.end_lineno:]).rstrip("\n")
        if surrounding(old) != surrounding(new):
            raise ValueError("weighted_average 범위 밖의 변경")
        report["patch"] = "".join(difflib.unified_diff(
            old.splitlines(True), new.rstrip("\n").splitlines(True), "a/" + TARGET, "b/" + TARGET))
        report["after"] = tests(target)
    return report


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(dir="/sandbox", prefix="fedops-") as folder:
        request = json.load(sys.stdin)
        def emit(item):
            print(json.dumps({"progress": item}), flush=True)
        print(json.dumps(execute(request, Path(folder), emit if request.get("stream") else None), ensure_ascii=False))
