# graph-context Specification

## Purpose

FedOps 질문에 답할 때 사용자가 Graphify 관계 근거를 원본 파일에서 확인하고 같은 버전으로 결과를 재현할 수 있게 한다.

## Requirements

### Requirement: Graphify 관계 근거

하네스는 brief에 해당 질문의 출처를 포함해야 한다 (SHALL). 코드 심볼 간 관계의 방향, 종류, 추출 신뢰도 및 원문 위치를 제공한다.

#### Scenario: 오프라인 근거 조회
- **WHEN** 사용자가 네트워크 없이 weighted_average가 어느 파일에 포함되는지 묻는다
- **THEN** Graphify가 추출한 contains 관계, 양 끝점, 신뢰도와 원문 링크가 표시된다.

#### Scenario: 검색 결과 없음
- **WHEN** 색인에 없는 식별자를 조회한다
- **THEN** 해당 항목에서 일치하는 근거가 없음을 알린다.
