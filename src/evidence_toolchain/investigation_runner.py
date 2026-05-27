from __future__ import annotations

from dataclasses import dataclass, replace

from evidence_toolchain.atoms import EvidenceAtom
from evidence_toolchain.ingestion import EvidenceUnit
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
from evidence_toolchain.normalization import NormalizationResult


@dataclass(frozen=True)
class LocalInvestigationRunner:
    """Framework/provider 없이 InvestigationState를 한 step 전진시키는 v0 runner."""

    planner: LLMPlannerPort
    vlm_observer: VLMObserverPort | None = None
    llm_atomizer: LLMAtomizerPort | None = None
    llm_normalizer: LLMNormalizerPort | None = None
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
        next_state = replace(
            state,
            agenda=state.agenda[1:],
            completed_tasks=state.completed_tasks + (result,),
            atoms=state.atoms + atoms,
            normalization_results=state.normalization_results + normalizations,
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
