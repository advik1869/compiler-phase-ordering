"""Controlled adjacent-swap analysis of pass-order interactions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from optimizer.pipeline.permutation_engine import PermutationExperimentResult, PermutationResult


class InteractionAnalysisError(ValueError):
    """Raised when Phase 8 results are incomplete or malformed."""


@dataclass(frozen=True)
class PairwiseComparison:
    """One controlled comparison of A->B against B->A."""

    first_ordering: str
    second_ordering: str
    prefix: tuple[str, ...]
    suffix: tuple[str, ...]
    first_final_count: int | None
    second_final_count: int | None
    signed_delta: int | None
    absolute_delta: int | None
    valid_for_comparison: bool
    enablement_evidence: str = "NONE"


@dataclass(frozen=True)
class PairInteractionResult:
    """Aggregate controlled adjacent-swap results for one unordered pair."""

    first_pass: str
    second_pass: str
    pair_name: str
    comparisons: tuple[PairwiseComparison, ...]
    valid_comparison_count: int
    invalid_comparison_count: int
    first_second_better: int
    second_first_better: int
    ties: int
    mean_signed_delta: float | None
    mean_absolute_delta: float | None
    minimum_delta: int | None
    maximum_delta: int | None
    maximum_absolute_effect: int | None


@dataclass(frozen=True)
class PassInteractionAnalysis:
    """Complete pairwise interaction analysis for one experiment."""

    pass_names: tuple[str, ...]
    pair_results: tuple[PairInteractionResult, ...]
    total_comparisons: int
    valid_comparisons: int
    invalid_comparisons: int
    strongest_pair: str | None
    strongest_pair_mean_absolute_delta: float | None
    strongest_pair_maximum_absolute_effect: int | None

    @property
    def all_pair_results(self) -> tuple[PairInteractionResult, ...]:
        return self.pair_results

    def get_pair_result(self, pair: str | tuple[str, str]) -> PairInteractionResult:
        """Return a pair result by ``"CP/CF"`` or ``("CP", "CF")``."""
        name = pair if isinstance(pair, str) else "/".join(pair)
        for result in self.pair_results:
            if result.pair_name == name:
                return result
        raise KeyError(f"unknown pass pair {name!r}")


_STATISTIC_FIELD = {
    "CP": "operands_replaced",
    "CF": "expressions_folded",
    "DCE": "dead_instructions_removed",
    "CSE": "expressions_reused",
}
_PIPELINE_NAME = {
    "CP": "constant_propagation",
    "CF": "constant_folding",
    "DCE": "dead_code_elimination",
    "CSE": "common_subexpression_elimination",
}
_CANONICAL_PASS_NAMES = ("CP", "CF", "DCE", "CSE")


def _validate_experiment(
    experiment: "PermutationExperimentResult",
) -> dict[str, "PermutationResult"]:
    from optimizer.pipeline.permutation_engine import PermutationExperimentResult

    if not isinstance(experiment, PermutationExperimentResult):
        raise InteractionAnalysisError("expected a PermutationExperimentResult")
    if len(experiment.results) != 24:
        raise InteractionAnalysisError(
            f"complete interaction analysis requires 24 results, got {len(experiment.results)}"
        )
    by_id: dict[str, "PermutationResult"] = {}
    for result in experiment.results:
        if result.permutation_id in by_id:
            raise InteractionAnalysisError(f"duplicate permutation ID {result.permutation_id!r}")
        if len(result.permutation) != 4 or set(result.permutation) != set(_CANONICAL_PASS_NAMES):
            raise InteractionAnalysisError(
                f"invalid pass membership for {result.permutation_id!r}"
            )
        if result.permutation_id != "-".join(result.permutation):
            raise InteractionAnalysisError(
                f"permutation ID does not match pass order: {result.permutation_id!r}"
            )
        if result.final_instruction_count is None:
            raise InteractionAnalysisError(
                f"missing final instruction count for {result.permutation_id!r}"
            )
        by_id[result.permutation_id] = result
    return by_id


def _pass_work(result: PermutationResult, pass_name: str) -> int | None:
    """Return stored work evidence for one pass, without executing anything."""
    pipeline = result.pipeline_result
    if pipeline is None:
        return None
    target = _PIPELINE_NAME[pass_name]
    for pass_result in pipeline.pass_results:
        if pass_result.statistics.pass_name == target:
            return getattr(pass_result.statistics, _STATISTIC_FIELD[pass_name])
    return None


def _enablement_evidence(
    first_result: PermutationResult,
    second_result: PermutationResult,
    first_pass: str,
    second_pass: str,
) -> str:
    """Classify only directly supported stored-statistic evidence."""
    second_after_first = _pass_work(first_result, second_pass)
    second_before_first = _pass_work(second_result, second_pass)
    first_after_second = _pass_work(second_result, first_pass)
    first_before_second = _pass_work(first_result, first_pass)
    if None in (second_after_first, second_before_first, first_after_second, first_before_second):
        return "INCONCLUSIVE"
    first_enhances_second = second_after_first > second_before_first
    second_enhances_first = first_after_second > first_before_second
    if first_enhances_second and second_enhances_first:
        return "BOTH"
    if first_enhances_second:
        return "FIRST_ENHANCES_SECOND"
    if second_enhances_first:
        return "SECOND_ENHANCES_FIRST"
    return "NONE"


def _pair_result(
    first_pass: str,
    second_pass: str,
    comparison_data: Iterable[PairwiseComparison],
) -> PairInteractionResult:
    comparisons = tuple(comparison_data)
    valid = [comparison for comparison in comparisons if comparison.valid_for_comparison]
    deltas = [comparison.signed_delta for comparison in valid if comparison.signed_delta is not None]
    absolute_deltas = [comparison.absolute_delta for comparison in valid if comparison.absolute_delta is not None]
    return PairInteractionResult(
        first_pass=first_pass,
        second_pass=second_pass,
        pair_name=f"{first_pass}/{second_pass}",
        comparisons=comparisons,
        valid_comparison_count=len(valid),
        invalid_comparison_count=len(comparisons) - len(valid),
        first_second_better=sum(delta < 0 for delta in deltas),
        second_first_better=sum(delta > 0 for delta in deltas),
        ties=sum(delta == 0 for delta in deltas),
        mean_signed_delta=None if not deltas else mean(deltas),
        mean_absolute_delta=None if not absolute_deltas else mean(absolute_deltas),
        minimum_delta=None if not deltas else min(deltas),
        maximum_delta=None if not deltas else max(deltas),
        maximum_absolute_effect=None if not absolute_deltas else max(absolute_deltas),
    )


def analyze_pass_interactions(
    experiment: PermutationExperimentResult,
) -> PassInteractionAnalysis:
    """Analyze all six unordered pass pairs using 36 adjacent-swap comparisons."""
    by_id = _validate_experiment(experiment)
    pair_results: list[PairInteractionResult] = []

    for first_pass, second_pass in combinations(_CANONICAL_PASS_NAMES, 2):
        comparisons: list[PairwiseComparison] = []
        remaining = tuple(name for name in _CANONICAL_PASS_NAMES if name not in {first_pass, second_pass})
        for position in range(3):
            for suffix_remaining in (remaining, remaining[::-1]):
                # The two remaining passes are assigned to prefix/suffix around
                # the adjacent pair in both deterministic arrangements.
                prefix = tuple(suffix_remaining[:position])
                suffix = tuple(suffix_remaining[position:])
                first_order = prefix + (first_pass, second_pass) + suffix
                second_order = prefix + (second_pass, first_pass) + suffix
                first_id = "-".join(first_order)
                second_id = "-".join(second_order)
                if first_id not in by_id or second_id not in by_id:
                    raise InteractionAnalysisError(
                        f"missing paired context for {first_pass}/{second_pass}: {first_id} vs {second_id}"
                    )
                first_result = by_id[first_id]
                second_result = by_id[second_id]
                valid = (
                    first_result.execution_success
                    and first_result.semantic_preserved
                    and second_result.execution_success
                    and second_result.semantic_preserved
                )
                first_count = first_result.final_instruction_count
                second_count = second_result.final_instruction_count
                delta = None if first_count is None or second_count is None else first_count - second_count
                comparisons.append(PairwiseComparison(
                    first_ordering=first_id,
                    second_ordering=second_id,
                    prefix=prefix,
                    suffix=suffix,
                    first_final_count=first_count,
                    second_final_count=second_count,
                    signed_delta=delta,
                    absolute_delta=None if delta is None else abs(delta),
                    valid_for_comparison=valid,
                    enablement_evidence=_enablement_evidence(
                        first_result, second_result, first_pass, second_pass
                    ) if valid else "INCONCLUSIVE",
                ))
        if len(comparisons) != 6:
            raise InteractionAnalysisError(f"expected six comparisons for {first_pass}/{second_pass}")
        pair_results.append(_pair_result(first_pass, second_pass, comparisons))

    valid_pair_results = [
        result for result in pair_results if result.mean_absolute_delta is not None
    ]
    # The pair list is already canonical; explicitly use that order for ties.
    strongest = None
    if valid_pair_results:
        strongest_value = max(result.mean_absolute_delta for result in valid_pair_results)
        strongest = next(
            result for result in pair_results
            if result.mean_absolute_delta == strongest_value
        )
    return PassInteractionAnalysis(
        pass_names=_CANONICAL_PASS_NAMES,
        pair_results=tuple(pair_results),
        total_comparisons=sum(len(result.comparisons) for result in pair_results),
        valid_comparisons=sum(result.valid_comparison_count for result in pair_results),
        invalid_comparisons=sum(result.invalid_comparison_count for result in pair_results),
        strongest_pair=None if strongest is None else strongest.pair_name,
        strongest_pair_mean_absolute_delta=None if strongest is None else strongest.mean_absolute_delta,
        strongest_pair_maximum_absolute_effect=None if strongest is None else strongest.maximum_absolute_effect,
    )
