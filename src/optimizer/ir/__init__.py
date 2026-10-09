"""Typed TAC intermediate representation and parser."""

from .model import (
    Assignment, BinaryOperation, ConditionalBranch, Goto, Instruction,
    IntegerConstant, Label, Operand, Print, Return, SourceLocation,
    TACProgram, UnaryOperation, Variable,
)
from .parser import TACParseError, load_tac, parse_tac

__all__ = [
    "Assignment", "BinaryOperation", "ConditionalBranch", "Goto",
    "Instruction", "IntegerConstant", "Label", "Operand", "Print",
    "Return", "SourceLocation", "TACParseError", "TACProgram",
    "UnaryOperation", "Variable", "load_tac", "parse_tac",
]
