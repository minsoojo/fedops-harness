## Context

기존 worker는 Claude 전용 로그에서 요청 시점을 추출한다. UI는 model_request, model_response, tool_use, tool_result와 done을 읽는다.

## Goals / Non-Goals

ask의 엔진을 교체한다. edit와 recall은 기존 샌드박스를 사용한다.

## Decisions

사용자 포크의 고정 소스로 실행 파일을 빌드한다. OpenRouter 요청 직전에 회차를 알리고 실제 도구 반환과 최종 텍스트를 같은 실행에 기록한다. 질문용 공급자에는 전용 실행 파일만 등록한다. OpenRouter에는 두 MCP 도구를 일반 함수로 광고하고 선택된 호출만 같은 이름의 저장소 도구에 연결한다.

실제 요청에서 OpenRouter가 기본 65,536토큰의 출력을 예약해 HTTP 402를 반환했다. 유료 모델에는 최대 출력 1,024토큰을 지정한다. 무료 라우터에서는 512토큰 소진으로 최종 답변이 잘려 기본값을 4,096토큰으로 높였다. 실행당 모델 요청 8회 제한과는 별개다.

## Risks / Trade-offs

OpenRouter의 Responses 호환성, 바이너리 출처, 도구 범위와 8회 제한을 독립적으로 확인한다. 라이브 실패는 성공 결과로 기록하지 않는다.
