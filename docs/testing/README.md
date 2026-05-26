# 테스트 전략

테스트 문서는 검증 전략을 설명하지 runtime authority를 정의하지 않는다.

Test suite는 프로젝트가 목적에 맞게 유지되도록 보호해야 합니다. 그 목적은 domain-neutral evidence-input consistency, provenance, uncertainty, failure reporting입니다.

Test는 toolchain의 역할을 정의하는 behavior를 보호해야 합니다. Extraction tool이 좋아지면서 바뀔 수 있는 implementation detail을 freeze하면 안 됩니다.

## 읽는 순서

1. [Synthetic Evidence Cases](synthetic-evidence-cases.md)
2. [Router and Planner Test Strategy](router-planner-test-strategy.md)
3. [Failure Mode Test Strategy](failure-mode-test-strategy.md)
4. [Generated Case Bundle Contract](generated-case-bundle-contract.md)

## 테스트 authority 규칙

Test는 synthetic world와 fixture document의 expected behavior를 정의할 수 있습니다. 하지만 real Downstream decision을 위한 runtime authority가 되어서는 안 됩니다.

강한 assertion은 다음을 보호해야 합니다.

- core import boundary
- manifest truth와 expected behavior의 분리
- 알려진 evidence condition에 대한 capability selection
- issue preservation
- review trigger
- report shape와 provenance

약한 assertion은 다음을 허용해야 합니다.

- internal module layout
- explanation의 exact wording
- future extraction backend choice
- final Downstream schema
- product-specific UI 또는 workflow label

## 해서는 안 되는 일

Test는 한 Downstream consumer의 policy를 core truth로 encode하면 안 됩니다. Consumer policy는 adapter 또는 Downstream test suite에 속합니다.
