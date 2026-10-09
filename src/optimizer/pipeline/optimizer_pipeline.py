"""Generic ordered execution of optimization passes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from optimizer.ir import TACProgram
from optimizer.passes import OptimizationPass, PassResult


class PipelineExecutionError(RuntimeError):
    """A pass failure annotated with its position and pass name."""

    def __init__(self, pass_name: str, pass_index: int, error: Exception) -> None:
        self.pass_name = pass_name
        self.pass_index = pass_index
        self.original_error = error
        super().__init__(
            f"optimization pipeline failed while executing pass {pass_index + 1} "
            f"({pass_name}): {error}"
        )


@dataclass(frozen=True)
class PipelineResult:
    """The final program and an immutable history of every executed pass."""

    final_program: TACProgram
    pass_results: tuple[PassResult, ...]
    pass_order: tuple[str, ...]
    changed: bool

    @property
    def final_instruction_count(self) -> int:
        """Return the final TAC instruction count."""
        return len(self.final_program)


class OptimizationPipeline:
    """Execute an explicitly ordered sequence of optimization passes."""

    def __init__(self, passes: Sequence[OptimizationPass] | None = None) -> None:
        self._passes = tuple(passes) if passes is not None else None

    def run(
        self,
        program: TACProgram,
        passes: Sequence[OptimizationPass] | None = None,
    ) -> PipelineResult:
        """Run the supplied passes in exact order and return their history.

        A copy is passed into the first pass, and every pass receives a copy of
        the previous intermediate program. This keeps the caller's input and
        prior snapshots safe even if a future pass implementation mutates its
        argument internally.
        """
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")
        selected = tuple(self._passes if passes is None else passes)
        for optimization_pass in selected:
            if not isinstance(optimization_pass, OptimizationPass):
                raise TypeError("all pipeline entries must be OptimizationPass instances")

        current = program.copy()
        pass_results: list[PassResult] = []
        pass_order: list[str] = []
        for index, optimization_pass in enumerate(selected):
            pass_order.append(optimization_pass.name)
            try:
                optimization_pass.run(current.copy())
                result = optimization_pass.last_result
                if result is None:
                    raise RuntimeError("pass did not provide a PassResult")
                current = result.program.copy()
            except Exception as error:
                raise PipelineExecutionError(
                    optimization_pass.name, index, error
                ) from error
            pass_results.append(result)

        return PipelineResult(
            final_program=current,
            pass_results=tuple(pass_results),
            pass_order=tuple(pass_order),
            changed=any(result.statistics.changed for result in pass_results),
        )

