# Router와 Planner 테스트 전략

Router와 planner test는 toolchain이 capability를 선택하기 전에 evidence condition을 먼저 본다는 점을 증명합니다.

목표는 모든 implementation detail을 freeze하는 것이 아닙니다. 목표는 이 프로젝트를 single-parser wrapper가 아니라 evidence-processing engine으로 만드는 observable behavior를 보존하는 것입니다.

## 강하게 assert할 것

Strong assertion은 다음을 확인해야 합니다.

- born-digital document는 structure-aware parsing을 선택할 수 있다
- scanned document는 OCR을 선택할 수 있다
- receipt-like document는 receipt extraction을 선택할 수 있다
- handwritten log는 handwriting과 review path를 선택할 수 있다
- meter photo는 visual과 meter-reading path를 선택할 수 있다
- risk가 남아 있을 때 fallback capability가 visible하게 남는다
- plan은 각 selected capability가 선택된 reason을 보존한다

이 assertion들은 observation -> planning -> extraction boundary를 보호합니다.

## freeze하지 말아야 할 것

Weak assertion은 다음을 freeze하지 말아야 합니다.

- private helper function name
- exact internal planner rule order
- future planner가 rule-based, model-assisted, hybrid 중 무엇인지
- exact prompt 또는 classifier implementation detail
- Downstream adapter shape

## 해서는 안 되는 일

Planner test는 final Downstream approval을 assert하면 안 됩니다.

Planner는 OCR, table extraction, manual review가 필요하다고 판단할 수 있습니다. 하지만 domain claim이 finally valid, committed, published, policy-approved하다고 결정하면 안 됩니다.
