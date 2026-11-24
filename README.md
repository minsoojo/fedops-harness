# FedOps 전담 에이전트 하네스

한 세션에서 확인한 팀 결정을 다음 세션의 코드 질문과 수정에 사용한다. 발표 과제는 가천대 FedOps 시뮬레이션의 평가 지표 집계다.

## 키 없이 바로 발표하기

ZIP을 풀고 Python 3.9 이상과 Git이 있는 터미널에서 실행한다.

```sh
cd fedops-agent
python3 offline.py
```

같은 질문에 대해 결정 저장 전후에 모델로 보낼 입력의 차이가 출력된다. 이어서 원본 함수에서 테스트 두 개가 실패하고, 참고 패치를 적용하면 일곱 개가 통과한다. 기억과 검증기는 실제로 실행하고 코드 수정은 참고 패치를 재생한다. 실행마다 결과가 별도의 `runs/offline-…` 폴더에 남는다.

## 실제 호출 경로

```text
사용자 → 호스트의 FedOps 하네스
           ├─ 현재 작업 + 공식 코드 근거 + SQLite의 최신 팀 결정
           └─ openshell sandbox exec (표준입력으로 전달)
                 ├─ ask → Codex 포크 → OpenAI API → Grep·Read
                 ├─ edit → 같은 Codex 포크 → 작업 복사본 패치와 원본 검증기 채점
                 └─ recall → Claude Code → OpenRouter
           ← 답변·도구 이벤트·변경 패치·별도 검증기의 결과
```

- **컨텍스트**는 호스트가 조립한다. `memory/fedops.sqlite3`에 승인된 결정과 출처를 보관하므로, 이 파일을 유지하면 샌드박스를 교체해도 팀 지식이 남는다. `PROJECT.md`에는 기준 커밋과 근거가 있다. 질문마다 Codex 프로세스와 임시 작업 디렉터리를 새로 만든다.
- **권한**은 OpenShell의 파일 정책과 provider 프로필이 담당한다. 모델 키는 호스트에서 provider로 등록한다. OpenShell은 질문에 `api.openai.com:443`, 편집과 recall에 `openrouter.ai:443`을 사용하며 각 호스트에서 자격 증명을 처리한다. 질문·편집용 프로필은 `/usr/local/bin/fedops-codex`, recall 프로필은 `/usr/local/bin/claude`를 허용한다.
- **편집 완료**는 원래 집계 함수에서 두 실패가 재현되고, 변경 범위가 함수 안이며, 이미지에 포함된 별도 검증기에서 일곱 개가 통과하고 패치가 생겼을 때다. 각 작업 복사본은 실행 후 폐기되며 패치는 호스트에 남는다.
- **실행 기록**은 `runs/` 아래의 `brief.md`, `events.jsonl`(도구 이름·ID·성공 여부), `result.json`(응답·세션 ID·사용량), `runtime.log`다. 편집 작업에는 `before.log`, `after.log`, `change.patch`도 포함된다.
- 단일 함수 실습에는 Claude Code 기본 실행 루프를 사용한다. 다중 에이전트 Dynamic Workflows는 이 버전에 포함하지 않았다.

## 모델 API 연결하기

대상은 **Docker 드라이버를 사용하는 로컬 NVIDIA OpenShell 0.1.9 게이트웨이**다. Linux에서는 Landlock ABI v3 이상을 실제로 사용할 수 있어야 한다. 호스트에 Python, Docker, OpenShell을 준비하고, `openshell whoami`로 활성 게이트웨이를 확인한다. 배포판의 기본 샌드박스 이미지에 의존하지 않고 Claude Code 2.1.330을 고정한 이미지를 빌드한다. [NVIDIA 설치 가이드](https://docs.nvidia.com/openshell/v0.1.9/about/installation) · [OpenShell 샌드박스](https://docs.nvidia.com/openshell/v0.1.9/how-it-works/sandboxes/overview)

프로젝트 루트의 `.env`에 질문용 `OPENAI_API_KEY`와 편집·recall용 `OPENROUTER_API_KEY`를 각각 설정한 뒤 (호스트 환경변수를 설정했다면 그 값이 우선한다) 아래 순서로 실행한다. 질문 기본 모델은 `gpt-4.1-mini`, 편집은 `openai/gpt-4.1-mini`, recall은 `anthropic/claude-sonnet-4.6`이다. `FEDOPS_MODEL`은 편집·recall 모델을, `FEDOPS_ASK_MODEL`은 질문 전용 모델을 지정한다. 질문 호출은 OpenAI API 계정에 청구된다. [OpenRouter의 Claude Code 연동 문서](https://openrouter.ai/docs/guides/coding-agents/claude-code-integration)

```sh
python3 agent.py setup
python3 agent.py live-demo
```

`setup`은 전용 프로필·provider를 등록하고 이미지를 빌드한 뒤 `fedops-repo-tools` 샌드박스를 만든다. 이미 있는 동명의 provider와 샌드박스는 재사용한다. 기존 샌드박스에 새 이미지를 반영하려면 다른 이름을 `FEDOPS_SANDBOX`에 지정해 setup을 실행한다. 빌드 환경이 별도 CA를 요구하면 호스트의 신뢰할 수 있는 CA 번들 경로를 `FEDOPS_BUILD_CA`에 설정한다.

`live-demo`는 독립된 메모리 파일로 두 번 실제 호출한다. 첫 응답은 현재 구현 0.20과 합의 없음이어야 한다. 하네스가 발표용 결정을 호스트에 기록한 뒤 두 번째 세션이 0.80, 명시한 0은 0.20, 이번 실행의 고유 출처까지 반환해야 PASS가 나온다. 세션 ID도 서로 달라야 한다.

일상 작업의 결정 저장·질문·코드 수정 예시는 다음과 같다. 라이브 시연의 가상 결정과 일상 작업의 DB는 분리한다.

```sh
python3 fedops.py remember --topic "지표 누락" --decision "미보고는 분모에서 제외하고 보고한 0은 포함한다." --source "발표 실습 회의 D-01"
python3 agent.py ask "정확도가 누락되면 현재 코드와 팀 결정이 어떻게 다른가?"
python3 agent.py setup-edit
python3 agent.py edit "팀이 정한 누락 지표 처리 기준을 집계 함수에 적용해 줘."
```

## Claude 도구 루프도 키 없이 확인하기

`replay.py`가 로컬 HTTP 서버로 미리 정한 Messages 응답을 제공한다. 실제 Claude Code 바이너리가 그 응답을 읽고 Read와 Edit를 실행한다. 이미지 속 독립 검증기가 결과를 채점한다. 모델 추론 품질을 평가하는 테스트는 `live-demo`다.

```sh
docker build -t fedops-claude:2.1.330 .
docker run --rm -i --network none --user 1000:1000 -e HOME=/tmp fedops-claude:2.1.330 python3 - < replay.py
```

## 검증 범위 · 2026-11-23

OpenShell 0.1.9 게이트웨이를 mTLS로 기동해 로그인, provider 프로필 lint·import, 샌드박스 생성 요청까지 확인했다. 이 클라우드 커널은 Landlock을 제공하지 않아 supervisor가 준비 단계에서 종료됐다. Claude 이미지, 로컬 모의 응답을 사용한 도구 실행, 컨텍스트 및 독립 검증기는 별도로 시험했다. 실제 OpenRouter 호출과 OpenShell 내부의 종단 간 실행은 미검증이다.

## 실행 중 도구 호출 보기

서버에서 `python3 viewer.py`를 실행하고 브라우저로 http://127.0.0.1:8765 를 연다. 원격 서버라면 SSH 연결에 `-L 8765:127.0.0.1:8765`를 추가한다. 다른 터미널에서 아래 명령을 실행하면 시작, 도구 호출·반환, 완료·실패가 순서대로 표시된다.

- 키 없는 연습: `docker build -t fedops-claude:2.1.330 .` 후 `python3 agent.py replay-loop`. 격리된 Docker 안에서 모의 모델 응답에 따라 실제 Claude Code가 Read와 Edit를 실행한다.
- 질문은 `python3 agent.py setup-ask`, 편집은 `python3 agent.py setup-edit`, live-demo는 `python3 agent.py setup`으로 준비한다.
- 창은 0.75초마다 로컬 실행 기록을 읽는다. 실행을 선택하면 해당 작업의 기록을 다시 볼 수 있다.

### 모델 회차별 다이어그램

서버에서 `python3 viewer.py`로 뷰어를 열고 최근 실행 따라가기를 선택한다.
다른 터미널에서 저장소 루트를 기준으로 실행한다.

```sh
docker build -t fedops-claude:2.1.330 .
python3 agent.py replay-loop --wait-first
```

첫 모델 요청을 받은 모의 서버가 10초 동안 응답을 보류한다. 이때 브라우저에는
‘1회차 · 모델 응답 대기 중’이 보인다. 응답이 오면 각 회차에서 모델 출력을 펼쳐
텍스트와 도구 인자를 읽을 수 있다. 이 실습은 Read, Edit, 최종 답변 순으로
세 회차를 기록한다. 실행 선택에서 같은 기록을 다시 열 수 있다.
이전 형식의 실행은 시간순 이벤트 목록으로 열린다. 기존 OpenShell 샌드박스에서
새 worker를 쓰려면 새 이름을 지정해 setup과 후속 명령에 같은 FEDOPS_SANDBOX를 사용한다.

## 질문에 들어가는 FedOps 컨텍스트

`ask`와 `edit`는 호스트에서 만든 동일한 형식의 brief를 받는다. 아래 명령으로 모델 호출 전에 근거를 확인할 수 있다.

```sh
python3 fedops.py brief 'weighted_average의 정의와 설정은 어디에 있나?'
python3 fedops.py brief 'get_top_clients_by_metrics를 호출하는 함수는?'
python3 fedops.py brief 'FedOps Agent Studio는 로컬 학습과 FL 참여를 어떻게 연결하나?'
```

| 소스 | 범위와 출처 |
|---|---|
| 저장소 | 기준 커밋 `3cd0842`에서 Python 함수·클래스 선언과 YAML의 `_target_` 줄을 검색한다. 결과 링크는 원본 커밋의 해당 줄을 연다. |
| 문서 | FedOps 1.3 공식 Overview의 Agent Studio 설명, URL, 확인일을 제공한다. |
| Graphify | 같은 커밋에서 추출한 코드 관계의 양 끝점, 방향, 종류, 신뢰도와 근거 위치를 제공한다. `INFERRED`는 Graphify의 추론이다. |

미리보기 검색은 로컬에서 수행한다. 저장소와 그래프에서 질문의 식별자·경로 및 한국어 대응어로 최대 네 건씩 고른다. 특정 심볼을 아는 경우 질문에 정확한 이름을 넣으면 된다. 기본 조회에는 Python 표준 라이브러리와 저장소에 포함된 색인만 필요하다.

실제 작업은 저장소 검색 결과 대신 고정 커밋의 읽기 전용 원문 경로를 받는다. 질문용 Codex는 MCP 도구 `Grep`으로 Python·YAML 파일을 검색한 뒤 `Read`의 offset과 limit으로 주변 줄을 확인한다. 문서·Graphify·팀 결정은 기존처럼 입력에 포함된다. `python3 agent.py replay-loop --repository`로 8턴 제한 안에서 검색 → 읽기 → 출처 답변을 키 없이 재현할 수 있다.

색인과 저장소 원문 아카이브를 다시 만들 때는 아래 명령을 저장소 루트에서 실행한다. 처음 한 번 빈 캐시에서 시작하는 예다. Graphify 버전은 이번 추출에 사용한 버전으로 고정했다.

```sh
mkdir -p .context-cache
git clone https://github.com/gachon-CCLab/FedOps.git .context-cache/FedOps
python3 build_context.py repository .context-cache/FedOps
python3 -m venv .context-cache/venv
. .context-cache/venv/bin/activate
python -m pip install graphifyy==0.9.110
python build_context.py graph .context-cache/FedOps
```

그래프 재생성은 고정 커밋의 임시 체크아웃에서 Graphify의 `--code-only` 추출을 실행한다. 소스 경로와 줄 번호가 있는 관계를 배포용 색인에 담는다. 문서 요약을 갱신할 때는 `evidence/fedops-overview.md`의 원문과 확인일을 함께 대조한다.

### Codex 포크로 질문 실행

Linux x86-64에서 하네스와 같은 상위 디렉터리에 [Codex 포크](https://github.com/minsoojo/codex)를 체크아웃한다. 다른 위치는 `FEDOPS_CODEX_SOURCE`로 지정한다. Docker에 접근할 수 있는 계정으로 실행한다.

```sh
git clone --branch fedops-ask-runtime https://github.com/minsoojo/codex.git ../fedops-codex
git -C ../fedops-codex checkout "$(python3 -c 'import agent; print(agent.CODEX_REV)')"
python3 agent.py setup-ask
python3 viewer.py
```

`setup-ask`는 체크아웃의 커밋과 수정 여부를 검사하고 Rust 소스에서 실행 파일을 빌드한다. 질문 전용 OpenShell 샌드박스 이름에는 빌드 커밋 앞 8자리가 들어간다. 같은 빌드의 다른 인스턴스는 `FEDOPS_ASK_SANDBOX`로 선택할 수 있다.

뷰어에서 **질문 실행**을 누르면 선택한 실행의 응답 대기, 도구 결과와 최종 답변을 볼 수 있다. `result.json`의 `engine`과 `revision`이 실행 엔진과 빌드 출처를 기록한다. `runtime.log`에는 공급자 오류가 남는다. Codex는 요청당 출력 예산을 무료 모델 4,096토큰, 그 외 1,024토큰으로 지정하고 실행당 최대 8회 한도를 검사한다. 편집도 같은 Codex 빌드에서 요청을 최대 8회로 제한한다. recall은 Claude Code의 `--max-turns 8`을 사용한다.

### 질문별 병렬 조사

질문 하나를 보내면 OpenShell의 계획 세션이 필요한 출처를 선택한다. 하네스는 선택한 출처마다 독립된 Codex 프로세스를 동시에 시작한다. 저장소 담당은 고정 커밋에서 Grep·Read를 사용한다. docs 담당은 배포된 FedOps Overview를, Graphify 담당은 질문으로 검색한 그래프 근거를 읽는다. 합성 세션은 조사 결과와 팀 결정을 받아 출처가 있는 답변을 작성한다.

타임라인의 **선택된 조사 에이전트**에서 출처별 진행 상태와 결과를 볼 수 있다. 역할이 표시된 회차는 실행 전체의 요청 전송 순서다. 계획과 합성을 포함해 질문당 최대 8회이며 일부 조사가 실패하면 성공한 출처로 답하고 누락을 표시한다.

### Codex 편집 실습

`python3 agent.py setup-edit` 후 `python3 agent.py edit "weighted_average에서 각 지표를 보고한 클라이언트의 표본 수만 분모에 포함하고 보고한 0은 포함해 줘."`를 실행한다. 편집 모델은 `FEDOPS_EDIT_MODEL`로 선택한다. 셸이나 쓰기 도구를 제공하지 않고 Codex가 제안한 함수 본문을 하네스가 검사한 뒤 임시 복사본에 적용한다. 샌드박스 이미지의 원본 check.py로 채점한 결과는 실행 디렉터리의 before.log, after.log 및 change.patch에서 확인한다.
