## Context
기존 edit는 Claude Code에 Edit와 제한된 Bash 권한을 부여한다.

## Goals / Non-Goals
동일 Codex 빌드로 집계 함수 편집을 수행한다. 범용 저장소 쓰기는 범위 밖이다.

## Decisions
질문 이미지에서 편집 이미지를 파생한다. 모델에는 도구 없이 기존 함수와 요청을 전달한다. 신뢰하는 worker가 고정된 함수 본문을 산술 및 컬렉션 연산으로 제한하고, 새 작업 복사본에 반영한 후 이미지의 check.py를 실행한다.

## Risks / Trade-offs
지원하는 Python 문법이 제한된다. 지원 범위를 벗어나면 채점 전에 오류를 반환한다.
