"""Shared interface and statistics for optimization passes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from optimizer.ir import TACProgram


@dataclass(frozen=True)
class PassStatistics:
    """Deterministic summary of one optimization pass execution."""

    pass_name: str
    instructions_before: int
    instructions_after: int
    operands_replaced: int = 0
    expressions_folded: int = 0
    expressions_reused: int = 0
    replacement_assignments_generated: int = 0
    dead_instructions_removed: int = 0
    instructions_removed: int = 0
    changed: bool = False


@dataclass(frozen=True)
class PassResult:
    """The transformed program and the statistics describing the transform."""

    program: TACProgram
    statistics: PassStatistics


class OptimizationPass(ABC):
    """Common interface for the four implemented optimization passes."""

    name: str

    def __init__(self) -> None:
        self.last_result: PassResult | None = None

    def run(self, program: TACProgram) -> TACProgram:
        """Return a transformed copy and retain its statistics in ``last_result``."""
        result = self.run_with_result(program)
        self.last_result = result
        return result.program

    @abstractmethod
    def run_with_result(self, program: TACProgram) -> PassResult:
        """Transform ``program`` and return the program plus statistics."""
