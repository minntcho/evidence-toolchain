# Synthetic Evidence Case

Synthetic evidence case는 개발을 위한 repeatable test world를 만듭니다.

Real evidence document는 지저분하고, private하고, 공유하기 어렵습니다. Synthetic case는 core를 한 domain에 묶지 않으면서 routing, extraction contract, failure mode, review trigger를 테스트하게 해 줍니다.

## Case 구조

각 case는 다음을 분리해야 합니다.

- `ground_truth`: synthetic world 안의 value
- `expected_behavior`: toolchain이 observe, plan, extract, issue, 또는 review로 보내야 하는 behavior
- generated document: materialized evidence input
- expected manifest: test를 위한 materialized comparison target

이 분리가 중요합니다. Known synthetic truth가 있다고 해서 toolchain이 document를 자동으로 trust해야 하는 것은 아닙니다.

## 강하게 assert할 것

Strong assertion은 다음을 확인해야 합니다.

- manifest-driven generation
- stable case id
- generated document existence
- generated expected manifest existence
- `ground_truth`와 `expected_behavior` separation
- baseline case의 expected capability
- degraded case의 expected issue

## freeze하지 말아야 할 것

Weak assertion은 다음을 freeze하지 말아야 합니다.

- generated document의 exact line wrapping
- synthetic business name
- real renderer가 생기기 전 fixture file extension
- final Downstream schema name
- visual degradation implementation detail

## 해서는 안 되는 일

Synthetic case는 core runtime authority가 되면 안 됩니다.

Core package는 synthetic generator를 import하면 안 됩니다. Synthetic manifest는 test world를 정의할 수 있지만, real policy, commit, receipt, publication decision은 Downstream system이 소유합니다.
