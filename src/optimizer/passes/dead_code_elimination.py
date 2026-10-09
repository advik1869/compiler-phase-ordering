"""Backward liveness-based dead-code elimination for TAC programs."""

from __future__ import annotations

from dataclasses import replace

from optimizer.ir import ConditionalBranch, Goto, Instruction, Label, Return, TACProgram

from .base import OptimizationPass, PassResult, PassStatistics


def _build_cfg(program: TACProgram) -> tuple[list[tuple[int, ...]], list[list[int]]]:
    """Build instruction successors and predecessors without changing the program."""
    labels: dict[str, int] = {
        instruction.name: index
        for index, instruction in enumerate(program)
        if isinstance(instruction, Label)
    }
    successors: list[tuple[int, ...]] = []
    predecessors: list[list[int]] = [[] for _ in program]

    for index, instruction in enumerate(program):
        fallthrough = (index + 1,) if index + 1 < len(program) else ()
        if isinstance(instruction, Goto):
            edges = (labels[instruction.target],) if instruction.target in labels else ()
        elif isinstance(instruction, ConditionalBranch):
            target = (labels[instruction.target],) if instruction.target in labels else ()
            edges = target + fallthrough
        elif isinstance(instruction, Return):
            edges = ()
        else:
            edges = fallthrough
        successors.append(edges)
        for successor in edges:
            predecessors[successor].append(index)
    return successors, predecessors


def _liveness(program: TACProgram) -> tuple[list[set[str]], list[set[str]]]:
    """Compute fixed-point live-in and live-out sets for every instruction."""
    successors, predecessors = _build_cfg(program)
    live_in = [set() for _ in program]
    live_out = [set() for _ in program]
    worklist = list(reversed(range(len(program))))

    while worklist:
        index = worklist.pop(0)
        new_out: set[str] = set()
        for successor in successors[index]:
            new_out.update(live_in[successor])
        defined = {variable.name for variable in program[index].defines()}
        used = {variable.name for variable in program[index].uses()}
        if _is_removable(program[index], new_out):
            # A dead pure instruction does not keep its own operands alive.
            # This allows dead dependency chains to disappear in one fixed point.
            new_in = new_out - defined
        else:
            new_in = used | (new_out - defined)
        if new_out == live_out[index] and new_in == live_in[index]:
            continue
        live_out[index] = new_out
        live_in[index] = new_in
        for predecessor in predecessors[index]:
            if predecessor not in worklist:
                worklist.append(predecessor)
    return live_in, live_out


def _is_removable(instruction: Instruction, live_out: set[str]) -> bool:
    """Return whether this instruction is a pure dead definition."""
    if isinstance(instruction, Label) or instruction.is_control_flow or instruction.has_side_effects:
        return False
    definitions = instruction.defines()
    return bool(definitions) and all(variable.name not in live_out for variable in definitions)


class DeadCodeElimination(OptimizationPass):
    """Remove pure instructions whose defined values are not live."""

    name = "dead_code_elimination"

    def run_with_result(self, program: TACProgram) -> PassResult:
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")

        _, live_out = _liveness(program)
        retained = [
            replace(instruction)
            for index, instruction in enumerate(program)
            if not _is_removable(instruction, live_out[index])
        ]
        result_program = TACProgram(retained)
        removed = len(program) - len(result_program)
        statistics = PassStatistics(
            pass_name=self.name,
            instructions_before=len(program),
            instructions_after=len(result_program),
            dead_instructions_removed=removed,
            instructions_removed=removed,
            changed=removed > 0,
        )
        return PassResult(result_program, statistics)
