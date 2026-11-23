"""Host-side FedOps context, OpenShell launcher, independent completion checks."""
import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from stream_loop import messages

import fedops

ROOT = Path(__file__).resolve().parent
BOX = os.getenv("FEDOPS_SANDBOX", "fedops-agent-loop")
MODEL = os.getenv("FEDOPS_MODEL", "anthropic/claude-sonnet-4.6")
PROVIDER = "fedops-openrouter"
IMAGE = "fedops-claude:2.1.330"
QUESTION = ("A는 표본 10개에서 accuracy 0.8을 보고하고 B는 30개에서 생략했다. 현재 코드의 결과, "
            "우리 팀이 정한 결과, B가 0을 보고할 때의 합의 결과, 결정 출처의 정확한 이름을 답해 줘.")


def setup():
    def exists(kind, name):
        return subprocess.run(["openshell", kind, "get", name], capture_output=True).returncode == 0
    version = subprocess.check_output(["openshell", "--version"], text=True).strip()
    if version != "openshell 0.1.9":
        raise ValueError("이 패키지의 OpenShell 버전은 0.1.9입니다.")
    subprocess.run(["openshell", "whoami"], check=True)
    if not exists("provider", PROVIDER):
        provider_env = os.environ.copy()
        if not provider_env.get("OPENROUTER_API_KEY"):
            env_file = ROOT / ".env"
            if env_file.is_file():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    name, sep, value = line.partition("=")
                    if sep and name.strip() == "OPENROUTER_API_KEY":
                        provider_env[name.strip()] = value.strip().strip("\"'")
        if not provider_env.get("OPENROUTER_API_KEY"):
            raise ValueError(".env 또는 환경변수에 OPENROUTER_API_KEY를 설정하세요.")
        subprocess.run(["openshell", "profile", "import", "-f", str(ROOT / "infra/provider.yaml")], check=True)
        subprocess.run(["openshell", "provider", "create", "--name", PROVIDER,
                        "--type", PROVIDER, "--from-existing"], check=True, env=provider_env)
    if not exists("sandbox", BOX):
        build = ["docker", "build", "-t", IMAGE]
        if os.getenv("FEDOPS_BUILD_CA"):
            build += ["--secret", "id=build_ca,src=" + os.environ["FEDOPS_BUILD_CA"]]
        subprocess.run([*build, str(ROOT)], check=True)
        subprocess.run(["openshell", "sandbox", "create", "--name", BOX, "--from", IMAGE,
                        "--provider", PROVIDER, "--policy", str(ROOT / "infra/policy.yaml"),
                        "--detach", "--", "sleep", "infinity"], check=True)
    subprocess.run(["openshell", "sandbox", "exec", "-n", BOX, "--", "claude", "--version"], check=True)


def run_folder(prefix):
    parent = ROOT / "runs"
    parent.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=parent, prefix=prefix + "-"))


def run_turn(folder, mode, question, memory=fedops.MEMORY):
    return trace_run(folder, mode, lambda record: _run_turn(folder, mode, question, memory, record))


def trace_run(folder, mode, job):
    with (folder / "timeline.jsonl").open("w", buffering=1) as timeline:
        def record(event, **fields):
            item = dict(event=event, time=datetime.now(timezone.utc).isoformat(), **fields)
            timeline.write(json.dumps(item) + "\n")

        record("start", mode=mode)
        try:
            report = job(record)
        except BaseException:
            record("failed")
            raise
        record("done")
        return report


def _run_turn(folder, mode, question, memory, record):
    buf = StringIO()
    with redirect_stdout(buf):
        fedops.brief(question, memory)
    brief = buf.getvalue()
    (folder / "brief.md").write_text(brief)
    req = {"mode": mode, "stream": True, "brief": brief, "model": MODEL}
    cmd = ["openshell", "sandbox", "exec", "-n", BOX, "--", "python3", "/opt/fedops/worker.py"]
    print(f"기록  {folder}", flush=True)
    report = None
    with (folder / "runtime.log").open("w") as log:
        for packet in messages(cmd, json.dumps(req), 370, stderr=log):
            if "progress" in packet:
                record(**packet["progress"])
            else:
                report = packet
    if report is None:
        raise ValueError(f"결과 없음 · {folder / 'runtime.log'}")
    (folder / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (folder / "events.jsonl").write_text("".join(
        json.dumps(event, ensure_ascii=False) + "\n" for event in report["trace"]))
    if mode == "edit":
        (folder / "change.patch").write_text(report["patch"])
        for phase in ("before", "after"):
            (folder / (phase + ".log")).write_text(report[phase]["log"])
        if not report["patch"] or report["after"]["code"] != 0:
            raise ValueError("코드 수정 완료 기준 미달 · after.log 확인")
    return report


def replay_loop():
    folder = run_folder("replay")
    def job(record):
        cmd = ["docker", "run", "--rm", "-i", "--network", "none", "--user", "1000:1000",
               "-e", "HOME=/tmp", IMAGE, "python3", "-", "--timeline"]
        for item in messages(cmd, (ROOT / "replay.py").read_text(), 370):
            record(**item)
    trace_run(folder, "replay", job)
    print(f"PASS · Claude Read → Edit · {folder}")


def live_demo():
    folder = run_folder("recall")
    memory = folder / "memory/fedops.sqlite3"
    source = "발표 실습 회의 D-01 " + folder.name
    sessions = []
    for phase in ("before", "after"):
        if phase == "after":
            fedops.remember("지표 누락", "미보고 클라이언트는 해당 지표의 분모에서 제외하고 0은 포함한다.", source, memory)
        out = folder / phase
        out.mkdir()
        report = run_turn(out, "recall", QUESTION, memory)
        sessions.append(report["session"])
        expected = {"current": 0.2, "agreed": None, "reported_zero": None, "source": None}
        if phase == "after":
            expected.update(agreed=0.8, reported_zero=0.2, source=source)
        print(phase, json.dumps(report["structured"], ensure_ascii=False))
        if report["structured"] != expected:
            raise ValueError(f"{phase} 답변이 기준과 다릅니다. {out / 'result.json'}")
    if not all(sessions) or sessions[0] == sessions[1]:
        raise ValueError("두 개의 독립 세션을 확인할 수 없습니다.")
    print("PASS · 새 세션이 결정과 출처를 복원했습니다.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("setup")
    sub.add_parser("live-demo")
    sub.add_parser("replay-loop")
    for mode in ("ask", "edit"):
        sub.add_parser(mode).add_argument("question")
    args = parser.parse_args()
    if args.mode == "setup":
        setup()
    elif args.mode == "replay-loop":
        replay_loop()
    elif args.mode == "live-demo":
        live_demo()
    else:
        report = run_turn(run_folder(args.mode), args.mode, args.question)
        print(report["result"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
