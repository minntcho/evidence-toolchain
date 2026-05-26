# Extracted Field Contract

An `ExtractedField` is a candidate value found in evidence material.

It is candidate evidence, not final truth.

## May

An extracted field may carry:

- field name
- value
- unit
- normalized value
- page or image reference
- bounding box
- text span
- table cell reference
- source capability
- confidence
- issue references

It may have multiple candidates for the same requested field.

## Must not

An extracted field must not decide that a Downstream input is finally valid.

It must not hide ambiguity by choosing one value without preserving competing
candidates, confidence, provenance, and issues.

## Provenance Rule

Every extracted field should preserve where it came from when the capability can
provide that information. If provenance cannot be recovered, the field should
carry an issue instead of pretending the value is fully grounded.
