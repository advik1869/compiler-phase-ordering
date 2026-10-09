"""Semantic-preservation tests using the Phase 2 interpreter."""

import pytest

from optimizer.analysis import TACExecutionError, execute
from optimizer.ir import parse_tac
from optimizer.passes import ConstantPropagation


def assert_semantics_preserved(text: str) -> None:
    original = parse_tac(text)
    transformed = ConstantPropagation().run(original)
    assert execute(original).semantic_signature() == execute(transformed).semantic_signature()


def test_constant_propagation_preserves_straight_line_semantics() -> None:
    assert_semantics_preserved("a = 10\nb = a\nc = b + 5\nprint c\nreturn c\n")


def test_constant_propagation_preserves_branching_semantics() -> None:
    assert_semantics_preserved(
        "a = 10\nb = 20\nif a < b goto yes\nprint b\ngoto done\nyes:\nprint a\ndone:\nreturn\n"
    )


def test_constant_propagation_does_not_evaluate_division_by_zero() -> None:
    original = parse_tac("a = 10\nb = 0\nc = a / b\n")
    transformed = ConstantPropagation().run(original)
    assert transformed.to_tac() == "a = 10\nb = 0\nc = 10 / 0"
    with pytest.raises(TACExecutionError) as original_error:
        execute(original)
    with pytest.raises(TACExecutionError) as transformed_error:
        execute(transformed)
    assert original_error.value.reason == transformed_error.value.reason
