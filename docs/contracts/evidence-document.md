# Evidence Document 계약

`EvidenceDocument`는 Downstream judgment가 일어나기 전 source material을 감싸는 중립적인 wrapper입니다.

이 contract는 무엇을 받았고 그 material에 대해 무엇을 알고 있는지 설명합니다. 어떤 policy 아래에서 material이 충분한지는 설명하지 않습니다.

## 포함할 수 있는 것

Evidence document는 다음을 담을 수 있습니다.

- document id
- file name
- media type
- file hash
- source metadata
- page 또는 image count
- 가능한 경우 document text
- caller-provided target field
- observed document-kind hint

## 해서는 안 되는 일

Evidence document는 final validation state를 담으면 안 됩니다.

Claim이 approved되었는지, declared value가 committed되었는지, Downstream policy가 satisfied되었는지 말하면 안 됩니다.

## Observation과의 관계

Observation은 evidence document에서 파생됩니다. Document는 input identity와 material fact를 저장하고, observation은 toolchain이 발견한 condition, quality, routing signal을 기록합니다.
