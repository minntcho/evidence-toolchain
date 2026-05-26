# evidence-toolchain

`evidence-toolchain`는 독립적인 document-evidence 처리 엔진입니다.

이 프로젝트는 지저분한 증거 문서를 관찰하고, 추출 전략을 고른 뒤, document tool을 실행하고, Downstream 시스템이 소비할 수 있는 중립적인 `EvidenceReport`를 냅니다.

핵심 흐름은 단순합니다.

```text
Evidence document
-> 문서 상태 관찰
-> tool 사용 계획 수립
-> extraction capability 실행
-> 추출된 field 통합
-> provenance와 issue를 포함한 EvidenceReport 발행
```

이 저장소는 특정 validator, LCA platform, ESG compiler, 또는 Downstream product에 묶이지 않습니다.

## 이 프로젝트가 해야 하는 일

- tool을 고르기 전에 evidence document를 먼저 검사한다.
- document parsing, OCR, table extraction, vision extraction, handwriting extraction, barcode/QR reading, manual review 같은 적절한 capability로 문서를 라우팅한다.
- 가능한 경우 page, bounding box, confidence, source span, tool provenance를 포함해 candidate field를 추출한다.
- failure mode를 best-effort 답변 뒤에 숨기지 않고 structured issue로 보존한다.
- 여러 consumer가 사용할 수 있는 중립적인 output을 만든다.

## 이 프로젝트가 하지 말아야 할 일

- 최종 validation authority가 되지 않는다.
- business claim이 true, compliant, publishable한지 결정하지 않는다.
- governance decision, commit receipt, audit ledger, policy verdict를 발행하지 않는다.
- core package가 특정 Downstream project에 의존하게 만들지 않는다.

Downstream system은 추출된 증거가 declared input을 지지하는지, 반박하는지, 또는 지지하지 못하는지 판단할 수 있습니다. 이 프로젝트는 그 판단의 evidence side만 준비합니다.

## 초기 문서

- [문서 색인](docs/index.md)
- [목적과 경계](docs/purpose-and-boundaries.md)
- [아키텍처](docs/architecture.md)
- [증거 라우팅](docs/evidence-routing.md)
- [오케스트레이션 경계](docs/orchestration-boundary.md)
- [Capability 레지스트리](docs/capability-registry.md)
- [실패 모드](docs/failure-modes.md)
- [Adapter 경계](docs/adapter-boundary.md)
- [합성 증거 테스트킷](docs/synthetic-evidence.md)

## 개발 빠른 시작

기본 synthetic evidence case를 생성하고 테스트를 실행합니다.

```bash
python tools/generate_evidence_cases.py
python -m pytest -q
```

생성된 case bundle은 기본적으로 `tests/fixtures/generated/` 아래에 놓입니다. 이 파일들은 runtime state가 아니라 development fixture입니다.

## 방향성

이 프로젝트는 도메인 중립적인 evidence-input consistency를 위한 재사용 가능한 evidence-document front end가 되어야 합니다.

```text
requested or declared input
+ evidence documents
-> evidence-toolchain
-> provenance, confidence, issue, review trigger를 포함한 EvidenceReport
-> downstream validator, audit UI, review workflow, adapter, or domain compiler
```

가장 안전한 설계 태도는 다음과 같습니다.

```text
Tools extract.
Reports preserve.
Adapters translate.
Downstream systems judge.
```

테스트를 위해 이 저장소는 합성 증거 테스트킷도 포함합니다.

```text
Synthetic manifest가 truth와 expected behavior를 정의한다.
Generator가 sample evidence document를 materialize한다.
Test가 observation, planning, issue, import boundary를 검증한다.
Core runtime은 synthetic testkit을 import하지 않는다.
```
