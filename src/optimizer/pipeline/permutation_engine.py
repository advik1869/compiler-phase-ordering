"""Exhaustive execution of the four canonical optimization-pass orders."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Callable, Mapping

from optimizer.analysis import TACExecutionError, execute
from optimizer.ir import TACProgram
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
    OptimizationPass,
)

from .optimizer_pipeline import OptimizationPipeline, PipelineResult


CANONICAL_PASS_NAMES = ("CP", "CF", "DCE", "CSE")
PassFactory = Callable[[], OptimizationPass]
CANONICAL_PASS_FACTORIES: Mapping[str, PassFactory] = {
    "CP": ConstantPropagation,
    "CF": ConstantFolding,
    "DCE": DeadCodeElimination,
    "CSE": CommonSubexpressionElimination,
}


def generate_permutations() -> tuple[tuple[str, ...], ...]:
    """Return all 24 canonical pass orders in deterministic order."""
    return tuple(permutations(CANONICAL_PASS_NAMES))


def permutation_id(order: tuple[str, ...]) -> str:
    """Serialize a canonical order as a stable identifier."""
    return "-".join(order)


@dataclass(frozen=True)
class PermutationResult:
    """Raw outcome for one independently executed pass permutation."""

    permutation: tuple[str, ...]
    permutation_id: str
    final_program: TACProgram | None
    final_instruction_count: int | None
    pipeline_result: PipelineResult | None
    semantic_preserved: bool
    execution_success: bool
    error: str | None = None


@dataclass(frozen=True)
class PermutationExperimentResult:
    """All independent permutation outcomes for one original TAC program."""

    original_program: TACProgram
    original_instruction_count: int
    results: tuple[PermutationResult, ...]

    @property
    def number_of_permutations(self) -> int:
        return len(self.results)


class PermutationEngine:
    """Execute every permutation of CP, CF, DCE, and CSE exactly once."""

    def __init__(self, pass_factories: Mapping[str, PassFactory] | None = None) -> None:
        self._pass_factories = dict(pass_factories or CANONICAL_PASS_FACTORIES)
        if tuple(self._pass_factories) != CANONICAL_PASS_NAMES:
            raise ValueError("pass_factories must contain CP, CF, DCE, and CSE in canonical order")

    def _fresh_passes(self, order: tuple[str, ...]) -> list[OptimizationPass]:
        return [self._pass_factories[name]() for name in order]

    @staticmethod
    def _execute_outcome(program: TACProgram):
        try:
            return execute(program), None
        except Exception as error:  # Runtime behavior is recorded, not discarded.
            return None, error

    @staticmethod
    def _compare_outcomes(original, original_error, optimized, optimized_error) -> bool:
        if original is not None and optimized is not None:
            return original.semantic_signature() == optimized.semantic_signature()
        if original_error is not None and optimized_error is not None:
            if type(original_error) is not type(optimized_error):
                return False
            if isinstance(original_error, TACExecutionError) and isinstance(optimized_error, TACExecutionError):
                return original_error.reason == optimized_error.reason
            return str(original_error) == str(optimized_error)
        return False

    def run(self, program: TACProgram) -> PermutationExperimentResult:
        """Run all canonical permutations independently from ``program``."""
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")
        original_program = program.copy()
        original_execution, original_error = self._execute_outcome(original_program)
        outcomes: list[PermutationResult] = []

        for order in generate_permutations():
            identifier = permutation_id(order)
            pipeline_result: PipelineResult | None = None
            final_program: TACProgram | None = None
            error: str | None = None
            try:
                pipeline_result = OptimizationPipeline().run(
                    original_program, self._fresh_passes(order)
                )
                final_program = pipeline_result.final_program
                optimized_execution, optimized_error = self._execute_outcome(final_program)
                preserved = self._compare_outcomes(
                    original_execution, original_error, optimized_execution, optimized_error
                )
                if not preserved:
                    if optimized_error is not None:
                        error = str(optimized_error)
                    elif original_error is not None:
                        error = f"semantic mismatch: original execution failed: {original_error}"
                    else:
                        error = "semantic signature mismatch"
                execution_success = True
            except Exception as failure:
                preserved = False
                execution_success = False
                error = str(failure)

            outcomes.append(PermutationResult(
                permutation=order,
                permutation_id=identifier,
                final_program=final_program,
                final_instruction_count=None if final_program is None else len(final_program),
                pipeline_result=pipeline_result,
                semantic_preserved=preserved,
                execution_success=execution_success,
                error=error,
            ))

        return PermutationExperimentResult(
            original_program=original_program,
            original_instruction_count=len(original_program),
            results=tuple(outcomes),
        )
