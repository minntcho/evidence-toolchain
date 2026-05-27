from __future__ import annotations

from dataclasses import dataclass, replace

from evidence_toolchain.atoms import EvidenceAtom, EvidenceAtomType
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit
from evidence_toolchain.investigation import (
    InvestigationEvent,
    InvestigationEventType,
    InvestigationState,
    InvestigationTask,
    InvestigationTaskResult,
    InvestigationTaskStatus,
    InvestigationTaskType,
)
from evidence_toolchain.investigation_ports import (
    LLMAtomizerPort,
    LLMNormalizerPort,
    LLMPlannerPort,
    VLMObserverPort,
)
from evidence_toolchain.investigation_retrieval import CandidateUnitRetriever
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.normalization import NormalizationResult


@dataclass(frozen=True)
class LocalInvestigationRunner:
    """Framework/provider 없이 InvestigationState를 한 step 전진시키는 v0 runner."""

    planner: LLMPlannerPort
    vlm_observer: VLMObserverPort | None = None
    llm_atomizer: LLMAtomizerPort | None = None
    llm_normalizer: LLMNormalizerPort | None = None
    unit_retriever: CandidateUnitRetriever | None = None
    artifact_bytes: dict[str, bytes] | None = None
    producer: str = "local_investigation_runner_v0"

    def run_once(self, state: InvestigationState) -> InvestigationState:
        """agenda 계획 또는 첫 task 실행 중 하나만 수행합니다."""

        if self._iteration_budget_exhausted(state):
            return self._record_budget_exhausted(state)

        if not state.agenda:
            return self._plan_next_tasks(state)

        task = state.agenda[0]
        state = self._record_event(
            state,
            InvestigationEventType.TASK_STARTED,
            {"task_id": task.task_id},
        )
        return self._execute_task(state, task)

    def run_agenda(
        self,
        state: InvestigationState,
        *,
        max_steps: int,
    ) -> InvestigationState:
        """현재 agenda에 이미 올라온 task chain만 deterministic하게 실행합니다."""

        next_state = state
        for _ in range(max(0, max_steps)):
            if not next_state.agenda:
                return next_state
            next_state = self.run_once(next_state)
        return next_state

    def _plan_next_tasks(self, state: InvestigationState) -> InvestigationState:
        plan = self.planner.plan_next_tasks(state)
        next_state = replace(
            state,
            agenda=state.agenda + plan.tasks,
            metadata={
                **state.metadata,
                "runner": self.producer,
                "planner": plan.producer,
            },
        )
        if plan.tasks:
            return self._record_event(
                next_state,
                InvestigationEventType.TASK_PLANNED,
                {"task_ids": [task.task_id for task in plan.tasks]},
            )
        if plan.stop_reason is not None:
            return self._record_event(
                replace(next_state, metadata={**next_state.metadata, "stop_reason": plan.stop_reason}),
                InvestigationEventType.STOPPED,
                {"reason": plan.stop_reason},
            )
        return next_state

    def _execute_task(
        self,
        state: InvestigationState,
        task: InvestigationTask,
    ) -> InvestigationState:
        if task.task_type == InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS:
            return self._execute_retrieval_task(state, task)

        if task.task_type in {
            InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
            InvestigationTaskType.INSPECT_VISUAL_REGION,
        }:
            result = self._execute_visual_task(task)
            return self._complete_task(state, task, result=result)

        if task.task_type == InvestigationTaskType.ATOMIZE_UNIT_CLUSTER:
            atoms = self._execute_atomizer_task(state, task)
            result = InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.COMPLETED,
                produced_atom_ids=tuple(atom.atom_id for atom in atoms),
                metadata={"producer": self.llm_atomizer.producer if self.llm_atomizer else None},
            )
            return self._complete_task(state, task, result=result, atoms=atoms)

        if task.task_type == InvestigationTaskType.NORMALIZE_CANDIDATE:
            results = self._execute_normalizer_task(state, task)
            result = InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.COMPLETED,
                produced_normalization_result_ids=tuple(result.target_id for result in results),
                metadata={"producer": self.llm_normalizer.producer if self.llm_normalizer else None},
            )
            return self._complete_task(state, task, result=result, normalizations=results)

        if task.task_type == InvestigationTaskType.REQUEST_MANUAL_REVIEW:
            result = InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.MANUAL_REVIEW_REQUIRED,
            )
            return self._complete_task(state, task, result=result)

        if task.task_type == InvestigationTaskType.STOP:
            result = InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.SKIPPED,
                metadata={"reason": "stop_task"},
            )
            return self._complete_task(state, task, result=result)

        result = InvestigationTaskResult(
            task_id=task.task_id,
            status=InvestigationTaskStatus.FAILED,
            metadata={"reason": "unsupported_task_type"},
        )
        return self._complete_task(state, task, result=result)

    def _execute_visual_task(self, task: InvestigationTask) -> InvestigationTaskResult:
        if self.vlm_observer is None:
            return InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.FAILED,
                metadata={"reason": "vlm_observer_missing"},
            )
        artifact_id = task.target_artifact_ids[0] if task.target_artifact_ids else None
        payload = (self.artifact_bytes or {}).get(artifact_id or "", b"")
        return self.vlm_observer.inspect(task, artifact_bytes=payload)

    def _execute_retrieval_task(
        self,
        state: InvestigationState,
        task: InvestigationTask,
    ) -> InvestigationState:
        if self.unit_retriever is None:
            result = InvestigationTaskResult(
                task_id=task.task_id,
                status=InvestigationTaskStatus.FAILED,
                metadata={"reason": "unit_retriever_missing"},
            )
            return self._complete_task(state, task, result=result)

        retrieval = self.unit_retriever.retrieve(
            task=task,
            inventory=state.inventory,
            need_spec=_need_spec_for_task(state, task),
        )
        next_task = retrieval.to_atomize_task(source_task=task)
        next_state = self._complete_task(
            state,
            task,
            result=retrieval.to_task_result(),
        )
        if next_task is None:
            return next_state
        next_state = replace(next_state, agenda=(next_task,) + next_state.agenda)
        return self._record_event(
            next_state,
            InvestigationEventType.TASK_PLANNED,
            {"task_ids": [next_task.task_id], "source_task_id": task.task_id},
        )

    def _execute_atomizer_task(
        self,
        state: InvestigationState,
        task: InvestigationTask,
    ) -> tuple[EvidenceAtom, ...]:
        if self.llm_atomizer is None:
            return ()
        units_by_id = {unit.unit_id: unit for unit in state.inventory.units}
        units = tuple(
            units_by_id[unit_id]
            for unit_id in task.target_unit_ids
            if unit_id in units_by_id
        )
        return self.llm_atomizer.atomize(task, units=units).atoms

    def _execute_normalizer_task(
        self,
        state: InvestigationState,
        task: InvestigationTask,
    ) -> tuple[NormalizationResult, ...]:
        if self.llm_normalizer is None:
            return ()
        target_atom_ids = tuple(str(atom_id) for atom_id in task.metadata.get("target_atom_ids", ()))
        atoms = _select_atoms(state.atoms, target_atom_ids)
        return self.llm_normalizer.normalize(task, atoms=atoms)

    def _complete_task(
        self,
        state: InvestigationState,
        task: InvestigationTask,
        *,
        result: InvestigationTaskResult,
        atoms: tuple[EvidenceAtom, ...] = (),
        normalizations: tuple[NormalizationResult, ...] = (),
    ) -> InvestigationState:
        merged_atoms = result.produced_atoms + atoms
        accepted_atoms, rejected_atom_ids, guardrail_issues = _filter_model_atoms(
            task,
            merged_atoms,
        )
        merged_normalizations = result.produced_normalization_results + normalizations
        merged_normalizations = _drop_normalizations_for_rejected_atoms(
            merged_normalizations,
            rejected_atom_ids,
        )
        if merged_atoms:
            result = replace(
                result,
                produced_atoms=accepted_atoms,
                produced_atom_ids=(),
                produced_normalization_results=merged_normalizations,
                produced_normalization_result_ids=(),
                issues=result.issues + guardrail_issues,
            )
        result = _with_produced_ids(
            result,
            atoms=accepted_atoms,
            normalizations=merged_normalizations,
        )
        next_state = replace(
            state,
            agenda=state.agenda[1:],
            completed_tasks=state.completed_tasks + (result,),
            inventory=_merge_inventory_units(state.inventory, result.produced_units),
            atoms=state.atoms + accepted_atoms,
            normalization_results=state.normalization_results + merged_normalizations,
            metadata={**state.metadata, "runner": self.producer},
        )
        return self._record_event(
            next_state,
            InvestigationEventType.TASK_COMPLETED,
            {
                "task_id": task.task_id,
                "status": result.status,
            },
        )

    def _iteration_budget_exhausted(self, state: InvestigationState) -> bool:
        return (
            state.budget.max_iterations > 0
            and len(state.completed_tasks) >= state.budget.max_iterations
        )

    def _record_budget_exhausted(self, state: InvestigationState) -> InvestigationState:
        return self._record_event(
            replace(
                state,
                metadata={
                    **state.metadata,
                    "runner": self.producer,
                    "stop_reason": "max_iterations_exhausted",
                },
            ),
            InvestigationEventType.BUDGET_EXHAUSTED,
            {"reason": "max_iterations_exhausted"},
        )

    def _record_event(
        self,
        state: InvestigationState,
        event_type: str,
        payload: dict[str, object],
    ) -> InvestigationState:
        return state.record_event(
            InvestigationEvent(
                run_id=state.run_id,
                sequence=len(state.events) + 1,
                event_type=event_type,
                payload=payload,
            )
        )


def _select_atoms(
    atoms: tuple[EvidenceAtom, ...],
    target_atom_ids: tuple[str, ...],
) -> tuple[EvidenceAtom, ...]:
    if not target_atom_ids:
        return atoms
    allowed = set(target_atom_ids)
    return tuple(atom for atom in atoms if atom.atom_id in allowed)


def _need_spec_for_task(
    state: InvestigationState,
    task: InvestigationTask,
):
    if task.target_claim_id is None:
        return None
    for need_spec in state.need_specs:
        if need_spec.x_id == task.target_claim_id:
            return need_spec
    return None


def _merge_inventory_units(
    inventory: EvidenceInventory,
    units: tuple[EvidenceUnit, ...],
) -> EvidenceInventory:
    if not units:
        return inventory
    return replace(inventory, units=inventory.units + units)


def _filter_model_atoms(
    task: InvestigationTask,
    atoms: tuple[EvidenceAtom, ...],
) -> tuple[tuple[EvidenceAtom, ...], tuple[str, ...], tuple[EvidenceIssue, ...]]:
    if not atoms:
        return (), (), ()

    accepted: list[EvidenceAtom] = []
    rejected_ids: list[str] = []
    issues: list[EvidenceIssue] = []
    allowed_atom_types = set(task.allowed_atom_types)
    for atom in atoms:
        issue = _atom_guardrail_issue(atom, allowed_atom_types)
        if issue is not None:
            rejected_ids.append(atom.atom_id)
            issues.append(issue)
            continue
        accepted.append(atom)
    return tuple(accepted), tuple(rejected_ids), tuple(issues)


def _atom_guardrail_issue(
    atom: EvidenceAtom,
    allowed_atom_types: set[str],
) -> EvidenceIssue | None:
    if not EvidenceAtomType.is_core_type(atom.atom_type):
        return EvidenceIssue(
            code="model_output_atom_type_unknown",
            severity="warning",
            message=f"모델 출력 atom '{atom.atom_id}'의 atom_type이 v0 vocabulary에 없습니다.",
        )
    if allowed_atom_types and atom.atom_type not in allowed_atom_types:
        return EvidenceIssue(
            code="model_output_atom_type_not_allowed",
            severity="warning",
            message=f"모델 출력 atom '{atom.atom_id}'의 atom_type이 task 허용 목록 밖입니다.",
        )
    if not atom.source_unit_ids and not atom.source_artifact_ids:
        return EvidenceIssue(
            code="model_output_missing_provenance",
            severity="warning",
            message=f"모델 출력 atom '{atom.atom_id}'에 source_unit_ids/source_artifact_ids가 없습니다.",
        )
    return None


def _drop_normalizations_for_rejected_atoms(
    normalizations: tuple[NormalizationResult, ...],
    rejected_atom_ids: tuple[str, ...],
) -> tuple[NormalizationResult, ...]:
    if not normalizations or not rejected_atom_ids:
        return normalizations
    rejected = set(rejected_atom_ids)
    return tuple(
        normalization
        for normalization in normalizations
        if normalization.target_id not in rejected
    )


def _with_produced_ids(
    result: InvestigationTaskResult,
    *,
    atoms: tuple[EvidenceAtom, ...],
    normalizations: tuple[NormalizationResult, ...],
) -> InvestigationTaskResult:
    produced_unit_ids = result.produced_unit_ids or tuple(
        unit.unit_id for unit in result.produced_units
    )
    produced_atom_ids = result.produced_atom_ids or tuple(atom.atom_id for atom in atoms)
    produced_normalization_result_ids = result.produced_normalization_result_ids or tuple(
        item.target_id for item in normalizations
    )
    return replace(
        result,
        produced_unit_ids=produced_unit_ids,
        produced_atom_ids=produced_atom_ids,
        produced_normalization_result_ids=produced_normalization_result_ids,
    )
