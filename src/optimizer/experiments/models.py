"""Structured models for Phase 12 experiment results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from optimizer.analysis import PassInteractionAnalysis
from optimizer.benchmarks import BenchmarkSpec
from optimizer.metrics import PhaseOrderingMetrics
from optimizer.pipeline import PermutationExperimentResult


HEURISTIC_ORDERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("heuristic_1", ("CP", "CF", "DCE", "CSE")),
    ("heuristic_2", ("CSE", "DCE", "CP", "CF")),
)


@dataclass(frozen=True)
class HeuristicComparison:
    """Comparison of one fixed order with exhaustive best and worst results."""

    name: str
    pass_order: tuple[str, ...]
    permutation_id: str
    final_instruction_count: int | None
    instructions_removed: int | None
    reduction_percentage: float | None
    semantic_preserved: bool
    execution_success: bool
    valid: bool
    heuristic_gap: int | None
    equals_exhaustive_best: bool
    worse_than_best: bool
    difference_from_exhaustive_worst: int | None
    error: str | None = None


@dataclass(frozen=True)
class BenchmarkExperimentResult:
    """All Phase 8-10 and heuristic results for one benchmark."""

    benchmark: BenchmarkSpec
    permutation_experiment: PermutationExperimentResult
    metrics: PhaseOrderingMetrics
    interaction: PassInteractionAnalysis
    heuristics: tuple[HeuristicComparison, ...]

    @property
    def baseline_instruction_count(self) -> int:
        return self.metrics.baseline_instruction_count

    @property
    def spread_percentage(self) -> float | None:
        spread = self.metrics.instruction_count_spread
        if spread is None:
            return None
        if self.baseline_instruction_count == 0:
            return 0.0
        return (spread / self.baseline_instruction_count) * 100.0

    @property
    def unique_final_instruction_counts(self) -> tuple[int, ...]:
        counts = {
            metric.final_instruction_count
            for metric in self.metrics.permutation_metrics
            if metric.valid_for_ranking and metric.final_instruction_count is not None
        }
        return tuple(sorted(counts))

    @property
    def semantic_valid_count(self) -> int:
        return sum(
            result.execution_success and result.semantic_preserved
            for result in self.permutation_experiment.results
        )


@dataclass(frozen=True)
class PairInteractionAggregate:
    """Equal-weight aggregation of one Phase 10 pair across benchmarks."""

    pair_name: str
    benchmark_count: int
    nonzero_effect_benchmarks: int
    mean_benchmark_absolute_delta: float | None
    maximum_observed_effect: int | None
    first_ordering_wins_more: int
    second_ordering_wins_more: int
    tied_benchmarks: int


@dataclass(frozen=True)
class ExperimentSuiteResult:
    """Complete deterministic result for the 20-benchmark experiment."""

    benchmark_results: tuple[BenchmarkExperimentResult, ...]
    experiment_version: str = "phase-12-v1"

    @property
    def total_benchmarks(self) -> int:
        return len(self.benchmark_results)

    @property
    def permutations_per_benchmark(self) -> int:
        return 24

    @property
    def total_permutation_evaluations(self) -> int:
        return sum(len(result.permutation_experiment.results) for result in self.benchmark_results)

    @property
    def semantic_valid_evaluations(self) -> int:
        return sum(result.semantic_valid_count for result in self.benchmark_results)

    @property
    def semantic_invalid_evaluations(self) -> int:
        return self.total_permutation_evaluations - self.semantic_valid_evaluations

    @property
    def failed_permutation_evaluations(self) -> int:
        return sum(
            not result.execution_success
            for benchmark in self.benchmark_results
            for result in benchmark.permutation_experiment.results
        )

    def interaction_aggregates(self) -> tuple[PairInteractionAggregate, ...]:
        """Aggregate benchmark-level Phase 10 effects with equal benchmark weight."""
        pair_names = tuple(pair.pair_name for pair in self.benchmark_results[0].interaction.pair_results)
        aggregates: list[PairInteractionAggregate] = []
        for pair_name in pair_names:
            pair_results = [benchmark.interaction.get_pair_result(pair_name) for benchmark in self.benchmark_results]
            means = [pair.mean_absolute_delta for pair in pair_results if pair.mean_absolute_delta is not None]
            maximums = [pair.maximum_absolute_effect for pair in pair_results if pair.maximum_absolute_effect is not None]
            aggregates.append(PairInteractionAggregate(
                pair_name=pair_name,
                benchmark_count=len(pair_results),
                nonzero_effect_benchmarks=sum(value != 0 for value in means),
                mean_benchmark_absolute_delta=None if not means else sum(means) / len(means),
                maximum_observed_effect=None if not maximums else max(maximums),
                first_ordering_wins_more=sum(pair.first_second_better > pair.second_first_better for pair in pair_results),
                second_ordering_wins_more=sum(pair.second_first_better > pair.first_second_better for pair in pair_results),
                tied_benchmarks=sum(pair.first_second_better == pair.second_first_better for pair in pair_results),
            ))
        return tuple(aggregates)

