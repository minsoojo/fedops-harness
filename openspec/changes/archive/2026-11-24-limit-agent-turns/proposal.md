## Why

도구 결과를 받고도 다음 작업을 반복하는 에이전트가 한 질문에 계속 자원을 쓰지 않도록 하네스에서 실행 길이를 제한한다.

## What Changes

모든 worker 실행에 Claude Code의 최대 턴 수를 전달한다.

## Capabilities

### New Capabilities

- `agent-turn-limit` · 실행당 에이전트 턴 제한

## Impact

UI와 CLI에서 사용하는 worker에 적용한다.
