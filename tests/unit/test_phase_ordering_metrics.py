"""Unit tests for Phase 9 metrics."""

from optimizer.ir import TACProgram, parse_tac
from optimizer.metrics import calculate_metrics
from optimizer.pipeline import PermutationExperimentResult, PermutationResult


def program_with_count(count: int) -> TACProgram:
    return parse_tac("\n".join(f"x{i} = 0" for i in range(count)))


def result(identifier: str, count: int, *, semantic: bool = True, success: bool = True) -> PermutationResult:
    order = tuple(identifier.split("-"))
    return PermutationResult(
        permutation=order,
        permutation_id=identifier,
        final_program=program_with_count(count) if success else None,
        final_instruction_count=count if success else None,
        pipeline_result=None,
        semantic_preserved=semantic,
        execution_success=success,
        error=None if success and semantic else "controlled invalid result",
    )


def experiment(results, baseline: int = 10) -> PermutationExperimentResult:
    return PermutationExperimentResult(
        original_program=program_with_count(baseline),
        original_instruction_count=baseline,
        results=tuple(results),
    )


def test_baseline_and_permutation_counts() -> None:
    metrics = calculate_metrics(experiment([result("P1", 8), result("P2", 7)]))
    assert metrics.baseline_instruction_count == 10
    assert [item.final_instruction_count for item in metrics.permutation_metrics] == [8, 7]
    assert [item.instructions_removed for item in metrics.permutation_metrics] == [2, 3]


def test_reduction_percentage_and_negative_reduction() -> None:
    metrics = calculate_metrics(experiment([result("P1", 8), result("P2", 12)]))
    assert metrics.permutation_metrics[0].reduction_percentage == 20.0
    assert metrics.permutation_metrics[1].reduction_percentage == -20.0
    assert metrics.permutation_metrics[1].instructions_removed == -2


def test_best_worst_ties_average_median_and_spreads() -> None:
    metrics = calculate_metrics(experiment([
        result("P1", 8), result("P2", 7), result("P3", 9), result("P4", 7),
    ]))
    assert metrics.best_final_instruction_count == 7
    assert metrics.worst_final_instruction_count == 9
    assert metrics.best_permutation == "P2"
    assert metrics.worst_permutation == "P3"
    assert metrics.best_permutations == ("P2", "P4")
    assert metrics.worst_permutations == ("P3",)
    assert metrics.average_final_instruction_count == 7.75
    assert metrics.median_final_instruction_count == 7.5
    assert metrics.best_reduction_percentage == 30.0
    assert metrics.worst_reduction_percentage == 10.0
    assert metrics.average_reduction_percentage == 22.5
    assert metrics.median_reduction_percentage == 25.0
    assert metrics.instruction_count_spread == 2
    assert metrics.reduction_spread == 20.0


def test_invalid_and_failed_results_remain_visible_but_are_excluded() -> None:
    metrics = calculate_metrics(experiment([
        result("VALID", 7),
        result("INVALID", 1, semantic=False),
        result("FAILED", 1, success=False),
    ]))
    assert len(metrics.permutation_metrics) == 3
    assert metrics.valid_result_count == 1
    assert metrics.invalid_result_count == 2
    assert metrics.best_permutation == "VALID"
    assert metrics.worst_permutation == "VALID"
    assert metrics.permutation_metrics[1].valid_for_ranking is False
    assert metrics.permutation_metrics[2].valid_for_ranking is False


def test_baseline_zero_is_safe() -> None:
    metrics = calculate_metrics(experiment([result("P1", 0)], baseline=0))
    assert metrics.permutation_metrics[0].reduction_percentage == 0.0
    assert metrics.average_reduction_percentage == 0.0


def test_all_equal_results_have_zero_spread() -> None:
    metrics = calculate_metrics(experiment([result("P1", 5), result("P2", 5), result("P3", 5)]))
    assert metrics.instruction_count_spread == 0
    assert metrics.reduction_spread == 0.0
    assert metrics.best_permutations == ("P1", "P2", "P3")
    assert metrics.worst_permutations == ("P1", "P2", "P3")


def test_no_valid_results_are_explicitly_empty() -> None:
    metrics = calculate_metrics(experiment([
        result("P1", 5, semantic=False), result("P2", 5, success=False),
    ]))
    assert metrics.valid_result_count == 0
    assert metrics.invalid_result_count == 2
    assert metrics.best_permutation is None
    assert metrics.worst_permutation is None
    assert metrics.best_permutations == ()
    assert metrics.average_final_instruction_count is None
    assert metrics.instruction_count_spread is None


def test_metrics_are_deterministic_and_do_not_need_to_run_optimizers() -> None:
    raw = experiment([result("P2", 7), result("P1", 8)])
    first = calculate_metrics(raw)
    second = calculate_metrics(raw)
    assert first == second

