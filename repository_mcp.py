"""Read-only MCP tools for the immutable FedOps source mounted in OpenShell."""
import json
from pathlib import Path
import sys

REVISION = "3cd08420ecb5662b5b28c10a9303e28e610313b2"
ROOT = Path("/opt/fedops/repository") / REVISION
SUFFIXES = {".py", ".yaml", ".yml"}
TOOLS = [
    {"name": "Grep", "description": "Search pinned Python and YAML files for literal text. Returns path:line:source.",
     "inputSchema": {"type": "object", "properties": {"pattern": {"type": "string"}},
                     "required": ["pattern"], "additionalProperties": False}},
    {"name": "Read", "description": "Read numbered lines of a pinned Python or YAML file. Use the path from Grep.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"},
                     "offset": {"type": "integer", "minimum": 1}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}},
                     "required": ["path"], "additionalProperties": False}},
]


def invoke(name, args):
    if name == "Grep":
        pattern = args["pattern"]
        if not isinstance(pattern, str) or not 1 <= len(pattern) <= 256:
            raise ValueError("pattern must contain 1–256 characters")
        matches = []
        for path in sorted(ROOT.rglob("*")):
            if path.suffix not in SUFFIXES or not path.is_file() or not path.resolve().is_relative_to(ROOT):
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if pattern in line:
                    matches.append(f"{path.relative_to(ROOT)}:{number}: {line[:400]}")
                    if len(matches) == 50:
                        return "\n".join(matches)
        return "\n".join(matches) or "No matches"
    if name != "Read":
        raise ValueError("unknown repository tool")
    path = (ROOT / args["path"]).resolve()
    if not path.is_relative_to(ROOT) or path.suffix not in SUFFIXES or not path.is_file():
        raise ValueError("expected a source file in the pinned repository")
    offset, limit = args.get("offset", 1), args.get("limit", 50)
    if type(offset) != int or offset < 1 or type(limit) != int or not 1 <= limit <= 100:
        raise ValueError("invalid line range")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(f"{i}: {line[:600]}" for i, line in enumerate(lines[offset-1:offset-1+limit], offset))


def respond(request):
    method = request["method"]
    if method == "initialize":
        return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "fedops-repository", "version": "1"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = request["params"]
        try:
            result = invoke(params["name"], params.get("arguments", {}))
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
        return {"content": [{"type": "text", "text": result}]}
    raise ValueError("method not found")


if __name__ == "__main__":
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        reply = {"jsonrpc": "2.0", "id": request["id"]}
        try:
            reply["result"] = respond(request)
        except ValueError as exc:
            reply["error"] = {"code": -32601, "message": str(exc)}
        print(json.dumps(reply), flush=True)
