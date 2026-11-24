## MODIFIED Requirements

### Requirement: 질문별 컨텍스트 조회
뷰어는 입력한 질문에 대한 근거 미리보기와 기존 회차 타임라인을 제공해야 한다 (SHALL).

#### Scenario: 근거 확인
- **WHEN** 사용자가 질문을 입력하고 근거를 조회한다
- **THEN** 저장소, 공식 문서와 Graphify 근거를 읽고 원문 링크를 열 수 있다.

#### Scenario: 빈 질문
- **WHEN** 사용자가 공백만 입력한다
- **THEN** 질문 입력을 안내한다.
