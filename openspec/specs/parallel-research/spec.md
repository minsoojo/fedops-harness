# parallel-research Specification

## Purpose

질문에 필요한 FedOps 출처를 병렬로 조사하고, 사용자가 UI에서 각 담당의 진행과 최종 답변의 근거를 확인할 수 있게 한다.

## Requirements

### Requirement: 선택한 출처의 병렬 조사
ask는 필요한 출처를 선택하고 독립 조사 결과와 실패 상태를 구분해 합성해야 한다 (SHALL).
#### Scenario: 복합 질문
- **WHEN** 둘 이상의 출처가 필요한 질문을 받는다
- **THEN** 선택한 세션이 동시에 실행되고 타임라인에 출처별 상태, 회차, 결과와 최종 답변이 표시된다.
#### Scenario: 단일 출처
- **WHEN** 공식 문서만 필요한 질문을 받는다
- **THEN** 문서 담당만 조사한다.
#### Scenario: OpenAI API 연결
- **WHEN** 질문 전용 OpenShell provider에 OPENAI_API_KEY를 등록하고 UI에서 질문한다
- **THEN** 선택된 세션과 합성이 OpenAI Responses API를 통해 실행된다.
