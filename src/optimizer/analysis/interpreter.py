"""Deterministic interpreter for the project's typed TAC IR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from optimizer.ir import (
    Assignment, BinaryOperation, ConditionalBranch, Goto, Instruction,
    IntegerConstant, Label, Print, Return, TACProgram, UnaryOperation, Variable,
)


class TACExecutionError(RuntimeError):
    """A runtime error raised while executing a TAC program."""

    def __init__(self, reason: str, *, program_counter: int | None = None,
                 instruction: Instruction | None = None, steps: int = 0) -> None:
        self.reason = reason
        self.program_counter = program_counter
        self.instruction = instruction
        self.steps = steps
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        location = "" if self.program_counter is None else f" at instruction {self.program_counter}"
        instruction = "" if self.instruction is None else f":\n    {self.instruction.to_tac()}"
        return f"{self.reason}{location}{instruction} (steps={self.steps})"


@dataclass(frozen=True)
class ExecutionResult:
    """Observable and debugging information produced by one execution."""

    output: tuple[int, ...]
    return_value: int | None
    variables: dict[str, int]
    steps: int
    terminated: bool
    trace: tuple[str, ...] = ()

    def semantic_signature(self) -> tuple[tuple[int, ...], int | None, bool]:
        """Return observable behavior, excluding internal variable state."""
        return (self.output, self.return_value, self.terminated)


def _runtime_error(reason: str, *, pc: int | None, instruction: Instruction | None,
                   steps: int) -> TACExecutionError:
    return TACExecutionError(reason, program_counter=pc, instruction=instruction, steps=steps)


def _read_operand(operand: IntegerConstant | Variable, environment: Mapping[str, int], *,
                  pc: int, instruction: Instruction, steps: int) -> int:
    if isinstance(operand, IntegerConstant):
        return operand.value
    if isinstance(operand, Variable):
        try:
            return environment[operand.name]
        except KeyError as error:
            raise _runtime_error(f"undefined variable {operand.name!r}", pc=pc,
                                 instruction=instruction, steps=steps) from error
    raise _runtime_error(f"unsupported operand type {type(operand).__name__}", pc=pc,
                         instruction=instruction, steps=steps)


def _truncating_division(left: int, right: int) -> int:
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def _binary_value(operator: str, left: int, right: int) -> int:
    if operator == "+": return left + right
    if operator == "-": return left - right
    if operator == "*": return left * right
    if operator == "/": return _truncating_division(left, right)
    if operator == "%": return left - _truncating_division(left, right) * right
    if operator == "<": return int(left < right)
    if operator == "<=": return int(left <= right)
    if operator == "==": return int(left == right)
    if operator == "!=": return int(left != right)
    if operator == ">": return int(left > right)
    if operator == ">=": return int(left >= right)
    raise ValueError(f"unsupported binary operator {operator!r}")


def execute(program: TACProgram, initial_environment: Mapping[str, int] | None = None,
            *, max_steps: int = 100_000, trace: bool = False) -> ExecutionResult:
    """Execute ``program`` and return captured observable behavior.

    Division truncates toward zero. Modulo follows ``a == (a / b) * b +
    (a % b)``, so its remainder has the dividend's sign. Relational
    expressions produce integer booleans: true is ``1`` and false is ``0``.
    Execution does not print to stdout.
    """
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if not isinstance(program, TACProgram):
        raise TypeError("program must be a TACProgram")
    environment = dict(initial_environment or {})
    if any(not isinstance(name, str) or not isinstance(value, int)
           for name, value in environment.items()):
        raise TypeError("initial_environment must map variable names to integers")

    labels: dict[str, int] = {}
    for index, instruction in enumerate(program):
        if isinstance(instruction, Label):
            if instruction.name in labels:
                raise TACExecutionError(f"duplicate label {instruction.name!r}", program_counter=index)
            labels[instruction.name] = index

    output: list[int] = []
    trace_lines: list[str] = []
    return_value: int | None = None
    pc = 0
    steps = 0
    terminated = False

    while 0 <= pc < len(program):
        instruction = program[pc]
        if steps >= max_steps:
            raise _runtime_error("maximum instruction-step limit exceeded", pc=pc,
                                 instruction=instruction, steps=steps)
        steps += 1
        if trace:
            trace_lines.append(f"PC={pc}: {instruction.to_tac()}")
        next_pc = pc + 1

        if isinstance(instruction, Label):
            pass
        elif isinstance(instruction, Assignment):
            environment[instruction.target.name] = _read_operand(
                instruction.value, environment, pc=pc, instruction=instruction, steps=steps)
        elif isinstance(instruction, BinaryOperation):
            left = _read_operand(instruction.left, environment, pc=pc, instruction=instruction, steps=steps)
            right = _read_operand(instruction.right, environment, pc=pc, instruction=instruction, steps=steps)
            if instruction.operator in {"/", "%"} and right == 0:
                raise _runtime_error("division or modulo by zero", pc=pc, instruction=instruction, steps=steps)
            environment[instruction.target.name] = _binary_value(instruction.operator, left, right)
        elif isinstance(instruction, UnaryOperation):
            if instruction.operator != "-":
                raise _runtime_error(f"unsupported unary operator {instruction.operator!r}", pc=pc, instruction=instruction, steps=steps)
            environment[instruction.target.name] = -_read_operand(
                instruction.operand, environment, pc=pc, instruction=instruction, steps=steps)
        elif isinstance(instruction, Goto):
            if instruction.target not in labels:
                raise _runtime_error(f"invalid branch target {instruction.target!r}", pc=pc, instruction=instruction, steps=steps)
            next_pc = labels[instruction.target]
        elif isinstance(instruction, ConditionalBranch):
            left = _read_operand(instruction.left, environment, pc=pc, instruction=instruction, steps=steps)
            right = _read_operand(instruction.right, environment, pc=pc, instruction=instruction, steps=steps)
            if _binary_value(instruction.operator, left, right):
                if instruction.target not in labels:
                    raise _runtime_error(f"invalid branch target {instruction.target!r}", pc=pc, instruction=instruction, steps=steps)
                next_pc = labels[instruction.target]
        elif isinstance(instruction, Print):
            output.append(_read_operand(instruction.value, environment, pc=pc, instruction=instruction, steps=steps))
        elif isinstance(instruction, Return):
            return_value = None if instruction.value is None else _read_operand(
                instruction.value, environment, pc=pc, instruction=instruction, steps=steps)
            terminated = True
            break
        else:
            raise _runtime_error(f"unsupported instruction type {type(instruction).__name__!r}", pc=pc, instruction=instruction, steps=steps)
        pc = next_pc

    if not terminated:
        terminated = True
    return ExecutionResult(tuple(output), return_value, dict(environment), steps, terminated, tuple(trace_lines))

