"""Run one forked codex-exec in the question sandbox and adapt its JSONL events."""
import json
import os
from pathlib import Path
import sys
import tempfile

from stream_loop import messages


def ask(request, work, emit, *, instructions_text, budget, repository=False, openrouter=False):
    env = os.environ.copy()
    home = work / "codex"
    home.mkdir(mode=0o700)
    env.update(CODEX_HOME=str(home), HOME=str(work), FEDOPS_ASK="1", FEDOPS_REQUEST_LIMIT=str(budget))
    instructions = home / "instructions.md"
    instructions.write_text(instructions_text)
    if openrouter:
        provider, name, endpoint, credential = "openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"
    else:
        provider, name, endpoint, credential = "fedops-openai", "OpenAI API", "https://api.openai.com/v1", "OPENAI_API_KEY"
    config = f'model_instructions_file = "{instructions}"\n' + f"""
model_provider = "{provider}"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
[model_providers.{provider}]
name = "{name}"
base_url = "{endpoint}"
env_key = "{credential}"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0
supports_websockets = false
[features]
code_mode = false
code_mode_only = false
tool_search = false
multi_agent = false
multi_agent_v2 = false
shell_tool = false
"""
    if repository:
        config += """
[mcp_servers.repository]
command = "/usr/local/bin/python3"
args = ["-I", "/opt/fedops/repository_mcp.py"]
required = true
default_tools_approval_mode = "approve"
"""
    (home / "config.toml").write_text(config)
    revision = Path("/opt/fedops/codex-revision").read_text().strip()
    last_message = work / "answer"
    cmd = ["/usr/local/bin/fedops-codex", "--json", "--ephemeral", "--skip-git-repo-check",
           "--model", request["model"], "-o", str(last_message), "-"]
    trace, calls, blocks = [], {}, []
    session, usage, number, failure = None, None, 0, None
    for packet in messages(cmd, request["brief"], 300, cwd=work, env=env):
        kind = packet.get("type")
        if kind == "thread.started":
            session = packet["thread_id"]
        elif kind == "fedops.request":
            number = packet["round"]
            blocks = []
            emit(event="model_request", round=number)
        elif kind == "fedops.output":
            item = packet["item"]
            if item["type"] == "message" and item.get("role") == "assistant":
                blocks.extend({"type": "text", "text": part["text"]} for part in item["content"]
                              if part["type"] == "output_text")
            elif item["type"] == "function_call":
                call = item["call_id"]
                calls[call] = number
                try:
                    arguments = json.loads(item["arguments"])
                except ValueError:
                    arguments = item["arguments"]
                blocks.append({"type": "tool_use", "name": item["name"].split("__")[-1],
                               "id": call, "input": arguments})
        elif kind == "fedops.response":
            emit(event="model_response", round=number, blocks=blocks)
        elif kind in {"item.started", "item.completed"} and packet["item"]["type"] == "mcp_tool_call":
            item = packet["item"]
            call = item["id"]
            fields = {"event": "tool_use", "id": call, "tool": item["tool"]} if kind == "item.started" else {
                "event": "tool_result", "id": call,
                "error": item["status"] != "completed" or bool(item.get("error"))}
            trace.append(fields)
            emit(**fields, round=calls.get(call, number))
        elif kind == "turn.completed":
            usage = packet["usage"]
        elif kind in {"error", "turn.failed"}:
            message = packet.get("message") or packet.get("error", {}).get("message")
            if message and message != failure:
                failure = message
                print(failure.replace(env.get(credential) or "\0", "[redacted]")[:1200],
                      file=sys.stderr, flush=True)
    if usage is None or not number or not last_message.is_file() or not last_message.read_text().strip():
        raise ValueError("Codex 질문 실행에서 최종 답변을 받지 못했습니다")
    return dict(result=last_message.read_text().strip(), session=session, usage=usage,
                trace=trace, engine="codex", revision=revision)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(dir="/sandbox", prefix="fedops-ask-") as folder:
        def emit(**fields):
            print(json.dumps({"progress": fields}), flush=True)
        from research import investigate
        print(json.dumps(investigate(json.load(sys.stdin), Path(folder), ask, emit)), flush=True)
