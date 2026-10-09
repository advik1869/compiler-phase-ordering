"""Generic ordered optimization-pipeline infrastructure."""

from .optimizer_pipeline import OptimizationPipeline, PipelineExecutionError, PipelineResult
from .permutation_engine import (
    CANONICAL_PASS_NAMES,
    PermutationEngine,
    PermutationExperimentResult,
    PermutationResult,
    generate_permutations,
    permutation_id,
)

__all__ = [
    "CANONICAL_PASS_NAMES",
    "OptimizationPipeline",
    "PermutationEngine",
    "PermutationExperimentResult",
    "PermutationResult",
    "PipelineExecutionError",
    "PipelineResult",
    "generate_permutations",
    "permutation_id",
]
