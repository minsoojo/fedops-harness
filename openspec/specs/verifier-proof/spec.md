# verifier-proof Specification

## Purpose

사용자가 실제 OpenShell 보호 실험에서 작업 파일과 검증기에 적용된 쓰기 권한, 동일 검증기로 채점한 결과를 웹 화면에서 비교할 수 있게 한다.

## Requirements

### Requirement: 보호 실험 비교
뷰어는 기록된 실험의 권한 결과와 패치 전후 통과 및 실패 수를 한 화면에 보여야 한다 (SHALL).

#### Scenario: 기록 확인
- **WHEN** 사용자가 보호 실험 다이어그램을 연다
- **THEN** 대상 경로, 쓰기 허용 또는 거부, 각 단계의 채점 결과와 실험 ID를 확인한다.
