"""Unit tests for the Phase 1 TAC representation and parser."""

import pytest

from optimizer.ir import (
    Assignment, BinaryOperation, ConditionalBranch, Goto, IntegerConstant,
    Label, Print, Return, TACParseError, UnaryOperation, Variable, parse_tac,
)


def test_integer_and_variable_operands_are_typed() -> None:
    program = parse_tac("x = 10\nt1 = x\n")
    assert isinstance(program[0], Assignment)
    assert program[0].value == IntegerConstant(10)
    assert isinstance(program[1].value, Variable)
    assert program[1].value.name == "x"
    assert Variable("t1").is_temporary
    assert not Variable("total").is_temporary


@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "%", "<", "<=", "==", "!=", ">", ">="])
def test_binary_operations(operator: str) -> None:
    instruction = parse_tac(f"t1 = a {operator} b")[0]
    assert isinstance(instruction, BinaryOperation)
    assert instruction.operator == operator
    assert instruction.uses() == (Variable("a"), Variable("b"))
    assert instruction.defines() == (Variable("t1"),)


def test_unary_operation() -> None:
    instruction = parse_tac("t1 = - x")[0]
    assert isinstance(instruction, UnaryOperation)
    assert instruction.uses() == (Variable("x"),)
    assert instruction.to_tac() == "t1 = -x"


def test_control_flow_and_observable_instructions() -> None:
    program = parse_tac("L1:\ngoto L1\nif x < y goto L1\nreturn x\nreturn\nprint x\n")
    assert isinstance(program[0], Label)
    assert isinstance(program[1], Goto)
    assert isinstance(program[2], ConditionalBranch)
    assert program[2].uses() == (Variable("x"), Variable("y"))
    assert isinstance(program[3], Return) and program[3].uses() == (Variable("x"),)
    assert isinstance(program[4], Return) and program[4].uses() == ()
    assert isinstance(program[5], Print) and program[5].uses() == (Variable("x"),)
    assert not program[0].has_side_effects
    assert program[1].has_side_effects and program[1].is_control_flow
    assert program[2].has_side_effects and program[2].is_control_flow
    assert program[3].has_side_effects and program[4].has_side_effects
    assert program[5].has_side_effects


def test_comments_blank_lines_source_locations_and_serialization() -> None:
    text = "# header\n\nx = 10  \n# comment\nt1 = x + 20\nprint t1\n"
    program = parse_tac(text)
    assert len(program) == 3
    assert program[0].source is not None
    assert program[0].source.line == 3
    assert program[0].source.text == "x = 10  "
    assert program.to_tac() == "x = 10\nt1 = x + 20\nprint t1"


def test_program_copy_is_independent() -> None:
    program = parse_tac("x = 1")
    copied = program.copy()
    copied.append(parse_tac("y = 2")[0])
    assert len(program) == 1
    assert len(copied) == 2


def test_round_trip_is_structurally_equivalent() -> None:
    text = "x = 10\ny = -5\nt1 = x + y\nt2 = - t1\nif t2 >= 0 goto done\nprint t2\ndone:\nreturn t2\n"
    first = parse_tac(text)
    second = parse_tac(first.to_tac())
    assert first.structurally_equal(second)
    assert first == second


@pytest.mark.parametrize("bad_text", ["t1 =", "t1 = x +", "if x goto", "goto", "invalid syntax"])
def test_malformed_tac_reports_line_context(bad_text: str) -> None:
    with pytest.raises(TACParseError) as error:
        parse_tac(f"x = 1\n{bad_text}\n")
    assert error.value.line_number == 2
    assert bad_text in str(error.value)


def test_invalid_identifier_is_rejected() -> None:
    with pytest.raises(TACParseError):
        parse_tac("1x = 3")
