"""Apply a model-proposed aggregation body and independently grade the working copy."""
import ast
import builtins
import difflib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

from codex_ask import ask

APP = Path(__file__).resolve().parent
TARGET = "src/python/fedops/simulation/fl_strategy/aggregation.py"
NODES = (ast.FunctionDef, ast.arguments, ast.arg, ast.Assign, ast.AugAssign, ast.Return,
         ast.Expr, ast.If, ast.IfExp, ast.For, ast.Continue, ast.Name, ast.Load, ast.Store,
         ast.Constant, ast.Subscript, ast.Dict, ast.List, ast.Tuple, ast.Set, ast.DictComp,
         ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.comprehension, ast.BinOp,
         ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Compare, ast.Gt, ast.GtE, ast.Lt,
         ast.LtE, ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.BoolOp, ast.And, ast.Or,
         ast.UnaryOp, ast.Not, ast.USub, ast.Call, ast.Attribute)
FUNCTIONS = {"sum", "float", "int", "set", "len", "dict", "list"}
METHODS = {"get", "items", "keys", "values", "append", "setdefault"}


def replacement(source, body):
    if not isinstance(body, str) or not body.strip() or len(body) > 8192:
        raise ValueError("Expected a nonempty Python body of at most 8192 characters")
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    candidate = ast.parse("def weighted_average(metrics):\n" + body)
    for node in ast.walk(candidate.body[0]):
        if not isinstance(node, NODES):
            raise ValueError(f"Unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr not in METHODS:
            raise ValueError("Unsupported attribute")
        if isinstance(node, ast.Name) and node.id.startswith("_") and node.id != "_":
            raise ValueError("Unsupported name")
        if isinstance(node, ast.Call):
            fn = node.func
            if not (isinstance(fn, ast.Name) and fn.id in FUNCTIONS or
                    isinstance(fn, ast.Attribute) and fn.attr in METHODS):
                raise ValueError("Unsupported call")
    # Allow only local variables, the fixed parameter and numerical/collection builtins.
    nodes = list(ast.walk(candidate.body[0]))
    locals_ = {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    if locals_ & set(dir(builtins)):
        raise ValueError("Builtin names cannot be rebound")
    if any(n.id not in locals_ | FUNCTIONS | {"metrics"} for n in nodes if isinstance(n, ast.Name)):
        raise ValueError("Unknown name")
    if any(isinstance(n, ast.FunctionDef) for n in nodes[1:]) or len(candidate.body) != 1:
        raise ValueError("Unexpected definition")
    original, = (n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                 and n.name == "weighted_average")
    lines = source.splitlines(keepends=True)
    return "".join(lines[:original.body[0].end_lineno]) + body + "\n" + "".join(lines[original.end_lineno:])


def grade(target):
    proc = subprocess.run([sys.executable, "-I", "-B", str(APP / "check.py"), str(target)],
                          cwd=target.parent, env={}, capture_output=True, text=True, timeout=30)
    return dict(code=proc.returncode, log=proc.stdout + proc.stderr)


def edit(request, work, emit):
    source = (APP / "evidence/aggregation.py").read_text()
    target = work / TARGET
    target.parent.mkdir(parents=True)
    target.write_text(source)
    before = grade(target)
    if before["code"] != 1 or "FAILED (failures=2)" not in before["log"]:
        raise RuntimeError("Unexpected baseline")
    original, = (n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                 and n.name == "weighted_average")
    instructions = ('Return a JSON object with string fields "body" (Python body only, no def, '
                    'no imports or type annotations) and "summary". Omit the docstring; the harness preserves it. '
                    'Start top-level body statements at column zero. Use simple dicts, arithmetic, for loops or comprehensions. Available functions: '
                    + ", ".join(sorted(FUNCTIONS)) + ". Available methods: " + ", ".join(sorted(METHODS)))
    prompt = request["brief"] + "\nCurrent working copy function:\n" + ast.get_source_segment(source, original)
    report = ask(dict(request, brief=prompt), work, emit, instructions_text=instructions, budget=8, openrouter=True)
    raw = report["result"].strip()
    if raw.startswith("```json\n") and raw.endswith("\n```"):
        raw = raw[8:-4]
    response = json.loads(raw)
    new = replacement(source, response["body"])
    target.write_text(new)
    patch = "".join(difflib.unified_diff(source.splitlines(True), new.splitlines(True),
                                         "a/" + TARGET, "b/" + TARGET))
    return dict(report, result=response["summary"], patch=patch, before=before, after=grade(target))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(dir="/sandbox", prefix="fedops-edit-") as folder:
        def emit(**fields):
            print(json.dumps({"progress": fields}), flush=True)
        print(json.dumps(edit(json.load(sys.stdin), Path(folder), emit)), flush=True)
