"""Forward dataflow constant propagation for the Phase 3 optimizer."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto

from optimizer.ir import (
    Assignment,
    BinaryOperation,
    ConditionalBranch,
    Goto,
    Instruction,
    IntegerConstant,
    Label,
    Operand,
    Print,
    Return,
    TACProgram,
    UnaryOperation,
    Variable,
)

from .base import OptimizationPass, PassResult, PassStatistics


class LatticeKind(Enum):
    """The three abstract values used by constant propagation."""

    UNDEFINED = auto()
    CONSTANT = auto()
    NOT_CONSTANT = auto()


@dataclass(frozen=True)
class LatticeValue:
    """An abstract variable value, optionally carrying an integer constant."""

    kind: LatticeKind
    value: int | None = None

    @classmethod
    def undefined(cls) -> LatticeValue:
        return cls(LatticeKind.UNDEFINED)

    @classmethod
    def constant(cls, value: int) -> LatticeValue:
        return cls(LatticeKind.CONSTANT, value)

    @classmethod
    def not_constant(cls) -> LatticeValue:
        return cls(LatticeKind.NOT_CONSTANT)


State = dict[str, LatticeValue]


def _value_for(state: State, variable: Variable) -> LatticeValue:
    return state.get(variable.name, LatticeValue.undefined())


def _meet(states: list[State]) -> State:
    """Meet incoming states conservatively at a control-flow join."""
    if not states:
        return {}
    result: State = {}
    names = set().union(*(state.keys() for state in states))
    for name in sorted(names):
        values = [state.get(name, LatticeValue.undefined()) for state in states]
        if all(value.kind is LatticeKind.UNDEFINED for value in values):
            continue
        if any(value.kind is LatticeKind.UNDEFINED for value in values):
            result[name] = LatticeValue.not_constant()
            continue
        if all(value.kind is LatticeKind.CONSTANT for value in values):
            constants = {value.value for value in values}
            if len(constants) == 1:
                result[name] = LatticeValue.constant(constants.pop())
                continue
        result[name] = LatticeValue.not_constant()
    return result


def _transfer(in_state: State, instruction: Instruction) -> State:
    state = dict(in_state)
    if isinstance(instruction, Assignment):
        if isinstance(instruction.value, IntegerConstant):
            state[instruction.target.name] = LatticeValue.constant(instruction.value.value)
        elif isinstance(instruction.value, Variable):
            value = _value_for(in_state, instruction.value)
            state[instruction.target.name] = (
                value if value.kind is LatticeKind.CONSTANT else LatticeValue.not_constant()
            )
    elif isinstance(instruction, (BinaryOperation, UnaryOperation)):
        # The expression remains an expression. Evaluating it belongs to folding.
        target = instruction.target
        state[target.name] = LatticeValue.not_constant()
    return state


def _successors(program: TACProgram) -> tuple[dict[str, int], list[tuple[int, ...]]]:
    labels: dict[str, int] = {}
    for index, instruction in enumerate(program):
        if isinstance(instruction, Label):
            labels[instruction.name] = index

    edges: list[tuple[int, ...]] = []
    for index, instruction in enumerate(program):
        fallthrough = (index + 1,) if index + 1 < len(program) else ()
        if isinstance(instruction, Goto):
            edges.append((labels[instruction.target],) if instruction.target in labels else ())
        elif isinstance(instruction, ConditionalBranch):
            target = (labels[instruction.target],) if instruction.target in labels else ()
            edges.append(target + fallthrough)
        elif isinstance(instruction, Return):
            edges.append(())
        else:
            edges.append(fallthrough)
    return labels, edges


def _replace_operand(operand: Operand, state: State) -> tuple[Operand, int]:
    if isinstance(operand, Variable):
        value = _value_for(state, operand)
        if value.kind is LatticeKind.CONSTANT:
            return IntegerConstant(value.value), 1
    return operand, 0


class ConstantPropagation(OptimizationPass):
    """Replace provably constant variable operands without evaluating expressions."""

    name = "constant_propagation"

    def _analyze(self, program: TACProgram) -> dict[int, State]:
        _, edges = _successors(program)
        predecessors: list[list[int]] = [[] for _ in program]
        for source, targets in enumerate(edges):
            for target in targets:
                predecessors[target].append(source)

        in_states: dict[int, State] = {0: {}} if len(program) else {}
        out_states: dict[int, State] = {}
        worklist = [0] if len(program) else []
        while worklist:
            index = worklist.pop(0)
            incoming_states = [out_states[pred] for pred in predecessors[index] if pred in out_states]
            if index == 0:
                incoming_states.insert(0, {})
            incoming = _meet(incoming_states)
            if in_states.get(index) != incoming:
                in_states[index] = incoming
            outgoing = _transfer(incoming, program[index])
            if out_states.get(index) == outgoing:
                continue
            out_states[index] = outgoing
            for successor in edges[index]:
                if successor not in worklist:
                    worklist.append(successor)
        return in_states

    def _transform_instruction(self, instruction: Instruction, state: State) -> tuple[Instruction, int]:
        if isinstance(instruction, Assignment):
            value, count = _replace_operand(instruction.value, state)
            return replace(instruction, value=value), count
        if isinstance(instruction, BinaryOperation):
            left, left_count = _replace_operand(instruction.left, state)
            right, right_count = _replace_operand(instruction.right, state)
            return replace(instruction, left=left, right=right), left_count + right_count
        if isinstance(instruction, UnaryOperation):
            operand, count = _replace_operand(instruction.operand, state)
            return replace(instruction, operand=operand), count
        if isinstance(instruction, ConditionalBranch):
            left, left_count = _replace_operand(instruction.left, state)
            right, right_count = _replace_operand(instruction.right, state)
            return replace(instruction, left=left, right=right), left_count + right_count
        if isinstance(instruction, Print):
            value, count = _replace_operand(instruction.value, state)
            return replace(instruction, value=value), count
        if isinstance(instruction, Return) and instruction.value is not None:
            value, count = _replace_operand(instruction.value, state)
            return replace(instruction, value=value), count
        return instruction, 0

    def run_with_result(self, program: TACProgram) -> PassResult:
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")
        in_states = self._analyze(program)
        transformed: list[Instruction] = []
        replacements = 0
        for index, instruction in enumerate(program):
            transformed_instruction, count = self._transform_instruction(
                instruction, in_states.get(index, {})
            )
            transformed.append(transformed_instruction)
            replacements += count
        result_program = TACProgram(transformed)
        statistics = PassStatistics(
            pass_name=self.name,
            instructions_before=len(program),
            instructions_after=len(result_program),
            operands_replaced=replacements,
            instructions_removed=0,
            changed=replacements > 0,
        )
        return PassResult(result_program, statistics)
