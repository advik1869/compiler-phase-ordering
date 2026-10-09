# The Phase-Ordering Problem in Compiler Optimization

**Team:** Advik K Nama (24BDS0253) and Adarsh Kumar Jha (24BDS0279)

**Repository:** [github.com/advik1869/compiler-phase-ordering](https://github.com/advik1869/compiler-phase-ordering)

## Project goal

This project is a small, deterministic, from-scratch TAC optimizer in Python
that empirically demonstrates the compiler phase-ordering problem: applying
the same correct optimizations in different orders can produce different final
programs and different optimization quality.

The planned optimizer contains exactly four passes:

1. Constant Propagation
2. Constant Folding
3. Dead-Code Elimination
4. Common Subexpression Elimination (CSE)

The experiment exhaustively evaluates all `4! = 24` permutations of those
passes on 20 representative TAC programs. It also compares the results with
selected fixed heuristic orders. Every accepted result
must preserve the program's observable semantics.

This is a small educational research prototype, not a production compiler.

## Problem statement and objectives

Compiler optimizations are individually useful, but their order can affect
which opportunities later passes can see. This project makes that interaction
measurable by running every ordering of four passes over the same TAC
programs.

The project objectives are to:

- represent and execute a small, understandable TAC language;
- implement four independently testable optimization passes;
- evaluate all 24 pass orderings deterministically;
- verify semantic preservation for every optimized result; and
- report instruction-count reductions and controlled pass interactions.

## Current implementation status

Phase 0 established the project foundation. Phase 1 provides a typed TAC
intermediate representation, a deterministic TAC parser/loader, canonical
serialization, source locations, and IR-level `uses()`/`defines()` and
side-effect helpers. Phase 2 adds a deterministic TAC interpreter with captured
output, return values, semantic signatures, runtime diagnostics, and
infinite-loop protection. Phase 3 adds Constant Propagation as a conservative
forward dataflow pass. Phase 4 adds Constant Folding as an independent local
expression-evaluation pass. Phase 5 adds Dead-Code Elimination using backward
liveness analysis.
Phase 6 adds Common Subexpression Elimination using conservative available-
expression analysis. Phase 7 adds a generic pipeline that executes arbitrary
ordered pass sequences and records every intermediate result. Phase 8 adds the
exhaustive engine for all `4! = 24` canonical pass orders.

Phase 9 now provides formal instruction-count and reduction metrics. All four
optimization passes, the generic pipeline, the permutation engine, and metrics
are independently implemented and use the interpreter in semantic-preservation
tests.
Phase 10 adds controlled pass-interaction analysis over the stored Phase 8
results. It compares each of the six unordered pass pairs in six matched
adjacent-swap contexts, for 36 comparisons per experiment, without rerunning
optimization or interpretation. Semantic-invalid comparisons remain visible
but are excluded from aggregate interaction statistics.

Phase 11 adds 20 representative, hand-authored TAC benchmarks covering
straight-line programs, branches, loops, CSE-focused cases, and deliberate
multi-pass interactions. Their intent is stored in `benchmarks/manifest.json`;
the manifest contains no measured best/worst orders or result counts. The
benchmark loader reuses the existing TAC parser, and validation executes every
benchmark plus all 24 pass permutations for semantic preservation.

Phase 12 adds a reproducible experiment runner, two fixed heuristic baselines,
JSON/CSV/Markdown serialization, and five headless matplotlib visualizations.
It evaluates all 20 benchmarks across all 24 permutations, for 480 total
permutation evaluations, while reusing the existing Phase 9 and Phase 10
results. Phase 14 adds an optional Streamlit presentation layer; it does not
change the optimizer, experiment methodology, or canonical results.

## Planned architecture

```text
TAC Input
   |
   v
TAC IR / Parser
   |
   v
Optimization Pipeline
   +--> Constant Propagation
   +--> Constant Folding
   +--> Dead-Code Elimination
   +--> CSE
   |
   v
Permutation Evaluation (24 orders)
   |
   v
Metrics + Interaction Analysis
   |
   v
Experiment Results
```

## Repository layout

```text
compiler_project/
├── src/optimizer/
│   ├── ir/          # TAC representation and parser (Phase 1)
│   ├── passes/      # CP, CF, DCE, and CSE (Phases 3-6)
│   ├── pipeline/    # Pipeline and exhaustive permutation engine (Phases 7-8)
│   ├── analysis/    # Interpreter and Phase 10 interaction analysis
│   ├── benchmarks/  # Phase 11 manifest loader
│   ├── experiments/ # Phase 12 runner, models, serialization, plots
│   └── metrics/     # Phase-ordering instruction-count metrics (Phase 9)
├── tests/
│   ├── unit/
│   └── integration/
├── examples/        # TAC examples and manual optimization demonstrations
├── benchmarks/      # 20 representative TAC programs + manifest (Phase 11)
├── results/         # Generated Phase 12 JSON, CSV, Markdown, and PNG output
├── docs/
├── scripts/
├── README.md
├── requirements.txt
└── pyproject.toml
```

See [docs/architecture.md](docs/architecture.md) for the detailed design
specification, including the future pass interface and testing strategy.

## Technology stack

- Python 3.11+
- Standard library for the optimizer core
- Streamlit for the optional interactive dashboard
- Matplotlib for canonical experiment visualizations
- Pytest for automated validation

No LLVM bindings, machine-learning libraries, compiler frameworks, databases,
API keys, or cloud services are required.

## Development

The project targets Python 3.11 or newer and uses the standard library for
the optimizer core. Pytest is used for testing.

From the repository root:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest
```

The optimizer core has no runtime network or external compiler dependency.
Installing the optional UI and visualization dependencies requires package
installation once in the selected environment.

## Running the Phase 12 experiment

```bash
source .venv/bin/activate
python3 scripts/run_experiment.py
```

This writes `results/experiment_results.json`, four CSV reports,
`results/experiment_summary.md`, and five PNG charts under `results/plots/`.
The two fixed baselines are `CP -> CF -> DCE -> CSE` and
`CSE -> DCE -> CP -> CF`; they are comparison baselines, not claims of
universal optimality.

## Interactive Streamlit UI

The project also includes a local research dashboard built on top of the
existing public APIs and canonical experiment results:

```bash
cd ~/Desktop/compiler_project
source .venv/bin/activate
streamlit run app/streamlit_app.py
```

The UI provides five sections:

- Optimize TAC: run a selected pass order and verify semantic equivalence.
- Compare 24 Orders: execute the existing exhaustive permutation engine for
  an entered TAC program.
- Benchmark Dashboard: inspect the stored 20-benchmark experiment and plots
  without rerunning all 480 evaluations.
- Pass Interactions: inspect the six Phase 10 pass-pair summaries.
- About: review the project's scope, methodology, and semantic-verification
  guarantees.

The CLI remains supported; the UI is only a presentation and interaction
layer and does not duplicate optimization or experiment logic.

For Streamlit Community Cloud deployment instructions, see
[DEPLOYMENT.md](DEPLOYMENT.md).

## Using the application

On **Optimize TAC**, enter TAC in the editor or upload a `.tac` file. Select a
named preset or any of the 24 orders, then choose **Optimize TAC**. The page
shows original and optimized TAC, instruction counts, reduction, execution
observations, and semantic equivalence.

The default example is:

```text
a = 10
b = 20
c = a + b
d = c * 2
t1 = a + b
t2 = a + b
unused = 999
e = d + 100
print t2
return t2
```

Its observable behavior is output `30` and return value `30`. With the H1
order (`CP -> CF -> DCE -> CSE`), the validated optimized example contains
three instructions while preserving that behavior.

TAC uses `print t1`, not Python-style `print(t1)`.

## Limitations and future improvements

This is an educational research prototype with a deliberately small TAC
language and conservative optimization implementations. Its instruction-count
metric is not a complete model of runtime performance, and observations from
the 20-program suite should not be generalized into universal compiler laws.
Possible future work includes a larger TAC language, additional independent
benchmarks, richer cost models, and more formal control-flow analyses.

## Public API quick reference

The repository's actual public entry points are:

```python
from optimizer.ir import load_tac, parse_tac
from optimizer.analysis import execute
from optimizer.pipeline import OptimizationPipeline, PermutationEngine
from optimizer.metrics import calculate_metrics
from optimizer.experiments import ExperimentRunner
```

Use `load_tac(path)` or `parse_tac(text)` to obtain a `TACProgram`; use
`execute(program)` to obtain an `ExecutionResult` with `output`,
`return_value`, `variables`, and `semantic_signature()`. Run one ordered
pipeline with `OptimizationPipeline().run(program, passes)`, all 24 orders
with `PermutationEngine().run(program)`, metrics with
`calculate_metrics(experiment)`, and the complete benchmark experiment with
`ExperimentRunner().run_suite()`. There is no `parse_tac_file` or
`TACInterpreter` API.

For a small end-to-end example:

```bash
python3 examples/manual_test.py
```

## Phase 11 benchmark inventory

| ID | Category | Focus |
|---|---|---|
| B01 | Straight-line | Constant propagation chain |
| B02 | Straight-line | Constant arithmetic |
| B03 | Straight-line | Dead temporary chain |
| B04 | Straight-line | Repeated expression |
| B05 | Straight-line | Mixed straight-line optimization |
| B06 | Branch | Constant condition |
| B07 | Branch | Branch-local dead code |
| B08 | Branch | Repeated expression across paths |
| B09 | Branch | Mixed branch optimization |
| B10 | Loop | Loop constant computation |
| B11 | Loop | Loop dead temporary |
| B12 | Loop | Loop repeated expression |
| B13 | CSE | Simple repeated expression |
| B14 | CSE | Separated repeated expression |
| B15 | CSE | Operand redefinition invalidation |
| B16 | Multi-pass interaction | CP then CF |
| B17 | Multi-pass interaction | CF then DCE |
| B18 | Multi-pass interaction | DCE and CSE |
| B19 | Multi-pass interaction | CP, CF, and DCE chain |
| B20 | Multi-pass interaction | CP, CF, DCE, CSE, and branch |

All programs are ordinary parser-compatible TAC, deterministic, and between
8 and 30 instructions. Phase 12 runs the experiment across this suite; its
measured rankings and result tables are stored under `results/`.
