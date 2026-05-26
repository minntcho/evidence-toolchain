# 합성 증거 테스트킷

이 디렉터리는 개발과 테스트를 위한 합성 증거 document를 만듭니다.

이 testkit은 의도적으로 core extraction package 밖에 있습니다. Generator는 manifest를 sample document와 expected behavior file로 materialize할 수 있지만, core package는 이 testkit을 import하면 안 됩니다.

Manifest는 각 case의 source of truth입니다.

- `ground_truth`: synthetic world 안의 value를 설명합니다.
- `expected_behavior`: toolchain이 무엇을 observe, plan, flag해야 하는지 설명합니다.

이 둘은 분리되어야 합니다. 어떤 document는 known truth를 가지면서도 manual review가 필요할 수 있습니다.
