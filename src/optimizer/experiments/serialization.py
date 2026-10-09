"""Stable JSON, CSV, and Markdown output for Phase 12 results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import BenchmarkExperimentResult, ExperimentSuiteResult


def _benchmark_dict(result: BenchmarkExperimentResult) -> dict[str, Any]:
    spec = result.benchmark
    return {
        "id": spec.benchmark_id,
        "file": spec.file,
        "category": spec.category,
        "description": spec.description,
        "optimization_opportunities": list(spec.optimization_opportunities),
        "control_flow": spec.control_flow,
        "ordering_sensitivity": spec.ordering_sensitivity,
        "expected_interactions": list(spec.expected_interactions),
    }


def suite_to_dict(suite: ExperimentSuiteResult) -> dict[str, Any]:
    """Convert a suite into deterministic JSON-compatible data."""
    benchmarks: list[dict[str, Any]] = []
    for result in suite.benchmark_results:
        metrics = result.metrics
        benchmarks.append({
            "benchmark": _benchmark_dict(result),
            "summary": {
                "baseline_instructions": result.baseline_instruction_count,
                "best_instructions": metrics.best_final_instruction_count,
                "worst_instructions": metrics.worst_final_instruction_count,
                "best_permutations": list(metrics.best_permutations),
                "worst_permutations": list(metrics.worst_permutations),
                "best_reduction_percent": metrics.best_reduction_percentage,
                "worst_reduction_percent": metrics.worst_reduction_percentage,
                "spread": metrics.instruction_count_spread,
                "spread_percent": result.spread_percentage,
                "mean_instructions": metrics.average_final_instruction_count,
                "median_instructions": metrics.median_final_instruction_count,
                "unique_final_counts": list(result.unique_final_instruction_counts),
                "semantic_valid_evaluations": result.semantic_valid_count,
                "semantic_invalid_evaluations": len(result.permutation_experiment.results) - result.semantic_valid_count,
            },
            "permutations": [
                {
                    "permutation_id": metric.permutation_id,
                    "permutation": list(metric.pass_order),
                    "final_instruction_count": metric.final_instruction_count,
                    "instructions_removed": metric.instructions_removed,
                    "reduction_percent": metric.reduction_percentage,
                    "semantic_valid": metric.semantic_preserved,
                    "execution_success": metric.execution_success,
                    "valid": metric.valid_for_ranking,
                    "error": metric.error,
                }
                for metric in metrics.permutation_metrics
            ],
            "interactions": [
                {
                    "pair_name": pair.pair_name,
                    "valid_comparison_count": pair.valid_comparison_count,
                    "invalid_comparison_count": pair.invalid_comparison_count,
                    "first_second_better": pair.first_second_better,
                    "second_first_better": pair.second_first_better,
                    "ties": pair.ties,
                    "mean_signed_delta": pair.mean_signed_delta,
                    "mean_absolute_delta": pair.mean_absolute_delta,
                    "minimum_delta": pair.minimum_delta,
                    "maximum_delta": pair.maximum_delta,
                    "maximum_absolute_effect": pair.maximum_absolute_effect,
                    "comparisons": [comparison.__dict__ for comparison in pair.comparisons],
                }
                for pair in result.interaction.pair_results
            ],
            "heuristics": [heuristic.__dict__ for heuristic in result.heuristics],
            "semantic_validation": {
                "all_permutations_valid": result.semantic_valid_count == 24,
                "valid_evaluations": result.semantic_valid_count,
                "invalid_evaluations": 24 - result.semantic_valid_count,
            },
        })
    return {
        "experiment": {
            "version": suite.experiment_version,
            "benchmark_count": suite.total_benchmarks,
            "permutations_per_benchmark": suite.permutations_per_benchmark,
            "total_permutation_evaluations": suite.total_permutation_evaluations,
            "semantic_valid_evaluations": suite.semantic_valid_evaluations,
            "semantic_invalid_evaluations": suite.semantic_invalid_evaluations,
            "failed_permutation_evaluations": suite.failed_permutation_evaluations,
            "heuristic_orders": {
                heuristic.name: list(heuristic.pass_order)
                for heuristic in suite.benchmark_results[0].heuristics
            },
        },
        "benchmarks": benchmarks,
        "interaction_aggregates": [aggregate.__dict__ for aggregate in suite.interaction_aggregates()],
    }


def write_json(suite: ExperimentSuiteResult, path: str | Path) -> Path:
    """Write the complete experiment result as stable indented JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(suite_to_dict(suite), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_csvs(suite: ExperimentSuiteResult, output_dir: str | Path) -> tuple[Path, ...]:
    """Write the four report-oriented CSV files."""
    directory = Path(output_dir)
    summary_rows = []
    permutation_rows = []
    interaction_rows = []
    heuristic_rows = []
    for result in suite.benchmark_results:
        metrics = result.metrics
        summary_rows.append({
            "benchmark_id": result.benchmark.benchmark_id,
            "filename": result.benchmark.file,
            "category": result.benchmark.category,
            "baseline_instructions": result.baseline_instruction_count,
            "best_instructions": metrics.best_final_instruction_count,
            "worst_instructions": metrics.worst_final_instruction_count,
            "best_reduction_percent": metrics.best_reduction_percentage,
            "worst_reduction_percent": metrics.worst_reduction_percentage,
            "spread": metrics.instruction_count_spread,
            "spread_percent": result.spread_percentage,
            "mean_instructions": metrics.average_final_instruction_count,
            "median_instructions": metrics.median_final_instruction_count,
            "unique_final_counts": len(result.unique_final_instruction_counts),
            "best_permutation_count": len(metrics.best_permutations),
            "worst_permutation_count": len(metrics.worst_permutations),
            "heuristic_1_instructions": result.heuristics[0].final_instruction_count,
            "heuristic_2_instructions": result.heuristics[1].final_instruction_count,
            "heuristic_1_gap": result.heuristics[0].heuristic_gap,
            "heuristic_2_gap": result.heuristics[1].heuristic_gap,
        })
        for metric in metrics.permutation_metrics:
            permutation_rows.append({
                "benchmark_id": result.benchmark.benchmark_id,
                "permutation": metric.permutation_id,
                "final_instruction_count": metric.final_instruction_count,
                "instructions_removed": metric.instructions_removed,
                "reduction_percent": metric.reduction_percentage,
                "semantic_valid": metric.semantic_preserved,
                "valid": metric.valid_for_ranking,
            })
        for pair in result.interaction.pair_results:
            interaction_rows.append({
                "benchmark_id": result.benchmark.benchmark_id,
                "pair_name": pair.pair_name,
                "valid_comparisons": pair.valid_comparison_count,
                "invalid_comparisons": pair.invalid_comparison_count,
                "first_second_better": pair.first_second_better,
                "second_first_better": pair.second_first_better,
                "ties": pair.ties,
                "mean_signed_delta": pair.mean_signed_delta,
                "mean_absolute_delta": pair.mean_absolute_delta,
                "maximum_absolute_effect": pair.maximum_absolute_effect,
            })
        for heuristic in result.heuristics:
            heuristic_rows.append({
                "benchmark_id": result.benchmark.benchmark_id,
                "heuristic": heuristic.name,
                "permutation": heuristic.permutation_id,
                "final_instruction_count": heuristic.final_instruction_count,
                "instructions_removed": heuristic.instructions_removed,
                "reduction_percent": heuristic.reduction_percentage,
                "heuristic_gap": heuristic.heuristic_gap,
                "equals_exhaustive_best": heuristic.equals_exhaustive_best,
                "worse_than_best": heuristic.worse_than_best,
                "difference_from_exhaustive_worst": heuristic.difference_from_exhaustive_worst,
                "valid": heuristic.valid,
            })
    return (
        _write_csv(directory / "benchmark_summary.csv", list(summary_rows[0]), summary_rows),
        _write_csv(directory / "permutation_results.csv", list(permutation_rows[0]), permutation_rows),
        _write_csv(directory / "interaction_summary.csv", list(interaction_rows[0]), interaction_rows),
        _write_csv(directory / "heuristic_comparison.csv", list(heuristic_rows[0]), heuristic_rows),
    )


def write_summary_markdown(suite: ExperimentSuiteResult, path: str | Path) -> Path:
    """Write a concise data-versus-interpretation experiment summary."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ranked = sorted(suite.benchmark_results, key=lambda item: (-(item.spread_percentage or 0.0), item.benchmark.benchmark_id))
    least = sorted(suite.benchmark_results, key=lambda item: (item.spread_percentage or 0.0, item.benchmark.benchmark_id))
    lines = [
        "# Phase 12 Experiment Summary", "",
        "## Experiment overview", "",
        f"- Benchmarks: {suite.total_benchmarks}",
        f"- Permutations per benchmark: {suite.permutations_per_benchmark}",
        f"- Total permutation evaluations: {suite.total_permutation_evaluations}",
        f"- Semantic-valid evaluations: {suite.semantic_valid_evaluations}",
        f"- Semantic-invalid evaluations: {suite.semantic_invalid_evaluations}",
        f"- Failed evaluations: {suite.failed_permutation_evaluations}",
        "",
        "## Data: benchmark results", "",
        "| Benchmark | Best | Worst | Spread | Spread % | Best permutations | Worst permutations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in suite.benchmark_results:
        metrics = result.metrics
        lines.append(
            f"| {result.benchmark.benchmark_id} | {metrics.best_final_instruction_count} | "
            f"{metrics.worst_final_instruction_count} | {metrics.instruction_count_spread} | "
            f"{result.spread_percentage:.2f} | {len(metrics.best_permutations)} | {len(metrics.worst_permutations)} |"
        )
    lines.extend(["", "## Data: heuristic comparison", "", "| Benchmark | Heuristic 1 | Heuristic 2 |", "|---|---:|---:|"])
    for result in suite.benchmark_results:
        lines.append(f"| {result.benchmark.benchmark_id} | {result.heuristics[0].final_instruction_count} | {result.heuristics[1].final_instruction_count} |")
    lines.extend(["", "## Data: highest and lowest observed spread", "", "### Highest five", ""])
    lines.extend(f"- {result.benchmark.benchmark_id}: {result.spread_percentage:.2f}%" for result in ranked[:5])
    lines.extend(["", "### Lowest five", ""])
    lines.extend(f"- {result.benchmark.benchmark_id}: {result.spread_percentage:.2f}%" for result in least[:5])
    lines.extend(["", "## Data: recurring interaction summary", "", "| Pair | Non-zero benchmark effects | Mean benchmark absolute delta | Maximum effect |", "|---|---:|---:|---:|"])
    for aggregate in suite.interaction_aggregates():
        lines.append(f"| {aggregate.pair_name} | {aggregate.nonzero_effect_benchmarks} | {aggregate.mean_benchmark_absolute_delta} | {aggregate.maximum_observed_effect} |")
    lines.extend([
        "", "## Interpretation", "",
        "Spread is the observed difference between the worst and best final instruction counts for each benchmark. "
        "Heuristic gaps are measured against the exhaustive best; zero means the heuristic matched that best result.",
        "The interaction summary gives each benchmark equal weight by averaging its Phase 10 mean absolute delta. "
        "These measurements describe ordering sensitivity and do not by themselves establish causal pass enablement.",
    ])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def write_all_outputs(suite: ExperimentSuiteResult, output_dir: str | Path) -> tuple[Path, ...]:
    """Write JSON, CSV, and Markdown outputs, returning their paths."""
    directory = Path(output_dir)
    paths = [
        write_json(suite, directory / "experiment_results.json"),
        *write_csvs(suite, directory),
        write_summary_markdown(suite, directory / "experiment_summary.md"),
    ]
    return tuple(paths)

