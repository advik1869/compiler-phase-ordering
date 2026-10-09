"""Headless matplotlib visualizations for structured Phase 12 results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .models import ExperimentSuiteResult


def _labels(suite: ExperimentSuiteResult) -> list[str]:
    return [result.benchmark.benchmark_id for result in suite.benchmark_results]


def plot_best_vs_worst(suite: ExperimentSuiteResult, output_dir: str | Path) -> Path:
    """Plot best and worst final instruction counts per benchmark."""
    path = Path(output_dir) / "best_vs_worst.png"
    labels = _labels(suite)
    figure, axis = plt.subplots(figsize=(12, 6))
    positions = list(range(len(labels)))
    width = 0.38
    axis.bar([position - width / 2 for position in positions], [result.metrics.best_final_instruction_count for result in suite.benchmark_results], width, label="Exhaustive best")
    axis.bar([position + width / 2 for position in positions], [result.metrics.worst_final_instruction_count for result in suite.benchmark_results], width, label="Exhaustive worst")
    axis.set_title("Best vs Worst Final Instruction Count")
    axis.set_xlabel("Benchmark")
    axis.set_ylabel("Instructions")
    axis.set_xticks(positions, labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)
    return path


def plot_reduction_range(suite: ExperimentSuiteResult, output_dir: str | Path) -> Path:
    """Plot the best and worst reduction percentages per benchmark."""
    path = Path(output_dir) / "reduction_range.png"
    labels = _labels(suite)
    figure, axis = plt.subplots(figsize=(12, 6))
    positions = list(range(len(labels)))
    width = 0.38
    axis.bar([position - width / 2 for position in positions], [result.metrics.best_reduction_percentage for result in suite.benchmark_results], width, label="Best reduction")
    axis.bar([position + width / 2 for position in positions], [result.metrics.worst_reduction_percentage for result in suite.benchmark_results], width, label="Worst reduction")
    axis.set_title("Instruction Reduction Range")
    axis.set_xlabel("Benchmark")
    axis.set_ylabel("Reduction (%)")
    axis.set_xticks(positions, labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)
    return path


def plot_heuristic_comparison(suite: ExperimentSuiteResult, output_dir: str | Path) -> Path:
    """Compare exhaustive best with the two fixed heuristic orders."""
    path = Path(output_dir) / "heuristic_vs_best.png"
    labels = _labels(suite)
    figure, axis = plt.subplots(figsize=(12, 6))
    positions = list(range(len(labels)))
    width = 0.25
    series = (
        ("Exhaustive best", [result.metrics.best_final_instruction_count for result in suite.benchmark_results]),
        ("Heuristic 1", [result.heuristics[0].final_instruction_count for result in suite.benchmark_results]),
        ("Heuristic 2", [result.heuristics[1].final_instruction_count for result in suite.benchmark_results]),
    )
    for index, (label, values) in enumerate(series):
        axis.bar([position + (index - 1) * width for position in positions], values, width, label=label)
    axis.set_title("Fixed Heuristics vs Exhaustive Best")
    axis.set_xlabel("Benchmark")
    axis.set_ylabel("Instructions")
    axis.set_xticks(positions, labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)
    return path


def plot_spread(suite: ExperimentSuiteResult, output_dir: str | Path) -> Path:
    """Plot spread percentage, where spread is worst minus best."""
    path = Path(output_dir) / "phase_ordering_spread.png"
    labels = _labels(suite)
    figure, axis = plt.subplots(figsize=(12, 6))
    axis.bar(labels, [result.spread_percentage for result in suite.benchmark_results])
    axis.set_title("Phase-Ordering Spread Percentage")
    axis.set_xlabel("Benchmark")
    axis.set_ylabel("Spread (%)")
    axis.tick_params(axis="x", labelrotation=45)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)
    return path


def plot_pairwise_interactions(suite: ExperimentSuiteResult, output_dir: str | Path) -> Path:
    """Plot equal-weight mean benchmark-level Phase 10 interaction strength."""
    path = Path(output_dir) / "pairwise_interaction_strength.png"
    aggregates = suite.interaction_aggregates()
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.bar([aggregate.pair_name for aggregate in aggregates], [aggregate.mean_benchmark_absolute_delta or 0.0 for aggregate in aggregates])
    axis.set_title("Pairwise Interaction Strength Across Benchmarks")
    axis.set_xlabel("Pass pair")
    axis.set_ylabel("Mean benchmark absolute instruction-count delta")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)
    return path


def create_all_plots(suite: ExperimentSuiteResult, output_dir: str | Path) -> tuple[Path, ...]:
    """Create the five required Phase 12 PNG visualizations."""
    return (
        plot_best_vs_worst(suite, output_dir),
        plot_reduction_range(suite, output_dir),
        plot_heuristic_comparison(suite, output_dir),
        plot_spread(suite, output_dir),
        plot_pairwise_interactions(suite, output_dir),
    )

