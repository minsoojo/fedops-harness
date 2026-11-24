## Why

저장소 검색 결과가 첫 질문에서 고정돼 후속 검색이 어렵고, 설정 위치를 찾아도 worker의 파일시스템에는 원문이 없어 확인에 실패한다.

## What Changes

실행 중 에이전트가 고정 커밋의 Python 및 YAML 파일을 검색하고 지정한 경로와 줄 범위를 읽는다. 웹 및 CLI의 brief 미리보기는 기존 검색 결과를 제공한다.

## Capabilities

### New Capabilities

- `repository-tools` · 고정 커밋을 대상으로 실행 중 소스 검색과 원문 읽기

### Modified Capabilities

- `context-workbench` · 화면의 조회 결과를 실행 전 미리보기로 표시한다.

## Impact

컨텍스트 생성기, 샌드박스 이미지, Claude Code 도구 목록 및 오프라인 실습에 적용한다.
