## Context
호스트가 만든 brief를 worker에 전달하는 경로가 이미 있다.

## Goals / Non-Goals
첫 변경은 Overview 한 페이지를 다룬다. 검색과 자동 동기화는 후속 과제다.

## Decisions
원문에서 확인한 요약·버전·URL·확인일을 저장소에 두고 brief가 읽는다. 매번 모델이나 웹을 호출하지 않아도 같은 입력을 재현할 수 있다.

## Risks / Trade-offs
문서가 바뀌면 요약이 오래될 수 있다. 갱신 시 원문을 대조하고 확인일을 수정한다.
