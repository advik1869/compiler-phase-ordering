"""Integration tests for loading the example TAC files."""

from pathlib import Path

from optimizer.ir import load_tac


EXAMPLES = Path(__file__).parents[2] / "examples"


def test_example_files_load_and_serialize() -> None:
    paths = sorted(EXAMPLES.glob("*.tac"))
    assert [path.name for path in paths] == [
        "basic_arithmetic.tac",
        "branching.tac",
        "manual_test.tac",
        "repeated_expression.tac",
    ]
    for path in paths:
        program = load_tac(str(path))
        assert len(program) > 0
        assert program.to_tac()
