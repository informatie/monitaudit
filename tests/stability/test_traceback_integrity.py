# tests/stability/test_traceback_integrity.py

from __future__ import annotations

import traceback

import pytest

from monitaudit import Observability


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def observability() -> Observability:
    return Observability(
        application="traceback-integrity-test",
        environment="test",
    )

def raise_value_error() -> None:
    raise ValueError("intentional traceback test")


def level_one() -> None:
    level_two()


def level_two() -> None:
    level_three()


def level_three() -> None:
    raise RuntimeError("nested traceback test")


# ---------------------------------------------------------------------------
# Python baseline
# ---------------------------------------------------------------------------


def test_python_traceback_contains_exception_type() -> None:
    """
    Verify the Python traceback baseline.

    This test deliberately does not use monitaudit. If this test fails,
    the assumptions used by the monitaudit traceback tests are incorrect.
    """
    try:
        raise_value_error()
    except ValueError:
        traceback_text = traceback.format_exc()

    assert "ValueError" in traceback_text


def test_python_traceback_contains_exception_message() -> None:
    try:
        raise_value_error()
    except ValueError:
        traceback_text = traceback.format_exc()

    assert "intentional traceback test" in traceback_text


def test_python_traceback_contains_original_function() -> None:
    try:
        raise_value_error()
    except ValueError:
        traceback_text = traceback.format_exc()

    assert "raise_value_error" in traceback_text


def test_python_nested_traceback_contains_complete_call_chain() -> None:
    try:
        level_one()
    except RuntimeError:
        traceback_text = traceback.format_exc()

    assert "level_one" in traceback_text
    assert "level_two" in traceback_text
    assert "level_three" in traceback_text
    assert "RuntimeError: nested traceback test" in traceback_text


# ---------------------------------------------------------------------------
# monitaudit @trace exception behaviour
# ---------------------------------------------------------------------------


def test_trace_reraises_original_exception(
    observability: Observability,
) -> None:
    @observability.trace
    def explode() -> None:
        raise ValueError("original exception")

    with pytest.raises(ValueError, match="original exception"):
        explode()


def test_trace_preserves_exception_type(
    observability: Observability,
) -> None:
    @observability.trace
    def explode() -> None:
        raise KeyError("missing-key")

    with pytest.raises(KeyError):
        explode()


def test_trace_preserves_exception_object(
    observability: Observability,
) -> None:
    original_exception = RuntimeError("same exception object")

    @observability.trace
    def explode() -> None:
        raise original_exception

    captured_exception: RuntimeError | None = None

    try:
        explode()
    except RuntimeError as exc:
        captured_exception = exc

    assert captured_exception is original_exception


def test_trace_preserves_original_exception_message(
    observability: Observability,
) -> None:
    @observability.trace
    def explode() -> None:
        raise ValueError("do-not-change-this-message")

    with pytest.raises(ValueError) as exc_info:
        explode()

    assert str(exc_info.value) == "do-not-change-this-message"


# ---------------------------------------------------------------------------
# Traceback integrity
# ---------------------------------------------------------------------------


def test_trace_preserves_original_function_in_traceback(
    observability: Observability,
) -> None:
    @observability.trace
    def unique_traceback_function() -> None:
        raise RuntimeError("traceback integrity")

    try:
        unique_traceback_function()
    except RuntimeError:
        traceback_text = traceback.format_exc()

    assert "unique_traceback_function" in traceback_text
    assert "RuntimeError: traceback integrity" in traceback_text


def test_trace_preserves_nested_application_stack(
    observability: Observability,
) -> None:
    @observability.trace
    def traced_entry_point() -> None:
        nested_application_function()

    def nested_application_function() -> None:
        deeply_nested_function()

    def deeply_nested_function() -> None:
        raise LookupError("deep failure")

    try:
        traced_entry_point()
    except LookupError:
        traceback_text = traceback.format_exc()

    assert "traced_entry_point" in traceback_text
    assert "nested_application_function" in traceback_text
    assert "deeply_nested_function" in traceback_text
    assert "LookupError: deep failure" in traceback_text


def test_trace_does_not_replace_application_exception(
    observability: Observability,
) -> None:
    """
    monitaudit internal handling must never replace the application's
    original exception with an monitaudit exception.
    """

    @observability.trace
    def application_function() -> None:
        raise ValueError("application failure")

    try:
        application_function()
    except Exception as exc:
        captured = exc

    assert type(captured) is ValueError
    assert str(captured) == "application failure"


def test_traceback_has_original_exception_as_final_exception(
    observability: Observability,
) -> None:
    @observability.trace
    def application_function() -> None:
        raise RuntimeError("final original exception")

    try:
        application_function()
    except RuntimeError as exc:
        traceback_exception = traceback.TracebackException.from_exception(exc)

    assert traceback_exception.exc_type_str == "RuntimeError"
    assert str(traceback_exception) == "final original exception"

# ---------------------------------------------------------------------------
# Exception chaining
# ---------------------------------------------------------------------------


def test_trace_preserves_exception_cause(
    observability: Observability,
) -> None:
    original_cause = ValueError("root cause")

    @observability.trace
    def application_function() -> None:
        try:
            raise original_cause
        except ValueError as exc:
            raise RuntimeError("wrapper exception") from exc

    with pytest.raises(RuntimeError) as exc_info:
        application_function()

    assert exc_info.value.__cause__ is original_cause


def test_traceback_contains_exception_chain(
    observability: Observability,
) -> None:
    @observability.trace
    def application_function() -> None:
        try:
            raise ValueError("root failure")
        except ValueError as exc:
            raise RuntimeError("outer failure") from exc

    try:
        application_function()
    except RuntimeError:
        traceback_text = traceback.format_exc()

    assert "ValueError: root failure" in traceback_text
    assert "RuntimeError: outer failure" in traceback_text
    assert "The above exception was the direct cause" in traceback_text


# ---------------------------------------------------------------------------
# Nested traced functions
# ---------------------------------------------------------------------------


def test_nested_trace_preserves_original_exception(
    observability: Observability,
) -> None:
    @observability.trace
    def inner_function() -> None:
        raise ArithmeticError("inner failure")

    @observability.trace
    def outer_function() -> None:
        inner_function()

    with pytest.raises(ArithmeticError) as exc_info:
        outer_function()

    assert str(exc_info.value) == "inner failure"


def test_nested_traceback_contains_both_traced_functions(
    observability: Observability,
) -> None:
    @observability.trace
    def inner_traced_function() -> None:
        raise RuntimeError("nested traced failure")

    @observability.trace
    def outer_traced_function() -> None:
        inner_traced_function()

    try:
        outer_traced_function()
    except RuntimeError:
        traceback_text = traceback.format_exc()

    assert "outer_traced_function" in traceback_text
    assert "inner_traced_function" in traceback_text
    assert "RuntimeError: nested traced failure" in traceback_text


# ---------------------------------------------------------------------------
# Traceback object integrity
# ---------------------------------------------------------------------------


def test_trace_preserves_traceback_object(
    observability: Observability,
) -> None:
    @observability.trace
    def original_failure_location() -> None:
        raise RuntimeError("traceback-object-test")

    try:
        original_failure_location()
    except RuntimeError as exc:
        tb = exc.__traceback__

    assert tb is not None

    frame_names: list[str] = []

    while tb is not None:
        frame_names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next

    assert "original_failure_location" in frame_names


def test_original_failure_frame_remains_in_traceback(
    observability: Observability,
) -> None:
    @observability.trace
    def level_a() -> None:
        level_b()

    def level_b() -> None:
        level_c()

    def level_c() -> None:
        raise ZeroDivisionError("simulated division failure")

    try:
        level_a()
    except ZeroDivisionError as exc:
        tb = exc.__traceback__

    assert tb is not None

    frame_names: list[str] = []

    while tb is not None:
        frame_names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next

    assert "level_a" in frame_names
    assert "level_b" in frame_names
    assert "level_c" in frame_names


# ---------------------------------------------------------------------------
# Critical stability invariant
# ---------------------------------------------------------------------------


def test_monitaudit_never_masks_application_exception(
    observability: Observability,
) -> None:
    """
    Critical monitaudit stability invariant:

    When application code fails, monitaudit must never replace that
    exception with an internal monitaudit exception.
    """

    original_exception = RuntimeError(
        "this exception must survive monitaudit unchanged"
    )

    @observability.trace
    def application_code() -> None:
        raise original_exception

    try:
        application_code()
    except Exception as exc:
        captured_exception = exc

    assert captured_exception is original_exception
    assert type(captured_exception) is RuntimeError
    assert (
        str(captured_exception)
        == "this exception must survive monitaudit unchanged"
    )