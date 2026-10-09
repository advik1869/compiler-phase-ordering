"""Unit tests for deterministic TAC semantic execution."""

import pytest

from optimizer.analysis import TACExecutionError, execute
from optimizer.ir import parse_tac


def run(text: str, **kwargs):
    return execute(parse_tac(text), **kwargs)


def test_assignments_and_arithmetic() -> None:
    result = run("a = 10\nb = a\nt1 = a + b\nt2 = a - b\nt3 = a * b\n")
    assert result.variables == {"a": 10, "b": 10, "t1": 20, "t2": 0, "t3": 100}


def test_integer_division_truncates_toward_zero_and_modulo_matches_it() -> None:
    result = run("a = -7\nb = 2\nt1 = a / b\nt2 = a % b\nt3 = 7 / -2\nt4 = 7 % -2\n")
    assert result.variables["t1"] == -3
    assert result.variables["t2"] == -1
    assert result.variables["t3"] == -3
    assert result.variables["t4"] == 1


@pytest.mark.parametrize("operator, expected", [
    ("<", 1), ("<=", 1), ("==", 0), ("!=", 1), (">", 0), (">=", 0),
])
def test_relational_results_are_integer_booleans(operator: str, expected: int) -> None:
    result = run(f"t1 = 2 {operator} 3")
    assert result.variables["t1"] == expected


def test_unary_negation() -> None:
    result = run("a = 10\nt1 = -a\n")
    assert result.variables["t1"] == -10


def test_print_return_and_semantic_signature() -> None:
    result = run("a = 10\nprint a\nreturn a\nprint 0\n")
    assert result.output == (10,)
    assert result.return_value == 10
    assert result.terminated
    assert result.semantic_signature() == ((10,), 10, True)


def test_return_without_value_and_sequential_end_are_terminated() -> None:
    returned = run("return")
    ended = run("a = 1")
    assert returned.return_value is None and returned.terminated
    assert ended.return_value is None and ended.terminated


def test_goto_and_conditional_branch_taken_and_not_taken() -> None:
    taken = run("if 1 == 1 goto yes\nprint 0\nyes:\nprint 1\nreturn")
    not_taken = run("if 1 == 2 goto yes\nprint 0\nyes:\nreturn")
    assert taken.output == (1,)
    assert not_taken.output == (0,)


def test_loop_output_and_optional_trace() -> None:
    result = run("i = 0\nL1:\nprint i\ni = i + 1\nif i < 3 goto L1\nreturn", trace=True)
    assert result.output == (0, 1, 2)
    assert result.trace[0] == "PC=0: i = 0"
    assert result.trace[-1] == "PC=5: return"


def test_initial_environment_is_supported_without_mutating_input() -> None:
    initial = {"x": 5}
    result = run("y = x + 1\nreturn y", initial_environment=initial)
    assert result.return_value == 6
    assert initial == {"x": 5}


@pytest.mark.parametrize("text, message", [
    ("print x", "undefined variable"),
    ("x = 1\ny = 0\nt1 = x / y", "zero"),
    ("goto missing", "invalid branch target"),
])
def test_runtime_errors_include_useful_context(text: str, message: str) -> None:
    with pytest.raises(TACExecutionError, match=message) as error:
        run(text)
    assert error.value.program_counter is not None
    assert error.value.instruction is not None
    assert error.value.steps > 0


def test_modulo_by_zero_is_rejected() -> None:
    with pytest.raises(TACExecutionError, match="zero"):
        run("t1 = 4 % 0")


def test_infinite_loop_hits_configurable_step_limit() -> None:
    with pytest.raises(TACExecutionError, match="step.*limit"):
        run("L1:\ngoto L1", max_steps=5)


def test_semantic_signature_ignores_internal_variables_and_is_deterministic() -> None:
    first = run("a = 10\nb = 20\nt1 = a + b\nprint t1\nreturn t1")
    second = run("x = 30\nprint x\nreturn x")
    assert first.semantic_signature() == second.semantic_signature()
    assert first == run("a = 10\nb = 20\nt1 = a + b\nprint t1\nreturn t1")
