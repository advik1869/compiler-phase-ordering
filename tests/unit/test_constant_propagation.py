"""Unit tests for the Phase 3 constant-propagation pass."""

from optimizer.ir import BinaryOperation, ConditionalBranch, IntegerConstant, parse_tac
from optimizer.passes import ConstantPropagation, LatticeKind


def optimize(text: str):
    return ConstantPropagation().run(parse_tac(text))


def test_simple_and_transitive_propagation() -> None:
    program = optimize("a = 10\nb = a\nc = b")
    assert program.to_tac() == "a = 10\nb = 10\nc = 10"


def test_propagates_operands_but_does_not_fold() -> None:
    program = optimize("a = 10\nb = 20\nc = a + b\nt1 = a < b")
    assert program.to_tac() == "a = 10\nb = 20\nc = 10 + 20\nt1 = 10 < 20"
    assert isinstance(program[2], BinaryOperation)
    assert isinstance(program[2].left, IntegerConstant)
    assert program[2].left.value == 10


def test_propagates_conditional_operands_without_simplifying_branch() -> None:
    program = optimize("a = 10\nb = 20\nif a < b goto L1\nL1:\nreturn")
    assert program.to_tac() == "a = 10\nb = 20\nif 10 < 20 goto L1\nL1:\nreturn"
    assert isinstance(program[2], ConditionalBranch)


def test_reassignment_kills_previous_constant() -> None:
    program = optimize("a = 10\nb = a\na = 20\nc = a")
    assert program.to_tac() == "a = 10\nb = 10\na = 20\nc = 20"


def test_unknown_assignment_is_not_propagated() -> None:
    program = optimize("a = x\nb = a\n")
    assert program.to_tac() == "a = x\nb = a"


def test_same_constant_at_branch_join_is_safe() -> None:
    program = optimize(
        "cond = 1\nif cond == 1 goto then\nx = 10\ngoto join\nthen:\nx = 10\njoin:\ny = x\n"
    )
    assert program.to_tac().splitlines()[-1] == "y = 10"


def test_different_constants_at_branch_join_are_not_propagated() -> None:
    program = optimize(
        "cond = 1\nif cond == 1 goto then\nx = 10\ngoto join\nthen:\nx = 20\njoin:\ny = x\n"
    )
    assert program.to_tac().splitlines()[-1] == "y = x"


def test_undefined_on_one_branch_is_not_propagated() -> None:
    program = optimize(
        "cond = 1\nif cond == 1 goto then\nx = 10\ngoto join\nthen:\ngoto join\njoin:\ny = x\n"
    )
    assert program.to_tac().splitlines()[-1] == "y = x"


def test_unreachable_code_does_not_influence_reachable_code() -> None:
    program = optimize("goto live\nx = 99\nlive:\ny = 1\nz = y\n")
    assert program.to_tac() == "goto live\nx = 99\nlive:\ny = 1\nz = 1"


def test_loop_analysis_terminates_and_is_conservative() -> None:
    program = optimize("i = 0\nL1:\nx = i\ni = i + 1\nif i < 3 goto L1\ny = i\n")
    assert len(program) == 6
    assert program.to_tac().splitlines()[2] == "x = i"
    assert program.to_tac().splitlines()[-1] == "y = i"


def test_lattice_helpers_have_expected_meaning() -> None:
    assert LatticeKind.CONSTANT.name == "CONSTANT"
    assert LatticeKind.UNDEFINED.name == "UNDEFINED"
    assert LatticeKind.NOT_CONSTANT.name == "NOT_CONSTANT"


def test_labels_and_control_flow_are_preserved_and_source_is_retained() -> None:
    original = parse_tac("a = 10\nL1:\ngoto L1\n")
    transformed = ConstantPropagation().run(original)
    assert transformed.to_tac() == original.to_tac()
    assert transformed[1].source == original[1].source


def test_pass_statistics_report_replacements_and_no_removals() -> None:
    pass_ = ConstantPropagation()
    transformed = pass_.run(parse_tac("a = 10\nb = a\nc = b + 1"))
    assert transformed.to_tac() == "a = 10\nb = 10\nc = 10 + 1"
    assert pass_.last_result is not None
    statistics = pass_.last_result.statistics
    assert statistics.pass_name == "constant_propagation"
    assert statistics.instructions_before == 3
    assert statistics.instructions_after == 3
    assert statistics.operands_replaced == 2
    assert statistics.instructions_removed == 0
    assert statistics.changed


def test_pass_is_deterministic() -> None:
    text = "a = 10\nb = a\nc = b + 5\n"
    first = ConstantPropagation().run(parse_tac(text))
    second = ConstantPropagation().run(parse_tac(text))
    assert first.to_tac() == second.to_tac()
