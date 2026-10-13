"""Unit tests for tools/gates.py parsing and decision logic (offline, fast)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gates", Path(__file__).resolve().parents[1] / "tools" / "gates.py")
gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gates)

# a real parameter id: spaces inside the brackets, '-<fixture>-' at the tail
TELEGRAM_ID = ("tests/test_messenger_gateway.py::"
               "test_ideas_message_is_title_then_two_paragraphs_then_link"
               "[یک جمله طولانی بدون هیچ نقطه پایانی که باید از وسط کلمه "
               "بریده نشود-telegram-_tg_render_digest]")


def test_parse_baseline_skips_comments_and_splits_tabs():
    text = ("# comment line\n"
            "\n"
            "tests/test_a.py::test_x\treason one\n"
            "tests/test_b.py::test_y[б]  \treason two\n")
    assert gates.parse_baseline(text) == {"tests/test_a.py::test_x",
                                          "tests/test_b.py::test_y[б]"}


def test_parse_failures_handles_param_ids_with_spaces():
    out = ("12 failed, 262 passed in 107.76s\n"
           f"FAILED {TELEGRAM_ID} - real-bug: split regression\n"
           "FAILED tests/test_core.py::test_simple - AssertionError: x\n")
    assert set(gates.parse_failures(out)) == {TELEGRAM_ID,
                                              "tests/test_core.py::test_simple"}


def test_parse_failures_unescapes_pytest_unicode_ids():
    """pytest escapes non-ASCII ids in the short summary (\\u06cc...); the
    baseline file keeps readable Persian — both must compare equal."""
    escaped = ("FAILED tests/test_messenger_gateway.py::test_x"
               "[\\u06cc\\u06a9 \\u062c\\u0645\\u0644\\u0647"
               "-telegram-_tg] - real-bug: split regression\n")
    assert gates.parse_failures(escaped) == [
        "tests/test_messenger_gateway.py::test_x[یک جمله-telegram-_tg]"]


def test_evaluate_flags_new_failure():
    baseline = "tests/test_a.py::old\twhy\n"
    out = ("2 failed, 10 passed in 1.0s\n"
           "FAILED tests/test_a.py::new_one - AssertionError\n"
           "FAILED tests/test_a.py::old - whatever\n")
    new, fixed, summary, n_actual = gates.evaluate(out, baseline)
    assert new == ["tests/test_a.py::new_one"]
    assert fixed == []
    assert n_actual == 2 and "2 failed" in summary


def test_evaluate_reports_fixed_without_failing():
    baseline = "tests/test_a.py::old\twhy\n"
    new, fixed, summary, n_actual = gates.evaluate("0 failed, 11 passed\n", baseline)
    assert new == [] and fixed == ["tests/test_a.py::old"] and n_actual == 0


def test_baseline_file_parses_to_the_documented_12():
    """The committed baseline must stay parseable and complete."""
    text = (Path(__file__).resolve().parent / "BASELINE_FAILURES.txt") \
        .read_text(encoding="utf-8")
    ids = gates.parse_baseline(text)
    assert len(ids) == 11
    assert "tests/test_messenger_gateway.py::test_ideas_push_shortens_the_link" in ids

