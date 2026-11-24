## Why
현재 질문 입력에는 코드 근거와 팀 결정이 있지만 FedOps 1.3 사용자 문서의 설명과 출처가 없다. 첫 실습에서는 공식 Overview 한 페이지의 근거를 CLI에서 확인한다.

## What Changes
- 공식 Overview에서 버전이 명시된 한국어 요약을 로컬에 준비한다.
- 질문 입력을 만들 때 요약과 원문 URL을 공식 문서 항목으로 포함한다.

## Capabilities
### New Capabilities
- `docs-context`: 공식 문서의 근거와 출처를 질문 입력에 제공한다.

### Modified Capabilities
없음.

## Impact
fedops.py의 brief 출력과 이를 사용하는 agent.py에 적용된다. 전체 문서 검색과 Graphify 연결은 후속 변경으로 둔다.
