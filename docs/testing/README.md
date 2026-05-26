# Testing Strategy

Testing documents describe verification strategy, not runtime authority.

The test suite should keep the project aligned with its purpose: domain-neutral
evidence-input consistency, provenance, uncertainty, and failure reporting.

Tests should protect behavior that defines the toolchain's role. They should not
freeze implementation details that can change as extraction tools improve.

## Read Order

1. [Synthetic Evidence Cases](synthetic-evidence-cases.md)
2. [Router and Planner Test Strategy](router-planner-test-strategy.md)
3. [Failure Mode Test Strategy](failure-mode-test-strategy.md)
4. [Generated Case Bundle Contract](generated-case-bundle-contract.md)

## Test Authority Rule

Tests may define expected behavior for synthetic worlds and fixture documents.
They must not become runtime authority for real downstream decisions.

Strong assertions should protect:

- core import boundaries
- manifest truth versus expected behavior separation
- capability selection for known evidence conditions
- issue preservation
- review triggers
- report shape and provenance

Weak assertions should leave room for:

- internal module layout
- exact wording of explanations
- future extraction backend choices
- final downstream schemas
- product-specific UI or workflow labels

## Must not

Tests must not encode one downstream consumer's policy as core truth. Consumer
policy belongs in adapters or downstream test suites.
