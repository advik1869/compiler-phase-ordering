"""Demonstrate one real optimization pipeline run from the project root."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from optimizer.ir import parse_tac
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
)
from optimizer.pipeline import OptimizationPipeline


program = parse_tac("""
a = 10
b = 20
c = a + b
d = c * 2
e = d + 100
t1 = a + b
t2 = a + b
unused = 50
print t2
return t2
""")
pass_order = (
    ConstantPropagation(),
    ConstantFolding(),
    DeadCodeElimination(),
    CommonSubexpressionElimination(),
)
result = OptimizationPipeline().run(program, pass_order)

print("Pass order:", " -> ".join(optimization_pass.name for optimization_pass in pass_order))
print("Original TAC:")
print(program.to_tac())
print("Optimized TAC:")
print(result.final_program.to_tac())
print("Instructions before:", len(program))
print("Instructions after:", len(result.final_program))
