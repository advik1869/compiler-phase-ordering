"""Unit tests for the Phase 8 exhaustive permutation engine."""

from optimizer.ir import TACProgram, parse_tac
from optimizer.passes import OptimizationPass, PassResult, PassStatistics
from optimizer.pipeline import (
    CANONICAL_PASS_NAMES,
    PermutationEngine,
    generate_permutations,
    permutation_id,
)


def test_generates_exactly_24_unique_permutations() -> None:
    orders = generate_permutations()
    ids = [permutation_id(order) for order in orders]
    assert len(orders) == 24
    assert len(set(ids)) == 24


def test_every_order_contains_each_canonical_pass_once() -> None:
    for order in generate_permutations():
        assert len(order) == 4
        assert set(order) == set(CANONICAL_PASS_NAMES)
        assert all(order.count(name) == 1 for name in CANONICAL_PASS_NAMES)


def test_engine_executes_and_records_all_24_orders() -> None:
    experiment = PermutationEngine().run(parse_tac("a = 10\nb = a\nreturn b"))
    assert experiment.number_of_permutations == 24
    assert len(experiment.results) == 24
    for result in experiment.results:
        assert result.permutation_id == "-".join(result.permutation)
        assert result.pipeline_result is not None
        assert result.final_program is not None
        assert result.final_instruction_count == len(result.final_program)
        assert result.execution_success


def test_pass_history_matches_the_recorded_permutation() -> None:
    experiment = PermutationEngine().run(parse_tac("t1 = 10 + 20\nreturn t1"))
    for result in experiment.results:
        assert result.pipeline_result is not None
        assert result.permutation_id == "-".join(result.permutation)
        assert len(result.pipeline_result.pass_results) == 4


def test_each_permutation_starts_from_the_same_original_program() -> None:
    original = parse_tac("a = 10\nb = a\nt1 = b + 5\nreturn t1")
    before = original.to_tac()
    experiment = PermutationEngine().run(original)
    assert experiment.original_program.to_tac() == before
    assert original.to_tac() == before
    assert all(result.pipeline_result is not None for result in experiment.results)


def test_identical_final_programs_are_not_deduplicated() -> None:
    experiment = PermutationEngine().run(parse_tac("return 0"))
    assert len(experiment.results) == 24
    assert len({result.permutation_id for result in experiment.results}) == 24


def test_engine_is_deterministic() -> None:
    program = parse_tac("a = 10\nb = a\nt1 = b + 5\nt2 = b + 5\nreturn t2")
    first = PermutationEngine().run(program)
    second = PermutationEngine().run(program)
    assert [result.permutation_id for result in first.results] == [result.permutation_id for result in second.results]
    assert [result.final_program.to_tac() for result in first.results] == [result.final_program.to_tac() for result in second.results]
    assert [result.final_instruction_count for result in first.results] == [result.final_instruction_count for result in second.results]
    assert [result.semantic_preserved for result in first.results] == [result.semantic_preserved for result in second.results]


def test_runtime_error_outcomes_are_recorded_consistently() -> None:
    experiment = PermutationEngine().run(parse_tac("a = 10\nb = 0\nt1 = a / b\n"))
    assert all(result.execution_success for result in experiment.results)
    assert any(not result.semantic_preserved for result in experiment.results)
    assert all(result.error for result in experiment.results if not result.semantic_preserved)


class FailingPass(OptimizationPass):
    name = "failing_test_pass"

    def run_with_result(self, program: TACProgram) -> PassResult:
        raise ValueError("controlled permutation failure")


def test_unexpected_permutation_failures_are_kept_as_results() -> None:
    factories = {
        "CP": lambda: FailingPass(),
        "CF": lambda: FailingPass(),
        "DCE": lambda: FailingPass(),
        "CSE": lambda: FailingPass(),
    }
    experiment = PermutationEngine(factories).run(parse_tac("return 0"))
    assert len(experiment.results) == 24
    assert all(not result.execution_success for result in experiment.results)
    assert all(not result.semantic_preserved for result in experiment.results)
    assert all(result.error and "controlled permutation failure" in result.error for result in experiment.results)
