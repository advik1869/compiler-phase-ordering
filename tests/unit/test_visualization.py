"""Headless smoke tests for required Phase 12 plots."""

from optimizer.experiments import ExperimentRunner, create_all_plots


def test_all_required_plots_are_created_without_gui(tmp_path) -> None:
    suite = ExperimentRunner().run_suite()
    paths = create_all_plots(suite, tmp_path)

    assert [path.name for path in paths] == [
        "best_vs_worst.png",
        "reduction_range.png",
        "heuristic_vs_best.png",
        "phase_ordering_spread.png",
        "pairwise_interaction_strength.png",
    ]
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)

