"""Unit tests for Phase 10 controlled pass-interaction analysis."""

from dataclasses import replace

import pytest

from optimizer.analysis import InteractionAnalysisError, analyze_pass_interactions
from optimizer.ir import parse_tac
from optimizer.pipeline import (
    PermutationEngine,
    PermutationExperimentResult,
    PermutationResult,
    generate_permutations,
    permutation_id,
)


def _experiment_with_counts(counts: dict[str, int] | None = None) -> PermutationExperimentResult:
    counts = counts or {}
    original = parse_tac("a = 1\nreturn a")
    results = tuple(
        PermutationResult(
            permutation=order,
            permutation_id=permutation_id(order),
            final_program=None,
            final_instruction_count=counts.get(permutation_id(order), 10),
            pipeline_result=None,
            semantic_preserved=True,
            execution_success=True,
        )
        for order in generate_permutations()
    )
    return PermutationExperimentResult(original, len(original), results)


def test_analyzer_records_six_pairs_and_36_controlled_comparisons() -> None:
    analysis = analyze_pass_interactions(_experiment_with_counts())

    assert len(analysis.pair_results) == 6
    assert all(len(pair.comparisons) == 6 for pair in analysis.pair_results)
    assert analysis.total_comparisons == 36
    assert analysis.valid_comparisons == 36
    assert analysis.invalid_comparisons == 0
    assert [pair.pair_name for pair in analysis.pair_results] == [
        "CP/CF", "CP/DCE", "CP/CSE", "CF/DCE", "CF/CSE", "DCE/CSE"
    ]


def test_comparison_uses_signed_first_minus_second_delta() -> None:
    counts = {
        "CP-CF-DCE-CSE": 7,
        "CF-CP-DCE-CSE": 10,
    }
    pair = analyze_pass_interactions(_experiment_with_counts(counts)).get_pair_result("CP/CF")
    comparison = pair.comparisons[0]

    assert comparison.first_ordering == "CP-CF-DCE-CSE"
    assert comparison.second_ordering == "CF-CP-DCE-CSE"
    assert comparison.prefix == ()
    assert comparison.suffix == ("DCE", "CSE")
    assert comparison.signed_delta == -3
    assert comparison.absolute_delta == 3
    assert pair.first_second_better >= 1


def test_pair_aggregates_are_derived_from_valid_comparisons() -> None:
    analysis = analyze_pass_interactions(_experiment_with_counts({"CP-CF-DCE-CSE": 7}))
    pair = analysis.get_pair_result(("CP", "CF"))
    deltas = [comparison.signed_delta for comparison in pair.comparisons]
    valid_deltas = [delta for comparison, delta in zip(pair.comparisons, deltas) if comparison.valid_for_comparison]

    assert pair.mean_signed_delta == sum(valid_deltas) / len(valid_deltas)
    assert pair.mean_absolute_delta == sum(abs(delta) for delta in valid_deltas) / len(valid_deltas)
    assert pair.minimum_delta == min(valid_deltas)
    assert pair.maximum_delta == max(valid_deltas)
    assert pair.maximum_absolute_effect == max(abs(delta) for delta in valid_deltas)
    assert pair.first_second_better + pair.second_first_better + pair.ties == 6


def test_strongest_pair_is_selected_in_canonical_order_on_ties() -> None:
    analysis = analyze_pass_interactions(_experiment_with_counts())
    assert analysis.strongest_pair == "CP/CF"
    assert analysis.strongest_pair_mean_absolute_delta == 0
    assert analysis.strongest_pair_maximum_absolute_effect == 0


def test_semantically_invalid_results_are_visible_but_excluded() -> None:
    experiment = _experiment_with_counts()
    invalid_id = "CP-CF-DCE-CSE"
    results = tuple(
        replace(result, semantic_preserved=False)
        if result.permutation_id == invalid_id else result
        for result in experiment.results
    )
    analysis = analyze_pass_interactions(replace(experiment, results=results))

    assert analysis.invalid_comparisons > 0
    assert analysis.valid_comparisons + analysis.invalid_comparisons == 36
    assert any(not comparison.valid_for_comparison for pair in analysis.pair_results for comparison in pair.comparisons)


def test_incomplete_and_duplicate_experiments_raise_clear_errors() -> None:
    experiment = _experiment_with_counts()
    with pytest.raises(InteractionAnalysisError, match="requires 24 results"):
        analyze_pass_interactions(replace(experiment, results=experiment.results[:-1]))

    duplicate = list(experiment.results)
    duplicate[1] = replace(duplicate[1], permutation_id=duplicate[0].permutation_id)
    with pytest.raises(InteractionAnalysisError, match="duplicate permutation ID"):
        analyze_pass_interactions(replace(experiment, results=tuple(duplicate)))


def test_analysis_does_not_require_pipeline_results_or_rerun_optimization() -> None:
    analysis = analyze_pass_interactions(_experiment_with_counts())
    assert all(
        comparison.enablement_evidence == "INCONCLUSIVE"
        for pair in analysis.pair_results
        for comparison in pair.comparisons
    )

