## ADDED Requirements

### Requirement: 공식 문서 근거 제공
하네스는 질문 입력에 공식 FedOps 문서의 버전, 제목, 내용 요약, 원문 URL을 함께 포함해야 한다 (SHALL).

#### Scenario: Agent Studio의 역할 조회
- **WHEN** 사용자가 brief 명령으로 Agent Studio의 역할을 묻는다
- **THEN** 공식 문서 항목에 FedOps 1.3, Overview, 로컬 학습과 연합학습 참여를 연결한다는 요약, https://gachon-cclab.github.io/fedops-docs-1.3/ 가 포함된다.

#### Scenario: 네트워크 없는 반복 실행
- **WHEN** 네트워크 연결 없이 같은 질문의 brief를 생성한다
- **THEN** 로컬 문서 요약과 동일한 출처를 표시하며 기존 프로젝트 근거와 저장된 팀 결정도 각 항목에서 확인할 수 있다.
