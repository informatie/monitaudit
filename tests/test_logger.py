from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from monitaudit.logger import monitauditLogger
from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext
from monitaudit.models.log import (
    CriticalLog,
    DebugLog,
    ErrorLog,
    InfoLog,
    WarningLog,
)
from monitaudit.sinks.base import Sink


class MemorySink(Sink):
    """Simple sink that stores all received log records."""

    def __init__(self) -> None:
        self.logs: list[BaseLog] = []

    def write(self, log: BaseLog) -> None:
        self.logs.append(log)


class FailingSink(Sink):
    """Sink used to verify sink failure isolation."""

    def __init__(
        self,
        message: str = "sink failed",
    ) -> None:
        self.message = message
        self.calls = 0

    def write(self, log: BaseLog) -> None:
        self.calls += 1
        raise RuntimeError(self.message)


class ExampleEnum(Enum):
    FIRST = "first"


class ExampleObject:
    def __repr__(self) -> str:
        return "ExampleObject()"


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )


@pytest.fixture
def sink() -> MemorySink:
    return MemorySink()


@pytest.fixture
def logger(
    context: LogContext,
    sink: MemorySink,
) -> monitauditLogger:
    return monitauditLogger(
        context,
        sink,
    )


@pytest.mark.parametrize(
    ("method_name", "expected_type", "expected_level"),
    [
        ("debug", DebugLog, "DEBUG"),
        ("info", InfoLog, "INFO"),
        ("warning", WarningLog, "WARNING"),
        ("error", ErrorLog, "ERROR"),
        ("critical", CriticalLog, "CRITICAL"),
    ],
)
def test_log_methods_create_expected_log_type(
    logger: monitauditLogger,
    sink: MemorySink,
    method_name: str,
    expected_type: type[BaseLog],
    expected_level: str,
) -> None:
    method = getattr(
        logger,
        method_name,
    )

    log = method(
        "test message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(log, expected_type)
    assert log.level == expected_level
    assert log.message == "test message"
    assert log.module == "test_module"
    assert log.function == "test_function"

    assert sink.logs == [log]


@pytest.mark.parametrize(
    "method_name",
    [
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ],
)
def test_log_methods_preserve_common_fields(
    logger: monitauditLogger,
    method_name: str,
) -> None:
    method = getattr(
        logger,
        method_name,
    )

    log = method(
        "message",
        call_id="call-123",
        parent_call_id="parent-456",
        parameters={
            "number": 10,
            "text": "hello",
        },
        duration_ms=12.5,
        module="my.module",
        function="my_function",
        event="example",
        item_count=5,
    )

    assert log.message == "message"
    assert log.call_id == "call-123"
    assert log.parent_call_id == "parent-456"
    assert log.duration_ms == 12.5
    assert log.module == "my.module"
    assert log.function == "my_function"

    assert log.parameters == {
        "number": 10,
        "text": "hello",
    }

    assert log.attributes == {
        "event": "example",
        "item_count": 5,
    }


def test_logger_uses_context(
    logger: monitauditLogger,
    context: LogContext,
) -> None:
    log = logger.info(
        "context test",
        module="test_module",
        function="test_function",
    )

    assert log.context == context
    assert log.context.application == "monitaudit-test"
    assert log.context.environment == "dev"
    assert log.context.correlation_id == "correlation-123"
    assert log.context.run_id == "run-456"


def test_logger_writes_to_all_sinks(
    context: LogContext,
) -> None:
    sink_one = MemorySink()
    sink_two = MemorySink()

    logger = monitauditLogger(
        context,
        sink_one,
        sink_two,
    )

    log = logger.info(
        "multi sink",
        module="test_module",
        function="test_function",
    )

    assert sink_one.logs == [log]
    assert sink_two.logs == [log]


def test_logger_without_sinks_still_returns_log(
    context: LogContext,
) -> None:
    logger = monitauditLogger(context)

    log = logger.info(
        "no sinks",
        module="test_module",
        function="test_function",
    )

    assert isinstance(log, InfoLog)
    assert log.message == "no sinks"


def test_prepare_parameters_none_returns_empty_dict() -> None:
    result = monitauditLogger._prepare_parameters(
        None
    )

    assert result == {}


def test_prepare_parameters_empty_returns_empty_dict() -> None:
    result = monitauditLogger._prepare_parameters(
        {}
    )

    assert result == {}


def test_prepare_parameters_converts_values_to_json_safe() -> None:
    identifier = uuid4()

    result = monitauditLogger._prepare_parameters(
        {
            "path": Path("/tmp/example"),
            "uuid": identifier,
            "enum": ExampleEnum.FIRST,
            "items": {1, 2, 3},
            "object": ExampleObject(),
        }
    )

    assert result["path"] == "/tmp/example"
    assert result["uuid"] == str(identifier)
    assert result["enum"] == "first"
    assert sorted(result["items"]) == [1, 2, 3]
    assert result["object"] == "ExampleObject()"


def test_prepare_attributes_empty_returns_empty_dict() -> None:
    result = monitauditLogger._prepare_attributes(
        {}
    )

    assert result == {}


def test_prepare_attributes_converts_values_to_json_safe() -> None:
    identifier = uuid4()

    result = monitauditLogger._prepare_attributes(
        {
            "path": Path("/tmp/example"),
            "uuid": identifier,
            "enum": ExampleEnum.FIRST,
            "nested": {
                "path": Path("/nested"),
            },
        }
    )

    assert result == {
        "path": "/tmp/example",
        "uuid": str(identifier),
        "enum": "first",
        "nested": {
            "path": "/nested",
        },
    }


def test_prepare_attributes_supports_datetime() -> None:
    value = datetime(
        2026,
        10,
        23,
        12,
        30,
        15,
    )

    result = monitauditLogger._prepare_attributes(
        {
            "timestamp": value,
        }
    )

    assert result == {
        "timestamp": value.isoformat(),
    }


def test_serialize_exception_none() -> None:
    result = monitauditLogger._serialize_exception(
        None
    )

    assert result == (
        None,
        None,
        [],
    )


def test_serialize_exception() -> None:
    try:
        raise ValueError("something went wrong")

    except ValueError as exception:
        (
            error_type,
            error_message,
            traceback_lines,
        ) = monitauditLogger._serialize_exception(
            exception
        )

    assert error_type == "ValueError"
    assert error_message == "something went wrong"
    assert traceback_lines
    assert any(
        "ValueError: something went wrong" in line
        for line in traceback_lines
    )


def test_error_without_exception(
    logger: monitauditLogger,
) -> None:
    log = logger.error(
        "error without exception",
        module="test_module",
        function="test_function",
    )

    assert log.error_type is None
    assert log.error_message is None
    assert log.traceback == []


def test_error_with_exception(
    logger: monitauditLogger,
) -> None:
    try:
        raise ValueError("invalid value")

    except ValueError as exception:
        log = logger.error(
            "operation failed",
            exception=exception,
            module="test_module",
            function="test_function",
        )

    assert isinstance(log, ErrorLog)
    assert log.error_type == "ValueError"
    assert log.error_message == "invalid value"
    assert log.traceback

    traceback_text = "".join(log.traceback)

    assert "ValueError: invalid value" in traceback_text


def test_critical_without_exception(
    logger: monitauditLogger,
) -> None:
    log = logger.critical(
        "critical without exception",
        module="test_module",
        function="test_function",
    )

    assert log.error_type is None
    assert log.error_message is None
    assert log.traceback == []


def test_critical_with_exception(
    logger: monitauditLogger,
) -> None:
    try:
        raise RuntimeError("critical failure")

    except RuntimeError as exception:
        log = logger.critical(
            "system failure",
            exception=exception,
            module="test_module",
            function="test_function",
        )

    assert isinstance(log, CriticalLog)
    assert log.error_type == "RuntimeError"
    assert log.error_message == "critical failure"
    assert log.traceback

    traceback_text = "".join(log.traceback)

    assert "RuntimeError: critical failure" in traceback_text


def test_explicit_module_and_function_are_preserved(
    logger: monitauditLogger,
) -> None:
    log = logger.info(
        "location",
        module="custom.module",
        function="custom_function",
    )

    assert log.module == "custom.module"
    assert log.function == "custom_function"


def test_resolve_caller_with_explicit_values(
    logger: monitauditLogger,
) -> None:
    module, function = logger._resolve_caller(
        module="explicit.module",
        function="explicit_function",
    )

    assert module == "explicit.module"
    assert function == "explicit_function"


def test_resolve_caller_detects_missing_values(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        logger,
        "_caller",
        lambda: (
            "detected.module",
            "detected_function",
        ),
    )

    module, function = logger._resolve_caller(
        module=None,
        function=None,
    )

    assert module == "detected.module"
    assert function == "detected_function"


def test_resolve_caller_preserves_explicit_module(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        logger,
        "_caller",
        lambda: (
            "detected.module",
            "detected_function",
        ),
    )

    module, function = logger._resolve_caller(
        module="explicit.module",
        function=None,
    )

    assert module == "explicit.module"
    assert function == "detected_function"


def test_resolve_caller_preserves_explicit_function(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        logger,
        "_caller",
        lambda: (
            "detected.module",
            "detected_function",
        ),
    )

    module, function = logger._resolve_caller(
        module=None,
        function="explicit_function",
    )

    assert module == "detected.module"
    assert function == "explicit_function"


def test_caller_returns_calling_test_location(
    logger: monitauditLogger,
) -> None:
    module, function = logger._caller()

    assert module == __name__
    assert function == "test_caller_returns_calling_test_location"


def test_sink_failure_continue_mode_does_not_raise(
    context: LogContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    failing_sink = FailingSink(
        "write failed"
    )
    good_sink = MemorySink()

    logger = monitauditLogger(
        context,
        failing_sink,
        good_sink,
        sink_failure_mode="continue",
    )

    log = logger.info(
        "test failure isolation",
        module="test_module",
        function="test_function",
    )

    captured = capsys.readouterr()

    assert failing_sink.calls == 1

    assert good_sink.logs == [
        log
    ]

    assert (
        "monitaudit sink failure: "
        "FailingSink: "
        "RuntimeError: "
        "write failed"
    ) in captured.err


def test_failed_sink_does_not_prevent_later_sinks(
    context: LogContext,
) -> None:
    first_sink = MemorySink()
    failing_sink = FailingSink()
    last_sink = MemorySink()

    logger = monitauditLogger(
        context,
        first_sink,
        failing_sink,
        last_sink,
        sink_failure_mode="continue",
    )

    log = logger.info(
        "all sinks attempted",
        module="test_module",
        function="test_function",
    )

    assert first_sink.logs == [log]
    assert failing_sink.calls == 1
    assert last_sink.logs == [log]


def test_multiple_failing_sinks_continue_mode(
    context: LogContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = FailingSink("first failure")
    second = FailingSink("second failure")
    good_sink = MemorySink()

    logger = monitauditLogger(
        context,
        first,
        second,
        good_sink,
        sink_failure_mode="continue",
    )

    log = logger.warning(
        "multiple failures",
        module="test_module",
        function="test_function",
    )

    captured = capsys.readouterr()

    assert first.calls == 1
    assert second.calls == 1
    assert good_sink.logs == [log]

    assert "first failure" in captured.err
    assert "second failure" in captured.err


def test_sink_failure_raise_mode_raises_after_all_sinks_attempted(
    context: LogContext,
) -> None:
    failing_sink = FailingSink(
        "write failed"
    )
    good_sink = MemorySink()

    logger = monitauditLogger(
        context,
        failing_sink,
        good_sink,
        sink_failure_mode="raise",
    )

    with pytest.raises(
        RuntimeError,
        match=r"monitaudit sink failure\(s\): FailingSink",
    ) as error_info:
        logger.info(
            "raise test",
            module="test_module",
            function="test_function",
        )

    assert failing_sink.calls == 1

    assert len(good_sink.logs) == 1

    assert isinstance(
        error_info.value.__cause__,
        RuntimeError,
    )

    assert str(
        error_info.value.__cause__
    ) == "write failed"


def test_multiple_sink_failures_raise_mode_lists_all_sinks(
    context: LogContext,
) -> None:
    class FirstFailingSink(Sink):
        def write(self, log: BaseLog) -> None:
            raise ValueError("first")

    class SecondFailingSink(Sink):
        def write(self, log: BaseLog) -> None:
            raise OSError("second")

    good_sink = MemorySink()

    logger = monitauditLogger(
        context,
        FirstFailingSink(),
        good_sink,
        SecondFailingSink(),
        sink_failure_mode="raise",
    )

    with pytest.raises(
        RuntimeError,
    ) as error_info:
        logger.error(
            "multiple sink failures",
            module="test_module",
            function="test_function",
        )

    assert (
        str(error_info.value)
        == (
            "monitaudit sink failure(s): "
            "FirstFailingSink, SecondFailingSink"
        )
    )

    assert len(good_sink.logs) == 1

    assert isinstance(
        error_info.value.__cause__,
        ValueError,
    )


def test_report_sink_failure_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = FailingSink()

    exception = RuntimeError(
        "example failure"
    )

    monitauditLogger._report_sink_failure(
        sink=sink,
        exception=exception,
    )

    captured = capsys.readouterr()

    assert captured.out == ""

    assert (
        "monitaudit sink failure: "
        "FailingSink: "
        "RuntimeError: "
        "example failure"
    ) in captured.err


def test_attributes_are_forwarded_to_sink_as_json_safe_values(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    identifier = UUID(
        "12345678-1234-5678-1234-567812345678"
    )

    log = logger.info(
        "attributes",
        module="test_module",
        function="test_function",
        path=Path("/tmp/example"),
        identifier=identifier,
        values={1, 2, 3},
    )

    assert sink.logs == [log]

    assert log.attributes["path"] == "/tmp/example"

    assert (
        log.attributes["identifier"]
        == "12345678-1234-5678-1234-567812345678"
    )

    assert sorted(
        log.attributes["values"]
    ) == [1, 2, 3]


def test_parameters_are_forwarded_to_sink_as_json_safe_values(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.info(
        "parameters",
        module="test_module",
        function="test_function",
        parameters={
            "path": Path("/tmp/example"),
            "enum": ExampleEnum.FIRST,
            "nested": {
                "values": {1, 2},
            },
        },
    )

    assert sink.logs == [log]

    assert log.parameters == {
        "path": "/tmp/example",
        "enum": "first",
        "nested": {
            "values": [1, 2],
        },
    }


def test_write_passes_same_log_instance_to_every_sink(
    context: LogContext,
) -> None:
    first_sink = MemorySink()
    second_sink = MemorySink()

    logger = monitauditLogger(
        context,
        first_sink,
        second_sink,
    )

    log = logger.debug(
        "identity test",
        module="test_module",
        function="test_function",
    )

    assert first_sink.logs[0] is log
    assert second_sink.logs[0] is log