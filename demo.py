"""같은 질문으로 프로젝트 컨텍스트와 결정 기록의 변화를 보여준다."""

from difflib import unified_diff
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


QUESTION = "클라이언트별 accuracy를 집계할 때 누락값과 0은 어떻게 처리하나요?"
DECISION = "accuracy를 보고하지 않은 클라이언트는 분모에서 제외하고, 보고한 값이 0이면 포함한다."
SOURCE = "발표 실습 회의 D-01"


def run_cli(workdir, *args):
    result = subprocess.run(
        [sys.executable, "fedops.py", *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or result.returncode)
    return result.stdout


def main():
    project = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix="fedops-demo-") as temp:
        workdir = Path(temp)
        for name in ("fedops.py", "PROJECT.md", "AGENTS.md", "CLAUDE.md"):
            shutil.copy2(project / name, workdir / name)
        shutil.copytree(project / "evidence", workdir / "evidence")

        print("같은 질문의 컨텍스트 비교 · 오프라인 실행 (모델 호출 0회)")
        print(f"질문  {QUESTION}")
        before = run_cli(workdir, "brief", QUESTION)
        if "D-01" in before or QUESTION not in before:
            raise SystemExit("첫 brief의 질문 또는 초기 결정 상태가 예상과 다릅니다.")
        print("\n[1] 첫 프로세스가 만든 brief")
        print(f"질문 포함 · 총 {len(before.splitlines())}줄 · D-01 기록 없음")

        run_cli(workdir, "remember", "--topic", "지표 누락", "--decision", DECISION, "--source", SOURCE)
        print("\n[2] 가상의 회의 결정을 remember로 저장")
        print(f"{SOURCE} | {DECISION}")

        after = run_cli(workdir, "brief", QUESTION)
        if "D-01" not in after or DECISION not in after or QUESTION not in after:
            raise SystemExit("새 brief에서 회의 결정, 출처 또는 질문을 확인할 수 없습니다.")
        print("\n[3] 새 프로세스가 같은 질문으로 만든 brief")
        print(f"질문 포함 · 총 {len(after.splitlines())}줄 · D-01 기록 확인")
        print("두 brief의 변경 줄 (− 삭제, + 추가)")
        for line in unified_diff(before.splitlines(), after.splitlines(), n=0):
            if line.startswith(("+++", "---", "@@")):
                continue
            print(line)


if __name__ == "__main__":
    main()
