"""Load, execute, optimize, and semantically verify manual_test.tac."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from optimizer.analysis import execute
from optimizer.ir import load_tac
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
)
from optimizer.pipeline import OptimizationPipeline


def main() -> int:
    program = load_tac(str(Path(__file__).with_name("manual_test.tac")))
    original_result = execute(program)
    pipeline = OptimizationPipeline()
    optimized = pipeline.run(program, [
        ConstantPropagation(),
        ConstantFolding(),
        DeadCodeElimination(),
        CommonSubexpressionElimination(),
    ])
    optimized_result = execute(optimized.final_program)

    print("Original output:", original_result.output)
    print("Original return value:", original_result.return_value)
    print("Original instruction count:", len(program))
    print("Optimized TAC:")
    print(optimized.final_program.to_tac())
    print("Optimized output:", optimized_result.output)
    print("Optimized return value:", optimized_result.return_value)
    print("Optimized instruction count:", len(optimized.final_program))

    if original_result.semantic_signature() != optimized_result.semantic_signature():
        raise RuntimeError("semantic equivalence check failed")
    print("Semantic equivalence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
