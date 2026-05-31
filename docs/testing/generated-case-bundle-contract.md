# 생성 case bundle 계약

Generated case bundle은 synthetic evidence generation이 commit하는 test target입니다. Generator는 내부적으로 manifest, renderer, helper model을 사용할 수 있지만, test는 먼저 generator가 produced한 file에 의존해야 합니다.

## Artifact 구조

각 generated case는 하나의 case directory를 만들어야 합니다.

```text
generated/<case_id>/
+-- evidence.<ext>
+-- expected.json
+-- experiment.json
`-- expected-behavior.json
```

Case directory는 가장 작은 complete generated artifact입니다. Input material과 comparison target을 함께 두어 test가 real consumer가 실행할 path와 같은 path를 실행할 수 있게 합니다.

```text
manifest
-> generator
-> generated/<case_id>/evidence.<ext>
-> EvidenceDocument.from_path
-> observe_document
-> plan_document
-> compare with generated/<case_id>/expected.json
```

The same generated directory can drive the experiment harness:

```text
generated/<case_id>/experiment.json
-> evidence-toolchain run-experiment
-> ExperimentRunTrace
-> compare with generated/<case_id>/expected-behavior.json
```

## Evidence 파일

`evidence.<ext>`는 toolchain이 읽는 file입니다.

첫 generator foundation에서는 `evidence.txt`를 control fixture로 사용하는 것이 허용됩니다. PDF, OCR, image dependency를 추가하지 않고 deterministic metadata와 content를 담을 수 있기 때문입니다. 이후 milestone에서는 `evidence.pdf`, `evidence.jpg`, `evidence.png`, spreadsheet format을 format family별 slice로 추가할 수 있습니다.

Extension은 test surface의 일부입니다. Tool selection은 container, media type, document condition을 자주 보존하므로, 새 file format은 하나의 broad generator rewrite로 묶기보다 separate slice로 진입해야 합니다.

## Expected 파일

`expected.json`는 generated case의 test oracle입니다.

이 file은 generated artifact, Ground truth, Expected toolchain behavior를 설명해야 합니다. Core package가 Downstream decision을 내리게 해서는 안 됩니다.

Minimum shape:

```json
{
  "case_id": "utility_bill_basic",
  "artifact": {
    "path": "evidence.txt",
    "format": "txt",
    "media_type": "text/plain",
    "document_kind": "utility_bill"
  },
  "ground_truth": {
    "amount": 6.4,
    "unit": "MWh"
  },
  "expected_observation": {
    "document_class": "utility_bill",
    "has_text_layer": true,
    "quality": "clean",
    "signals": []
  },
  "expected_plan": {
    "selected_capabilities": [
      "docling_parse",
      "table_structure_extract",
      "utility_bill_extract"
    ],
    "fallbacks": [],
    "issues": []
  }
}
```

Ground truth는 synthetic world가 알고 있는 value입니다. Expected toolchain behavior는 evidence toolchain이 observe, plan, extract, issue, 또는 review로 보내야 하는 behavior입니다. 이 둘을 분리하면 synthetic truth가 automatic trust가 되는 일을 막습니다.

## Experiment harness files

`experiment.json`는 generated evidence file과 최소 declared claim을 묶습니다. 현재 slice에서는 deterministic resolution cycle이 안정적으로 처리하는 `amount` + `unit` claim만 생성합니다. site, supplier, activity, period truth는 `expected.json`에 남아 있지만, 아직 resolver authority로 승격하지 않습니다.

`expected-behavior.json`는 generated case가 현재 harness에서 만들어야 하는 expected behavior expectation입니다. Resolution fixture는 `claim_resolutions`를 쓸 수 있고, convergence fixture는 `claim_convergences`를 쓸 수 있습니다. 이 파일은 `run-experiment`와 `run-convergence`의 `--expected` 입력으로 사용할 수 있습니다.

Example:

```powershell
evidence-toolchain run-experiment .\generated\utility_bill_basic\experiment.json `
  --trace-out .\generated\utility_bill_basic\out\trace.json `
  --expected .\generated\utility_bill_basic\expected-behavior.json `
  --expected-report-out .\generated\utility_bill_basic\out\expected-report.json
```

```powershell
evidence-toolchain run-convergence .\generated\convergence_clean_support\experiment.json `
  --trace-out .\generated\convergence_clean_support\out\trace.json `
  --expected .\generated\convergence_clean_support\expected-behavior.json `
  --expected-report-out .\generated\convergence_clean_support\out\expected-report.json
```

Convergence file-backed fixtures currently cover:

```text
convergence_clean_support
convergence_nonblocking_issue
convergence_candidate_conflict
```

The bad patch rejected convergence slice is intentionally runner-level because
it needs a fake `PatchProducer`. It is still checked through
`ExperimentExpectedBehavior.claim_convergences`, not by projecting into
`EvidenceResolutionGraph`.

## 강하게 assert할 것

Test는 다음을 강하게 assert할 수 있습니다.

- generated case directory existence
- `evidence.<ext>` existence
- `expected.json` existence
- `experiment.json` existence
- `expected-behavior.json` existence
- stable `case_id`
- expected artifact format과 media type
- Ground truth와 Expected toolchain behavior separation
- 현재 format slice에 대한 selected capability, fallback, issue
- generated experiment files can drive `run-experiment`
- convergence fixture files can drive `run-convergence`

## freeze하지 말아야 할 것

Test는 다음을 freeze하지 말아야 합니다.

- generated evidence file의 exact line wrapping
- synthetic document 안의 cosmetic name
- final renderer internal
- future PDF, image, spreadsheet generation library
- Downstream adapter schema
- future full-claim resolver coverage for site, supplier, activity, or period

## 해서는 안 되는 일

Generated case bundle은 core runtime authority가 되면 안 됩니다.

Core package는 test에서 `evidence.<ext>`를 읽을 수 있지만 synthetic generator를 import하거나 `expected.json`을 runtime policy source로 취급하면 안 됩니다.

`expected.json`는 OCR, table extraction, manual review가 expected라고 말할 수 있습니다. 하지만 business claim이 finally valid, committed, reportable, policy-approved하다고 말하면 안 됩니다. 그런 Downstream judgment는 core package 밖의 adapter, validator, review workflow에 속합니다.

`expected-behavior.json`도 마찬가지로 runtime authority가 아닙니다. 그것은 generated case가 현재 local harness에서 기대하는 비교값일 뿐입니다.
