"""Integration tests connecting Phase 8 results to Phase 9 metrics."""

from pathlib import Path

from optimizer.ir import load_tac
from optimizer.metrics import calculate_metrics
from optimizer.pipeline import PermutationEngine


def test_existing_examples_produce_24_metrics_each() -> None:
    for path in sorted((Path(__file__).parents[2] / "examples").glob("*.tac")):
        experiment = PermutationEngine().run(load_tac(str(path)))
        metrics = calculate_metrics(experiment)
        assert len(metrics.permutation_metrics) == 24
        assert metrics.baseline_instruction_count == experiment.original_instruction_count
        assert metrics.valid_result_count == 24
        assert metrics.invalid_result_count == 0
        assert metrics.best_permutation is not None
        assert metrics.worst_permutation is not None

