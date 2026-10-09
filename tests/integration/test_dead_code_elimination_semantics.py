"""Semantic-preservation tests for Dead Code Elimination."""

from optimizer.analysis import execute
from optimizer.ir import parse_tac
from optimizer.passes import ConstantFolding, DeadCodeElimination


def assert_semantics_preserved(text: str) -> None:
    original = parse_tac(text)
    transformed = DeadCodeElimination().run(original)
    assert execute(original).semantic_signature() == execute(transformed).semantic_signature()


def test_dce_preserves_print_and_return_semantics() -> None:
    assert_semantics_preserved("dead = 99\na = 10\nprint a\nreturn a\n")


def test_dce_preserves_branch_and_loop_semantics() -> None:
    assert_semantics_preserved(
        "dead = 100\ni = 0\nL1:\nprint i\ni = i + 1\nif i < 3 goto L1\nreturn\n"
    )


def test_dce_after_constant_folding_without_pipeline_implementation() -> None:
    original = parse_tac("t1 = 10 + 20\nx = 5\nreturn t1\n")
    folded = ConstantFolding().run(original)
    eliminated = DeadCodeElimination().run(folded)
    assert folded.to_tac() == "t1 = 30\nx = 5\nreturn t1"
    assert eliminated.to_tac() == "t1 = 30\nreturn t1"
    assert execute(original).semantic_signature() == execute(eliminated).semantic_signature()

