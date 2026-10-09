"""Program analysis and semantic execution utilities."""

from .interpreter import ExecutionResult, TACExecutionError, execute
from .pass_interaction_analysis import (
    InteractionAnalysisError,
    PairInteractionResult,
    PairwiseComparison,
    PassInteractionAnalysis,
    analyze_pass_interactions,
)

__all__ = [
    "ExecutionResult", "InteractionAnalysisError", "PairInteractionResult",
    "PairwiseComparison", "PassInteractionAnalysis", "TACExecutionError",
    "analyze_pass_interactions", "execute",
]
