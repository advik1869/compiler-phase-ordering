"""Validation of Phase 11 benchmark metadata."""

from collections import Counter
from pathlib import Path

from optimizer.benchmarks import load_manifest


MANIFEST = Path(__file__).parents[2] / "benchmarks" / "manifest.json"


def test_manifest_contains_exactly_20_unique_benchmarks_and_files() -> None:
    specs = load_manifest(MANIFEST)

    assert len(specs) == 20
    assert len({spec.benchmark_id for spec in specs}) == 20
    assert len({spec.file for spec in specs}) == 20
    assert Counter(spec.category for spec in specs) == Counter({
        "straight_line": 5,
        "branch": 4,
        "loop": 3,
        "cse": 3,
        "multi_pass_interaction": 5,
    })


def test_manifest_entries_have_existing_files_and_experimental_intent() -> None:
    specs = load_manifest(MANIFEST)

    for spec in specs:
        assert spec.path.is_file()
        assert spec.description
        assert spec.optimization_opportunities
        assert spec.control_flow
        assert spec.expected_interactions

