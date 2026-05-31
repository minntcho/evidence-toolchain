# ?? case bundle ??

Generated case bundle? synthetic evidence generation? commit?? test target???. Generator? ????? manifest, renderer, helper model? ??? ? ???, test? ?? generator? produced? file? ???? ???.

## Artifact ??

? generated case? ??? case directory? ???? ???.

```text
generated/<case_id>/
+-- evidence.<ext>
+-- expected.json
+-- experiment.json
`-- expected-behavior.json
```

Case directory? ?? ?? complete generated artifact???. Input material? comparison target? ?? ?? test? real consumer? ??? path? ?? path? ??? ? ?? ???.

```text
manifest
-> generator
-> generated/<case_id>/evidence.<ext>
-> EvidenceDocument.from_path
-> observe_document
-> plan_document
-> compare with generated/<case_id>/expected.json
```

The same generated directory can drive the experiment harness:

```text
generated/<case_id>/experiment.json
-> evidence-toolchain run-experiment
-> ExperimentRunTrace
-> compare with generated/<case_id>/expected-behavior.json
```

## Evidence ??

`evidence.<ext>`? toolchain? ?? file???.

? generator foundation??? `evidence.txt`? control fixture? ???? ?? ?????. PDF, OCR, image dependency? ???? ?? deterministic metadata? content? ?? ? ?? ?????. ?? milestone??? `evidence.pdf`, `evidence.jpg`, `evidence.png`, spreadsheet format? format family? slice? ??? ? ????.

Extension? test surface? ?????. Tool selection? container, media type, document condition? ?? ?????, ? file format? ??? broad generator rewrite? ???? separate slice? ???? ???.

## Expected ??

`expected.json`? generated case? test oracle???.

? file? generated artifact, Ground truth, Expected toolchain behavior? ???? ???. Core package? Downstream decision? ??? ??? ? ???.

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

Ground truth? synthetic world? ?? ?? value???. Expected toolchain behavior? evidence toolchain? observe, plan, extract, issue, ?? review? ??? ?? behavior???. ? ?? ???? synthetic truth? automatic trust? ?? ?? ????.

## Experiment harness files

`experiment.json`? generated evidence file? ?? declared claim? ????. ?? slice??? deterministic resolution cycle? ????? ???? `amount` + `unit` claim? ?????. site, supplier, activity, period truth? `expected.json`? ?? ???, ?? resolver authority? ???? ????.

`expected-behavior.json`? generated case? ?? harness?? ???? ?? expected behavior expectation???. Resolution fixture? `claim_resolutions`? ? ? ??, convergence fixture? `claim_convergences`? ? ? ????. ? ??? `run-experiment`? `run-convergence`? `--expected` ???? ??? ? ????.

Example:

```powershell
evidence-toolchain run-experiment .\generated\utility_bill_basic\experiment.json `
  --trace-out .\generated\utility_bill_basic\out\trace.json `
  --expected .\generated\utility_bill_basic\expected-behavior.json `
  --expected-report-out .\generated\utility_bill_basic\out\expected-report.json
```

```powershell
evidence-toolchain run-convergence .\generated\convergence_clean_support\experiment.json `
  --trace-out .\generated\convergence_clean_support\out\trace.json `
  --expected .\generated\convergence_clean_support\expected-behavior.json `
  --expected-report-out .\generated\convergence_clean_support\out\expected-report.json
```

Convergence file-backed fixtures currently cover:

```text
convergence_clean_support
convergence_nonblocking_issue
convergence_candidate_conflict
```

The bad patch rejected convergence slice is intentionally runner-level because
it needs a fake `PatchProducer`. It is still checked through
`ExperimentExpectedBehavior.claim_convergences`, not by projecting into
`EvidenceResolutionGraph`.

## ??? assert? ?

Test? ??? ??? assert? ? ????.

- generated case directory existence
- `evidence.<ext>` existence
- `expected.json` existence
- `experiment.json` existence
- `expected-behavior.json` existence
- stable `case_id`
- expected artifact format? media type
- Ground truth? Expected toolchain behavior separation
- ?? format slice? ?? selected capability, fallback, issue
- generated experiment files can drive `run-experiment`
- convergence fixture files can drive `run-convergence`

## freeze?? ??? ? ?

Test? ??? freeze?? ??? ???.

- generated evidence file? exact line wrapping
- synthetic document ?? cosmetic name
- final renderer internal
- future PDF, image, spreadsheet generation library
- Downstream adapter schema
- future full-claim resolver coverage for site, supplier, activity, or period

## ??? ? ?? ?

Generated case bundle? core runtime authority? ?? ? ???.

Core package? test?? `evidence.<ext>`? ?? ? ??? synthetic generator? import??? `expected.json`? runtime policy source? ???? ? ???.

`expected.json`? OCR, table extraction, manual review? expected?? ?? ? ????. ??? business claim? finally valid, committed, reportable, policy-approved??? ??? ? ???. ?? Downstream judgment? core package ?? adapter, validator, review workflow? ????.

`expected-behavior.json`? ????? runtime authority? ????. ??? generated case? ?? local harness?? ???? ???? ????.
