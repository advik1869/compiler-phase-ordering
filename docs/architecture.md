# Architecture Design

This document is the design specification for the Phase-Ordering Problem in
Compiler Optimization project. Phases 1-2 implement the TAC IR, parser, and
deterministic semantic execution. Phases 3-6 implement the four optimization
passes, and Phases 7-10 implement the pipeline, exhaustive permutation engine,
metrics, and interaction analysis.

## 1. Project Scope

The project will be a deterministic, from-scratch Python prototype that takes
small three-address-code (TAC) programs and studies how optimization-pass order
affects the resulting program. The planned pass set contains exactly four
passes: constant propagation, constant folding, dead-code elimination, and
common subexpression elimination (CSE).

The project is educational and experimental, not a production compiler. It
will avoid external compiler frameworks, LLVM bindings, machine learning, and
network access.

## 2. TAC Intermediate Representation

TAC is used because each instruction has a small, explicit shape: at most one
result and a small number of operands. This makes data flow, instruction
ordering, and later optimization effects easy to inspect during a Compiler
Design viva. The representation is intentionally smaller than an AST or a
production compiler IR.

`src/optimizer/ir/model.py` contains typed dataclasses for assignments, binary
operations, unary negation, labels, unconditional and conditional branches,
returns, and print operations. Every instruction can expose its opcode,
variables used, variables defined, control-flow status, side-effect status, and
canonical TAC rendering.

### Operands

Operands are either `IntegerConstant(value)` or `Variable(name)`. Integer
constants are signed decimal integers. A variable whose name matches `t` plus
one or more digits is recognized as a temporary through
`Variable.is_temporary`; all other valid names are ordinary variables. This is
a naming convention, not a separate semantic storage class.

### Identifiers

Identifiers follow `[A-Za-z_][A-Za-z0-9_]*`. The words `if`, `goto`, `return`,
and `print` are reserved in their grammatical positions and cannot be used as
variable or label names.

### Program container and source locations

`TACProgram` stores instructions in source order and supports iteration,
indexing, length, append, deep copy, structural comparison, and `to_tac()`.
Each parsed instruction has an optional `SourceLocation` containing its
one-based source line and original line text. Structural equality intentionally
ignores source locations so a parse/serialize/parse round trip compares program
meaning rather than comments or whitespace.

### Instruction classification

`uses()` and `defines()` return tuples of typed `Variable` objects. Assignments
and computations define their destination; operands that are variables are
reported as uses. Labels have neither. Branches use their comparison operands,
`print` uses its value, and `return` uses its optional value.

The IR marks assignments, computations, and labels as non-side-effecting.
`goto`, conditional branches, `return`, and `print` are side-effecting; control
flow instructions additionally expose `is_control_flow`. These are
classification helpers only and do not perform dead-code elimination.

### TAC grammar implemented in Phase 1

The parser is line-oriented. Blank lines and lines beginning with `#` after
optional whitespace are ignored. Canonical forms are:

```text
assignment       ::= identifier "=" operand
                   | identifier "=" operand arithmetic-op operand
                   | identifier "=" "-" identifier
arithmetic-op    ::= "+" | "-" | "*" | "/" | "%"
relational-op    ::= "<" | "<=" | "==" | "!=" | ">" | ">="
label            ::= identifier ":"
goto             ::= "goto" identifier
conditional      ::= "if" operand relational-op operand "goto" identifier
return           ::= "return" [operand]
print            ::= "print" operand
operand          ::= integer | identifier
integer          ::= "-"? digit+
```

The parser accepts arithmetic and relational operators in assignment expressions
and relational operators in conditional branches. It does not accept floating
point values, multi-operator expressions, inline comments, or implicit labels.
`to_tac()` emits one canonical instruction per line and does not preserve input
whitespace.

### Parser and loader

`parse_tac(text)` validates every non-comment line and returns a `TACProgram`.
`load_tac(path)` reads UTF-8 text and delegates to the same parser. Malformed
input raises `TACParseError`, which includes the one-based line number, original
source line, and a short description. There is no error recovery.

## 3. TAC Interpreter and Semantic Execution

The interpreter in `src/optimizer/analysis/interpreter.py` executes the typed
TAC program without printing directly to stdout. It maintains a program
counter, integer variable environment, captured output sequence, optional
return value, step count, and termination status. `execute()` accepts an
optional initial environment, which is copied before execution.

Labels are indexed before execution. A label consumes one execution step but
has no computational effect. Sequential instructions advance the program
counter; `goto` and taken conditional branches replace it with the target label
index; `return` terminates immediately. Reaching the end of the instruction
list also counts as normal termination.

All Phase 1 instruction kinds are supported. Arithmetic uses integer values;
division truncates toward zero, so `7 / 2` is `3` and `-7 / 2` is `-3`.
Modulo follows `a == (a / b) * b + (a % b)`, so the remainder has the
dividend's sign. Relational operations produce integer booleans: true is `1`
and false is `0`.

`ExecutionResult` exposes `output`, `return_value`, `variables`, `steps`,
`terminated`, and an optional trace. Its `semantic_signature()` contains only
the observable output tuple, return value, and termination status; internal
variable state is intentionally excluded so later optimizations may remove or
rename temporaries.

`TACExecutionError` reports runtime failures such as undefined variables,
division or modulo by zero, invalid branch targets, unsupported instructions,
duplicate labels, and maximum-step exhaustion. The default limit is 100,000
executed instructions and can be configured with `max_steps`. The interpreter
raises on the limit rather than silently claiming successful termination.

## 4. Optimization Pass Interface

Each pass will implement a common conceptual interface:

```python
class OptimizationPass:
    name: str

    def run(self, program) -> TACProgram:
        ...
```

The Phase 3 implementation returns the transformed `TACProgram` from `run()`
and retains a `PassResult` in `last_result`. `PassResult` contains the
transformed program and traceable statistics, including
`instructions_before`, `instructions_after`, `operands_replaced`,
`instructions_removed`, and `changed`. The interface should make each pass
independently testable and should not hide transformations behind global state.
Constant Propagation, Constant Folding, and Dead-Code Elimination use this
interface; Common Subexpression Elimination is the fourth implemented pass.

## 5. Constant Propagation

Constant Propagation replaces a variable operand with an integer constant only
when that value is guaranteed at the relevant program point. It does not
evaluate arithmetic or relational expressions: for example, `c = a + b` with
`a = 10` and `b = 20` becomes `c = 10 + 20`, not `c = 30`. Evaluating the
expression belongs to the future Constant Folding pass. Unary negation follows
the same separation: a known operand may be substituted, but the pass does not
perform general expression evaluation.

### Lattice and transfer functions

The pass uses a small forward lattice for each variable:

- `UNDEFINED`: no definition is known on the relevant incoming path.
- `CONSTANT(value)`: every relevant incoming path agrees on this integer.
- `NOT_CONSTANT`: the value is unknown, differs across paths, or comes from a
  non-constant expression.

An assignment of an integer literal produces `CONSTANT(value)`. Assignment
from a variable copies its constant state only when that state is constant;
otherwise it produces `NOT_CONSTANT`. Binary and unary computations define
their destination as `NOT_CONSTANT`, while their operands can still be
substituted in the output TAC. Reassignment naturally replaces the prior state.

At a control-flow join, equal constants meet to the same constant. Different
constants meet to `NOT_CONSTANT`, and a constant meeting an undefined incoming
path also meets to `NOT_CONSTANT`. This prevents propagation from assuming a
definition exists on every reachable path.

### Control flow and fixed point

`ConstantPropagation` builds a minimal instruction-level CFG from sequential
edges, fall-through edges, `goto` edges, conditional branch edges, and loop
back edges. Labels are resolved to instruction indices. A worklist repeatedly
applies the transfer functions until all reachable instruction states stop
changing. Unreachable instructions are not used as incoming dataflow paths and
are left structurally intact.

The pass returns a new `TACProgram`, preserving instruction order, labels,
control flow, and source metadata. It reports its name, instruction counts,
operand replacement count, zero removed instructions, and whether any operand
changed through `PassStatistics`.

### Shared pass interface

`OptimizationPass` is the common base for the future four passes. Its `run`
method returns a transformed `TACProgram` and stores a `PassResult` in
`last_result`; the result contains the program and `PassStatistics`. The
remaining passes will use this interface in later phases, but are not present
yet.

### Semantic preservation

Integration tests execute original and transformed programs with the Phase 2
interpreter and compare `semantic_signature()`. The pass only substitutes
operands, so it does not itself evaluate division, modulo, or any other
arithmetic; runtime errors remain the interpreter's responsibility.

## 6. Constant Folding

Constant Folding evaluates a local TAC expression when all of its operands are
already integer literals. It supports arithmetic operators `+`, `-`, `*`, `/`,
and `%`, relational operators `<`, `<=`, `==`, `!=`, `>`, and `>=`, and unary
negation. Relational results use the interpreter's integer booleans: `1` for
true and `0` for false. Division truncates toward zero and modulo follows the
same dividend-sign convention as the interpreter.

The pass does not inspect earlier assignments and does not call Constant
Propagation. Thus `a = 10; b = a; c = b + 5` remains unchanged when Constant
Folding runs alone, while `c = 10 + 5` becomes `c = 15`. This separation makes
the effect of pass ordering observable in later experiments.

Division or modulo by zero is never folded. The original expression is
preserved so the interpreter remains responsible for the runtime error rather
than receiving an invented value. Conditional branches are also preserved;
this pass does not remove or simplify control flow, labels, blocks, or gotos.

The pass returns a new program, preserves source metadata, and reports
`expressions_folded` through `PassStatistics`. Instruction counts remain
unchanged because Constant Folding does not remove instructions.

## 7. Dead-Code Elimination

Dead-Code Elimination removes pure instructions whose defined values are not
needed by any observable computation. It uses the existing IR `uses()`,
`defines()`, `has_side_effects`, and `is_control_flow` helpers rather than
duplicating instruction semantics.

The pass computes live-in and live-out variable sets with a backward dataflow
analysis. At each instruction, live-out is the union of live-in sets for all
successors. A pure definition is removable when every value it defines is
absent from live-out. If an instruction is retained, its uses are added to
live-in after its definitions are removed. If a pure instruction is dead, its
uses do not keep earlier computations alive; this allows transitive dead
computation chains to disappear.

The CFG includes sequential and fall-through edges, both successors of a
conditional branch, the target of a `goto`, and no successor for `return`.
Backward liveness is iterated with a worklist to a fixed point, so loops and
branch joins are handled conservatively and deterministically.

Labels, gotos, conditional branches, returns, prints, and all instructions
marked as side-effecting or control-flow instructions are preserved. DCE does
not remove labels, simplify branches, eliminate unreachable blocks, propagate
constants, fold expressions, reorder instructions, or perform CSE. Unreachable
code therefore remains structurally present; only independently dead pure
instructions may be removed.

The pass returns a new program with retained instruction order and source
metadata. Its statistics report `dead_instructions_removed`,
`instructions_removed`, before/after counts, and `changed`. Integration tests
execute original and transformed programs with the interpreter and compare
semantic signatures.

## 8. Common Subexpression Elimination

Common Subexpression Elimination (CSE) reuses a previously computed pure
binary expression when the same expression is available at the current
program point. For example, `t2 = a + b` can become `t2 = t1` after
`t1 = a + b`. The destination remains present because later code may use it.

Expressions are keyed by the typed, ordered tuple `(operator, left, right)`.
Operand order is significant: `a + b` and `b + a` are different keys. CSE does
not perform constant propagation, constant folding, commutative normalization,
algebraic simplification, or dead-code elimination.

The pass uses forward available-expression analysis over the existing TAC CFG.
For each instruction it computes `IN` and `OUT` mappings from expression keys
to the result variable holding the available value. At joins, mappings are
intersected and an expression is retained only when every incoming path agrees
on the same result variable. Transfer first kills expressions whose operands
or result variable are redefined, then generates the current pure binary
expression. Sequential edges, fall-through, gotos, conditional branches,
returns, and loop back edges are handled by a deterministic worklist to a fixed
point. Unreachable instructions are not used to establish availability.

Assignments to unrelated variables do not invalidate an expression. Assigning
an operand or reusing a result variable does invalidate dependent entries.
Division and modulo are treated as pure expressions under the interpreter's
semantics: if the operands remain unchanged, reusing a successful evaluation
cannot change its result, and a prior division-by-zero error prevents later
instructions from executing. Branch structure and all side-effecting
instructions are preserved.

The pass reports `expressions_reused` and
`replacement_assignments_generated`; instruction counts and removal counts
remain unchanged. Semantic tests compare interpreter signatures before and
after CSE, including runtime-error behavior.

## 9. Optimization Pipeline

`OptimizationPipeline` is the reusable execution engine for an explicitly
ordered sequence of `OptimizationPass` objects. It accepts a `TACProgram` and
either a pass sequence supplied to `run(program, passes)` or a sequence stored
at construction time. It executes each object exactly once in the supplied
order, including repeated pass instances, and never searches, reorders,
deduplicates, or scores pass sequences.

Each pass receives a copy of the current intermediate program. The resulting
`PassResult` is captured before its program is copied forward to the next pass.
`PipelineResult` exposes `final_program`, ordered `pass_results`, exact
`pass_order`, `changed`, and `final_instruction_count`. Per-pass statistics are
the statistics produced by the pass itself; the pipeline does not recalculate
them. An empty sequence returns a copied, unchanged program with an empty
history.

If a pass raises an exception, execution stops immediately. The pipeline raises
`PipelineExecutionError` containing the one-based pass position, pass name,
and original exception as both `original_error` and the exception cause. The
pipeline does not depend on the interpreter; callers can compare the original
and final programs with `semantic_signature()` externally.

This phase deliberately provides execution infrastructure only. Exhaustive
`4!` permutation enumeration, heuristic comparison, benchmark evaluation, and
phase-ordering analysis belong to later phases.

## 10. Exhaustive Permutation Engine

`PermutationEngine` generates the four canonical pass names `CP`, `CF`, `DCE`,
and `CSE` with `itertools.permutations`, producing exactly 24 deterministic
orders. Each order receives fresh pass instances and a fresh copy of the same
original `TACProgram`; no result is fed into another permutation and duplicate
final TAC programs are never merged.

Each order is identified with a stable hyphen-separated ID such as
`CP-CF-DCE-CSE`. `PermutationResult` stores the canonical order, identifier,
final program and instruction count, complete `PipelineResult`, semantic
preservation status, execution status, and any diagnostic error. The enclosing
`PermutationExperimentResult` retains the original program, baseline count, and
all 24 results.

Before the permutations run, the original program is executed with the Phase 2
interpreter. Each final program is then executed and compared using
`semantic_signature()`. Matching runtime-error behavior is compared by error
kind/reason; mismatches remain visible in the result rather than being
discarded. Pipeline failures are retained as unsuccessful permutation results
with their pass context.

This phase deliberately performs no ranking, best/worst selection, reduction
percentage, benchmark loop, metrics calculation, or interaction analysis. It
only collects raw independent results for the later experiment phases.

## 11. Phase-Ordering Metrics

`calculate_metrics(experiment_result)` consumes one existing
`PermutationExperimentResult`; it does not rerun passes, execute the
interpreter, generate permutations, or modify programs. For every raw result it
records the baseline count from the original program, final count, instructions
removed, reduction percentage, pass order, semantic validity, execution status,
and any error.

Ranking eligibility requires both successful execution and semantic
preservation. Invalid or failed results remain in `permutation_metrics` and are
counted, but are excluded from best/worst, averages, medians, and spreads. The
best valid ordering minimizes final instruction count; the worst maximizes it.
All tied IDs are exposed in deterministic lexicographic order, with the first
ID also available as the representative `best_permutation` or
`worst_permutation`.

The aggregate object reports valid/invalid counts, average and median final
instruction counts, best/worst and average reduction percentages, instruction
count spread, and reduction spread. Reduction is
`((baseline - final) / baseline) * 100`; a zero baseline produces `0.0` rather
than a division error, and negative reductions are preserved when an output is
larger than its baseline. If no valid result exists, ranking and aggregate
fields are explicitly `None` or empty tuples.

## 12. Fixed-Point Execution

Some pass interactions may require repeated execution until no pass changes the
program. The future design will define whether fixed-point execution is a
pipeline option or a separate execution mode, with a deterministic iteration
limit and a clear trace of each iteration. The termination policy must prevent
non-terminating transformations from making experiments ambiguous.

## 13. Permutation Search

The experiment layer will enumerate all `4! = 24` permutations of the four
passes. Every permutation will be evaluated on every benchmark program using
the same initial input and execution settings. Results will retain the exact
pass order so that outcomes can be reproduced and inspected.

## 14. Semantic Verification

Each transformation and each complete pipeline result must preserve program
semantics under the project's defined TAC execution model. A future verifier
will compare observable behavior between the original and optimized programs,
using deterministic test inputs or an explicitly bounded equivalence strategy.
An optimization result that cannot be verified must not be treated as a valid
experiment result.

## 15. Metrics

The metrics layer will record at least instruction count before and after
optimization, instructions removed, number of iterations, and whether semantic
verification succeeded. It may also record per-pass changes and runtime if
those measurements remain deterministic and useful for the lab study.

## 16. Pass Interaction Analysis

Phase 10 provides `analyze_pass_interactions(experiment_result)`, a read-only
analysis of one complete `PermutationExperimentResult`. It does not invoke the
pipeline, individual passes, interpreter, or permutation generator. It uses
only the final instruction counts, semantic/execution status, and already
stored per-pass statistics.

The analysis uses the canonical pair order
`CP/CF`, `CP/DCE`, `CP/CSE`, `CF/DCE`, `CF/CSE`, and `DCE/CSE`. For each pair,
the two passes are kept adjacent and swapped while the two remaining passes
are placed before, between, or after the pair in both deterministic orders.
This gives six matched comparisons per pair and 36 comparisons overall. A
comparison records both full permutation IDs, its prefix and suffix, both final
instruction counts, and the signed delta:

```text
delta = count(first-pass-then-second-pass) \
        - count(second-pass-then-first-pass)
```

Thus, a negative delta favors the first ordering, a positive delta favors the
second ordering, and zero is a tie. Pair aggregates report wins, ties, mean
signed and absolute deltas, minimum/maximum delta, and maximum absolute effect.
The strongest pair is selected by maximum mean absolute delta, with canonical
pair order resolving ties.

If either permutation in a comparison failed or did not preserve semantics,
the comparison remains in the returned records but is marked invalid and is
excluded from pair aggregates. Incomplete, duplicated, or malformed 24-result
experiments raise `InteractionAnalysisError`. Optional enablement evidence is
classified only from the stored pass statistics and is diagnostic; it is not a
causal claim and is not required for the core interaction metric.

## 17. Representative Benchmark Suite

Phase 11 provides exactly 20 hand-authored, deterministic TAC programs under
`benchmarks/`. They are intentionally designed rather than randomly generated:
five are straight-line, four are branch-oriented, three contain terminating
loops, three focus on CSE, and five target multi-pass interactions. Programs
are kept between 8 and 30 instructions so their behavior remains inspectable
in a viva.

`benchmarks/manifest.json` is machine-readable metadata. Each entry records an
ID, filename, category, description, optimization opportunities, control-flow
shape, qualitative ordering-sensitivity expectation, and expected interaction
topics. It deliberately contains no measured best/worst permutation, final
instruction count, or reduction percentage.

`optimizer.benchmarks.loader` validates the manifest and resolves each TAC file
through the existing `load_tac()` parser. It does not define a second TAC
format or execute programs. The Phase 11 integration tests then execute each
original program and run the existing 24-permutation engine, requiring normal
termination and semantic preservation for every result.

The suite includes relatively insensitive cases as well as cases intended to
expose stronger interactions. These are experimental purposes, not claims
about universal outcomes; Phase 12 calculates the measured outcomes.

## 18. Experiment Output

The experiment writes reproducible results under `results/`, with the input
identity, pass order, metrics, verification status, and tool version recorded.
Generated output remains separate from source benchmarks. Phase 12 creates
reproducible result tables and visualizations from the stored experiment data.
No dashboard or web UI is included.

## 19. Phase 12 Experiment Runner and Visualization

`ExperimentRunner` loads the Phase 11 manifest, runs each benchmark once
through `PermutationEngine`, then passes the resulting
`PermutationExperimentResult` to `calculate_metrics()` and
`analyze_pass_interactions()`. It does not rerun individual passes or the
interpreter for metrics and interaction analysis. The runner evaluates 20
benchmarks and 24 permutations per benchmark, preserving ties and semantic
validity information.

The fixed heuristic baselines are exactly `CP -> CF -> DCE -> CSE` and
`CSE -> DCE -> CP -> CF`. Because both orders are already among the exhaustive
permutations, heuristic comparisons reuse their stored permutation results.
For each benchmark, heuristic gaps are computed as heuristic final count minus
exhaustive best count.

The serialization layer writes JSON, four CSV reports, and a Markdown summary.
The visualization layer writes five PNG charts: best versus worst count,
reduction range, heuristic versus exhaustive best, spread percentage, and
equal-weight pairwise interaction strength. Plot functions accept structured
results and never load TAC or rerun optimization. The interaction aggregate
averages benchmark-level mean absolute deltas so every benchmark has equal
conceptual weight.

The CLI entry point is:

```bash
python3 scripts/run_experiment.py
```

The workflow is deterministic and does not include volatile timestamps in the
serialized comparison data.

## 20. Testing Strategy

Phase 1 tests cover IR construction and rendering, operand typing, all supported
instruction categories, source locations, parser errors, uses/defines,
side-effect classification, copying, round trips, and loading the three example
files. Phase 2 tests cover arithmetic and relational execution, control flow,
loops, output capture, returns, errors, initial environments, semantic
signatures, determinism, and example execution. Phase 3 tests cover constant
propagation, conservative joins, reassignment, loops, unreachable code,
statistics, semantic preservation, and pass separation. Phase 5 tests cover
liveness, control-flow joins, loops, side-effect preservation, dead chains,
statistics, and semantic preservation. Phase 6 tests cover expression keys,
redefinition invalidation, branch joins, loops, runtime-error preservation,
statistics, and semantic preservation. Phase 7 tests cover empty, single,
repeated, forward, reverse, and arbitrary pass sequences, history/statistics,
immutability, failures, determinism, and semantic preservation. Later tests will cover each pass independently,
pipeline ordering and fixed points, semantic verification, deterministic
permutation enumeration, metric aggregation, and end-to-end benchmark runs.

The test suite should use small examples with expected transformations and
should include regression tests for any discovered phase-ordering behavior.

Phase 9 tests cover baseline and final counts, reduction percentages,
valid-result filtering, ties, averages, medians, spreads, zero baselines,
determinism, and Phase 8 integration. Phase 10 tests cover the six-pair/36-
comparison structure, controlled adjacent-swap deltas, aggregate wins and
ties, deterministic strongest-pair selection, invalid-result filtering,
malformed input validation, no-rerun behavior, and real example integration.
Phase 11 tests cover manifest structure and uniqueness, parser loading, normal
termination, deterministic loading, all 24 permutations, and semantic
preservation across the complete benchmark suite. Phase 12 tests cover result
models, heuristic consistency, one engine run per benchmark, deterministic
JSON/CSV/Markdown serialization, CLI output, and headless plot generation.

## Design Principles

- Deterministic behavior.
- Reproducible experiments.
- No external compiler dependency.
- No network dependency.
- No machine learning.
- Small and understandable implementation.
- Each optimization pass independently testable.
- Optimization passes must preserve semantics.
- All 24 permutations must be evaluated.
- Experiment results must be reproducible.
- Every transformation should be traceable and debuggable.
