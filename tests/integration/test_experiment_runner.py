"""End-to-end Phase 12 runner and output validation."""

import csv
import json
import subprocess
import sys


def test_experiment_cli_generates_complete_output_set(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_experiment.py", "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "evaluated 20 benchmarks and 480 permutations" in result.stdout
    expected = {
        "experiment_results.json",
        "experiment_summary.md",
        "benchmark_summary.csv",
        "permutation_results.csv",
        "interaction_summary.csv",
        "heuristic_comparison.csv",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
    assert {path.name for path in (tmp_path / "plots").iterdir()} == {
        "best_vs_worst.png",
        "reduction_range.png",
        "heuristic_vs_best.png",
        "phase_ordering_spread.png",
        "pairwise_interaction_strength.png",
    }

    data = json.loads((tmp_path / "experiment_results.json").read_text())
    assert len(data["benchmarks"]) == 20
    assert data["experiment"]["total_permutation_evaluations"] == 480
    with (tmp_path / "benchmark_summary.csv").open(newline="") as source:
        assert len(list(csv.DictReader(source))) == 20
    with (tmp_path / "permutation_results.csv").open(newline="") as source:
        assert len(list(csv.DictReader(source))) == 480

