"""Local constant folding for literal TAC expressions."""

from __future__ import annotations

from dataclasses import replace

from optimizer.ir import (
    Assignment,
    BinaryOperation,
    IntegerConstant,
    TACProgram,
    UnaryOperation,
)

from .base import OptimizationPass, PassResult, PassStatistics


def _truncating_division(left: int, right: int) -> int:
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def _fold_binary(operator: str, left: int, right: int) -> int | None:
    """Evaluate one literal expression using the interpreter's integer rules."""
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator in {"/", "%"} and right == 0:
        return None
    if operator == "/":
        return _truncating_division(left, right)
    if operator == "%":
        return left - _truncating_division(left, right) * right
    if operator == "<":
        return int(left < right)
    if operator == "<=":
        return int(left <= right)
    if operator == "==":
        return int(left == right)
    if operator == "!=":
        return int(left != right)
    if operator == ">":
        return int(left > right)
    if operator == ">=":
        return int(left >= right)
    raise ValueError(f"unsupported binary operator {operator!r}")


class ConstantFolding(OptimizationPass):
    """Fold only expressions whose operands are already integer constants."""

    name = "constant_folding"

    def run_with_result(self, program: TACProgram) -> PassResult:
        if not isinstance(program, TACProgram):
            raise TypeError("program must be a TACProgram")

        transformed = []
        expressions_folded = 0
        for instruction in program:
            if isinstance(instruction, BinaryOperation):
                if isinstance(instruction.left, IntegerConstant) and isinstance(instruction.right, IntegerConstant):
                    value = _fold_binary(instruction.operator, instruction.left.value, instruction.right.value)
                    if value is not None:
                        transformed.append(Assignment(
                            target=instruction.target,
                            value=IntegerConstant(value),
                            source=instruction.source,
                        ))
                        expressions_folded += 1
                        continue
            elif isinstance(instruction, UnaryOperation):
                if isinstance(instruction.operand, IntegerConstant) and instruction.operator == "-":
                    transformed.append(Assignment(
                        target=instruction.target,
                        value=IntegerConstant(-instruction.operand.value),
                        source=instruction.source,
                    ))
                    expressions_folded += 1
                    continue
            transformed.append(replace(instruction))

        result_program = TACProgram(transformed)
        statistics = PassStatistics(
            pass_name=self.name,
            instructions_before=len(program),
            instructions_after=len(result_program),
            expressions_folded=expressions_folded,
            instructions_removed=0,
            changed=expressions_folded > 0,
        )
        return PassResult(result_program, statistics)

