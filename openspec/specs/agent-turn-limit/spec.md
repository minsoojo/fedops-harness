# agent-turn-limit Specification

## Purpose

사용자가 질문이나 편집 작업을 맡길 때 에이전트가 반복해서 도구를 호출하더라도 정해진 에이전트 턴 안에서 실행을 마치도록 한다.

## Requirements

### Requirement: 실행당 최대 턴
worker는 ask의 모델 요청을 실행당 최대 8회로 제한하고 edit와 recall은 Claude Code의 최대 8턴을 유지해야 한다 (SHALL).

#### Scenario: 추가 턴 필요
- **WHEN** 질문을 마치려면 아홉 번째 모델 요청이 필요하다
- **THEN** 추가 전송 전에 중단하고 실패 원인을 기록한다.

#### Scenario: 한도 안에서 완료
- **WHEN** 주어진 턴 안에서 작업이 끝난다
- **THEN** 기존 방식으로 실행 결과를 전달한다.
