## Why

FedOps 질문 실행에서 실제로 수정하고 빌드할 수 있는 Codex 포크를 사용하고, 기존 UI에서 모델 요청과 근거 확인 과정을 관찰한다.

## What Changes

- 고정 커밋의 포크 실행 파일을 별도 OpenShell 이미지에 설치한다.
- ask는 읽기 전용 저장소 도구로 원문을 확인하고 기존 타임라인 형식으로 결과를 낸다.

## Capabilities

### New Capabilities
- `codex-ask` 포크한 실행 엔진으로 질문 처리

### Modified Capabilities
- `agent-turn-limit` 질문 실행 엔진의 반복 제한

## Impact

OpenShell 이미지와 공급자 설정, 질문 실행 경로, Codex 포크의 이벤트가 영향을 받는다.
