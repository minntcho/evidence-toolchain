"""Pure core types for the Evidence Convergence Kernel."""

from evidence_toolchain.convergence.candidates import (
    CandidateMaskState,
    EvidenceCandidate,
)
from evidence_toolchain.convergence.gaps import CandidateGap
from evidence_toolchain.convergence.masks import (
    mask_has_unknown_bits,
    provenance_present_mask,
)
from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
from evidence_toolchain.convergence.schemas import EvidenceSchema, SlotDef
from evidence_toolchain.convergence.validator import (
    PatchValidationError,
    PatchValidationResult,
    validate_candidate_state,
)

__all__ = [
    "CapabilitySpec",
    "CandidateGap",
    "CandidateMaskState",
    "EvidenceCandidate",
    "EvidenceSchema",
    "MaskPatch",
    "PatchValidationError",
    "PatchValidationResult",
    "SlotDef",
    "mask_has_unknown_bits",
    "provenance_present_mask",
    "validate_candidate_state",
]
