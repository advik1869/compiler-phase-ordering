"""Optimization-pass interfaces and implemented passes."""

from .base import OptimizationPass, PassResult, PassStatistics
from .constant_propagation import ConstantPropagation, LatticeKind, LatticeValue
from .constant_folding import ConstantFolding
from .dead_code_elimination import DeadCodeElimination
from .common_subexpression_elimination import CommonSubexpressionElimination

__all__ = [
    "ConstantPropagation",
    "ConstantFolding",
    "DeadCodeElimination",
    "CommonSubexpressionElimination",
    "LatticeKind",
    "LatticeValue",
    "OptimizationPass",
    "PassResult",
    "PassStatistics",
]
