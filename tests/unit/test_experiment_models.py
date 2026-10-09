"""Unit tests for Phase 12 result models and fixed baselines."""

import json

import pytest

from optimizer.benchmarks import BenchmarkManifestError, load_manifest
from optimizer.experiments import ExperimentRunner, HEURISTIC_ORDERS


def test_suite_has_20_benchmarks_and_480_permutation_evaluations() -> None:
    suite = ExperimentRunner().run_suite()

    assert suite.total_benchmarks == 20
    assert suite.permutations_per_benchmark == 24
    assert suite.total_permutation_evaluations == 480
    assert suite.semantic_valid_evaluations == 480
    assert suite.semantic_invalid_evaluations == 0


def test_best_worst_ties_and_heuristic_gaps_are_consistent() -> None:
    suite = ExperimentRunner().run_suite()

    assert HEURISTIC_ORDERS == (
        ("heuristic_1", ("CP", "CF", "DCE", "CSE")),
        ("heuristic_2", ("CSE", "DCE", "CP", "CF")),
    )
    for result in suite.benchmark_results:
        metrics = result.metrics
        assert metrics.best_final_instruction_count <= metrics.worst_final_instruction_count
        assert metrics.instruction_count_spread == (
            metrics.worst_final_instruction_count - metrics.best_final_instruction_count
        )
        assert all(
            heuristic.final_instruction_count >= metrics.best_final_instruction_count
            for heuristic in result.heuristics
        )
        assert all(
            heuristic.heuristic_gap == heuristic.final_instruction_count - metrics.best_final_instruction_count
            for heuristic in result.heuristics
        )
        assert all(
            metric.final_instruction_count == metrics.best_final_instruction_count
            for metric in metrics.permutation_metrics
            if metric.permutation_id in metrics.best_permutations
        )
        assert all(
            metric.final_instruction_count == metrics.worst_final_instruction_count
            for metric in metrics.permutation_metrics
            if metric.permutation_id in metrics.worst_permutations
        )


def test_runner_uses_one_permutation_engine_run_per_benchmark(monkeypatch) -> None:
    from optimizer.pipeline import PermutationEngine

    calls = 0
    original_run = PermutationEngine.run

    def counted_run(self, program):
        nonlocal calls
        calls += 1
        return original_run(self, program)

    monkeypatch.setattr(PermutationEngine, "run", counted_run)
    ExperimentRunner().run_suite()
    assert calls == 20


def test_empty_or_malformed_manifest_fails_clearly(tmp_path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"benchmarks": []}))
    with pytest.raises(ValueError, match="contains no benchmarks"):
        ExperimentRunner(empty).run_suite()

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({"benchmarks": [{"id": "B01"}]}))
    with pytest.raises(BenchmarkManifestError, match="requires a non-empty 'file'"):
        load_manifest(malformed)
