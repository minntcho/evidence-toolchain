# Evidence Check Contract

An `EvidenceCheck` records the comparison between declared or requested input and
extracted evidence candidates.

It is the contract that makes this project more than raw extraction: it shows how
evidence relates to what the caller wanted to verify.

## May

An evidence check may say:

- supported
- contradicted
- missing
- uncertain
- review needed

It may preserve:

- declared input reference
- extracted field reference
- normalization notes
- unit conversion notes
- confidence
- issue references
- review trigger references

## Must not

An evidence check must not make final domain decisions.

It must not approve a claim, commit a value, issue a receipt, write an audit
ledger entry, or decide publication readiness. Those are Downstream authority
decisions.

## Review Semantics

`review needed` is an evidence-processing state. It means the toolchain could not
resolve the check safely enough by automated means. It does not mean the
Downstream consumer must reject the input.
