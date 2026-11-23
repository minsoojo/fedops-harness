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


def execute(request, work):
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
    result = subprocess.run(args, input=prompt, text=True, capture_output=True,
                            cwd=work, env=env, timeout=300)
    if result.returncode:
        raise RuntimeError("Claude 종료 코드 " + str(result.returncode) + " · " +
                           (result.stderr or result.stdout)[-1500:].replace(token, "[redacted]"))
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if not events or events[-1].get("type") != "result":
        raise RuntimeError("Claude 최종 결과 이벤트가 없습니다.")
    answer = events[-1]
    trace = []
    for event in events:
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                trace.append({"event": "tool_use", "id": block.get("id"), "tool": block.get("name")})
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                trace.append({"event": "tool_result", "id": block.get("tool_use_id"),
                              "error": bool(block.get("is_error"))})
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
        print(json.dumps(execute(json.load(sys.stdin), Path(folder)), ensure_ascii=False))
