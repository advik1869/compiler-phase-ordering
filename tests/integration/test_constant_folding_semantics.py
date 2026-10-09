"""Semantic-preservation tests for Constant Folding."""

from optimizer.analysis import execute
from optimizer.ir import parse_tac
from optimizer.passes import ConstantFolding


def test_direct_constant_expression_preserves_semantics() -> None:
    original = parse_tac("a = 10 + 20\nprint a\nreturn a\n")
    folded = ConstantFolding().run(original)
    assert folded.to_tac() == "a = 30\nprint a\nreturn a"
    assert execute(original).semantic_signature() == execute(folded).semantic_signature()


def test_variable_expression_remains_unchanged_and_semantic() -> None:
    original = parse_tac("a = 10\nb = 20\nc = a + b\nprint c\nreturn c\n")
    folded = ConstantFolding().run(original)
    assert folded.to_tac() == original.to_tac()
    assert execute(original).semantic_signature() == execute(folded).semantic_signature()


def test_constant_folding_does_not_call_constant_propagation() -> None:
    original = parse_tac("a = 10\nb = a\nc = b + 5\n")
    folded = ConstantFolding().run(original)
    assert folded.to_tac() == original.to_tac()

