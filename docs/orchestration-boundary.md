# 오케스트레이션 경계

`evidence-toolchain`은 workflow framework가 바뀌어도 계속 유용해야 합니다.

Core package는 오케스트레이션 중립적인 증거 의미론을 정의합니다. evidence document에 무슨 일이 있었는지, 무엇이 pending인지, 어떤 tool이 실행되었는지, 무엇이 실패했는지, 어떤 report가 emitted되었는지를 설명해야 합니다. LangGraph, Prefect, Temporal, 또는 다른 runner DSL이 core meaning의 source가 되어서는 안 됩니다.

기본 설계 태도는 다음과 같습니다.

```text
core = 오케스트레이션 중립적인 증거 의미론
local runner = reference execution path
framework adapters = optional execution wrappers
```

## 이 경계가 필요한 이유

LLM/VLM-assisted routing은 첫 번째 semantic observation step이 될 수 있지만, 최종 validation authority가 아닙니다. Framework는 observation, schema validation, retry, capability execution, fallback selection, human review handoff를 실행하는 데 도움을 줄 수 있습니다. 그래도 output은 bounded evidence record여야 합니다.

Framework는 workflow를 orchestrate할 수 있습니다. 하지만 core evidence schema를 정의하거나, Downstream validity를 결정하거나, framework state를 public contract로 바꾸면 안 됩니다.

## Core runtime 기록

Core runtime contract는 serializable하고 framework independent해야 합니다.

### `EvidenceRunState`

`EvidenceRunState`는 evidence processing run의 현재 snapshot입니다.

나중에 포함해야 하는 정보:

- `run_id`
- input `EvidenceDocument`
- optional preflight summary
- current `EvidenceObservation`
- current `EvidenceToolPlan`
- completed `EvidenceStep` record
- pending `EvidenceStep` record
- `EvidenceToolResult` record
- issue
- interrupt 또는 review request
- emitted된 경우 final `EvidenceReport`

State는 serializable해야 합니다. 그래야 local test runner, checkpoint database, framework saver, durable workflow engine이 core semantics를 바꾸지 않고 저장할 수 있습니다.

### `EvidenceEvent`

`EvidenceEvent`는 run 중 발생한 일을 기록하는 append-only record입니다.

초기 event type:

- `document_received`
- `preflight_completed`
- `observation_created`
- `plan_created`
- `capability_started`
- `capability_completed`
- `capability_failed`
- `fallback_selected`
- `review_requested`
- `review_resumed`
- `report_emitted`

Event는 replay, debugging, audit review, runner implementation 비교에 유용합니다. Event history는 run을 설명할 수 있지만, Downstream approval의 별도 source가 되어서는 안 됩니다.

### `EvidenceStep`

`EvidenceStep`은 계획되었거나 실행된 work unit입니다.

예시:

- run preflight probe
- create LLM/VLM observation
- execute `docling_parse`
- execute `ocr_extract`
- execute `table_structure_extract`
- request manual review
- emit report

Step은 framework node id를 core concept로 embedding하지 말고 capability name과 routing reason을 reference해야 합니다.

### `EvidenceToolResult`

`EvidenceToolResult`는 capability의 framework-neutral output입니다.

보존해야 하는 정보:

- capability name
- 가능한 경우 capability version
- input document 또는 page reference
- status
- 가능한 경우 extracted text, table, field, span, region
- confidence metadata
- warning
- error
- produced artifact

Tool result는 JSON-compatible해야 합니다. 그래야 여러 runner가 framework-specific result object에 의존하지 않고 behavior를 비교할 수 있습니다.

## 런타임 port

Core는 framework-specific implementation을 채택하기 전에 작고 중립적인 port를 정의해야 합니다.

### `CapabilityRunner`

`EvidenceRunState`에 대해 capability를 실행하고 `EvidenceToolResult`를 반환합니다.

Capability는 가능한 경우 idempotent해야 합니다. capability가 artifact를 쓰는 경우 retry와 resume을 위해 artifact id 또는 path가 충분히 stable해야 합니다.

### `CheckpointStore`

`EvidenceRunState`를 저장하고 불러옵니다.

Local execution은 checkpoint를 memory 또는 file에 저장할 수 있습니다. LangGraph는 saver를 사용할 수 있습니다. Temporal은 workflow history를 사용할 수 있습니다. Prefect는 task state를 사용할 수 있습니다. Core는 checkpoint contract에만 의존해야 합니다.

### `EventSink`

Append-only `EvidenceEvent` entry를 기록합니다.

Event sink는 memory, JSONL, database, observability tool에 쓸 수 있습니다. Event payload는 framework-neutral해야 합니다.

### `ArtifactStore`

Page thumbnail, OCR text, structured table, intermediate JSON output 같은 generated artifact를 저장합니다.

Core는 framework task handle이 아니라 neutral id 또는 path로 stored artifact를 reference해야 합니다.

### `ReviewQueue`

Human review interrupt와 resume input을 나타냅니다.

Manual review는 evidence toolchain의 일부입니다. 하지만 review input은 neutral state와 event로 기록되어야 local runner와 framework runner가 같은 run contract를 resume할 수 있습니다.

### `RetryPolicy`

Retry limit, timeout behavior, fallback eligibility를 설명합니다.

Retry policy는 local runner와 durable workflow runner가 comparable decision을 내릴 수 있을 만큼 명시적이어야 합니다.

## Runner 역할

### Local runner 역할

Local runner는 reference implementation입니다.

오케스트레이션 framework 없이 같은 evidence semantics를 실행해야 합니다. Test는 local runner가 generated case bundle을 처리하고 expected event, state transition, report shape를 emitted할 수 있음을 증명해야 합니다.

### Framework adapter 역할

Framework adapters는 다른 execution guarantee로 같은 runner contract를 구현할 수 있습니다.

예시:

- graph-shaped agentic routing과 repair loop를 위한 LangGraph adapter
- batch-oriented extraction job을 위한 Prefect adapter
- durable long-running workflow를 위한 Temporal adapter

Adapter는 scheduling, persistence, parallelism, tracing, worker deployment behavior를 더할 수 있습니다. 하지만 같은 core record를 emitted해야 합니다.

## Framework 이식성

Workflow가 framework DSL이 아니라 core record와 port로 표현되면 framework replacement가 더 저렴해집니다.

그래도 어려운 부분은 남습니다.

- checkpoint behavior
- retry policy
- parallel capability execution
- human interrupt와 resume semantics
- timeout handling
- cache와 artifact store integration
- observability와 tracing
- deployment와 worker model

이 관심사들은 runtime port 뒤에 격리되어야 합니다. Framework 전환은 runner adapter 변경이어야 하며 evidence semantics rewrite가 되어서는 안 됩니다.

## 테스트 기대사항

Test가 강하게 assert할 수 있는 것:

- `EvidenceRunState` is serializable
- `EvidenceEvent` is append-only
- tool result is JSON-compatible
- local runner output matches expected generated case bundle
- framework adapters emit the same core event and report contracts

Test가 freeze하지 말아야 하는 것:

- framework node name
- framework checkpoint internal
- plan이 parallel execution을 허용할 때의 exact task scheduling order
- vendor-specific tracing metadata
- deployment topology

## 해서는 안 되는 일

Core package는 framework DSL을 authoritative workflow definition으로 만들면 안 됩니다.

Framework adapter는 `EvidenceObservation`, `EvidenceToolPlan`, `EvidenceToolResult`, `EvidenceReport`를 재정의하면 안 됩니다.

LLM/VLM routing은 observation과 plan을 propose할 수 있습니다. 하지만 최종 Downstream validation judgment를 만들면 안 됩니다. 최종 business, policy, audit, publication, commit decision은 core package 밖에 있습니다.
