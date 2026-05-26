# Declared Input Contract

A `DeclaredInput` represents a value, field, or question the caller wants to
compare with evidence.

The name may change as the implementation evolves, but the responsibility should
stay stable: it is the caller-side value or request that evidence may support,
contradict, fail to find, or leave uncertain.

## May

A declared input may carry:

- input id
- requested field name
- declared value
- declared unit
- declared period or date
- source system metadata
- optional matching hints
- optional required evidence type

It may be absent when the caller only wants open-ended extraction.

## Must not

A declared input must not carry final downstream approval.

It must not say that a value is committed, policy-sufficient, legally accepted,
or ready for publication. Those states belong to Downstream systems.

## Relationship To Evidence

Evidence may support, contradict, miss, or leave the declared input uncertain.
The declared input itself is not evidence. It is the value being checked against
evidence.
