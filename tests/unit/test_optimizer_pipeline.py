"""Unit tests for the Phase 7 generic optimization pipeline."""

import pytest

from optimizer.ir import TACProgram, parse_tac
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
    OptimizationPass,
    PassResult,
    PassStatistics,
)
from optimizer.pipeline import OptimizationPipeline, PipelineExecutionError


def test_empty_pipeline_preserves_program_and_has_no_history() -> None:
    original = parse_tac("a = 10\nreturn a")
    result = OptimizationPipeline().run(original, [])
    assert result.final_program == original
    assert result.final_program is not original
    assert result.pass_results == ()
    assert result.pass_order == ()
    assert result.final_instruction_count == 2
    assert not result.changed


def test_single_pass_matches_direct_execution() -> None:
    original = parse_tac("t1 = 10 + 20\nreturn t1")
    direct = ConstantFolding().run(original)
    pipelined = OptimizationPipeline().run(original, [ConstantFolding()])
    assert pipelined.final_program == direct
    assert pipelined.pass_order == ("constant_folding",)


def test_multiple_passes_execute_in_exact_order_and_record_history() -> None:
    original = parse_tac("a = 10\nb = 20\nt1 = a + b\nt2 = a + b\nx = 999\nreturn t2")
    passes = [ConstantPropagation(), ConstantFolding(), DeadCodeElimination(), CommonSubexpressionElimination()]
    result = OptimizationPipeline().run(original, passes)
    assert result.pass_order == (
        "constant_propagation", "constant_folding",
        "dead_code_elimination", "common_subexpression_elimination",
    )
    assert len(result.pass_results) == 4
    assert result.final_program.to_tac()
    assert result.changed


def test_different_orders_are_preserved_and_can_have_different_intermediates() -> None:
    original = parse_tac("a = 10\nb = a\nc = b + 5")
    order_a = OptimizationPipeline().run(original, [ConstantPropagation(), ConstantFolding()])
    order_b = OptimizationPipeline().run(original, [ConstantFolding(), ConstantPropagation()])
    assert order_a.pass_order == ("constant_propagation", "constant_folding")
    assert order_b.pass_order == ("constant_folding", "constant_propagation")
    assert order_a.pass_results[0].program.to_tac() == "a = 10\nb = 10\nc = 10 + 5"
    assert order_b.pass_results[0].program.to_tac() == original.to_tac()


def test_reverse_order_and_repeated_passes_are_not_normalized() -> None:
    reverse = OptimizationPipeline().run(parse_tac("t1 = 10 + 20"), [
        CommonSubexpressionElimination(), DeadCodeElimination(),
        ConstantFolding(), ConstantPropagation(),
    ])
    repeated = OptimizationPipeline().run(parse_tac("a = 10\nb = a"), [
        ConstantPropagation(), ConstantFolding(), ConstantPropagation(),
    ])
    assert reverse.pass_order == (
        "common_subexpression_elimination", "dead_code_elimination",
        "constant_folding", "constant_propagation",
    )
    assert repeated.pass_order == (
        "constant_propagation", "constant_folding", "constant_propagation"
    )
    assert len(repeated.pass_results) == 3


def test_pass_statistics_are_preserved_without_recalculation() -> None:
    result = OptimizationPipeline().run(parse_tac("t1 = 10 + 20\nreturn t1"), [ConstantFolding()])
    statistics = result.pass_results[0].statistics
    assert statistics.pass_name == "constant_folding"
    assert statistics.expressions_folded == 1
    assert statistics.instructions_before == 2
    assert statistics.instructions_after == 2


def test_final_program_matches_manual_sequential_application() -> None:
    original = parse_tac("a = 10\nb = a\nt1 = b + 5\nreturn t1")
    cp = ConstantPropagation()
    cf = ConstantFolding()
    dce = DeadCodeElimination()
    cse = CommonSubexpressionElimination()
    manual = cse.run(dce.run(cf.run(cp.run(original))))
    pipelined = OptimizationPipeline().run(original, [
        ConstantPropagation(), ConstantFolding(), DeadCodeElimination(),
        CommonSubexpressionElimination(),
    ])
    assert pipelined.final_program == manual


def test_original_program_is_not_modified() -> None:
    original = parse_tac("a = 10\nb = a\nreturn b")
    before = original.to_tac()
    OptimizationPipeline().run(original, [ConstantPropagation(), DeadCodeElimination()])
    assert original.to_tac() == before


def test_pipeline_is_deterministic() -> None:
    original = parse_tac("a = 10\nb = a\nt1 = b + 5\nreturn t1")
    passes = [ConstantPropagation(), ConstantFolding(), DeadCodeElimination()]
    first = OptimizationPipeline().run(original, passes)
    second = OptimizationPipeline().run(original, [ConstantPropagation(), ConstantFolding(), DeadCodeElimination()])
    assert first.final_program.to_tac() == second.final_program.to_tac()
    assert first.pass_order == second.pass_order
    assert tuple(result.statistics for result in first.pass_results) == tuple(result.statistics for result in second.pass_results)


class FailingPass(OptimizationPass):
    name = "failing_test_pass"

    def run_with_result(self, program: TACProgram) -> PassResult:
        raise ValueError("controlled failure")


class TrackingPass(OptimizationPass):
    name = "tracking_test_pass"

    def __init__(self) -> None:
        super().__init__()
        self.called = False

    def run_with_result(self, program: TACProgram) -> PassResult:
        self.called = True
        return PassResult(program, PassStatistics(self.name, len(program), len(program)))


def test_failure_identifies_pass_and_stops_later_passes() -> None:
    later = TrackingPass()
    with pytest.raises(PipelineExecutionError, match="failing_test_pass") as error:
        OptimizationPipeline().run(parse_tac("return 0"), [FailingPass(), later])
    assert isinstance(error.value.__cause__, ValueError)
    assert "controlled failure" in str(error.value.original_error)
    assert not later.called

