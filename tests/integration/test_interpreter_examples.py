"""Integration coverage for parser-to-interpreter execution."""

from pathlib import Path

from optimizer.analysis import execute
from optimizer.ir import load_tac


def test_basic_arithmetic_example_executes() -> None:
    path = Path(__file__).parents[2] / "examples" / "basic_arithmetic.tac"
    result = execute(load_tac(str(path)))
    assert result.output == (60,)
    assert result.return_value == 60
    assert result.terminated

