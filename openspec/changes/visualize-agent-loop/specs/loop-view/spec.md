## ADDED Requirements

### Requirement: 실시간 루프 관찰
뷰어는 작업 시작, 도구 호출과 반환, 완료 또는 실패를 순서대로 표시해야 한다 (SHALL).

#### Scenario: 실행 중 관찰
- **WHEN** worker가 도구를 호출하고 최종 응답을 기다린다
- **THEN** 사용자는 종료 전에 도구 이름과 진행 상태를 볼 수 있다.

#### Scenario: 다시 열기
- **WHEN** 사용자가 완료된 턴을 선택한다
- **THEN** 동일한 실행 이력과 종료 상태를 다시 확인할 수 있다.
