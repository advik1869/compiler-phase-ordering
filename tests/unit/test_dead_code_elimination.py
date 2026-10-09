"""Unit tests for the Phase 5 dead-code-elimination pass."""

from optimizer.ir import parse_tac
from optimizer.passes import DeadCodeElimination


def eliminate(text: str):
    return DeadCodeElimination().run(parse_tac(text))


def test_simple_dead_assignment() -> None:
    assert eliminate("a = 10\nreturn 0").to_tac() == "return 0"


def test_live_assignment_for_return_and_print() -> None:
    assert eliminate("a = 10\nreturn a").to_tac() == "a = 10\nreturn a"
    assert eliminate("a = 10\nprint a").to_tac() == "a = 10\nprint a"


def test_dead_temporary_and_transitive_chain() -> None:
    assert eliminate("t1 = 10 + 20\nreturn 0").to_tac() == "return 0"
    assert eliminate("a = 10\nb = a + 5\nc = b * 2\nreturn 100").to_tac() == "return 100"


def test_redefinition_is_handled_backward() -> None:
    assert eliminate("a = 10\na = 20\nreturn a").to_tac() == "a = 20\nreturn a"
    assert eliminate("a = 10\nb = a\na = 20\nprint a").to_tac() == "a = 20\nprint a"


def test_branch_join_keeps_both_live_definitions() -> None:
    text = "if x < 10 goto L1\na = 20\ngoto L2\nL1:\na = 30\nL2:\nprint a\n"
    assert eliminate(text).to_tac() == text.rstrip()


def test_control_flow_and_labels_are_never_removed() -> None:
    text = "L1:\nt1 = 10 + 20\ngoto L1\nif x < 1 goto L1\nreturn 0\n"
    result = eliminate(text)
    assert result.to_tac() == "L1:\ngoto L1\nif x < 1 goto L1\nreturn 0"


def test_unreachable_code_is_not_removed_as_a_block() -> None:
    text = "goto live\nx = 10\nlive:\nreturn 0\n"
    result = eliminate(text)
    assert result.to_tac() == "goto live\nlive:\nreturn 0"


def test_loop_liveness_converges_and_preserves_loop_value() -> None:
    text = "i = 0\nL1:\ni = i + 1\nif i < 3 goto L1\nreturn i\n"
    assert eliminate(text).to_tac() == text.rstrip()


def test_dce_does_not_fold_or_propagate() -> None:
    text = "a = 10\nb = a + 5\nc = b * 2\nreturn c\n"
    assert eliminate(text).to_tac() == text.rstrip()


def test_statistics_and_determinism() -> None:
    text = "a = 10\nb = 20\nreturn a\n"
    pass_ = DeadCodeElimination()
    result = pass_.run(parse_tac(text))
    assert result.to_tac() == "a = 10\nreturn a"
    assert pass_.last_result is not None
    statistics = pass_.last_result.statistics
    assert statistics.pass_name == "dead_code_elimination"
    assert statistics.instructions_before == 3
    assert statistics.instructions_after == 2
    assert statistics.instructions_removed == 1
    assert statistics.dead_instructions_removed == 1
    assert statistics.changed
    assert DeadCodeElimination().run(parse_tac(text)).to_tac() == result.to_tac()

