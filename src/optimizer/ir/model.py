"""Typed, deliberately small three-address-code intermediate representation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterator, Sequence


@dataclass(frozen=True)
class SourceLocation:
    """Optional location of an instruction in its source TAC text."""

    line: int
    text: str


class Operand:
    """Base class for values that can occur as TAC operands."""

    def __str__(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class IntegerConstant(Operand):
    """A signed integer literal."""

    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Variable(Operand):
    """A named variable or temporary in the TAC program."""

    name: str

    @property
    def is_temporary(self) -> bool:
        """Whether this variable follows the conventional ``t`` + digits form."""
        return self.name.startswith("t") and self.name[1:].isdigit()

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, kw_only=True)
class Instruction:
    """Base instruction with optional source information."""

    source: SourceLocation | None = None

    @property
    def opcode(self) -> str:
        """Return a stable, human-readable instruction category."""
        raise NotImplementedError

    def uses(self) -> tuple[Variable, ...]:
        """Return variables read by this instruction, in source order."""
        return ()

    def defines(self) -> tuple[Variable, ...]:
        """Return variables defined by this instruction, in source order."""
        return ()

    @property
    def has_side_effects(self) -> bool:
        """Whether the instruction affects observable state or control flow."""
        return False

    @property
    def is_control_flow(self) -> bool:
        """Whether the instruction changes or observes control flow."""
        return False

    def to_tac(self) -> str:
        """Render this instruction in canonical TAC syntax."""
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class Assignment(Instruction):
    """Copy an operand into a variable."""

    target: Variable
    value: Operand

    @property
    def opcode(self) -> str:
        return "assign"

    def uses(self) -> tuple[Variable, ...]:
        return (self.value,) if isinstance(self.value, Variable) else ()

    def defines(self) -> tuple[Variable, ...]:
        return (self.target,)

    def to_tac(self) -> str:
        return f"{self.target} = {self.value}"


@dataclass(frozen=True, kw_only=True)
class BinaryOperation(Instruction):
    """Apply a binary arithmetic or relational operator."""

    target: Variable
    left: Operand
    operator: str
    right: Operand

    @property
    def opcode(self) -> str:
        return "binary"

    def uses(self) -> tuple[Variable, ...]:
        return tuple(value for value in (self.left, self.right) if isinstance(value, Variable))

    def defines(self) -> tuple[Variable, ...]:
        return (self.target,)

    def to_tac(self) -> str:
        return f"{self.target} = {self.left} {self.operator} {self.right}"


@dataclass(frozen=True, kw_only=True)
class UnaryOperation(Instruction):
    """Apply unary negation to an operand."""

    target: Variable
    operator: str
    operand: Operand

    @property
    def opcode(self) -> str:
        return "unary"

    def uses(self) -> tuple[Variable, ...]:
        return (self.operand,) if isinstance(self.operand, Variable) else ()

    def defines(self) -> tuple[Variable, ...]:
        return (self.target,)

    def to_tac(self) -> str:
        return f"{self.target} = {self.operator}{self.operand}"


@dataclass(frozen=True, kw_only=True)
class Label(Instruction):
    """A named position in the program."""

    name: str

    @property
    def opcode(self) -> str:
        return "label"

    def to_tac(self) -> str:
        return f"{self.name}:"


@dataclass(frozen=True, kw_only=True)
class Goto(Instruction):
    """Unconditionally jump to a label."""

    target: str

    @property
    def opcode(self) -> str:
        return "goto"

    @property
    def has_side_effects(self) -> bool:
        return True

    @property
    def is_control_flow(self) -> bool:
        return True

    def to_tac(self) -> str:
        return f"goto {self.target}"


@dataclass(frozen=True, kw_only=True)
class ConditionalBranch(Instruction):
    """Jump when a relational comparison is true."""

    left: Operand
    operator: str
    right: Operand
    target: str

    @property
    def opcode(self) -> str:
        return "conditional_branch"

    def uses(self) -> tuple[Variable, ...]:
        return tuple(value for value in (self.left, self.right) if isinstance(value, Variable))

    @property
    def has_side_effects(self) -> bool:
        return True

    @property
    def is_control_flow(self) -> bool:
        return True

    def to_tac(self) -> str:
        return f"if {self.left} {self.operator} {self.right} goto {self.target}"


@dataclass(frozen=True, kw_only=True)
class Return(Instruction):
    """Return an optional value from the TAC program."""

    value: Operand | None = None

    @property
    def opcode(self) -> str:
        return "return"

    def uses(self) -> tuple[Variable, ...]:
        return (self.value,) if isinstance(self.value, Variable) else ()

    @property
    def has_side_effects(self) -> bool:
        return True

    @property
    def is_control_flow(self) -> bool:
        return True

    def to_tac(self) -> str:
        return "return" if self.value is None else f"return {self.value}"


@dataclass(frozen=True, kw_only=True)
class Print(Instruction):
    """Print an operand, an observable operation for later verification."""

    value: Operand

    @property
    def opcode(self) -> str:
        return "print"

    def uses(self) -> tuple[Variable, ...]:
        return (self.value,) if isinstance(self.value, Variable) else ()

    @property
    def has_side_effects(self) -> bool:
        return True

    def to_tac(self) -> str:
        return f"print {self.value}"


class TACProgram:
    """Deterministic ordered container for TAC instructions."""

    def __init__(self, instructions: Sequence[Instruction] = ()) -> None:
        self._instructions = list(instructions)

    def __iter__(self) -> Iterator[Instruction]:
        return iter(self._instructions)

    def __len__(self) -> int:
        return len(self._instructions)

    def __getitem__(self, index: int) -> Instruction:
        return self._instructions[index]

    def append(self, instruction: Instruction) -> None:
        self._instructions.append(instruction)

    def copy(self) -> TACProgram:
        return deepcopy(self)

    def structural_key(self) -> tuple[tuple[object, ...], ...]:
        """Return instruction meaning without source locations."""
        return tuple(
            tuple((field, value) for field, value in instruction.__dict__.items() if field != "source")
            + (("type", instruction.__class__.__name__),)
            for instruction in self
        )

    def structurally_equal(self, other: object) -> bool:
        return isinstance(other, TACProgram) and self.structural_key() == other.structural_key()

    def __eq__(self, other: object) -> bool:
        return self.structurally_equal(other)

    def to_tac(self) -> str:
        return "\n".join(instruction.to_tac() for instruction in self)

