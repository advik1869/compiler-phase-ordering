"""Phase 12 experiment orchestration and result models."""

from .models import (
    BenchmarkExperimentResult,
    ExperimentSuiteResult,
    HEURISTIC_ORDERS,
    HeuristicComparison,
    PairInteractionAggregate,
)
from .runner import ExperimentRunner
from .serialization import suite_to_dict, write_all_outputs, write_csvs, write_json, write_summary_markdown
from .visualization import (
    create_all_plots,
    plot_best_vs_worst,
    plot_heuristic_comparison,
    plot_pairwise_interactions,
    plot_reduction_range,
    plot_spread,
)

__all__ = [
    "BenchmarkExperimentResult",
    "ExperimentRunner",
    "ExperimentSuiteResult",
    "HEURISTIC_ORDERS",
    "HeuristicComparison",
    "PairInteractionAggregate",
    "create_all_plots",
    "plot_best_vs_worst",
    "plot_heuristic_comparison",
    "plot_pairwise_interactions",
    "plot_reduction_range",
    "plot_spread",
    "suite_to_dict",
    "write_all_outputs",
    "write_csvs",
    "write_json",
    "write_summary_markdown",
]
