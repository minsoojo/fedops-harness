## Purpose

사용자가 질문이나 편집 작업을 맡길 때 에이전트가 반복해서 도구를 호출하더라도 정해진 에이전트 턴 안에서 실행을 마치도록 한다.

## ADDED Requirements

### Requirement: 실행당 최대 턴
worker는 Claude Code를 최대 8턴으로 실행해야 한다 (SHALL).

#### Scenario: 추가 턴 필요
- **WHEN** Claude Code가 턴 한도로 종료한다
- **THEN** 하네스는 한도와 실패 원인을 기록하며 작업을 완료로 처리하지 않는다.

#### Scenario: 한도 안에서 완료
- **WHEN** 주어진 턴 안에서 작업이 끝난다
- **THEN** 기존 방식으로 실행 결과를 전달한다.
