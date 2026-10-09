"""End-to-end semantic validation of every Phase 11 benchmark."""

from pathlib import Path

from optimizer.analysis import execute
from optimizer.benchmarks import load_benchmark_program, load_manifest
from optimizer.pipeline import PermutationEngine


MANIFEST = Path(__file__).parents[2] / "benchmarks" / "manifest.json"


def test_every_benchmark_parses_and_executes_to_normal_termination() -> None:
    for spec in load_manifest(MANIFEST):
        program = load_benchmark_program(spec)
        result = execute(program)
        assert result.terminated
        assert result.return_value is not None
        assert 8 <= len(program) <= 30


def test_every_benchmark_preserves_semantics_for_all_24_permutations() -> None:
    for spec in load_manifest(MANIFEST):
        experiment = PermutationEngine().run(load_benchmark_program(spec))

        assert experiment.number_of_permutations == 24
        assert len(experiment.results) == 24
        assert all(result.execution_success for result in experiment.results)
        assert all(result.semantic_preserved for result in experiment.results)


def test_benchmark_loading_is_deterministic() -> None:
    first = load_manifest(MANIFEST)
    second = load_manifest(MANIFEST)

    assert first == second
    assert [load_benchmark_program(spec).to_tac() for spec in first] == [
        load_benchmark_program(spec).to_tac() for spec in second
    ]

