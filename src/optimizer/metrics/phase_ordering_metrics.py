"""Instruction-count metrics for Phase 8 permutation experiments."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median

from optimizer.pipeline.permutation_engine import PermutationExperimentResult


@dataclass(frozen=True)
class PermutationMetrics:
    """Quantitative and validity information for one permutation result."""

    permutation_id: str
    pass_order: tuple[str, ...]
    baseline_instruction_count: int
    final_instruction_count: int | None
    instructions_removed: int | None
    reduction_percentage: float | None
    semantic_preserved: bool
    execution_success: bool
    valid_for_ranking: bool
    error: str | None = None


@dataclass(frozen=True)
class PhaseOrderingMetrics:
    """Per-permutation metrics and aggregate phase-ordering statistics."""

    baseline_instruction_count: int
    permutation_metrics: tuple[PermutationMetrics, ...]
    valid_result_count: int
    invalid_result_count: int
    best_permutation: str | None
    worst_permutation: str | None
    best_permutations: tuple[str, ...]
    worst_permutations: tuple[str, ...]
    best_final_instruction_count: int | None
    worst_final_instruction_count: int | None
    average_final_instruction_count: float | None
    median_final_instruction_count: float | None
    best_reduction_percentage: float | None
    worst_reduction_percentage: float | None
    average_reduction_percentage: float | None
    median_reduction_percentage: float | None
    reduction_spread: float | None
    instruction_count_spread: int | None


def calculate_metrics(experiment: PermutationExperimentResult) -> PhaseOrderingMetrics:
    """Analyze one Phase 8 result without rerunning optimization or execution."""
    baseline = experiment.original_instruction_count
    permutation_metrics: list[PermutationMetrics] = []
    for result in experiment.results:
        final_count = result.final_instruction_count
        removed = None if final_count is None else baseline - final_count
        reduction = None
        if final_count is not None:
            reduction = 0.0 if baseline == 0 else ((baseline - final_count) / baseline) * 100.0
        valid = (
            result.execution_success
            and result.semantic_preserved
            and final_count is not None
        )
        permutation_metrics.append(PermutationMetrics(
            permutation_id=result.permutation_id,
            pass_order=result.permutation,
            baseline_instruction_count=baseline,
            final_instruction_count=final_count,
            instructions_removed=removed,
            reduction_percentage=reduction,
            semantic_preserved=result.semantic_preserved,
            execution_success=result.execution_success,
            valid_for_ranking=valid,
            error=result.error,
        ))

    valid_metrics = [metric for metric in permutation_metrics if metric.valid_for_ranking]
    valid_metrics.sort(key=lambda metric: metric.permutation_id)
    final_counts = [metric.final_instruction_count for metric in valid_metrics]
    reductions = [metric.reduction_percentage for metric in valid_metrics]
    # Valid metrics necessarily have concrete values; these assertions also
    # keep the type narrowing explicit for readers of the lab code.
    final_counts = [count for count in final_counts if count is not None]
    reductions = [value for value in reductions if value is not None]

    if valid_metrics:
        best_count = min(final_counts)
        worst_count = max(final_counts)
        best_ties = tuple(metric.permutation_id for metric in valid_metrics if metric.final_instruction_count == best_count)
        worst_ties = tuple(metric.permutation_id for metric in valid_metrics if metric.final_instruction_count == worst_count)
        best_reduction = max(reductions)
        worst_reduction = min(reductions)
        return PhaseOrderingMetrics(
            baseline_instruction_count=baseline,
            permutation_metrics=tuple(permutation_metrics),
            valid_result_count=len(valid_metrics),
            invalid_result_count=len(permutation_metrics) - len(valid_metrics),
            best_permutation=best_ties[0],
            worst_permutation=worst_ties[0],
            best_permutations=best_ties,
            worst_permutations=worst_ties,
            best_final_instruction_count=best_count,
            worst_final_instruction_count=worst_count,
            average_final_instruction_count=mean(final_counts),
            median_final_instruction_count=median(final_counts),
            best_reduction_percentage=best_reduction,
            worst_reduction_percentage=worst_reduction,
            average_reduction_percentage=mean(reductions),
            median_reduction_percentage=median(reductions),
            reduction_spread=best_reduction - worst_reduction,
            instruction_count_spread=worst_count - best_count,
        )

    return PhaseOrderingMetrics(
        baseline_instruction_count=baseline,
        permutation_metrics=tuple(permutation_metrics),
        valid_result_count=0,
        invalid_result_count=len(permutation_metrics),
        best_permutation=None,
        worst_permutation=None,
        best_permutations=(),
        worst_permutations=(),
        best_final_instruction_count=None,
        worst_final_instruction_count=None,
        average_final_instruction_count=None,
        median_final_instruction_count=None,
        best_reduction_percentage=None,
        worst_reduction_percentage=None,
        average_reduction_percentage=None,
        median_reduction_percentage=None,
        reduction_spread=None,
        instruction_count_spread=None,
    )

