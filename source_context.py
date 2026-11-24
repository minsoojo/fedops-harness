"""Retrieve bounded, revision-linked FedOps evidence from local snapshots."""
import gzip
import json
from pathlib import Path
import re
from urllib.parse import quote

REVISION = "3cd08420ecb5662b5b28c10a9303e28e610313b2"
EVIDENCE = Path(__file__).resolve().parent / "evidence"
ALIASES = {"집계": "aggregation", "가중": "weighted_average", "지표": "metrics",
           "클라이언트": "client", "서버": "server", "시뮬레이션": "simulation",
           "에이전트": "agent", "스튜디오": "studio", "학습": "train", "평가": "evaluate"}


def print_matches(source, question):
    with gzip.open(EVIDENCE / (source + ".json.gz"), "rt", encoding="utf-8") as file:
        index = json.load(file)
    terms = set(re.findall(r"[a-z][a-z0-9_]+", question.lower()))
    symbols = {term for term in terms if "_" in term}
    terms.update(word for korean, word in ALIASES.items() if korean in question)
    if "집계" in question and any(term in question for term in ("누락", "accuracy", "지표")):
        terms.add("weighted_average")
    candidates = []
    for row in index["rows"]:
        path, line, *fields = row
        # Rank matching identifiers ahead of incidental matches in directory names.
        content = " ".join(fields if source == "repository" else [fields[0], fields[2]]).lower()
        tokens = set(re.findall(r"[a-z][a-z0-9_]*", content))
        score = sum(8 if term in tokens else 4 if term in content else 1 if term in path.lower()
                    else 0 for term in terms)
        if score:
            candidates.append((len(symbols & tokens) if source == "graph" else 0, score, path.startswith("src/python/fedops/"), row))
    revision = index["revision"]
    title = "FedOps 저장소" if source == "repository" else f"Graphify {index['graphify_version']} · 코드 관계"
    print(f"\n## {title} · {revision[:7]}")
    if not candidates:
        print("질문과 일치하는 근거 없음")
    for _, _, _, (path, line, *fields) in sorted(candidates, key=lambda c: (-c[0], -c[1], -c[2], c[3]))[:4]:
        if source == "repository":
            description = fields[0]
        else:
            start, relation, end, confidence = fields
            description = f"{start} —{relation}→ {end} [{confidence}]"
        print(f"- {description}\n  https://github.com/gachon-CCLab/FedOps/blob/{revision}/{quote(path)}#L{line}")
