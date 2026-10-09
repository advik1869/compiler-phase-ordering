"""Semantic-preservation tests for Common Subexpression Elimination."""

import pytest

from optimizer.analysis import TACExecutionError, execute
from optimizer.ir import parse_tac
from optimizer.passes import CommonSubexpressionElimination


def test_cse_preserves_repeated_arithmetic_semantics() -> None:
    original = parse_tac("a = 10\nb = 20\nt1 = a + b\nt2 = a + b\nprint t2\nreturn t2\n")
    transformed = CommonSubexpressionElimination().run(original)
    assert transformed.to_tac() == "a = 10\nb = 20\nt1 = a + b\nt2 = t1\nprint t2\nreturn t2"
    assert execute(original).semantic_signature() == execute(transformed).semantic_signature()


def test_cse_preserves_branch_semantics() -> None:
    # The parser supports print of one operand, so materialize the expression.
    text = "a = 10\nb = 20\nif a < b goto yes\nt1 = a + b\ngoto done\nyes:\nt2 = a + b\ndone:\nt3 = a + b\nprint t3\nreturn\n"
    original = parse_tac(text)
    transformed = CommonSubexpressionElimination().run(original)
    assert execute(original).semantic_signature() == execute(transformed).semantic_signature()


def test_cse_preserves_division_by_zero_error_behavior() -> None:
    original = parse_tac("a = 10\nb = 0\nt1 = a / b\nt2 = a / b\n")
    transformed = CommonSubexpressionElimination().run(original)
    with pytest.raises(TACExecutionError) as original_error:
        execute(original)
    with pytest.raises(TACExecutionError) as transformed_error:
        execute(transformed)
    assert original_error.value.reason == transformed_error.value.reason
