# repository-context Specification

## Purpose

FedOps 질문에 답할 때 사용자가 고정 커밋의 저장소 근거를 원본 파일에서 확인하고 같은 버전으로 결과를 재현할 수 있게 한다.

## Requirements

### Requirement: 고정 커밋의 저장소 근거

하네스는 brief에 해당 질문의 출처를 포함해야 한다 (SHALL). Python 함수·클래스 정의와 YAML 대상 설정에서 질문에 맞는 원문과 줄 번호를 제공한다.

#### Scenario: 오프라인 근거 조회
- **WHEN** 사용자가 네트워크 없이 weighted_average의 정의와 설정을 조회한다
- **THEN** 커밋에 고정된 aggregation.py와 config.yaml의 원문 위치를 확인할 수 있다.

#### Scenario: 검색 결과 없음
- **WHEN** 색인에 없는 식별자를 조회한다
- **THEN** 해당 항목에서 일치하는 근거가 없음을 알린다.
