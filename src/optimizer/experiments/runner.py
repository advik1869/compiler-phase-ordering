"""Orchestration for the reproducible Phase 12 experiment."""

from __future__ import annotations

from pathlib import Path

from optimizer.benchmarks import load_benchmark_program, load_manifest
from optimizer.metrics import calculate_metrics
from optimizer.pipeline import PermutationEngine

from .models import (
    BenchmarkExperimentResult,
    ExperimentSuiteResult,
    HEURISTIC_ORDERS,
    HeuristicComparison,
)


class ExperimentRunner:
    """Run the existing permutation, metrics, and interaction layers once."""

    def __init__(self, manifest_path: str | Path = "benchmarks/manifest.json") -> None:
        self.manifest_path = Path(manifest_path)

    def run_suite(self) -> ExperimentSuiteResult:
        specs = load_manifest(self.manifest_path)
        if not specs:
            raise ValueError("benchmark manifest contains no benchmarks")
        benchmark_results = tuple(self._run_benchmark(spec) for spec in specs)
        return ExperimentSuiteResult(benchmark_results=benchmark_results)

    def _run_benchmark(self, spec):
        from optimizer.analysis import analyze_pass_interactions

        program = load_benchmark_program(spec)
        permutation_experiment = PermutationEngine().run(program)
        metrics = calculate_metrics(permutation_experiment)
        interaction = analyze_pass_interactions(permutation_experiment)
        metric_by_id = {metric.permutation_id: metric for metric in metrics.permutation_metrics}
        heuristics = tuple(
            self._heuristic_result(name, order, permutation_experiment, metric_by_id, metrics)
            for name, order in HEURISTIC_ORDERS
        )
        return BenchmarkExperimentResult(
            benchmark=spec,
            permutation_experiment=permutation_experiment,
            metrics=metrics,
            interaction=interaction,
            heuristics=heuristics,
        )

    @staticmethod
    def _heuristic_result(name, order, experiment, metric_by_id, metrics):
        permutation_id = "-".join(order)
        raw_result = next(result for result in experiment.results if result.permutation_id == permutation_id)
        metric = metric_by_id[permutation_id]
        best = metrics.best_final_instruction_count
        worst = metrics.worst_final_instruction_count
        gap = None if metric.final_instruction_count is None or best is None else metric.final_instruction_count - best
        return HeuristicComparison(
            name=name,
            pass_order=order,
            permutation_id=permutation_id,
            final_instruction_count=metric.final_instruction_count,
            instructions_removed=metric.instructions_removed,
            reduction_percentage=metric.reduction_percentage,
            semantic_preserved=raw_result.semantic_preserved,
            execution_success=raw_result.execution_success,
            valid=metric.valid_for_ranking,
            heuristic_gap=gap,
            equals_exhaustive_best=gap == 0 if gap is not None else False,
            worse_than_best=gap > 0 if gap is not None else False,
            difference_from_exhaustive_worst=(
                None
                if metric.final_instruction_count is None or worst is None
                else worst - metric.final_instruction_count
            ),
            error=raw_result.error,
        )

