## Why
질문과 편집에 같은 Codex 포크를 사용하면서 작업별 파일 권한을 유지한다.

## What Changes
- 편집 요청을 Codex로 보내고 작업 복사본의 집계 함수만 바꾼다.
- 원본 검증기를 패치 전후에 실행하고 패치와 결과를 보존한다.

## Capabilities
### New Capabilities
- `codex-edit` — 제한된 편집과 독립 채점.

### Modified Capabilities
- `agent-turn-limit` — 편집의 요청 한도를 Codex에서 집행한다.

## Impact
편집 CLI, 전용 OpenShell 이미지 및 실행 기록. 질문 권한과 recall 경로는 유지한다.
