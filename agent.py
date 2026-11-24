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
BOX = os.getenv("FEDOPS_SANDBOX", "fedops-repo-tools")
MODEL = os.getenv("FEDOPS_MODEL", "anthropic/claude-sonnet-4.6")
PROVIDER = "fedops-openrouter"
IMAGE = "fedops-claude:2.1.330"
QUESTION = ("A는 표본 10개에서 accuracy 0.8을 보고하고 B는 30개에서 생략했다. 현재 코드의 결과, "
            "우리 팀이 정한 결과, B가 0을 보고할 때의 합의 결과, 결정 출처의 정확한 이름을 답해 줘.")


CODEX_REV = "84ea60b8997564cffe385af2259494f9bdf5c38d"
ASK_BOX = os.getenv("FEDOPS_ASK_SANDBOX", "fedops-oa-" + CODEX_REV[:8])
ASK_MODEL = os.getenv("FEDOPS_ASK_MODEL") or "gpt-4.1-mini"
ASK_IMAGE = "fedops-codex:" + CODEX_REV[:12]


def exists(kind, name):
    return subprocess.run(["openshell", kind, "get", name], capture_output=True).returncode == 0


def ensure_provider(name, profile, credential="OPENROUTER_API_KEY"):
    if not exists("provider", name):
        provider_env = os.environ.copy()
        if not provider_env.get(credential):
            env_file = ROOT / ".env"
            if env_file.is_file():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    key, sep, value = line.partition("=")
                    if sep and key.strip() == credential:
                        provider_env[key.strip()] = value.strip().strip("\"'")
        if not provider_env.get(credential):
            raise ValueError(f".env 또는 환경변수에 {credential}를 설정하세요.")
        if subprocess.run(["openshell", "profile", "describe", name], capture_output=True).returncode:
            subprocess.run(["openshell", "profile", "import", "-f", str(ROOT / profile)], check=True)
        subprocess.run(["openshell", "provider", "create", "--name", name,
                        "--type", name, "--from-existing"], check=True, env=provider_env)


def setup_ask():
    name = "fedops-codex-openai"
    ensure_provider(name, "infra/openai-provider.yaml", "OPENAI_API_KEY")
    if not exists("sandbox", ASK_BOX):
        source = Path(os.getenv("FEDOPS_CODEX_SOURCE", ROOT.parent / "fedops-codex"))
        subprocess.run(["docker", "build", "--build-context", f"codex={source}",
                        "--build-arg", f"CODEX_REV={CODEX_REV}", "-t", ASK_IMAGE,
                        "-f", str(ROOT / "infra/Codex.Dockerfile"), str(ROOT)], check=True)
        subprocess.run(["openshell", "sandbox", "create", "--name", ASK_BOX, "--from", ASK_IMAGE,
                        "--provider", name, "--policy", str(ROOT / "infra/policy.yaml"),
                        "--detach", "--", "sleep", "infinity"], check=True)
    actual = subprocess.check_output(["openshell", "sandbox", "exec", "-n", ASK_BOX, "--",
                                      "cat", "/opt/fedops/codex-revision"], text=True).strip()
    if actual != CODEX_REV:
        raise ValueError(f"Codex 빌드 커밋 불일치: {actual}")


def setup():
    version = subprocess.check_output(["openshell", "--version"], text=True).strip()
    if version != "openshell 0.1.9":
        raise ValueError("이 패키지의 OpenShell 버전은 0.1.9입니다.")
    subprocess.run(["openshell", "whoami"], check=True)
    ensure_provider(PROVIDER, "infra/provider.yaml")
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
        current_round = None
        def record(event, **fields):
            nonlocal current_round
            if event == "model_request":
                current_round = fields["round"]
            if event in {"failed", "done"} and current_round is not None:
                fields["round"] = current_round
            item = dict(event=event, time=datetime.now(timezone.utc).isoformat(), **fields)
            timeline.write(json.dumps(item) + "\n")

        record("start", mode=mode, timeline_version=2)
        try:
            report = job(record)
        except BaseException as error:
            with (folder / "runtime.log").open("a") as log:
                print(f"{type(error).__name__}: {error}", file=log)
            record("failed")
            raise
        if mode == "ask":
            record("done", answer=report["result"])
        else:
            record("done")
        return report


def _run_turn(folder, mode, question, memory, record):
    buf = StringIO()
    if mode == "ask":
        with redirect_stdout(buf):
            fedops.print_matches("graph", question)
        graph = buf.getvalue()
        buf = StringIO()
        with redirect_stdout(buf):
            fedops.print_memory(memory)
        req = dict(mode=mode, question=question, model=ASK_MODEL, graph=graph,
                   docs=(ROOT / "evidence/fedops-overview.md").read_text(),
                   memory=buf.getvalue(), source_revision=fedops.REVISION)
        brief = question
    else:
        with redirect_stdout(buf):
            fedops.brief(question, memory, for_agent=True)
        brief = buf.getvalue()
        req = dict(mode=mode, stream=True, brief=brief, model=MODEL)
    (folder / "brief.md").write_text(brief)
    cmd = ["openshell", "sandbox", "exec", "-n", BOX, "--", "python3", "/opt/fedops/worker.py"]
    if mode == "ask":
        cmd = ["openshell", "sandbox", "exec", "-n", ASK_BOX, "--", "python3", "/opt/fedops/codex_ask.py"]
    report = None
    with (folder / "runtime.log").open("w") as log:
        for packet in messages(cmd, json.dumps(req), 950 if mode == "ask" else 370, stderr=log):
            if "progress" in packet:
                record(**packet["progress"])
            else:
                report = packet
    if report is None:
        raise ValueError(f"결과 없음 · {folder / 'runtime.log'}")
    if mode == "ask" and (report.get("engine"), report.get("revision")) != ("codex", CODEX_REV):
        raise ValueError("예상한 Codex 포크에서 생성한 답변인지 확인할 수 없습니다")
    if mode == "ask":
        report["model"] = req["model"]
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


def replay_loop(wait_first=False, repository=False):
    folder = run_folder("replay")
    def job(record):
        cmd = ["docker", "run", "--rm", "-i", "--network", "none", "--user", "1000:1000",
               "-e", "HOME=/tmp", IMAGE, "python3", "-", "--timeline"]
        if repository:
            cmd.append("--repository")
        if wait_first:
            cmd.append("--wait-first")
        for item in messages(cmd, (ROOT / "replay.py").read_text(), 370):
            record(**item)
    trace_run(folder, "replay", job)
    tools = "Grep → Read" if repository else "Read → Edit"
    print(f"PASS · Claude {tools} · {folder}")


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
    sub.add_parser("setup-ask")
    sub.add_parser("live-demo")
    replay_parser = sub.add_parser("replay-loop")
    replay_parser.add_argument("--repository", action="store_true", help="저장소 검색과 원문 읽기 실습")
    replay_parser.add_argument("--wait-first", action="store_true", help="모의 서버의 첫 모델 응답을 10초 보류")
    for mode in ("ask", "edit"):
        sub.add_parser(mode).add_argument("question")
    args = parser.parse_args()
    if args.mode == "setup":
        setup()
    elif args.mode == "replay-loop":
        replay_loop(args.wait_first, args.repository)
    elif args.mode == "setup-ask":
        setup_ask()
    elif args.mode == "live-demo":
        live_demo()
    else:
        folder = run_folder(args.mode)
        print(f"기록  {folder}", flush=True)
        report = run_turn(folder, args.mode, args.question)
        print(report["result"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
