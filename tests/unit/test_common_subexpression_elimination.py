"""Unit tests for Phase 6 common subexpression elimination."""

from optimizer.ir import BinaryOperation, Assignment, parse_tac
from optimizer.passes import CommonSubexpressionElimination


def eliminate(text: str):
    return CommonSubexpressionElimination().run(parse_tac(text))


def test_repeated_expression_reuses_existing_result() -> None:
    result = eliminate("t1 = a + b\nt2 = a + b")
    assert result.to_tac() == "t1 = a + b\nt2 = t1"
    assert isinstance(result[1], Assignment)


def test_repeated_multiplication_and_relational_expression() -> None:
    result = eliminate("t1 = a * b\nt2 = a * b\nt3 = a < b\nt4 = a < b")
    assert result.to_tac() == "t1 = a * b\nt2 = t1\nt3 = a < b\nt4 = t3"


def test_different_and_reversed_operands_are_not_reused() -> None:
    result = eliminate("t1 = a + b\nt2 = a - b\nt3 = b + a")
    assert result.to_tac() == "t1 = a + b\nt2 = a - b\nt3 = b + a"


def test_operand_redefinition_invalidates_expression() -> None:
    result = eliminate("t1 = a + b\na = 10\nt2 = a + b\n")
    assert result.to_tac() == "t1 = a + b\na = 10\nt2 = a + b"
    result = eliminate("t1 = a + b\nb = b + 1\nt2 = a + b\n")
    assert result.to_tac() == "t1 = a + b\nb = b + 1\nt2 = a + b"


def test_unrelated_assignment_does_not_invalidate_expression() -> None:
    assert eliminate("t1 = a + b\nc = 20\nt2 = a + b").to_tac() == "t1 = a + b\nc = 20\nt2 = t1"


def test_multiple_expression_keys_are_tracked_independently() -> None:
    result = eliminate("t1 = a + b\nt2 = c * d\nt3 = a + b\nt4 = c * d")
    assert result.to_tac() == "t1 = a + b\nt2 = c * d\nt3 = t1\nt4 = t2"


def test_redefined_result_is_not_reused() -> None:
    result = eliminate("t1 = a + b\nt1 = c + d\nt2 = a + b")
    assert result.to_tac() == "t1 = a + b\nt1 = c + d\nt2 = a + b"


def test_branch_only_expression_is_not_available_at_join() -> None:
    text = "if x < 10 goto L1\nt1 = a + b\ngoto L2\nL1:\nt2 = a + b\nL2:\nt3 = a + b\n"
    assert eliminate(text).to_tac() == text.rstrip()


def test_expression_available_on_all_join_paths_can_be_reused() -> None:
    text = "if x < 10 goto L1\nt1 = a + b\ngoto L2\nL1:\nt1 = a + b\nL2:\nt2 = a + b\n"
    assert eliminate(text).to_tac().splitlines()[-1] == "t2 = t1"


def test_loop_analysis_terminates_and_reuses_safe_expression() -> None:
    result = eliminate("t1 = a + b\nL1:\nt2 = a + b\ngoto L1\n")
    assert result.to_tac() == "t1 = a + b\nL1:\nt2 = a + b\ngoto L1"


def test_division_and_modulo_are_reused_without_changing_runtime_behavior() -> None:
    result = eliminate("t1 = a / b\nt2 = a / b\nt3 = a % b\nt4 = a % b")
    assert result.to_tac() == "t1 = a / b\nt2 = t1\nt3 = a % b\nt4 = t3"


def test_cse_does_not_propagate_or_fold_or_remove() -> None:
    result = eliminate("a = 10\nb = 20\nt1 = a + b\nt2 = a + b\n")
    assert result.to_tac() == "a = 10\nb = 20\nt1 = a + b\nt2 = t1"
    assert isinstance(result[2], BinaryOperation)


def test_control_flow_and_side_effects_are_preserved() -> None:
    text = "t1 = a + b\nprint t1\nif a < b goto L1\ngoto L2\nL1:\nreturn t1\nL2:\nreturn\n"
    result = eliminate(text)
    assert result.to_tac() == text.rstrip()


def test_statistics_and_determinism() -> None:
    text = "t1 = a + b\nt2 = a + b\nt3 = c + d\nt4 = c + d"
    pass_ = CommonSubexpressionElimination()
    result = pass_.run(parse_tac(text))
    assert result.to_tac() == "t1 = a + b\nt2 = t1\nt3 = c + d\nt4 = t3"
    assert pass_.last_result is not None
    stats = pass_.last_result.statistics
    assert stats.pass_name == "common_subexpression_elimination"
    assert stats.instructions_before == 4
    assert stats.instructions_after == 4
    assert stats.expressions_reused == 2
    assert stats.replacement_assignments_generated == 2
    assert stats.instructions_removed == 0
    assert stats.changed
    assert CommonSubexpressionElimination().run(parse_tac(text)).to_tac() == result.to_tac()
