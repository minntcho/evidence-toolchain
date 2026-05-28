# Synthetic Evidence Artifact Factory

이 문서는 합성 증거 테스트킷의 다음 확장 축을 정의합니다.

목표는 `clean text`를 조금 더럽히는 helper가 아니라, 현실 intake에서 들어오는 지저분한
파일 묶음을 deterministic하게 만드는 artifact factory입니다.

```text
ScenarioSpec
-> ScenarioIR
-> BundlePlan
-> ToolPlan
-> GeneratedArtifactBundle
-> VerificationReport
```

요약하면 `ScenarioSpec -> ScenarioIR -> BundlePlan -> ToolPlan` 순서로 낮춘 뒤
deterministic tool을 실행합니다.

생성 쪽은 AI를 쓰지 않습니다. `reportlab`, `Pillow`, `OpenCV`, `openpyxl`, Python email
library 같은 deterministic tool을 사용할 수 있습니다. 추출 쪽 runtime harness는 생성된
`input/` artifact만 evidence-toolchain에 넣고, 필요하면 OCR, VLM, LLM, parser, table
extractor, capability runner를 사용할 수 있습니다.

## 경계

이 factory는 synthetic testkit입니다. `evidence_toolchain` core package의 runtime contract가
아닙니다.

허용되는 방향:

```text
tests / synthetic CLI -> synthetic artifact factory -> generated input artifacts
tests / runtime harness -> evidence-toolchain -> evidence state
```

금지되는 방향:

```text
evidence_toolchain core -> synthetic artifact factory
evidence_toolchain core -> _synthetic latent oracle
ScenarioSpec -> direct reportlab/Pillow/OpenCV/openpyxl/email lib call
```

ScenarioSpec이 직접 reportlab, Pillow, OpenCV, openpyxl, email lib를 호출하면 안 된다.
명세서는 현실 intake 상황을 말하고, compiler와 planner가 그 의도를 실행 가능한
ToolInvocationDAG로 낮춥니다.

## 계층

### ScenarioSpec

`ScenarioSpec`은 사람이 쓰는 외부 intake 상황 명세입니다.

포함할 수 있는 것:

```text
scenario_id
seed
intake_story
document roles
lifecycle events
evidence_need
confusions
expected_syndrome
```

포함하지 말아야 하는 것:

```text
OpenCV function name
reportlab canvas command
Pillow filter name
exact affine matrix
hidden sheet implementation detail
```

예를 들어 `quality_profile: fax_scan_medium`은 허용됩니다. `gaussian_blur_sigma: 1.4`나
`cv2.warpAffine` 같은 구현 세부사항은 기본 명세 언어가 아닙니다. 특정 회귀 테스트에서
operator stack을 고정해야 할 때만 optional implementation hint로 둘 수 있습니다.

### ScenarioIR

`ScenarioIR`은 명세를 정규화한 내부 표현입니다. 이 단계는 파일 형식과 tool을 모릅니다.

담는 것:

```text
intake events
document intents
evidence_need
latent evidence roles
confusion graph
expected syndrome
```

`later_correction_overrides_initial` 같은 confusion은 여기에서 evidence role graph로
정규화됩니다. 예를 들어 statement의 summary value는 superseded value이고, xlsx raw sheet의
value는 corrected value이며, correction email은 corrected source를 가리킨다는 관계를
표현합니다.

### BundlePlan

`BundlePlan`은 각 artifact가 어떤 논리 문서와 역할을 가져야 하는지 설명합니다.

담는 것:

```text
artifact_id
carrier goal
document archetype
evidence roles to realize
logical document requirements
confusion requirements
carrier profile
expected postconditions
```

이 단계도 아직 concrete library call은 모릅니다. `supplier_monthly_statement`가 title, period,
table, footnote를 가져야 한다는 논리 요구사항과, `scanned_pdf` carrier goal이 있다는 사실만
알면 됩니다.

### ToolPlan

`ToolPlan`은 `BundlePlan`을 실제 deterministic tool 호출 DAG로 낮춘 결과입니다.

```text
ToolInvocationDAG
  archetype builder
  EvidenceConfusionOperator
  Renderer
  CarrierOperator
  packager
  verifier
```

예시:

```text
archetype.supplier_monthly_statement.build
-> confusion.unit_context_detached
-> renderer.pdf_text
-> carrier.pdf.rasterize
-> carrier.image.skew
-> carrier.image.downsample_upscale
-> carrier.image.salt_pepper_noise
-> carrier.pdf.image_only_packager
-> verifier.scanned_pdf
```

Executor는 ToolPlan의 DAG를 실행할 뿐입니다. Scenario 의미를 다시 해석하거나 Downstream
판단을 만들면 안 됩니다.

## Tool 인터페이스

각 tool은 입력 state와 출력 state를 선언해야 합니다. 그래야 planner가 `csv_bom`을
`page_image_bundle`에 붙이는 식의 잘못된 조합을 막을 수 있습니다.

```text
ToolDescriptor
  id
  kind
  version
  implementation_digest
  input_state
  output_state
  supported_carriers
  params_schema
  postconditions
  deterministic
```

`implementation_digest`는 같은 spec과 seed로 다른 결과가 나왔을 때 tool 구현 변경인지,
입력 변경인지 구분하기 위한 값입니다.

### ArtifactState

Tool은 path만 주고받지 않습니다. carrier, trace, metadata가 붙은 state를 주고받습니다.

```text
ArtifactState
  state_type
  artifact_id
  model_ref
  file_ref
  carrier
  TraceLayer
  metadata
```

가능한 state transition 예:

```text
logical_document_model
-> pdf_text_artifact
-> page_image_bundle
-> scanned_pdf_artifact
```

### ToolInvocation

`ToolInvocation`은 ToolPlan DAG의 한 node입니다.

```text
ToolInvocation
  id
  tool_id
  input_state_id
  output_state_id
  params
  seed
  required_postconditions
```

모든 random은 invocation seed와 ToolContext의 rng에서 나와야 합니다. 전역 random을 쓰면
재현 가능한 synthetic fixture가 아닙니다.

### ToolResult

Tool은 output state와 검증 가능한 실행 정보를 반환합니다.

```text
ToolResult
  output_state
  trace_delta
  postconditions
  metrics
  warnings
```

## TraceLayer

TraceLayer는 어떤 evidence slot이 생성물의 어디에 심겼는지 보존합니다. OCR/VLM/parser를
테스트하려면 파일만으로는 부족합니다. 생성 쪽은 deterministic하게 carrier trace를 남겨야
합니다.

Carrier별 locator vocabulary는 다를 수 있습니다.

```text
PDF / image:
  page, bbox, polygon, transform matrix

XLSX:
  sheet, cell, range, formula, hidden state

EML:
  MIME part, body span, quote block, attachment link

CSV:
  row, column, byte offset, encoding marker
```

CarrierOperator는 파일을 바꾸면 trace도 함께 변환해야 합니다. 예를 들어 `skew`가 image에
affine transform을 적용했다면 bbox는 이전 bbox 그대로가 아니라 transform된 polygon으로
남아야 합니다.

## Operator 종류

### EvidenceConfusionOperator

EvidenceConfusionOperator는 carrier를 망가뜨리지 않습니다. evidence 의미 관계를 꼽니다.

예:

```text
later_correction_overrides_initial
quoted_old_value_remains
body_attachment_conflict
summary_stale_raw_corrected
unit_context_detached
```

이 operator는 `ScenarioIR`을 직접 훼손하기보다 `BundlePlan`에 logical requirements,
role assignment, expected syndrome delta를 추가해야 합니다. ScenarioIR은 latent truth와
lifecycle graph의 안정 정규형으로 남습니다.

### CarrierOperator

CarrierOperator는 실제 carrier나 intermediate artifact를 변경합니다.

예:

```text
pdf_text_artifact -> page_image_bundle
page_image_bundle -> page_image_bundle
xlsx_artifact -> xlsx_artifact
eml_artifact -> eml_artifact
csv_artifact -> csv_artifact
```

가능한 operator:

```text
rasterize_pdf
skew_image
downsample_upscale
salt_pepper_noise
glare_overlay
xlsx_hidden_sheet
csv_bom
email_quote_chain
pdf_hidden_text_layer
```

CarrierOperator는 자기 postcondition만 검증합니다. 전체 bundle syndrome을 판단하지 않습니다.

## Verifier

Verifier는 generation-side 검증과 runtime-side 검증을 분리합니다.

### Operator postcondition verifier

각 operator가 약속한 postcondition만 확인합니다.

```text
skew_image:
  transform matrix applied
  image geometry changed
  trace polygon updated

xlsx_hidden_sheet:
  workbook has hidden sheet

csv_bom:
  file starts with UTF-8 BOM
```

### ArtifactVerifier

ArtifactVerifier는 생성된 파일 carrier가 실제로 열리고 의도한 구조를 갖는지 확인합니다.

```text
PDF:
  opens
  page count matches
  image-only when required

XLSX:
  openpyxl opens
  sheet, cell, merged range, hidden state match

EML:
  MIME parses
  attachment exists
  quote block exists

CSV:
  encoding, delimiter, header, footer match
```

### Syndrome precondition verifier

Syndrome precondition verifier는 extraction 결과를 보지 않습니다. 이 case가 expected syndrome을
만들 조건을 실제로 갖췄는지 확인합니다.

예:

```text
conflicting_values:
  same evidence_need has old_value and corrected_value
  values are distinct
  values are placed in distinct source roles

quoted_old_value_should_not_win:
  old_value exists in quote zone
  correction email is the newer lifecycle event
  quote zone has trace locator
```

### Runtime result verifier

Runtime result verifier는 생성된 `input/` artifact를 evidence-toolchain에 태운 뒤 확인합니다.

검증 대상은 evidence-side behavior입니다.

```text
conflict issue observed
manual review required
quoted old value is not treated as latest corrected source
resolution remains non-final when correction relation is unresolved
```

`auto_commit_allowed`, `policy_approved`, `publication_ready` 같은 Downstream authority field는
expected syndrome에 넣지 않습니다.

## Generated bundle 계약

생성 결과는 core runtime input과 synthetic-only truth를 분리해야 합니다.

```text
generated/
  supplier_correction_bundle_001/
    input/
      statement.pdf
      breakdown.xlsx
      correction_email.eml

    expected/
      expected_syndrome.json
      expected_runtime_contract.json

    _synthetic/
      scenario_spec.yaml
      scenario_ir.json
      bundle_plan.json
      tool_plan.json
      manifest.json
      carrier_trace.json
      latent_oracle.json
      verification_report.json
```

`evidence-toolchain core는 input artifact만` 읽어야 합니다. Runtime harness도 가능하면
`input/`과 `expected/`만 별도 temp directory로 복사해서 실행해야 합니다.

`_synthetic/`은 generator와 verifier 전용입니다. `_synthetic/latent_oracle.json`은 runtime
authority가 아니며, evidence-toolchain core가 읽으면 안 됩니다.

## 초기 구현 순서

처음부터 PDF, image, XLSX, EML을 모두 구현하지 않습니다.

권장 순서:

```text
1. ScenarioSpec / ScenarioIR / BundlePlan / ToolPlan 문서와 skeleton
2. ToolDescriptor, ArtifactState, ToolInvocationDAG, TraceLayer contract
3. CSV 또는 XLSX carrier 하나로 proof
4. PDF text renderer와 scanned PDF carrier profile
5. EML correction bundle
6. Runtime harness와 expected syndrome predicate verifier
```

Phase 1은 fixed stack이어도 됩니다. Capability-based planning은 나중에 붙입니다.

```text
Phase 1:
  ScenarioSpec -> BundlePlan -> fixed ToolPlan

Phase 2:
  ToolDescriptor + registry로 input/output state 검사

Phase 3:
  quality_profile을 capability-based ToolInvocationDAG로 compile

Phase 4:
  runtime harness가 expected_syndrome predicate를 확인
```

## 해서는 안 되는 일

```text
ScenarioSpec이 direct tool call script가 되면 안 됩니다.
clean_text를 받아 dirty_text만 만드는 helper로 축소하면 안 됩니다.
_synthetic oracle을 evidence-toolchain runtime input으로 넘기면 안 됩니다.
Generator truth를 Downstream validation authority처럼 사용하면 안 됩니다.
모든 file type과 carrier degradation을 첫 PR에 넣으면 안 됩니다.
```

이 factory의 목적은 실제 더러운 파일 묶음을 재현하는 것입니다. 하지만 그 파일이 어떤
Downstream policy 아래에서 충분한지는 여전히 이 저장소 밖의 판단입니다.
