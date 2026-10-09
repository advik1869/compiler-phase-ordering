# Phase 12 Experiment Summary

## Experiment overview

- Benchmarks: 20
- Permutations per benchmark: 24
- Total permutation evaluations: 480
- Semantic-valid evaluations: 480
- Semantic-invalid evaluations: 0
- Failed evaluations: 0

## Data: benchmark results

| Benchmark | Best | Worst | Spread | Spread % | Best permutations | Worst permutations |
|---|---:|---:|---:|---:|---:|---:|
| B01 | 5 | 8 | 3 | 37.50 | 12 | 12 |
| B02 | 6 | 8 | 2 | 25.00 | 12 | 12 |
| B03 | 1 | 1 | 0 | 0.00 | 24 | 24 |
| B04 | 7 | 9 | 2 | 22.22 | 12 | 12 |
| B05 | 6 | 8 | 2 | 22.22 | 12 | 12 |
| B06 | 8 | 10 | 2 | 20.00 | 12 | 12 |
| B07 | 5 | 7 | 2 | 22.22 | 12 | 12 |
| B08 | 8 | 10 | 2 | 20.00 | 12 | 12 |
| B09 | 9 | 11 | 2 | 15.38 | 12 | 12 |
| B10 | 10 | 12 | 2 | 16.67 | 4 | 12 |
| B11 | 7 | 9 | 2 | 20.00 | 12 | 12 |
| B12 | 10 | 14 | 4 | 28.57 | 5 | 4 |
| B13 | 6 | 8 | 2 | 25.00 | 12 | 12 |
| B14 | 6 | 9 | 3 | 33.33 | 12 | 12 |
| B15 | 4 | 6 | 2 | 25.00 | 12 | 12 |
| B16 | 6 | 8 | 2 | 25.00 | 12 | 12 |
| B17 | 2 | 5 | 3 | 33.33 | 5 | 4 |
| B18 | 5 | 8 | 3 | 37.50 | 5 | 4 |
| B19 | 6 | 8 | 2 | 22.22 | 12 | 12 |
| B20 | 10 | 12 | 2 | 14.29 | 12 | 12 |

## Data: heuristic comparison

| Benchmark | Heuristic 1 | Heuristic 2 |
|---|---:|---:|
| B01 | 5 | 8 |
| B02 | 6 | 8 |
| B03 | 1 | 1 |
| B04 | 7 | 9 |
| B05 | 6 | 8 |
| B06 | 8 | 10 |
| B07 | 5 | 7 |
| B08 | 8 | 10 |
| B09 | 9 | 11 |
| B10 | 11 | 12 |
| B11 | 7 | 9 |
| B12 | 10 | 14 |
| B13 | 6 | 8 |
| B14 | 6 | 9 |
| B15 | 4 | 6 |
| B16 | 6 | 8 |
| B17 | 2 | 5 |
| B18 | 5 | 8 |
| B19 | 6 | 8 |
| B20 | 10 | 12 |

## Data: highest and lowest observed spread

### Highest five

- B01: 37.50%
- B18: 37.50%
- B14: 33.33%
- B17: 33.33%
- B12: 28.57%

### Lowest five

- B03: 0.00%
- B20: 14.29%
- B09: 15.38%
- B10: 16.67%
- B06: 20.00%

## Data: recurring interaction summary

| Pair | Non-zero benchmark effects | Mean benchmark absolute delta | Maximum effect |
|---|---:|---:|---:|
| CP/CF | 4 | 0.05 | 1 |
| CP/DCE | 19 | 2.025 | 3 |
| CP/CSE | 0 | 0.0 | 0 |
| CF/DCE | 0 | 0.0 | 0 |
| CF/CSE | 3 | 0.025 | 1 |
| DCE/CSE | 3 | 0.125 | 1 |

## Interpretation

Spread is the observed difference between the worst and best final instruction counts for each benchmark. Heuristic gaps are measured against the exhaustive best; zero means the heuristic matched that best result.
The interaction summary gives each benchmark equal weight by averaging its Phase 10 mean absolute delta. These measurements describe ordering sensitivity and do not by themselves establish causal pass enablement.
