"""Build the context for one FedOps question using project-owned knowledge."""
import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "memory" / "fedops.sqlite3"


def remember(topic, decision, source, memory=MEMORY):
    memory.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(memory) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY, topic TEXT NOT NULL, decision TEXT NOT NULL,
            source TEXT NOT NULL, recorded TEXT NOT NULL
        )""")
        cursor = db.execute(
            "INSERT INTO decisions (topic, decision, source, recorded) VALUES (?, ?, ?, ?)",
            (topic, decision, source, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        print(f"기록 #{cursor.lastrowid} · {topic} · {source}")


def brief(question, memory=MEMORY):
    print((ROOT / "PROJECT.md").read_text(encoding="utf-8").strip())
    print("\n## 담당자가 저장한 프로젝트 결정")
    rows = []
    if memory.exists():
        with sqlite3.connect(memory.resolve().as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute("""
                SELECT id, topic, decision, source, recorded FROM decisions
                WHERE id IN (SELECT MAX(id) FROM decisions GROUP BY topic)
                ORDER BY id
            """).fetchall()
    for number, topic, decision, source, recorded in rows:
        print(f"- [기록 #{number} · {topic}] {decision}\n  근거 · {source} · {recorded}")
    if not rows:
        print("저장된 결정 없음")
    print(f"\n## 현재 질문\n{question}")


def nonempty(text):
    if not text.strip():
        raise argparse.ArgumentTypeError("빈 값은 입력할 수 없습니다.")
    return text.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("brief", help="새 세션에 전달할 근거와 결정 출력").add_argument("question", type=nonempty)
    save = commands.add_parser("remember", help="담당자가 확인한 결정을 출처와 함께 저장")
    for field in ("topic", "decision", "source"):
        save.add_argument("--" + field, type=nonempty, required=True)
    args = parser.parse_args()
    if args.command == "brief":
        brief(args.question)
    else:
        remember(args.topic, args.decision, args.source)
