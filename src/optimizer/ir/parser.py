"""Parser for the project's small line-oriented TAC syntax."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import (
    Assignment, BinaryOperation, ConditionalBranch, Goto, IntegerConstant,
    Label, Operand, Print, Return, SourceLocation, TACProgram, UnaryOperation,
    Variable,
)

IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
RESERVED_WORDS = {"if", "goto", "return", "print"}
_IDENTIFIER_RE = re.compile(rf"^{IDENTIFIER}$")
_INTEGER_RE = re.compile(r"^-?[0-9]+$")
_BINARY_RE = re.compile(
    rf"^(?P<left>{IDENTIFIER}|-?[0-9]+)\s+(?P<operator>\+|-|\*|/|%|<=|>=|==|!=|<|>)\s+(?P<right>{IDENTIFIER}|-?[0-9]+)$"
)


@dataclass
class TACParseError(ValueError):
    """A syntax error with line number and original source context."""

    line_number: int
    source_line: str
    description: str

    def __str__(self) -> str:
        return f"line {self.line_number}: {self.description}:\n    {self.source_line}"


def _error(line_number: int, source_line: str, description: str) -> TACParseError:
    return TACParseError(line_number, source_line, description)


def _validate_identifier(token: str, line_number: int, source_line: str, role: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(token):
        raise _error(line_number, source_line, f"invalid {role} identifier {token!r}")
    if token in RESERVED_WORDS:
        raise _error(line_number, source_line, f"reserved word cannot be used as {role}")
    return token


def _parse_operand(token: str, line_number: int, source_line: str) -> Operand:
    if _INTEGER_RE.fullmatch(token):
        return IntegerConstant(int(token))
    if _IDENTIFIER_RE.fullmatch(token) and token not in RESERVED_WORDS:
        return Variable(token)
    raise _error(line_number, source_line, f"invalid operand {token!r}")


def _parse_assignment(text: str, line_number: int, source_line: str, location: SourceLocation):
    target_text, expression = (part.strip() for part in text.split("=", 1))
    target = Variable(_validate_identifier(target_text, line_number, source_line, "target"))
    if not expression:
        raise _error(line_number, source_line, "assignment requires an expression")

    binary_match = _BINARY_RE.fullmatch(expression)
    if binary_match:
        return BinaryOperation(
            target=target,
            left=_parse_operand(binary_match.group("left"), line_number, source_line),
            operator=binary_match.group("operator"),
            right=_parse_operand(binary_match.group("right"), line_number, source_line),
            source=location,
        )
    unary_match = re.fullmatch(rf"-\s*({IDENTIFIER})", expression)
    if unary_match:
        return UnaryOperation(
            target=target, operator="-",
            operand=_parse_operand(unary_match.group(1), line_number, source_line),
            source=location,
        )
    if expression.startswith("-") and not _INTEGER_RE.fullmatch(expression):
        raise _error(line_number, source_line, "invalid unary expression")
    return Assignment(
        target=target,
        value=_parse_operand(expression, line_number, source_line),
        source=location,
    )


def parse_tac(text: str) -> TACProgram:
    """Parse TAC text into a typed :class:`TACProgram`."""
    program = TACProgram()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        source_line = raw_line
        stripped = source_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        location = SourceLocation(line_number, source_line)

        label_match = re.fullmatch(rf"({IDENTIFIER})\s*:", stripped)
        if label_match:
            program.append(Label(name=_validate_identifier(label_match.group(1), line_number, source_line, "label"), source=location))
            continue
        goto_match = re.fullmatch(rf"goto\s+({IDENTIFIER})", stripped)
        if goto_match:
            program.append(Goto(target=_validate_identifier(goto_match.group(1), line_number, source_line, "label"), source=location))
            continue
        conditional_match = re.fullmatch(
            rf"if\s+({IDENTIFIER}|-?[0-9]+)\s+(<=|>=|==|!=|<|>)\s+({IDENTIFIER}|-?[0-9]+)\s+goto\s+({IDENTIFIER})",
            stripped,
        )
        if conditional_match:
            program.append(ConditionalBranch(
                left=_parse_operand(conditional_match.group(1), line_number, source_line),
                operator=conditional_match.group(2),
                right=_parse_operand(conditional_match.group(3), line_number, source_line),
                target=_validate_identifier(conditional_match.group(4), line_number, source_line, "label"),
                source=location,
            ))
            continue
        if stripped == "return":
            program.append(Return(source=location))
            continue
        return_match = re.fullmatch(rf"return\s+({IDENTIFIER}|-?[0-9]+)", stripped)
        if return_match:
            program.append(Return(value=_parse_operand(return_match.group(1), line_number, source_line), source=location))
            continue
        print_match = re.fullmatch(rf"print\s+({IDENTIFIER}|-?[0-9]+)", stripped)
        if print_match:
            program.append(Print(value=_parse_operand(print_match.group(1), line_number, source_line), source=location))
            continue
        if re.match(rf"^{IDENTIFIER}\s*=", stripped):
            program.append(_parse_assignment(stripped, line_number, source_line, location))
            continue
        raise _error(line_number, source_line, "invalid TAC instruction")
    return program


def load_tac(path: str) -> TACProgram:
    """Load and parse a UTF-8 TAC file from ``path``."""
    with open(path, encoding="utf-8") as source_file:
        return parse_tac(source_file.read())
