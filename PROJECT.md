# FedOps 프로젝트 근거

가천대 CCL의 FedOps는 Flower 기반 연합학습의 클라이언트와 서버, 학습 진행, 성능 모니터링을 다룬다. 이 발표에서 담당할 범위는 시뮬레이션의 클라이언트 평가 지표 집계다.

| 확인할 내용 | 근거 |
|---|---|
| 평가 지표가 집계 함수로 들어오는 위치 | CIFAR100 예제 설정의 `strategy.evaluate_metrics_aggregation_fn`이 `weighted_average`를 지정한다. |
| 현재 코드가 누락된 지표를 처리하는 방식 | `evidence/aggregation.py`의 `weighted_average`는 해당 지표가 있는 클라이언트만 분자에 넣고, 분모에는 전체 표본 수를 넣는다. |
| 팀이 바라는 동작과 결정 배경 | 담당자가 명시적으로 저장한 결정에서 확인한다. 코드만으로 팀의 의도를 확정할 수 없다. |

기준 커밋은 `3cd08420ecb5662b5b28c10a9303e28e610313b2`다. [저장소](https://github.com/gachon-CCLab/FedOps/tree/3cd08420ecb5662b5b28c10a9303e28e610313b2) · [설정 41–43행](https://github.com/gachon-CCLab/FedOps/blob/3cd08420ecb5662b5b28c10a9303e28e610313b2/simulation/examples/CIFAR100/conf/config.yaml#L41-L43) · [집계 함수](https://github.com/gachon-CCLab/FedOps/blob/3cd08420ecb5662b5b28c10a9303e28e610313b2/src/python/fedops/simulation/fl_strategy/aggregation.py#L25-L56)
