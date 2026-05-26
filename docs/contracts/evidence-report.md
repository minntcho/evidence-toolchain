# Evidence Report Contract

An `EvidenceReport` is the consolidated neutral output from the toolchain.

It should be useful to many consumers without becoming any one consumer's
authority model.

## May

An evidence report may include:

- document identity
- observations
- selected tool plan
- capability result summaries
- extracted fields
- evidence checks
- provenance
- confidence
- issues
- unresolved ambiguities
- recommended next action

The recommended next action may include trying a fallback capability or sending a
case to review.

## Must not

An evidence report must not include final Downstream validation judgment.

It must not approve a claim, commit a value, issue a receipt, write an audit
ledger decision, or decide that a report may be publicly published.

## Adapter Use

Adapters may translate an evidence report into review tasks, domain validator
payloads, dashboards, or compiler-specific candidates. That translation must not
change what the core report is authorized to decide.
