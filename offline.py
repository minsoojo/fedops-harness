"""Replay the documented decision and reviewed FedOps patch without credentials."""
import shutil
import subprocess
import sys

import agent
import demo
import worker


def main():
    demo.main()
    folder = agent.run_folder("offline")
    target = folder / worker.TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(agent.ROOT / "evidence/aggregation.py", target)
    before = worker.tests(target)
    (folder / "before.log").write_text(before["log"])
    if before["code"] != 1 or "FAILED (failures=2)" not in before["log"]:
        sys.exit("원본에서 예상한 두 실패를 재현하지 못했습니다.")
    subprocess.run(["git", "init", "-q", str(folder)], check=True)
    patch = folder / "change.patch"
    shutil.copyfile(agent.ROOT / "reference.patch", patch)
    subprocess.run(["git", "apply", str(patch)], cwd=folder, check=True)
    after = worker.tests(target)
    (folder / "after.log").write_text(after["log"])
    if after["code"] != 0 or "Ran 7 tests" not in after["log"]:
        sys.exit("참고 패치 검증 실패")
    print(f"PASS · 참고 패치 적용 전 2개 실패 → 적용 후 7개 통과\n기록  {folder}")


if __name__ == "__main__":
    main()
