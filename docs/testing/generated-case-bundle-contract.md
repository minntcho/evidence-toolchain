# Generated Case Bundle Contract

Generated case bundles are the committed test target for synthetic evidence
generation. The generator may use manifests, renderers, or helper models
internally, but tests should first depend on the files it produces.

## Artifact shape

Each generated case should produce one case directory:

```text
generated/<case_id>/
+-- evidence.<ext>
`-- expected.json
```

The case directory is the smallest complete generated artifact. It keeps the
input material and the comparison target together so tests can run the same path
a real consumer would run:

```text
manifest
-> generator
-> generated/<case_id>/evidence.<ext>
-> EvidenceDocument.from_path
-> observe_document
-> plan_document
-> compare with generated/<case_id>/expected.json
```

## Evidence file

`evidence.<ext>` is the file that the toolchain reads.

For the first generator foundation, `evidence.txt` is acceptable as a control
fixture because it can carry deterministic metadata and content without adding a
PDF, OCR, or image dependency. Later milestones may add `evidence.pdf`,
`evidence.jpg`, `evidence.png`, or spreadsheet formats one format family at a
time.

The extension is part of the test surface. Tool selection often depends on the
container, media type, and document condition, so new file formats should be
introduced as separate slices rather than bundled into one broad generator
rewrite.

## Expected file

`expected.json` is the test oracle for the generated case.

It should describe the generated artifact, Ground truth, and Expected toolchain
behavior without asking the core package to make Downstream decisions.

Minimum shape:

```json
{
  "case_id": "utility_bill_basic",
  "artifact": {
    "path": "evidence.txt",
    "format": "txt",
    "media_type": "text/plain",
    "document_kind": "utility_bill"
  },
  "ground_truth": {
    "amount": 6.4,
    "unit": "MWh"
  },
  "expected_observation": {
    "document_class": "utility_bill",
    "has_text_layer": true,
    "quality": "clean",
    "signals": []
  },
  "expected_plan": {
    "selected_capabilities": [
      "docling_parse",
      "table_structure_extract",
      "utility_bill_extract"
    ],
    "fallbacks": [],
    "issues": []
  }
}
```

Ground truth is the synthetic world's known value. Expected toolchain behavior
is what the evidence toolchain should observe, plan, extract, issue, or send to
review. Keeping those sections separate prevents synthetic truth from becoming
automatic trust.

## Strong assertions

Tests may strongly assert:

- generated case directory existence
- `evidence.<ext>` existence
- `expected.json` existence
- stable `case_id`
- expected artifact format and media type
- Ground truth and Expected toolchain behavior separation
- selected capabilities, fallbacks, and issues for the current format slice

## Weak assertions

Tests should avoid freezing:

- exact line wrapping in generated evidence files
- cosmetic names inside synthetic documents
- final renderer internals
- future PDF, image, or spreadsheet generation libraries
- Downstream adapter schemas

## Must not

Generated case bundles must not become core runtime authority.

The core package may read `evidence.<ext>` in tests, but it must not import the
synthetic generator or treat `expected.json` as a runtime policy source.

`expected.json` may say that OCR, table extraction, or manual review is expected.
It must not say that a business claim is finally valid, committed, reportable,
or policy-approved. Those Downstream judgments belong to adapters, validators,
or review workflows outside the core package.
