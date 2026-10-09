"""Unit tests for deterministic Phase 12 output serialization."""

import json

from optimizer.experiments import (
    ExperimentRunner,
    suite_to_dict,
    write_all_outputs,
    write_json,
)


def test_json_data_is_serializable_and_contains_all_benchmarks(tmp_path) -> None:
    suite = ExperimentRunner().run_suite()
    data = suite_to_dict(suite)

    encoded = json.dumps(data, sort_keys=True)
    assert encoded
    assert data["experiment"]["total_permutation_evaluations"] == 480
    assert len(data["benchmarks"]) == 20


def test_json_csv_and_markdown_outputs_are_created(tmp_path) -> None:
    suite = ExperimentRunner().run_suite()
    paths = write_all_outputs(suite, tmp_path)

    assert {path.name for path in paths} == {
        "experiment_results.json",
        "benchmark_summary.csv",
        "permutation_results.csv",
        "interaction_summary.csv",
        "heuristic_comparison.csv",
        "experiment_summary.md",
    }
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)
    assert json.loads((tmp_path / "experiment_results.json").read_text())


def test_json_content_is_deterministic(tmp_path) -> None:
    first = ExperimentRunner().run_suite()
    second = ExperimentRunner().run_suite()
    first_path = write_json(first, tmp_path / "first.json")
    second_path = write_json(second, tmp_path / "second.json")

    assert first_path.read_text() == second_path.read_text()

