"""Conservative available-expression analysis for common subexpression elimination."""

from __future__ import annotations

from dataclasses import replace

from optimizer.ir import (
    Assignment,
    BinaryOperation,
    ConditionalBranch,
    Goto,
    Instruction,
    Label,
    Return,
    TACProgram,
    Variable,
)

from .base import OptimizationPass, PassResult, PassStatistics


ExpressionKey = tuple[str, object, object]
AvailableExpressions = dict[ExpressionKey, Variable]


def _expression_key(instruction: BinaryOperation) -> ExpressionKey:
    """Build an ordered, typed key for one pure binary expression."""
    return (instruction.operator, instruction.left, instruction.right)


def _build_cfg(program: TACProgram) -> tuple[list[tuple[int, ...]], list[list[int]]]:
    labels = {
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


def _kill_definitions(state: AvailableExpressions, instruction: Instruction) -> None:
    definitions = {variable.name for variable in instruction.defines()}
    if not definitions:
        return
    for key, result in list(state.items()):
        operands = key[1:]
        if result.name in definitions or any(
            isinstance(operand, Variable) and operand.name in definitions
            for operand in operands
        ):
            del state[key]


def _transfer(state: AvailableExpressions, instruction: Instruction) -> AvailableExpressions:
    result = dict(state)
    _kill_definitions(result, instruction)
    if isinstance(instruction, BinaryOperation):
        result[_expression_key(instruction)] = instruction.target
    return result


def _meet(states: list[AvailableExpressions]) -> AvailableExpressions:
    if not states:
        return {}
    common_keys = set(states[0])
    for state in states[1:]:
        common_keys.intersection_update(state)
    return {
        key: states[0][key]
        for key in sorted(common_keys, key=repr)
        if all(state[key] == states[0][key] for state in states[1:])
    }


def _available_in_states(program: TACProgram) -> dict[int, AvailableExpressions]:
    """Compute fixed-point available expressions at every instruction."""
    successors, predecessors = _build_cfg(program)
    reachable: set[int] = set()
    pending = [0] if len(program) else []
    while pending:
        index = pending.pop()
        if index in reachable:
            continue
        reachable.add(index)
        pending.extend(successors[index])

    in_states: dict[int, AvailableExpressions] = {0: {}} if len(program) else {}
    out_states: dict[int, AvailableExpressions] = {}
    worklist = [0] if len(program) else []

    while worklist:
        index = worklist.pop(0)
        incoming = [
            out_states[pred]
            for pred in predecessors[index]
            if pred in reachable and pred in out_states
        ]
        if index == 0:
            incoming.insert(0, {})
        new_in = _meet(incoming)
        new_out = _transfer(new_in, program[index])
        if in_states.get(index) == new_in and out_states.get(index) == new_out:
            continue
        in_states[index] = new_in
        out_states[index] = new_out
        for successor in successors[index]:
            if successor not in worklist:
                worklist.append(successor)
    return in_states


class CommonSubexpressionElimination(OptimizationPass):
    """Reuse previously available pure binary expression results."""

    name = "common_subexpression_elimination"

    def run_with_result(self, program: TACProgram) -> PassResult:
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")
        in_states = _available_in_states(program)
        transformed: list[Instruction] = []
        expressions_reused = 0

        for index, instruction in enumerate(program):
            available = in_states.get(index, {})
            if isinstance(instruction, BinaryOperation):
                result = available.get(_expression_key(instruction))
                if result is not None and result != instruction.target:
                    transformed.append(Assignment(
                        target=instruction.target,
                        value=result,
                        source=instruction.source,
                    ))
                    expressions_reused += 1
                    continue
            transformed.append(replace(instruction))

        result_program = TACProgram(transformed)
        statistics = PassStatistics(
            pass_name=self.name,
            instructions_before=len(program),
            instructions_after=len(result_program),
            expressions_reused=expressions_reused,
            replacement_assignments_generated=expressions_reused,
            instructions_removed=0,
            changed=expressions_reused > 0,
        )
        return PassResult(result_program, statistics)
