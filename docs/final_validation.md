# Final Validation

Audit date: 2026-10-07

This document records the Phase 13 audit of the completed educational
phase-ordering experiment. Values below were checked against the generated
JSON/CSV outputs and, where noted, independently recomputed from the TAC
programs.

## 1. Test Suite

Command:

```bash
source .venv/bin/activate
python3 -m pytest
```

Result: 171 tests collected, 171 passed, 0 failed, 0 skipped, in 17.47
seconds. Pytest reported no warning summary. The test suite includes the
original phases, benchmark validation, experiment runner, serialization,
heuristic, reproducibility, and headless visualization tests.

The required command `python3 scripts/run_experiment.py` also completed
successfully after the test run.

## 2. Benchmark Coverage

The manifest contains exactly 20 unique benchmark IDs and 20 unique TAC files.
All entries map to existing files, parse successfully, and execute with normal
termination.

| Category | Count |
|---|---:|
| Straight-line | 5 |
| Branch | 4 |
| Loop | 3 |
| CSE-focused | 3 |
| Multi-pass interaction | 5 |
| Total | 20 |

Every manifest benchmark appears in the serialized experiment results. No
duplicate IDs or filenames were found.

## 3. Permutation Coverage

Each benchmark has exactly 24 unique permutations containing `CP`, `CF`,
`DCE`, and `CSE` exactly once. The serialized results contain:

- 20 benchmarks
- 24 permutations per benchmark
- 480 total permutation evaluations
- 480 rows in `permutation_results.csv`

The six Phase 10 pair groups contain 6 comparisons each for every benchmark,
giving 720 controlled comparisons in total.

## 4. Semantic Preservation

The serialized results report 480 semantic-valid evaluations, 0
semantic-invalid evaluations, and 0 failed evaluations. An independent audit
reloaded every benchmark, executed its baseline program, executed every final
permutation program, and compared `semantic_signature()` values.

Independent result: 480 matching signatures, 0 mismatches.

No failed execution was silently omitted.

## 5. Metric Consistency

The audit compared `experiment_results.json` with all four CSV reports:

- `benchmark_summary.csv`: 20 data rows
- `permutation_results.csv`: 480 data rows
- `interaction_summary.csv`: 120 data rows
- `heuristic_comparison.csv`: 40 data rows

For every benchmark, the reported best and worst counts equal the minimum and
maximum valid permutation counts. Best is never greater than worst, and
`spread = worst - best` holds for every benchmark. Reported best and worst
permutation tie sets were checked against the corresponding raw counts.

Phase 9 baseline counts, removed-instruction counts, reductions, means,
medians, and spreads were consistent with the raw permutation records. The
Phase 9 zero-baseline and invalid-result safeguards remain covered by the
existing tests.

Observed spread summary:

- Zero-spread benchmarks: 1
- Non-zero-spread benchmarks: 19
- Maximum instruction spread: 4 instructions, B12
- Maximum spread percentage: 37.50%, B18
- Lowest non-zero spread percentage: 14.29%, B20

## 6. Interaction Analysis

Every benchmark contains the expected six unordered pairs:
`CP/CF`, `CP/DCE`, `CP/CSE`, `CF/DCE`, `CF/CSE`, and `DCE/CSE`.

The audit verified that each controlled comparison preserves its prefix and
suffix, swaps only the analyzed adjacent pair, and satisfies:

```text
signed_delta = first_final_count - second_final_count
```

Across benchmarks, the pair-level aggregate results were:

| Pair | Non-zero effects | Mean benchmark absolute delta | Maximum effect | First direction wins more | Second direction wins more |
|---|---:|---:|---:|---:|---:|
| CP/CF | 4 | 0.050 | 1 | 3 | 1 |
| CP/DCE | 19 | 2.025 | 3 | 19 | 0 |
| CP/CSE | 0 | 0.000 | 0 | 0 | 0 |
| CF/DCE | 0 | 0.000 | 0 | 0 | 0 |
| CF/CSE | 3 | 0.025 | 1 | 3 | 0 |
| DCE/CSE | 3 | 0.125 | 1 | 3 | 0 |

CP/DCE showed the strongest recurring measured sensitivity by mean benchmark
absolute delta. This describes the observed data and does not establish that
one ordering is universally better.

## 7. Heuristic Comparison

The exact fixed orders were verified:

- H1: `CP -> CF -> DCE -> CSE`
- H2: `CSE -> DCE -> CP -> CF`

Both are existing exhaustive permutations, so the runner reuses their stored
results rather than rerunning optimization.

- H1 matched exhaustive best on 19 of 20 benchmarks: 95.0%.
- H2 matched exhaustive best on 1 of 20 benchmarks: 5.0%.
- H1 average gap from exhaustive best: 0.05 instructions.
- H2 average gap from exhaustive best: 2.20 instructions.

For every benchmark, both heuristic counts were within the observed best/worst
range and their gaps equaled `heuristic_count - best_count`.

## 8. Reproducibility

The experiment was run twice with separate output directories. The following
substantive files were byte-identical between runs:

- `experiment_results.json`
- `benchmark_summary.csv`
- `permutation_results.csv`
- `interaction_summary.csv`
- `heuristic_comparison.csv`
- `experiment_summary.md`

No volatile timestamp is included in the compared experiment data.

## 9. Visualization Validation

All required plots exist under `results/plots/`, are non-empty, and were opened
successfully as valid PNG files:

- `best_vs_worst.png` — best and worst final instruction counts.
- `reduction_range.png` — best and worst reduction percentages.
- `heuristic_vs_best.png` — exhaustive best versus H1 and H2.
- `phase_ordering_spread.png` — spread percentage per benchmark.
- `pairwise_interaction_strength.png` — equal-weight mean benchmark-level
  absolute interaction delta.

The images have readable report-sized dimensions (1200x600, except the
1000x600 interaction chart), and all plots are generated from structured
experiment results rather than hard-coded measurements. No placeholder data,
NaN values, or infinite values were found in the generated outputs.

## 10. Project Requirement Alignment

| Requirement | Implemented? | Evidence |
|---|---|---|
| Custom TAC IR and parser | Yes | `src/optimizer/ir/` and parser tests |
| Four optimization passes | Yes | `src/optimizer/passes/` and pass tests |
| Exhaustive 24-order evaluation | Yes | Phase 8 engine and 480 serialized results |
| Semantic preservation | Yes | Interpreter signatures and 480/480 audit |
| 15–20 representative programs | Yes | 20 manifest benchmarks |
| Best/worst comparison | Yes | Phase 9 metrics and summary CSV |
| Phase-ordering spread | Yes | Summary metrics and spread plot |
| Recurring pass interactions | Yes | 720 Phase 10 comparisons and aggregate table |
| Fixed heuristic comparison | Yes | H1/H2 records and heuristic CSV |
| Deterministic evaluation | Yes | Repeated outputs are byte-identical |
| Transparent implementation | Yes | Typed models, parser-compatible TAC, tests, and documentation |

## 11. Known Limitations

- The study covers exactly four optimization passes and the 24 permutations of
  those four passes.
- Instruction count is the primary code-size proxy; no machine-code size or
  runtime performance is measured.
- The TAC representation and benchmark suite are intentionally small and
  pedagogical.
- There is no LLVM/GCC production-compiler comparison.
- There is no machine-learning phase-ordering model.
- A fresh temporary virtual environment could not complete `pip install -r
  requirements.txt` during this audit because the environment could not resolve
  `pypi.org`. The existing project virtual environment had the declared
  dependencies installed and passed all tests; this was an environment/network
  limitation rather than a repository test failure.

These limitations are intentional boundaries for a transparent compiler-design
lab demonstration and do not invalidate the completed experiment.

## 12. Final Status

All requested audit checks passed, with the clean-environment package download
limitation documented above.

Status: COMPLETE
