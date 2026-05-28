from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from evidence_toolchain.atomizers import SimpleTextAtomizer
from evidence_toolchain.atoms import AtomizerResult
from evidence_toolchain.claims import DeclaredClaim, derive_need_spec
from evidence_toolchain.ingestion import EvidenceInventory
from evidence_toolchain.investigation import InvestigationBudget, InvestigationState
from evidence_toolchain.investigation_gaps import ResolutionGapPlan, ResolutionGapPlanner
from evidence_toolchain.investigation_ports import InvestigationPlan
from evidence_toolchain.investigation_retrieval import CandidateUnitRetriever
from evidence_toolchain.investigation_runner import LocalInvestigationRunner
from evidence_toolchain.normalization import NormalizationAdapter, NormalizationResult
from evidence_toolchain.normalizers import DeterministicNormalizer
from evidence_toolchain.resolution import EvidenceResolutionGraph, HardGateResolver


@dataclass(frozen=True)
class EvidenceResolutionRun:
    """Reference resolution cycle output for local orchestration demos."""

    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    need_specs: tuple[Any, ...]
    initial_normalization_results: tuple[NormalizationResult, ...]
    initial_graph: EvidenceResolutionGraph
    gap_plan: ResolutionGapPlan
    investigation_state: InvestigationState

    @property
    def final_graph(self) -> EvidenceResolutionGraph:
        return self.investigation_state.draft_graph or self.initial_graph

    @property
    def stop_reason(self) -> str:
        stop_reason = self.investigation_state.metadata.get("stop_reason")
        if stop_reason is not None:
            return str(stop_reason)
        if not self.investigation_state.agenda:
            return "agenda_exhausted"
        return "max_investigation_steps_reached"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "inventory": _to_json_compatible(self.inventory),
            "claims": _to_json_compatible(self.claims),
            "need_specs": _to_json_compatible(self.need_specs),
            "initial_normalization_results": _to_json_compatible(
                self.initial_normalization_results
            ),
            "initial_graph": _to_json_compatible(self.initial_graph),
            "gap_plan": _to_json_compatible(self.gap_plan),
            "investigation_state": _to_json_compatible(self.investigation_state),
            "final_graph": _to_json_compatible(self.final_graph),
            "stop_reason": self.stop_reason,
        }


@dataclass(frozen=True)
class SimpleUnitClusterAtomizer:
    """Adapter that runs the deterministic text atomizer on selected unit clusters."""

    bundle_id: str
    producer: str = "simple_unit_cluster_atomizer_v0"
    atomizer: SimpleTextAtomizer = field(default_factory=SimpleTextAtomizer)

    def atomize(self, task, units) -> AtomizerResult:
        inventory = EvidenceInventory(
            bundle_id=f"{self.bundle_id}_{task.task_id}",
            attachments=(),
            artifacts=(),
            units=tuple(units),
            route_decisions=(),
        )
        result = self.atomizer.atomize(inventory)
        atoms = tuple(
            replace(
                atom,
                atom_id=f"{task.task_id}_atom_{index:03d}",
                producer=self.producer,
            )
            for index, atom in enumerate(result.atoms, start=1)
        )
        return AtomizerResult(
            bundle_id=self.bundle_id,
            atoms=atoms,
            issues=result.issues,
            metadata={
                "producer": self.producer,
                "source_task_id": task.task_id,
                "source_atomizer": self.atomizer.producer,
            },
        )


def run_resolution_cycle(
    *,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    run_id: str | None = None,
    max_investigation_steps: int = 10,
    budget: InvestigationBudget | None = None,
    normalizer: NormalizationAdapter | None = None,
    resolver: HardGateResolver | None = None,
    gap_planner: ResolutionGapPlanner | None = None,
    unit_retriever: CandidateUnitRetriever | None = None,
    investigation_runner: LocalInvestigationRunner | None = None,
) -> EvidenceResolutionRun:
    """Run the deterministic local X-Y evidence resolution cycle."""

    active_run_id = run_id or f"{inventory.bundle_id}_resolution_cycle"
    active_normalizer = normalizer or DeterministicNormalizer()
    active_resolver = resolver or HardGateResolver()
    active_gap_planner = gap_planner or ResolutionGapPlanner()
    active_unit_retriever = unit_retriever or CandidateUnitRetriever()
    active_budget = budget or InvestigationBudget(max_iterations=max_investigation_steps)
    active_claims = tuple(claims)
    need_specs = tuple(derive_need_spec(claim) for claim in active_claims)
    initial_normalizations = tuple(
        normalization
        for need_spec in need_specs
        for need in need_spec.needs
        for normalization in active_normalizer.normalize_claim_need(need)
    )
    initial_graph = active_resolver.resolve(
        bundle_id=inventory.bundle_id,
        claims=active_claims,
        need_specs=need_specs,
        atoms=(),
        normalization_results=initial_normalizations,
    )
    gap_plan = active_gap_planner.plan_from_graph(
        graph=initial_graph,
        need_specs=need_specs,
    )
    state = InvestigationState(
        run_id=active_run_id,
        inventory=inventory,
        claims=active_claims,
        need_specs=need_specs,
        atoms=(),
        normalization_results=initial_normalizations,
        draft_graph=initial_graph,
        agenda=gap_plan.tasks,
        clue_ledger=gap_plan.ledger_entries,
        budget=active_budget,
        metadata={
            "runner": "resolution_cycle_v0",
            "gap_planner": active_gap_planner.producer,
        },
    )
    runner = investigation_runner or LocalInvestigationRunner(
        planner=_NoOpPlanner(),
        unit_retriever=active_unit_retriever,
        llm_atomizer=SimpleUnitClusterAtomizer(bundle_id=inventory.bundle_id),
        normalizer=active_normalizer,
        resolver=active_resolver,
        producer="resolution_cycle_local_runner_v0",
    )
    final_state = runner.run_agenda(
        state,
        max_steps=max(0, max_investigation_steps),
    )
    return EvidenceResolutionRun(
        run_id=active_run_id,
        inventory=inventory,
        claims=active_claims,
        need_specs=need_specs,
        initial_normalization_results=initial_normalizations,
        initial_graph=initial_graph,
        gap_plan=gap_plan,
        investigation_state=final_state,
    )


@dataclass(frozen=True)
class _NoOpPlanner:
    producer: str = "noop_investigation_planner_v0"

    def plan_next_tasks(self, state: InvestigationState) -> InvestigationPlan:
        del state
        return InvestigationPlan(
            tasks=(),
            stop_reason="agenda_empty",
            producer=self.producer,
        )


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _to_json_compatible(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
