"""Focused tests for the Streamlit layer's pure helper functions."""

from app.streamlit_app import DEFAULT_TAC, format_order, parse_and_execute, selected_order


def test_streamlit_helpers_use_canonical_pass_order_format() -> None:
    order = ("CP", "CF", "DCE", "CSE")
    assert format_order(order) == "CP → CF → DCE → CSE"
    assert selected_order(format_order(order)) == order


def test_streamlit_helper_executes_default_tac() -> None:
    program, execution = parse_and_execute(DEFAULT_TAC)
    assert len(program) == 10
    assert execution.output == (30,)
    assert execution.return_value == 30
