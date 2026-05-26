# Contract Documents

Contract documents define behavior, not downstream policy.

These documents describe the current core contracts that `evidence-toolchain`
should preserve as code evolves. They are intentionally domain-neutral. They
name what each object may carry, what it may decide, and what it must not decide.

## Read Order

1. [Evidence Document](evidence-document.md)
2. [Declared Input](declared-input.md)
3. [Extracted Field](extracted-field.md)
4. [Evidence Check](evidence-check.md)
5. [Evidence Report](evidence-report.md)

## Contract Rule

The core contracts may describe evidence-processing state:

- document identity
- requested or declared inputs
- extracted candidate fields
- provenance
- confidence
- issues
- review triggers
- support, contradiction, missing, or uncertainty states

They must not encode downstream authority:

- final domain approval
- legal or compliance sufficiency
- publication approval
- commit or receipt authority
- audit ledger decisions

Downstream consumers may translate these contracts into their own policy or
workflow language through adapters.
