# codex-ask Specification

## Purpose

FedOps 질문을 고정 커밋에서 빌드한 Codex로 실행하고, 사용자가 기존 UI에서 회차별 도구 실행과 최종 답변을 확인할 수 있게 한다.

## Requirements

### Requirement: 포크 실행과 질문 타임라인
하네스는 고정된 Codex 포크로 OpenShell 안에서 질문을 실행하고 실제 요청별 회차, 도구와 답변을 기존 UI에 표시해야 한다 (SHALL).

#### Scenario: 설정 위치 질문
- **WHEN** 사용자가 UI에 weighted_average의 설정 위치를 질문한다
- **THEN** 실제 첫 요청 전송부터 대기 상태를 표시하고 읽기 전용 검색과 원문 읽기의 결과를 해당 회차에 연결한 뒤 설정 파일 근거를 포함한 답변을 표시한다.

#### Scenario: 공급자 오류
- **WHEN** 모델이 오류를 반환한다
- **THEN** 실행을 실패로 기록하고 이미 수집된 회차를 보존한다.
