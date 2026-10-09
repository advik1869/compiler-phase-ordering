"""Integration tests for Phase 10 against the real permutation engine."""

from pathlib import Path

from optimizer.analysis import analyze_pass_interactions
from optimizer.ir import load_tac
from optimizer.pipeline import PermutationEngine


def test_all_existing_examples_have_complete_interaction_analysis() -> None:
    examples = sorted((Path(__file__).parents[2] / "examples").glob("*.tac"))
    assert len(examples) == 4

    for path in examples:
        experiment = PermutationEngine().run(load_tac(str(path)))
        analysis = analyze_pass_interactions(experiment)

        assert len(analysis.pair_results) == 6
        assert analysis.total_comparisons == 36
        assert analysis.valid_comparisons == 36
        assert analysis.invalid_comparisons == 0
        assert analysis.strongest_pair is not None


def test_interaction_analysis_is_deterministic_for_an_example() -> None:
    path = Path(__file__).parents[2] / "examples" / "repeated_expression.tac"
    first = analyze_pass_interactions(PermutationEngine().run(load_tac(str(path))))
    second = analyze_pass_interactions(PermutationEngine().run(load_tac(str(path))))

    assert first == second
