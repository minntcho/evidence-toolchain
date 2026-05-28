# Adapter acceptance

Adapter acceptance tests prove that an optional provider or orchestration
adapter can enter the core harness without changing the core evidence contract.
They do not prove that the adapter is good enough for a downstream policy,
publication, audit, or receipt decision.

The current reusable helper is:

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

## 강하게 assert할 것

- adapter objects satisfy the public port shape they claim to implement
- produced trace payload is JSON-serializable
- model/tool output keeps provenance through `EvidenceAtom`
- expected behavior checks fail when the adapter cannot support the basic case
- `AdapterAcceptanceReport` preserves both the trace and comparison report

## freeze하지 말아야 할 것

- provider SDK choice
- framework node names
- prompt wording
- exact internal scheduling used by an external framework
- downstream policy thresholds

## 해서는 안 되는 일

Adapter acceptance must not import provider SDKs into the core package, treat a
passing fixture as downstream approval, or encode a product-specific validator
schema as core truth.

Real adapters may live outside this package. Their tests can import the helper,
run their adapter ports against the shared scenario, and then add their own
provider-specific assertions outside the core suite.
