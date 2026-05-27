# 조사 루프 경계

이 문서는 LLM/VLM을 `evidence-toolchain` 어디에 놓을지 정합니다.
핵심 원칙은 단순합니다.

```text
LLM/VLM은 판사가 아니라 조사관입니다.
```

모델은 부족한 단서를 찾고, 애매한 영역을 읽고, 다음 조사 task를 제안할 수 있습니다.
하지만 모델 output이 곧 support, contradict, valid, publishable 같은 최종 판정이 되면 안 됩니다.

## 위치

LLM/VLM은 ingestion reader에 들어가지 않는다.
LLM/VLM은 resolver authority가 아니다.

모델은 다음 계층 사이의 조사 오케스트레이션에 놓입니다.

```text
EvidenceInventory
-> EvidenceAtom
-> NeedSpec
-> NormalizationResult
-> draft EvidenceResolutionGraph
-> EvidenceInvestigationLoop
-> 추가 EvidenceUnit / EvidenceAtom / NormalizationResult
-> resolver 재실행
-> EvidenceResolutionGraph
```

`EvidenceInvestigationLoop`는 baseline atomization, normalization, resolver가 드러낸
`missing/conflict/ambiguous clue`를 보고 다음에 어떤 artifact, unit, region, table row를
조사할지 정하는 계층입니다.

## 책임

조사 루프는 다음 일을 할 수 있습니다.

```text
missing need를 채우기 위한 task를 만든다.
이미지 또는 PDF page preview를 VLM observer에 보낸다.
text/table unit cluster를 LLM atomizer에 보낸다.
ambiguous date, period, alias 후보를 LLM normalizer에 보낸다.
새 observation을 EvidenceUnit으로 보존한다.
새 semantic candidate를 EvidenceAtom으로 보존한다.
새 comparison material을 NormalizationResult로 보존한다.
resolver를 다시 실행할 수 있는 state를 만든다.
```

조사 루프는 다음 일을 하면 안 됩니다.

```text
support/contradict edge를 직접 authorize하지 않는다.
ClaimResolution.status를 직접 확정하지 않는다.
reader 대신 파일 안전성, MIME, archive expansion을 판단하지 않는다.
model output을 provenance 없이 받아들이지 않는다.
model output을 곧바로 Downstream verdict로 내보내지 않는다.
```

model output은 EvidenceUnit, EvidenceAtom, NormalizationResult 중 하나로 내려와야 한다.
그 외 shape는 runner 내부 임시값으로만 취급하고 public-ish contract로 노출하지 않습니다.

VLM observation task result는 실제 `EvidenceUnit`, `EvidenceAtom`, `NormalizationResult`
후보를 `InvestigationTaskResult` 안에 담을 수 있습니다. 예를 들어 이미지 또는 PDF page
preview에서 본 내용은 `unit_type="visual_observation"` EvidenceUnit으로 보존하고, 그
observation에서 읽은 사용량 후보는 EvidenceAtom으로 보존합니다.
`LocalInvestigationRunner`는 visual task result에 포함된 produced unit과 atom을
`InvestigationState.inventory.units`와 `InvestigationState.atoms`에 append할 수 있습니다.
그래도 resolver edge나 claim status는 만들지 않습니다.

`ResolutionGapPlanner`는 EvidenceResolutionGraph gap을 NeedLedgerEntry와 InvestigationTask로 번역합니다.
이 bridge는 resolver가 만든 missing/contradict 상태를 조사 agenda로 낮출 뿐이며,
resolver를 다시 실행하거나 model/provider를 호출하지 않습니다.

`CandidateUnitRetriever`는 retrieve_candidate_units task를 EvidenceUnit 후보 선택으로 접지합니다.
입력은 `InvestigationTask`, `EvidenceInventory`, `NeedSpec`이고, 출력은
`EvidenceUnitRetrievalResult`입니다. 이 결과는 선택된 기존 unit id와 matched clue,
rejected unit id를 보존하고, 다음 `atomize_unit_cluster` task의 `target_unit_ids`를 만들 수
있습니다. retrieval은 EvidenceAtom이나 ResolutionEdge를 만들지 않습니다.

model output atom은 core atom vocabulary와 task의 `allowed_atom_types`를 통과해야 합니다.
또한 source_unit_ids 또는 source_artifact_ids provenance가 없으면 state에 append하지 않습니다.
이 gate는 모델 출력으로 판정하는 권한이 아니라, 출처와 vocabulary가 확인된 후보만 다음 resolver 입력으로
넘기는 ingestion 이후의 안전장치입니다.

## Controller

모델끼리 직접 서로 호출하지 않는다.

나쁜 구조는 다음과 같습니다.

```text
LLM -> VLM -> LLM -> VLM -> ...
```

좋은 구조는 다음과 같습니다.

```text
Controller
-> LLM planner port
-> tool/model executor
   -> VLM observer port
   -> LLM atomizer port
   -> LLM normalizer port
   -> deterministic tool adapter
-> state update
-> resolver rerun
-> Controller
```

Controller가 state와 budget을 들고 model/tool port를 호출한다.
모델은 task 결과를 반환할 뿐이고, 다음 반복 여부는 controller가 결정해야 합니다.

## Port 방향

core contract는 provider와 framework를 몰라야 합니다.

예상되는 port 이름은 다음처럼 둘 수 있습니다.

```text
LLMPlannerPort
VLMObserverPort
LLMAtomizerPort
LLMNormalizerPort
ResolverPort
```

각 port는 직접 provider SDK를 core에 끌어오지 않습니다. real provider adapter와 LangGraph adapter는 core contract 뒤에 붙인다.

```text
evidence_toolchain core contracts
<- local fake/test adapter
<- provider adapter
<- LangGraph adapter
```

반대 방향 의존성은 금지합니다.

```text
evidence_toolchain core -> OpenAI SDK
evidence_toolchain core -> LangGraph
evidence_toolchain readers -> VLM provider
evidence_toolchain resolution -> LLM planner
```

## 종료 조건

조사 루프는 무제한 반복되면 안 됩니다.

종료 조건은 다음처럼 명시되어야 합니다.

```text
모든 required need가 satisfied
명확한 contradiction
새 EvidenceUnit/EvidenceAtom/NormalizationResult가 없음
동일 task 반복 감지
max iterations 초과
model budget 초과
manual review required
```

이 종료 조건은 모델 판단이 아니라 controller의 state rule이어야 합니다.

## 현재 범위

현재 구현은 조사 루프 record contract와 model port contract를 제공합니다.

현재 구현된 contract는 다음과 같습니다.

```text
InvestigationState dataclass
InvestigationTask dataclass
InvestigationTaskResult dataclass
InvestigationEvent dataclass
NeedLedgerEntry
InvestigationBudget
InvestigationTaskType
InvestigationTaskStatus
NeedLedgerStatus
InvestigationEventType
InvestigationPlan
LLMPlannerPort
VLMObserverPort
LLMAtomizerPort
LLMNormalizerPort
FakeLLMPlanner
FakeVLMObserver
FakeLLMAtomizer
FakeLLMNormalizer
ResolverPort
EvidenceUnitRetrievalResult
CandidateUnitRetriever
LocalInvestigationRunner
```

이 contract들은 state snapshot, agenda, completed task, clue ledger, event, budget을
직렬화하기 위한 record와 테스트용 deterministic model port를 제공합니다.
fake adapter는 외부 모델을 호출하지 않습니다.
`LocalInvestigationRunner`는 agenda가 비어 있으면 planner port로 task를 계획하고,
agenda가 있으면 첫 task 하나를 fake/model port로 실행해 `InvestigationState`를 갱신합니다.
이 runner는 provider SDK, LangGraph, resolver 구현을 직접 import하지 않습니다.
LocalInvestigationRunner는 `CandidateUnitRetriever`가 주입되면 `retrieve_candidate_units` task를 실행할 수 있습니다.
이 실행은 기존 `EvidenceUnit` id만 선택하고, 선택된 unit이 있을 때 다음
`atomize_unit_cluster` task를 agenda 앞에 추가합니다. 선택된 unit이 없으면 completed task는
`no_new_clue`로 남고 follow-up task를 만들지 않습니다.
LocalInvestigationRunner는 `NormalizationAdapter`가 주입되고 agenda에 `normalize_candidate`
task가 있으면 선택된 `EvidenceAtom` 후보를 `NormalizationResult`로 낮출 수 있습니다.
이 실행도 resolver edge나 claim status를 만들지 않습니다.
normalizer가 주입된 runner는 `atomize_unit_cluster`가 accepted atom id를 만들면
그 id를 대상으로 하는 follow-up `normalize_candidate` task를 agenda 앞에 추가할 수 있습니다.
이미 같은 atom id를 대상으로 하는 normalize task가 agenda에 있으면 중복으로 만들지 않습니다.
ResolverPort가 주입된 runner는 `normalize_candidate` 완료 뒤 현재 state material로
draft `EvidenceResolutionGraph`를 갱신할 수 있습니다. 이때 runner는 resolver 구현을 직접
import하지 않고, 주입된 port 결과를 `draft_graph`에 저장하며 `state_updated` event를 남깁니다.
`run_agenda(max_steps=...)`는 이미 올라온 agenda만 deterministic하게 실행합니다.
이 helper는 `retrieve_candidate_units -> atomize_unit_cluster -> normalize_candidate` 같은 queued task chain을
로컬에서 검증하기 위한 것이며, run_agenda는 새 planner task를 요청하지 않습니다.
같은 task fingerprint가 다시 나타나면 `repeated_task_detected`로 멈춥니다.
runner가 agenda, completed task, unit, atom, normalization, event를 전혀 바꾸지 못하면 `no_progress_detected`로 멈춥니다.

다음은 아직 구현하지 않습니다.

```text
provider adapter
LangGraph adapter
```

provider adapter와 LangGraph adapter도 아직 구현하지 않습니다.

이 문서는 앞으로 구현될 investigation 계층의 권한 경계만 고정합니다.
다음 code slice는 resolver hard-gate 또는 investigation contract 중 하나가 될 수 있지만,
둘 중 어느 경우에도 이 문서의 원칙을 따라야 합니다.
