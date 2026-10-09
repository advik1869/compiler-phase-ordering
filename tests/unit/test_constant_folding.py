"""Unit tests for the Phase 4 constant-folding pass."""

import pytest

from optimizer.ir import (
    Assignment, BinaryOperation, ConditionalBranch, Goto, IntegerConstant,
    Label, Print, Return, TACProgram, UnaryOperation, Variable, parse_tac,
)
from optimizer.passes import ConstantFolding


def fold(text: str):
    return ConstantFolding().run(parse_tac(text))


@pytest.mark.parametrize("expression, expected", [
    ("10 + 20", 30), ("20 - 7", 13), ("6 * 7", 42), ("20 / 6", 3), ("20 % 6", 2),
])
def test_arithmetic_folding(expression: str, expected: int) -> None:
    program = fold(f"t1 = {expression}")
    assert isinstance(program[0], Assignment)
    assert program[0].value == IntegerConstant(expected)


@pytest.mark.parametrize("expression, expected", [
    ("7 / 2", 3), ("-7 / 2", -3), ("7 / -2", -3), ("-7 / -2", 3),
])
def test_negative_division_uses_truncation_toward_zero(expression: str, expected: int) -> None:
    assert fold(f"t1 = {expression}")[0].value == IntegerConstant(expected)


def test_unary_negation_with_literal_is_canonical_constant() -> None:
    program = ConstantFolding().run(parse_tac("t1 = -10"))
    assert program.to_tac() == "t1 = -10"
    explicit = ConstantFolding().run(TACProgram([UnaryOperation(
        target=Variable("t2"), operator="-", operand=IntegerConstant(10)
    )]))
    assert explicit.to_tac() == "t2 = -10"


@pytest.mark.parametrize("expression, expected", [
    ("2 < 3", 1), ("2 <= 2", 1), ("2 == 2", 1),
    ("2 != 2", 0), ("3 > 4", 0), ("3 >= 3", 1),
])
def test_relational_folding(expression: str, expected: int) -> None:
    program = fold(f"t1 = {expression}")
    assert program[0].value == IntegerConstant(expected)


def test_nonconstant_operands_are_not_folded() -> None:
    assert fold("a = 10\nt1 = a + x").to_tac() == "a = 10\nt1 = a + x"
    assert fold("a = 10\nb = 20\nt1 = a + b").to_tac() == "a = 10\nb = 20\nt1 = a + b"


def test_division_and_modulo_by_zero_are_preserved() -> None:
    program = fold("t1 = 10 / 0\nt2 = 10 % 0")
    assert program.to_tac() == "t1 = 10 / 0\nt2 = 10 % 0"


def test_control_flow_and_observable_instructions_are_preserved() -> None:
    original = parse_tac("L1:\nt1 = 10 + 20\ngoto L1\nif 1 < 2 goto L1\nprint t1\nreturn t1\n")
    folded = ConstantFolding().run(original)
    assert folded.to_tac() == "L1:\nt1 = 30\ngoto L1\nif 1 < 2 goto L1\nprint t1\nreturn t1"
    assert isinstance(folded[0], Label)
    assert isinstance(folded[2], Goto)
    assert isinstance(folded[3], ConditionalBranch)
    assert isinstance(folded[4], Print)
    assert isinstance(folded[5], Return)
    assert folded[0].source == original[0].source


def test_statistics_and_pass_separation() -> None:
    pass_ = ConstantFolding()
    result = pass_.run(parse_tac("a = 10\nb = 20\nc = a + b\nt1 = 10 + 20"))
    assert result.to_tac() == "a = 10\nb = 20\nc = a + b\nt1 = 30"
    assert pass_.last_result is not None
    statistics = pass_.last_result.statistics
    assert statistics.pass_name == "constant_folding"
    assert statistics.instructions_before == 4
    assert statistics.instructions_after == 4
    assert statistics.expressions_folded == 1
    assert statistics.instructions_removed == 0
    assert statistics.changed


def test_determinism() -> None:
    text = "t1 = 10 + 20\nt2 = 7 / 2\n"
    assert ConstantFolding().run(parse_tac(text)).to_tac() == ConstantFolding().run(parse_tac(text)).to_tac()
