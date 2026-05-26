# 합성 증거 테스트킷

합성 증거 테스트킷은 core document-evidence pipeline을 위한 development fixture를 만듭니다.

이 testkit은 이 프로젝트에 repeatable messy evidence case가 필요하기 때문에 존재합니다.

- clean utility bill
- scanned 또는 rotated bill
- quantity/price ambiguity가 있는 fuel receipt
- handwritten meter log
- future blurred, cropped, low-resolution, table-risk case

Testkit은 runtime extraction engine의 일부가 아닙니다. Test와 developer tooling을 위한 experiment surface입니다. Synthetic case는 runtime authority를 정의하지 않습니다.

## 경계

허용되는 dependency direction:

```text
tests -> synthetic generator -> generated files
tests -> evidence_toolchain
CLI/dev tool -> synthetic generator -> generated files
```

금지되는 dependency direction:

```text
evidence_toolchain core -> synthetic generator
```

Core package는 real evidence document에 대해 reusable하게 유지되어야 합니다. Synthetic case는 core를 test하는 데 도움을 주지만 runtime authority를 정의하지 않습니다.

## Manifest 계약

각 case는 `synthetic/manifests/` 아래 manifest에서 시작합니다.

Manifest는 truth와 expected behavior를 분리합니다.

```json
{
  "case_id": "utility_bill_basic",
  "document_kind": "utility_bill",
  "ground_truth": {
    "amount": 6.4,
    "unit": "MWh"
  },
  "expected_behavior": {
    "plan_includes": [
      "docling_parse",
      "table_structure_extract",
      "utility_bill_extract"
    ],
    "fallbacks_include": [],
    "issues_include": []
  }
}
```

이 분리가 중요합니다. 어떤 synthetic case는 known ground truth를 가지면서도 manual review가 필요할 수 있습니다. 예를 들어 handwritten meter log는 synthetic world 안에서는 known usage value를 가질 수 있지만, expected behavior는 여전히 review path를 포함해야 합니다.

## 생성

Default case 생성:

```bash
python tools/generate_evidence_cases.py
```

Selected case 생성:

```bash
python tools/generate_evidence_cases.py utility_bill_basic handwritten_meter_log
```

기본적으로 generated case bundle은 다음 위치에 written됩니다.

```text
tests/fixtures/generated/<case_id>/
+-- evidence.txt
`-- expected.json
```

이 directory는 git에서 ignored됩니다. Manifest와 generator code가 committed source of truth입니다.

## 현재 case

- `utility_bill_basic`
- `scanned_utility_bill_rotated`
- `handwritten_meter_log`
- `receipt_quantity_vs_price`

Default CLI command는 baseline test run을 작게 유지하기 위해 첫 세 case를 생성합니다.
