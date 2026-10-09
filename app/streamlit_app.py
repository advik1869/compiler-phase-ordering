"""Streamlit presentation layer for the phase-ordering optimizer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from optimizer.analysis import execute
from optimizer.ir import TACParseError, parse_tac
from optimizer.metrics import calculate_metrics
from optimizer.passes import (
    CommonSubexpressionElimination,
    ConstantFolding,
    ConstantPropagation,
    DeadCodeElimination,
)
from optimizer.pipeline import OptimizationPipeline, PermutationEngine, generate_permutations


DEFAULT_TAC = """a = 10
b = 20
c = a + b
d = c * 2
t1 = a + b
t2 = a + b
unused = 999
e = d + 100
print t2
return t2"""

PASS_FACTORIES = {
    "CP": ConstantPropagation,
    "CF": ConstantFolding,
    "DCE": DeadCodeElimination,
    "CSE": CommonSubexpressionElimination,
}
PRESETS = {
    "H1: CP → CF → DCE → CSE": ("CP", "CF", "DCE", "CSE"),
    "H2: CSE → DCE → CP → CF": ("CSE", "DCE", "CP", "CF"),
}


def format_order(order: Iterable[str]) -> str:
    """Render a pass order consistently throughout the UI."""
    return " → ".join(order)


def program_to_text(program: Any) -> str:
    """Render a TAC program using the IR's canonical instruction renderer."""
    return "\n".join(instruction.to_tac() for instruction in program)


def source_text(uploaded_file: Any, text: str) -> str:
    """Return uploaded TAC when present, otherwise the editor contents."""
    if uploaded_file is None:
        return text
    return uploaded_file.getvalue().decode("utf-8")


def selected_order(selection: str) -> tuple[str, ...]:
    """Convert the displayed order selector value into canonical pass names."""
    if selection in PRESETS:
        return PRESETS[selection]
    return tuple(selection.split(" → "))


def format_count(value: int | float | None) -> str:
    return "—" if value is None else f"{value:g}" if isinstance(value, float) else str(value)


@st.cache_data(show_spinner=False)
def load_experiment_json() -> dict[str, Any]:
    """Load the canonical experiment output without rerunning experiments."""
    path = PROJECT_ROOT / "results" / "experiment_results.json"
    if not path.exists():
        raise FileNotFoundError("results/experiment_results.json is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_and_execute(text: str):
    """Parse and execute TAC, allowing the UI to present readable errors."""
    if not text.strip():
        raise ValueError("TAC input is empty.")
    program = parse_tac(text)
    return program, execute(program)


def run_selected_optimization(text: str, order: tuple[str, ...]) -> dict[str, Any]:
    """Run one selected pipeline and compare observable semantic signatures."""
    program, original_execution = parse_and_execute(text)
    pipeline = OptimizationPipeline().run(
        program, [PASS_FACTORIES[name]() for name in order]
    )
    optimized_execution = execute(pipeline.final_program)
    return {
        "program": program,
        "pipeline": pipeline,
        "original_execution": original_execution,
        "optimized_execution": optimized_execution,
        "semantic_equivalent": (
            original_execution.semantic_signature()
            == optimized_execution.semantic_signature()
        ),
    }


def render_tac_input(key: str, *, default: str = DEFAULT_TAC) -> str:
    editor = st.text_area("TAC input", value=default, height=260, key=f"{key}_editor")
    uploaded = st.file_uploader("Optional .tac file", type=["tac"], key=f"{key}_upload")
    if uploaded is not None:
        try:
            return source_text(uploaded, editor)
        except UnicodeDecodeError:
            st.error("The uploaded file is not valid UTF-8 TAC text.")
    return editor


def render_syntax_help() -> None:
    with st.expander("TAC Syntax Help"):
        st.code("a = 10\nb = a + 5\nt1 = a * b\nprint t1\nreturn t1", language="text")
        st.caption("Use `print t1`, not `print(t1)`. The parser accepts TAC syntax, not Python syntax.")


def page_optimize() -> None:
    st.header("Optimize TAC")
    st.write("Run one selected order through the existing optimization pipeline and verify its observable behavior.")
    text = render_tac_input("optimize")
    preset = st.selectbox("Pass-order preset", list(PRESETS), key="optimize_preset")
    order_options = [format_order(order) for order in generate_permutations()]
    order_label = st.selectbox("Pass order", order_options, index=order_options.index(format_order(PRESETS[preset])))
    order = selected_order(order_label)
    if st.button("Optimize TAC", type="primary"):
        try:
            result = run_selected_optimization(text, order)
        except (TACParseError, ValueError) as error:
            st.error(f"Unable to parse TAC: {error}")
            return
        except Exception as error:
            st.error(f"Unable to execute the selected pipeline: {error}")
            return

        original = result["original_execution"]
        optimized = result["optimized_execution"]
        pipeline = result["pipeline"]
        baseline = len(result["program"])
        final_count = len(pipeline.final_program)
        removed = baseline - final_count
        reduction = 0.0 if baseline == 0 else removed / baseline * 100
        left, right = st.columns(2)
        with left:
            st.subheader("Original TAC")
            st.code(program_to_text(result["program"]), language="text")
            st.caption(f"Output: {original.output} | Return: {original.return_value}")
        with right:
            st.subheader("Optimized TAC")
            st.code(program_to_text(pipeline.final_program), language="text")
            st.caption(f"Output: {optimized.output} | Return: {optimized.return_value}")
        metrics = st.columns(5)
        metrics[0].metric("Original instructions", baseline)
        metrics[1].metric("Optimized instructions", final_count)
        metrics[2].metric("Instructions removed", removed)
        metrics[3].metric("Reduction", f"{reduction:.1f}%")
        metrics[4].metric("Pass order", format_order(order))
        if result["semantic_equivalent"]:
            st.success("Semantic equivalence: PASS")
        else:
            st.error("Semantic equivalence: FAIL")
        st.caption(f"Selected order: {format_order(order)}")
    render_syntax_help()


def permutation_rows(experiment: Any, metrics: Any) -> list[dict[str, Any]]:
    """Build display rows from existing engine and metrics objects."""
    return [
        {
            "Pass order": format_order(metric.pass_order),
            "Final instructions": metric.final_instruction_count,
            "Removed": metric.instructions_removed,
            "Reduction %": None if metric.reduction_percentage is None else round(metric.reduction_percentage, 2),
            "Semantic valid": metric.semantic_preserved,
            "Execution status": "OK" if metric.execution_success else "FAILED",
        }
        for metric in sorted(metrics.permutation_metrics, key=lambda item: (item.final_instruction_count is None, item.final_instruction_count or 0, item.permutation_id))
    ]


def page_compare() -> None:
    st.header("Compare 24 Orders")
    text = render_tac_input("compare")
    if st.button("Run All 24 Permutations", type="primary"):
        try:
            program, _ = parse_and_execute(text)
            experiment = PermutationEngine().run(program)
            metrics = calculate_metrics(experiment)
        except (TACParseError, ValueError) as error:
            st.error(f"Unable to parse TAC: {error}")
            return
        except Exception as error:
            st.error(f"Unable to evaluate permutations: {error}")
            return
        st.session_state["compare_result"] = (experiment, metrics)
    if "compare_result" not in st.session_state:
        st.info("Enter TAC and run the exhaustive comparison to see all 24 orders.")
        return
    experiment, metrics = st.session_state["compare_result"]
    st.dataframe(permutation_rows(experiment, metrics), width="stretch", hide_index=True)
    best = metrics.best_permutations
    worst = metrics.worst_permutations
    st.write(f"**BEST ORDER{'S' if len(best) != 1 else ''}:** {', '.join(best) if best else '—'}")
    st.write(f"**WORST ORDER{'S' if len(worst) != 1 else ''}:** {', '.join(worst) if worst else '—'}")
    cards = st.columns(5)
    cards[0].metric("Baseline", metrics.baseline_instruction_count)
    cards[1].metric("Best", format_count(metrics.best_final_instruction_count))
    cards[2].metric("Worst", format_count(metrics.worst_final_instruction_count))
    cards[3].metric("Best reduction", f"{metrics.best_reduction_percentage:.1f}%" if metrics.best_reduction_percentage is not None else "—")
    cards[4].metric("Spread", format_count(metrics.instruction_count_spread))

    valid = [row for row in permutation_rows(experiment, metrics) if row["Final instructions"] is not None]
    if valid:
        import matplotlib.pyplot as plt
        figure, axis = plt.subplots(figsize=(10, 7))
        labels = [row["Pass order"] for row in reversed(valid)]
        values = [row["Final instructions"] for row in reversed(valid)]
        axis.barh(labels, values, color="#4c78a8")
        axis.set_xlabel("Final instruction count")
        axis.set_title("Pass Order vs Final Instruction Count")
        figure.tight_layout()
        st.pyplot(figure, clear_figure=True)


def page_benchmarks(data: dict[str, Any]) -> None:
    st.header("Benchmark Dashboard")
    experiment = data["experiment"]
    cards = st.columns(5)
    cards[0].metric("Benchmarks", experiment["benchmark_count"])
    cards[1].metric("Permutation evaluations", experiment["total_permutation_evaluations"])
    cards[2].metric("Semantic valid", experiment["semantic_valid_evaluations"])
    cards[3].metric("Semantic invalid", experiment["semantic_invalid_evaluations"])
    cards[4].metric("Failed", experiment["failed_permutation_evaluations"])
    benchmarks = data.get("benchmarks", [])
    selected_id = st.selectbox("Benchmark", [item["benchmark"]["id"] for item in benchmarks])
    selected = next(item for item in benchmarks if item["benchmark"]["id"] == selected_id)
    spec, summary = selected["benchmark"], selected["summary"]
    st.subheader(f"{spec['id']}: {spec['description']}")
    st.caption(f"Category: {spec['category']} | Control flow: {spec['control_flow']}")
    cards = st.columns(6)
    cards[0].metric("Baseline", summary["baseline_instructions"])
    cards[1].metric("Best", summary["best_instructions"])
    cards[2].metric("Worst", summary["worst_instructions"])
    cards[3].metric("Best reduction", f"{summary['best_reduction_percent']:.1f}%")
    cards[4].metric("Spread", summary["spread"])
    cards[5].metric("Heuristic 1", selected["heuristics"][0]["final_instruction_count"])
    st.write(f"Best order(s): {', '.join(summary['best_permutations'])}")
    st.write(f"Worst order(s): {', '.join(summary['worst_permutations'])}")
    st.dataframe(selected["heuristics"], width="stretch", hide_index=True)
    st.subheader("Canonical experiment plots")
    plot_names = ["best_vs_worst.png", "reduction_range.png", "heuristic_vs_best.png", "phase_ordering_spread.png", "pairwise_interaction_strength.png"]
    for name in plot_names:
        path = PROJECT_ROOT / "results" / "plots" / name
        if path.exists():
            st.image(str(path), caption=name.replace("_", " ").removesuffix(".png").title(), width="stretch")
        else:
            st.warning(f"Missing canonical plot: {name}")


def page_interactions(data: dict[str, Any]) -> None:
    st.header("Pass Interactions")
    st.write("Observed ordering sensitivity in this benchmark suite. These results are not universal causal laws.")
    st.info("A negative delta means the first ordering produced fewer instructions under the project's delta convention.")
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for benchmark in data.get("benchmarks", []):
        for interaction in benchmark.get("interactions", []):
            by_pair.setdefault(interaction["pair_name"], []).append(interaction)
    rows = []
    for pair in ("CP/CF", "CP/DCE", "CP/CSE", "CF/DCE", "CF/CSE", "DCE/CSE"):
        items = by_pair.get(pair, [])
        comparisons = [comparison for item in items for comparison in item.get("comparisons", [])]
        valid = [comparison for comparison in comparisons if comparison.get("valid_for_comparison")]
        deltas = [comparison["signed_delta"] for comparison in valid if comparison.get("signed_delta") is not None]
        absolute_deltas = [comparison["absolute_delta"] for comparison in valid if comparison.get("absolute_delta") is not None]
        rows.append({
            "Pair": pair,
            "Controlled comparisons": len(comparisons),
            "Wins (first order)": sum(delta < 0 for delta in deltas),
            "Losses (first order)": sum(delta > 0 for delta in deltas),
            "Ties": sum(delta == 0 for delta in deltas),
            "Mean signed delta": None if not deltas else round(sum(deltas) / len(deltas), 3),
            "Mean absolute delta": None if not absolute_deltas else round(sum(absolute_deltas) / len(absolute_deltas), 3),
            "Maximum observed effect": None if not absolute_deltas else max(absolute_deltas),
        })
    st.dataframe(rows, width="stretch", hide_index=True)
    path = PROJECT_ROOT / "results" / "plots" / "pairwise_interaction_strength.png"
    if path.exists():
        st.image(str(path), width="stretch")


def page_about(data: dict[str, Any]) -> None:
    st.header("About")
    st.markdown("""This educational research prototype studies how the order of compiler optimization phases affects the final optimized TAC program.

The four passes are Constant Propagation, Constant Folding, Dead-Code Elimination, and Common Subexpression Elimination. Their `4! = 24` permutations are evaluated on 20 hand-authored benchmark programs.

Every optimized result is checked against the original program through the existing TAC interpreter and semantic-signature mechanism. The Phase 10 analysis contains 720 controlled adjacent-order comparisons.

The project is a transparent educational demonstration of phase ordering, not a production compiler. The Streamlit application is only a presentation layer over the validated optimizer and experiment results.""")
    st.metric("Loaded experiment version", data["experiment"].get("version", "unknown"))


def main() -> None:
    st.set_page_config(page_title="Phase Ordering Optimizer", page_icon="⚙️", layout="wide")
    st.title("Phase Ordering Optimizer")
    st.caption("Interactive Study of Compiler Optimization Phase Ordering")
    pages = ["Optimize TAC", "Compare 24 Orders", "Benchmark Dashboard", "Pass Interactions", "About"]
    selected_page = st.sidebar.radio("Navigation", pages)
    st.sidebar.markdown("---")
    st.sidebar.caption("A deterministic educational TAC optimizer research dashboard.")
    if selected_page == "Optimize TAC":
        page_optimize()
    elif selected_page == "Compare 24 Orders":
        page_compare()
    else:
        try:
            data = load_experiment_json()
        except (OSError, KeyError, json.JSONDecodeError) as error:
            st.error(f"Canonical experiment results are unavailable: {error}")
            return
        if selected_page == "Benchmark Dashboard":
            page_benchmarks(data)
        elif selected_page == "Pass Interactions":
            page_interactions(data)
        else:
            page_about(data)


if __name__ == "__main__":
    main()
