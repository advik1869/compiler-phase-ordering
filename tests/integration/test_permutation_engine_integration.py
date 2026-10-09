"""Integration tests for permutation semantic validation."""

from pathlib import Path

from optimizer.analysis import execute
from optimizer.ir import load_tac, parse_tac
from optimizer.pipeline import PermutationEngine


def test_all_24_permutations_preserve_semantics_on_interaction_program() -> None:
    program = parse_tac(
        "a = 10\nb = 20\nt1 = a + b\nt2 = a + b\nunused = t2\nreturn t1\n"
    )
    experiment = PermutationEngine().run(program)
    original_signature = execute(program).semantic_signature()
    assert experiment.number_of_permutations == 24
    assert all(result.execution_success for result in experiment.results)
    assert all(result.semantic_preserved for result in experiment.results)
    assert all(execute(result.final_program).semantic_signature() == original_signature for result in experiment.results)


def test_existing_examples_run_through_all_permutations() -> None:
    for path in sorted((Path(__file__).parents[2] / "examples").glob("*.tac")):
        experiment = PermutationEngine().run(load_tac(str(path)))
        assert experiment.number_of_permutations == 24
        assert all(result.semantic_preserved for result in experiment.results)

