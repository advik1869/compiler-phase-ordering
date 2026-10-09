"""Integration tests for pipeline semantic preservation."""

from optimizer.analysis import execute
from optimizer.ir import parse_tac
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
)
from optimizer.pipeline import OptimizationPipeline


def test_pipeline_preserves_semantics() -> None:
    original = parse_tac(
        "a = 10\nb = a\nt1 = b + 5\nt2 = b + 5\nprint t2\nreturn t2\n"
    )
    result = OptimizationPipeline().run(original, [
        ConstantPropagation(), ConstantFolding(),
        CommonSubexpressionElimination(), DeadCodeElimination(),
    ])
    assert execute(original).semantic_signature() == execute(result.final_program).semantic_signature()

