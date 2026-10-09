#!/usr/bin/env python3
"""Run the complete Phase 12 benchmark experiment and write its outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from optimizer.experiments import ExperimentRunner, create_all_plots, write_all_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 12 TAC experiment.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "results"), help="directory for generated reports")
    parser.add_argument("--benchmark", help="optional benchmark ID to display after the complete run")
    parser.add_argument("--no-plots", action="store_true", help="skip PNG visualization generation")
    parser.add_argument("--verbose", action="store_true", help="print per-benchmark progress")
    args = parser.parse_args()

    suite = ExperimentRunner(PROJECT_ROOT / "benchmarks" / "manifest.json").run_suite()
    output_dir = Path(args.output_dir)
    paths = write_all_outputs(suite, output_dir)
    if not args.no_plots:
        paths += create_all_plots(suite, output_dir / "plots")
    if args.benchmark:
        selected = next((result for result in suite.benchmark_results if result.benchmark.benchmark_id == args.benchmark), None)
        if selected is None:
            parser.error(f"unknown benchmark ID {args.benchmark!r}")
        print(f"{args.benchmark}: best={selected.metrics.best_final_instruction_count}, worst={selected.metrics.worst_final_instruction_count}")
    if args.verbose:
        for result in suite.benchmark_results:
            print(f"{result.benchmark.benchmark_id}: {len(result.permutation_experiment.results)} permutations")
    print(f"evaluated {suite.total_benchmarks} benchmarks and {suite.total_permutation_evaluations} permutations")
    print(f"semantic valid={suite.semantic_valid_evaluations}, invalid={suite.semantic_invalid_evaluations}")
    print(f"wrote {len(paths)} output files under {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
