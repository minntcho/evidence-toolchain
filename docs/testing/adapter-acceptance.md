# Adapter acceptance

Adapter acceptance tests prove that an optional provider, orchestration adapter,
or reader-backed real tool can enter the core harness without changing the core
evidence contract. They do not prove that the adapter is good enough for a
downstream policy, publication, audit, or receipt decision.

The current atomizer/normalizer/resolver helper is:

```text
run_basic_resolution_adapter_acceptance
```

It runs a small deterministic scenario through this path:

```text
adapter ports
-> LocalInvestigationRunner
-> run_resolution_cycle
-> ExperimentRunTrace
-> ExperimentExpectedBehavior comparison
-> AdapterAcceptanceReport
```

The reader-backed real tool smoke helper is:

```text
run_reader_resolution_adapter_acceptance
```

It treats a reader such as `PdfPlumberExtractReader` as the real local tool
adapter and proves that its inventory can travel through this path:

```text
PdfPlumberExtractReader
-> EvidenceInventory -> EvidenceAtom -> EvidenceResolutionGraph
-> ExperimentRunTrace
-> ExperimentExpectedBehavior comparison
-> AdapterAcceptanceReport
```

This helper is intentionally separate from
`run_basic_resolution_adapter_acceptance`. The basic helper checks
`LLMAtomizerPort`, `NormalizationAdapter`, and `ResolverPort` conformance. The
reader-backed helper checks whether a tool-created `EvidenceInventory` keeps
provenance and failure information all the way into trace and expected-behavior
reports.

The first real-tool smoke target is `PdfPlumberExtractReader`. It should record
successful text/word extraction, `pdfplumber_dependency_missing`, and
`pdf_text_extract_failed` as structured acceptance outcomes. A passing reader
smoke is still only a harness proof. It is not downstream policy sufficiency,
publication approval, audit approval, or a final validation authority.

## 강하게 assert할 것

- adapter objects satisfy the public port shape they claim to implement
- produced trace payload is JSON-serializable
- model/tool output keeps provenance through `EvidenceAtom`
- expected behavior checks fail when the adapter cannot support the basic case
- `AdapterAcceptanceReport` preserves both the trace and comparison report
- reader-backed real tool smoke preserves inventory issue codes in report metadata
- reader-backed real tool smoke fails expected behavior when a real reader
  produces no usable units

## freeze하지 말아야 할 것

- provider SDK choice
- framework node names
- prompt wording
- exact internal scheduling used by an external framework
- downstream policy thresholds
- exact pdfplumber internal word extraction ordering beyond the provenance
  fields needed by the reader contract

## 해서는 안 되는 일

Adapter acceptance must not import provider SDKs into the core package, treat a
passing fixture as downstream approval, or encode a product-specific validator
schema as core truth.

Reader-backed acceptance must not make `PdfPlumberExtractReader` the default PDF
route. The default `ingest_attachment` PDF route may stay a cheap profile path
while experiments and acceptance tests explicitly opt into the real reader.

Real adapters may live outside this package. Their tests can import the helper,
run their adapter ports against the shared scenario, and then add their own
provider-specific assertions outside the core suite.
