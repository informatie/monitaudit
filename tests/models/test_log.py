from __future__ import annotations

import pytest
from pydantic import ValidationError

from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext
from monitaudit.models.log import (
    CriticalLog,
    DebugLog,
    ErrorLog,
    InfoLog,
    WarningLog,
)


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )


@pytest.mark.parametrize(
    ("log_class", "expected_level"),
    [
        (DebugLog, "DEBUG"),
        (InfoLog, "INFO"),
        (WarningLog, "WARNING"),
        (ErrorLog, "ERROR"),
        (CriticalLog, "CRITICAL"),
    ],
)
def test_log_has_expected_level(
    context: LogContext,
    log_class: type[BaseLog],
    expected_level: str,
) -> None:
    log = log_class(
        message="test message",
        context=context,
    )

    assert log.level == expected_level


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_log_inherits_from_base_log(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    log = log_class(
        message="test message",
        context=context,
    )

    assert isinstance(
        log,
        BaseLog,
    )


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_log_preserves_message(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    log = log_class(
        message="monitaudit message",
        context=context,
    )

    assert log.message == "monitaudit message"


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_log_preserves_context(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    log = log_class(
        message="test",
        context=context,
    )

    assert log.context == context


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_common_fields_are_supported(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    log = log_class(
        message="test",
        context=context,
        call_id="call-123",
        parent_call_id="parent-456",
        parameters={
            "name": "monitaudit",
        },
        duration_ms=12.5,
        module="example.module",
        function="example_function",
        attributes={
            "event": "test_event",
        },
    )

    assert log.call_id == "call-123"

    assert (
        log.parent_call_id
        == "parent-456"
    )

    assert log.parameters == {
        "name": "monitaudit",
    }

    assert log.duration_ms == 12.5
    assert log.module == "example.module"

    assert (
        log.function
        == "example_function"
    )

    assert log.attributes == {
        "event": "test_event",
    }


@pytest.mark.parametrize(
    ("log_class", "wrong_level"),
    [
        (DebugLog, "INFO"),
        (InfoLog, "DEBUG"),
        (WarningLog, "ERROR"),
        (ErrorLog, "WARNING"),
        (CriticalLog, "ERROR"),
    ],
)
def test_log_rejects_incorrect_level(
    context: LogContext,
    log_class: type[BaseLog],
    wrong_level: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        log_class(
            message="test",
            context=context,
            level=wrong_level,
        )


def test_error_log_defaults(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="failed",
        context=context,
    )

    assert log.level == "ERROR"
    assert log.error_type is None
    assert log.error_message is None
    assert log.traceback == []


def test_error_log_error_fields(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="failed",
        context=context,
        error_type="ValueError",
        error_message="invalid value",
        traceback=[
            "Traceback:\n",
            "ValueError: invalid value\n",
        ],
    )

    assert (
        log.error_type
        == "ValueError"
    )

    assert (
        log.error_message
        == "invalid value"
    )

    assert log.traceback == [
        "Traceback:\n",
        "ValueError: invalid value\n",
    ]


def test_critical_log_defaults(
    context: LogContext,
) -> None:
    log = CriticalLog(
        message="critical failure",
        context=context,
    )

    assert log.level == "CRITICAL"
    assert log.error_type is None
    assert log.error_message is None
    assert log.traceback == []


def test_critical_log_error_fields(
    context: LogContext,
) -> None:
    log = CriticalLog(
        message="critical failure",
        context=context,
        error_type="RuntimeError",
        error_message="system failure",
        traceback=[
            "Traceback:\n",
            "RuntimeError: system failure\n",
        ],
    )

    assert (
        log.error_type
        == "RuntimeError"
    )

    assert (
        log.error_message
        == "system failure"
    )

    assert log.traceback == [
        "Traceback:\n",
        "RuntimeError: system failure\n",
    ]


@pytest.mark.parametrize(
    "log_class",
    [
        ErrorLog,
        CriticalLog,
    ],
)
def test_traceback_default_factory_creates_independent_lists(
    context: LogContext,
    log_class: type[ErrorLog] | type[CriticalLog],
) -> None:
    first = log_class(
        message="first",
        context=context,
    )

    second = log_class(
        message="second",
        context=context,
    )

    assert first.traceback == []
    assert second.traceback == []

    assert (
        first.traceback
        is not second.traceback
    )

    first.traceback.append(
        "traceback line"
    )

    assert first.traceback == [
        "traceback line",
    ]

    assert second.traceback == []


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_extra_fields_are_rejected(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        log_class(
            message="test",
            context=context,
            unknown_field="value",
        )


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_negative_duration_is_rejected(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        log_class(
            message="test",
            context=context,
            duration_ms=-0.001,
        )


@pytest.mark.parametrize(
    "log_class",
    [
        DebugLog,
        InfoLog,
        WarningLog,
        ErrorLog,
        CriticalLog,
    ],
)
def test_zero_duration_is_valid(
    context: LogContext,
    log_class: type[BaseLog],
) -> None:
    log = log_class(
        message="test",
        context=context,
        duration_ms=0,
    )

    assert log.duration_ms == 0


def test_error_log_serialises_error_fields(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="failed",
        context=context,
        error_type="ValueError",
        error_message="invalid value",
        traceback=[
            "ValueError: invalid value\n",
        ],
    )

    data = log.model_dump()

    assert data["level"] == "ERROR"

    assert (
        data["error_type"]
        == "ValueError"
    )

    assert (
        data["error_message"]
        == "invalid value"
    )

    assert data["traceback"] == [
        "ValueError: invalid value\n",
    ]


def test_critical_log_serialises_error_fields(
    context: LogContext,
) -> None:
    log = CriticalLog(
        message="critical",
        context=context,
        error_type="RuntimeError",
        error_message="system failure",
        traceback=[
            "RuntimeError: system failure\n",
        ],
    )

    data = log.model_dump()

    assert data["level"] == "CRITICAL"

    assert (
        data["error_type"]
        == "RuntimeError"
    )

    assert (
        data["error_message"]
        == "system failure"
    )

    assert data["traceback"] == [
        "RuntimeError: system failure\n",
    ]