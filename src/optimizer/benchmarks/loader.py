"""Machine-readable benchmark metadata and existing TAC parser integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from optimizer.ir import TACProgram, load_tac


VALID_CATEGORIES = {
    "straight_line",
    "branch",
    "loop",
    "cse",
    "multi_pass_interaction",
}
VALID_CONTROL_FLOW = {
    "straight_line",
    "conditional_branch",
    "conditional_branch_and_join",
    "counted_loop",
}


class BenchmarkManifestError(ValueError):
    """Raised when benchmark metadata is incomplete or inconsistent."""


@dataclass(frozen=True)
class BenchmarkSpec:
    """Metadata for one benchmark, including its manifest-relative path."""

    benchmark_id: str
    file: str
    category: str
    description: str
    optimization_opportunities: tuple[str, ...]
    control_flow: str
    ordering_sensitivity: str
    expected_interactions: tuple[str, ...]
    root: Path

    @property
    def path(self) -> Path:
        """Return the TAC file path resolved relative to the manifest."""
        return self.root / self.file


def _required_string(entry: dict[str, Any], field: str, index: int) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkManifestError(f"entry {index} requires a non-empty {field!r}")
    return value


def _string_tuple(entry: dict[str, Any], field: str, index: int) -> tuple[str, ...]:
    value = entry.get(field)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise BenchmarkManifestError(f"entry {index} requires a non-empty string list {field!r}")
    return tuple(value)


def load_manifest(path: str | Path = "benchmarks/manifest.json") -> tuple[BenchmarkSpec, ...]:
    """Load and validate benchmark metadata without executing any TAC."""
    manifest_path = Path(path).resolve()
    try:
        with manifest_path.open(encoding="utf-8") as source_file:
            document = json.load(source_file)
    except (OSError, json.JSONDecodeError) as error:
        raise BenchmarkManifestError(f"cannot read manifest {manifest_path}: {error}") from error

    entries = document.get("benchmarks") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise BenchmarkManifestError("manifest must contain a 'benchmarks' list")

    specs: list[BenchmarkSpec] = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise BenchmarkManifestError(f"entry {index} must be an object")
        benchmark_id = _required_string(entry, "id", index)
        filename = _required_string(entry, "file", index)
        category = _required_string(entry, "category", index)
        description = _required_string(entry, "description", index)
        control_flow = _required_string(entry, "control_flow", index)
        ordering_sensitivity = _required_string(entry, "ordering_sensitivity", index)
        opportunities = _string_tuple(entry, "optimization_opportunities", index)
        interactions = _string_tuple(entry, "expected_interactions", index)
        if benchmark_id in seen_ids:
            raise BenchmarkManifestError(f"duplicate benchmark ID {benchmark_id!r}")
        if filename in seen_files:
            raise BenchmarkManifestError(f"duplicate benchmark filename {filename!r}")
        if category not in VALID_CATEGORIES:
            raise BenchmarkManifestError(f"entry {benchmark_id!r} has invalid category {category!r}")
        if control_flow not in VALID_CONTROL_FLOW:
            raise BenchmarkManifestError(
                f"entry {benchmark_id!r} has invalid control flow {control_flow!r}"
            )
        if Path(filename).name != filename or Path(filename).is_absolute():
            raise BenchmarkManifestError(f"entry {benchmark_id!r} must use a manifest-relative filename")
        seen_ids.add(benchmark_id)
        seen_files.add(filename)
        specs.append(BenchmarkSpec(
            benchmark_id=benchmark_id,
            file=filename,
            category=category,
            description=description,
            optimization_opportunities=opportunities,
            control_flow=control_flow,
            ordering_sensitivity=ordering_sensitivity,
            expected_interactions=interactions,
            root=manifest_path.parent,
        ))
    return tuple(specs)


def load_benchmark_program(spec: BenchmarkSpec) -> TACProgram:
    """Parse one benchmark through the project's existing TAC loader."""
    if not isinstance(spec, BenchmarkSpec):
        raise TypeError("spec must be a BenchmarkSpec")
    return load_tac(str(spec.path))
