# codex-edit Specification

## Purpose

Codex가 제안한 집계 함수 변경을 OpenShell 작업 복사본에만 적용하고 원본 검증기로 패치의 정확성을 확인한다.

## Requirements

### Requirement: Scoped Codex edit and independent grading
The harness SHALL use the ask Codex fork revision for edit, allow only changes to the working copy of weighted_average and fixed verifier execution, and keep ask read-only.

#### Scenario: Successful edit
- **WHEN** the model supplies an allowed function body that fixes aggregation
- **THEN** the harness records the nonempty patch, failing baseline and passing original verifier output

#### Scenario: Unsupported operation
- **WHEN** a replacement requests filesystem access or external execution
- **THEN** the harness rejects the body before writing or grading it
