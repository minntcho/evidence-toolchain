"""Pure core types for the Evidence Convergence Kernel."""

from evidence_toolchain.convergence.candidates import (
    CandidateMaskState,
    EvidenceCandidate,
)
from evidence_toolchain.convergence.gaps import CandidateGap, compute_candidate_gap
from evidence_toolchain.convergence.masks import (
    mask_has_unknown_bits,
    provenance_present_mask,
)
from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
from evidence_toolchain.convergence.scheduler import select_capabilities
from evidence_toolchain.convergence.schemas import EvidenceSchema, SlotDef
from evidence_toolchain.convergence.validator import (
    PatchValidationError,
    PatchValidationResult,
    apply_patch,
    validate_candidate_state,
    validate_patch,
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
    "apply_patch",
    "compute_candidate_gap",
    "mask_has_unknown_bits",
    "provenance_present_mask",
    "select_capabilities",
    "validate_candidate_state",
    "validate_patch",
]
