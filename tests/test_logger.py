# tests/test_logger.py

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from monitaudit.logger import (
    SinkFailureMode,
    monitauditLogger,
)
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
    """Sink that stores every received log record."""

    def __init__(self) -> None:
        self.logs: list[BaseLog] = []

    def write(
        self,
        log: BaseLog,
    ) -> None:
        self.logs.append(log)


class FailingSink(Sink):
    """Sink used to verify sink failure isolation."""

    def __init__(
        self,
        message: str = "sink failed",
    ) -> None:
        self.message = message
        self.calls = 0

    def write(
        self,
        log: BaseLog,
    ) -> None:
        self.calls += 1

        raise RuntimeError(
            self.message
        )


class ExampleEnum(Enum):
    FIRST = "first"


class ExampleObject:
    def __repr__(self) -> str:
        return "ExampleObject()"


class BrokenStringException(Exception):
    def __str__(self) -> str:
        raise RuntimeError(
            "broken exception string"
        )


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


def test_logger_stores_context(
    context: LogContext,
) -> None:
    logger = monitauditLogger(
        context
    )

    assert logger.context is context


def test_logger_stores_sinks_as_tuple(
    context: LogContext,
) -> None:
    first = MemorySink()
    second = MemorySink()

    logger = monitauditLogger(
        context,
        first,
        second,
    )

    assert logger.sinks == (
        first,
        second,
    )


def test_logger_defaults_to_continue_mode(
    context: LogContext,
) -> None:
    logger = monitauditLogger(
        context
    )

    assert (
        logger.sink_failure_mode
        == "continue"
    )


def test_invalid_context_raises_type_error() -> None:
    invalid_context = cast(
        LogContext,
        object(),
    )

    with pytest.raises(
        TypeError,
        match="context must be a LogContext instance",
    ):
        monitauditLogger(
            invalid_context
        )


def test_invalid_sink_raises_type_error(
    context: LogContext,
) -> None:
    invalid_sink = cast(
        Sink,
        object(),
    )

    with pytest.raises(
        TypeError,
        match="All sinks must inherit from Sink",
    ):
        monitauditLogger(
            context,
            invalid_sink,
        )


def test_invalid_sink_failure_mode_raises_value_error(
    context: LogContext,
) -> None:
    invalid_mode = cast(
        SinkFailureMode,
        "invalid",
    )

    with pytest.raises(
        ValueError,
        match="sink_failure_mode must be",
    ):
        monitauditLogger(
            context,
            sink_failure_mode=invalid_mode,
        )


def test_debug_creates_debug_log(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.debug(
        "debug message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        DebugLog,
    )

    assert log.level == "DEBUG"
    assert log.message == "debug message"
    assert sink.logs == [log]


def test_info_creates_info_log(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.info(
        "info message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        InfoLog,
    )

    assert log.level == "INFO"
    assert log.message == "info message"
    assert sink.logs == [log]


def test_warning_creates_warning_log(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.warning(
        "warning message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        WarningLog,
    )

    assert log.level == "WARNING"
    assert log.message == "warning message"
    assert sink.logs == [log]


def test_error_creates_error_log(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.error(
        "error message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        ErrorLog,
    )

    assert log.level == "ERROR"
    assert log.message == "error message"
    assert sink.logs == [log]


def test_critical_creates_critical_log(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.critical(
        "critical message",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        CriticalLog,
    )

    assert log.level == "CRITICAL"
    assert log.message == "critical message"
    assert sink.logs == [log]


def test_common_log_fields_are_preserved(
    logger: monitauditLogger,
) -> None:
    log = logger.info(
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

    assert (
        log.parent_call_id
        == "parent-456"
    )

    assert log.duration_ms == 12.5
    assert log.module == "my.module"

    assert (
        log.function
        == "my_function"
    )

    assert log.parameters == {
        "number": 10,
        "text": "hello",
    }

    assert log.attributes == {
        "event": "example",
        "item_count": 5,
    }


def test_logger_uses_original_context(
    logger: monitauditLogger,
    context: LogContext,
) -> None:
    log = logger.info(
        "context test",
        module="test_module",
        function="test_function",
    )

    assert log.context is context

    assert (
        log.context.application
        == "monitaudit-test"
    )

    assert (
        log.context.environment
        == "dev"
    )

    assert (
        log.context.correlation_id
        == "correlation-123"
    )

    assert (
        log.context.run_id
        == "run-456"
    )


def test_logger_writes_to_all_sinks(
    context: LogContext,
) -> None:
    first_sink = MemorySink()
    second_sink = MemorySink()

    logger = monitauditLogger(
        context,
        first_sink,
        second_sink,
    )

    log = logger.info(
        "multi sink",
        module="test_module",
        function="test_function",
    )

    assert first_sink.logs == [log]
    assert second_sink.logs == [log]


def test_logger_without_sinks_returns_log(
    context: LogContext,
) -> None:
    logger = monitauditLogger(
        context
    )

    log = logger.info(
        "no sinks",
        module="test_module",
        function="test_function",
    )

    assert isinstance(
        log,
        InfoLog,
    )

    assert log.message == "no sinks"


def test_same_log_instance_is_sent_to_every_sink(
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


def test_prepare_parameters_none_returns_empty_dict() -> None:
    result = (
        monitauditLogger._prepare_parameters(
            None
        )
    )

    assert result == {}


def test_prepare_parameters_empty_returns_empty_dict() -> None:
    result = (
        monitauditLogger._prepare_parameters(
            {}
        )
    )

    assert result == {}


def test_prepare_parameters_are_json_safe() -> None:
    identifier = uuid4()

    result = (
        monitauditLogger._prepare_parameters(
            {
                "path": Path(
                    "/tmp/example"
                ),
                "uuid": identifier,
                "enum": ExampleEnum.FIRST,
                "items": {
                    1,
                    2,
                    3,
                },
                "object": ExampleObject(),
            }
        )
    )

    assert (
        result["path"]
        == "/tmp/example"
    )

    assert (
        result["uuid"]
        == str(identifier)
    )

    assert (
        result["enum"]
        == "first"
    )

    items = result["items"]

    assert isinstance(
        items,
        list,
    )

    assert sorted(items) == [
        1,
        2,
        3,
    ]

    assert (
        result["object"]
        == "ExampleObject()"
    )


def test_prepare_parameters_does_not_reuse_input_dict() -> None:
    source: dict[str, Any] = {
        "value": "original",
    }

    result = (
        monitauditLogger._prepare_parameters(
            source
        )
    )

    assert result is not source

    assert result == {
        "value": "original",
    }


def test_prepare_attributes_empty_returns_empty_dict() -> None:
    result = (
        monitauditLogger._prepare_attributes(
            {}
        )
    )

    assert result == {}


def test_prepare_attributes_are_json_safe() -> None:
    identifier = uuid4()

    result = (
        monitauditLogger._prepare_attributes(
            {
                "path": Path(
                    "/tmp/example"
                ),
                "uuid": identifier,
                "enum": ExampleEnum.FIRST,
                "nested": {
                    "path": Path(
                        "/nested"
                    ),
                },
            }
        )
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

    result = (
        monitauditLogger._prepare_attributes(
            {
                "timestamp": value,
            }
        )
    )

    assert result == {
        "timestamp": value.isoformat(),
    }


def test_prepare_attributes_does_not_reuse_input_dict() -> None:
    source: dict[str, Any] = {
        "event": "example",
    }

    result = (
        monitauditLogger._prepare_attributes(
            source
        )
    )

    assert result is not source

    assert result == {
        "event": "example",
    }


def test_json_safe_attributes_are_forwarded_to_sink(
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
        path=Path(
            "/tmp/example"
        ),
        identifier=identifier,
        values={
            1,
            2,
            3,
        },
    )

    assert sink.logs == [log]

    assert (
        log.attributes["path"]
        == "/tmp/example"
    )

    assert (
        log.attributes["identifier"]
        == "12345678-1234-5678-1234-567812345678"
    )

    values = log.attributes["values"]

    assert isinstance(
        values,
        list,
    )

    assert sorted(values) == [
        1,
        2,
        3,
    ]


def test_json_safe_parameters_are_forwarded_to_sink(
    logger: monitauditLogger,
    sink: MemorySink,
) -> None:
    log = logger.info(
        "parameters",
        module="test_module",
        function="test_function",
        parameters={
            "path": Path(
                "/tmp/example"
            ),
            "enum": ExampleEnum.FIRST,
            "nested": {
                "values": {
                    1,
                    2,
                },
            },
        },
    )

    assert sink.logs == [log]

    assert (
        log.parameters["path"]
        == "/tmp/example"
    )

    assert (
        log.parameters["enum"]
        == "first"
    )

    nested_value = log.parameters[
        "nested"
    ]

    assert isinstance(
        nested_value,
        dict,
    )

    values = nested_value[
        "values"
    ]

    assert isinstance(
        values,
        list,
    )

    assert sorted(values) == [
        1,
        2,
    ]


def test_serialize_exception_none() -> None:
    result = (
        monitauditLogger._serialize_exception(
            None
        )
    )

    assert result == (
        None,
        None,
        [],
    )


def test_serialize_exception() -> None:
    try:
        raise ValueError(
            "something went wrong"
        )

    except ValueError as exception:
        result = (
            monitauditLogger._serialize_exception(
                exception
            )
        )

    (
        error_type,
        error_message,
        traceback_lines,
    ) = result

    assert error_type == "ValueError"

    assert (
        error_message
        == "something went wrong"
    )

    assert traceback_lines

    assert any(
        "ValueError: something went wrong"
        in line
        for line in traceback_lines
    )


def test_safe_exception_text() -> None:
    exception = ValueError(
        "invalid value"
    )

    result = (
        monitauditLogger._safe_exception_text(
            exception
        )
    )

    assert result == "invalid value"


def test_safe_exception_text_handles_broken_str() -> None:
    exception = BrokenStringException()

    result = (
        monitauditLogger._safe_exception_text(
            exception
        )
    )

    assert (
        result
        == "<exception message unavailable>"
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
        raise ValueError(
            "invalid value"
        )

    except ValueError as exception:
        log = logger.error(
            "operation failed",
            exception=exception,
            module="test_module",
            function="test_function",
        )

        assert log.error_type == "ValueError"

        assert (
            log.error_message
            == "invalid value"
        )

        assert log.traceback

        traceback_text = "".join(
            log.traceback
        )

        assert (
            "ValueError: invalid value"
            in traceback_text
        )


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
        raise RuntimeError(
            "critical failure"
        )

    except RuntimeError as exception:
        log = logger.critical(
            "system failure",
            exception=exception,
            module="test_module",
            function="test_function",
        )

        assert (
            log.error_type
            == "RuntimeError"
        )

        assert (
            log.error_message
            == "critical failure"
        )

        assert log.traceback

        traceback_text = "".join(
            log.traceback
        )

        assert (
            "RuntimeError: critical failure"
            in traceback_text
        )


def test_explicit_location_is_preserved(
    logger: monitauditLogger,
) -> None:
    log = logger.info(
        "location",
        module="custom.module",
        function="custom_function",
    )

    assert (
        log.module
        == "custom.module"
    )

    assert (
        log.function
        == "custom_function"
    )


def test_resolve_caller_with_explicit_values(
    logger: monitauditLogger,
) -> None:
    module, function = (
        logger._resolve_caller(
            module="explicit.module",
            function="explicit_function",
        )
    )

    assert module == "explicit.module"

    assert (
        function
        == "explicit_function"
    )


def test_resolve_caller_detects_missing_values(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_caller() -> tuple[
        str | None,
        str | None,
    ]:
        return (
            "detected.module",
            "detected_function",
        )

    monkeypatch.setattr(
        logger,
        "_caller",
        fake_caller,
    )

    module, function = (
        logger._resolve_caller(
            module=None,
            function=None,
        )
    )

    assert module == "detected.module"

    assert (
        function
        == "detected_function"
    )


def test_resolve_caller_preserves_explicit_module(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_caller() -> tuple[
        str | None,
        str | None,
    ]:
        return (
            "detected.module",
            "detected_function",
        )

    monkeypatch.setattr(
        logger,
        "_caller",
        fake_caller,
    )

    module, function = (
        logger._resolve_caller(
            module="explicit.module",
            function=None,
        )
    )

    assert module == "explicit.module"

    assert (
        function
        == "detected_function"
    )


def test_resolve_caller_preserves_explicit_function(
    logger: monitauditLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_caller() -> tuple[
        str | None,
        str | None,
    ]:
        return (
            "detected.module",
            "detected_function",
        )

    monkeypatch.setattr(
        logger,
        "_caller",
        fake_caller,
    )

    module, function = (
        logger._resolve_caller(
            module=None,
            function="explicit_function",
        )
    )

    assert module == "detected.module"

    assert (
        function
        == "explicit_function"
    )


def test_explicit_empty_location_is_preserved(
    logger: monitauditLogger,
) -> None:
    module, function = (
        logger._resolve_caller(
            module="",
            function="",
        )
    )

    assert module == ""
    assert function == ""


def test_caller_returns_calling_test_location() -> None:
    module, function = (
        monitauditLogger._caller()
    )

    assert module == __name__

    assert function == (
        "test_caller_returns_calling_test_location"
    )


def test_logger_module_is_internal() -> None:
    assert (
        monitauditLogger._is_internal_module(
            "monitaudit.logger"
        )
        is True
    )


def test_monitaudit_module_is_internal() -> None:
    assert (
        monitauditLogger._is_internal_module(
            "monitaudit.models.monitaudit"
        )
        is True
    )


def test_application_module_is_not_internal() -> None:
    assert (
        monitauditLogger._is_internal_module(
            "application.main"
        )
        is False
    )


def test_none_module_is_not_internal() -> None:
    assert (
        monitauditLogger._is_internal_module(
            None
        )
        is False
    )


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
        "failure isolation",
        module="test_module",
        function="test_function",
    )

    captured = capsys.readouterr()

    assert failing_sink.calls == 1
    assert good_sink.logs == [log]

    assert (
        "monitaudit sink failure: "
        "FailingSink: "
        "RuntimeError: "
        "write failed"
        in captured.err
    )


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
    first = FailingSink(
        "first failure"
    )

    second = FailingSink(
        "second failure"
    )

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

    assert (
        "first failure"
        in captured.err
    )

    assert (
        "second failure"
        in captured.err
    )


def test_sink_failure_raise_mode_raises_after_all_sinks(
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
        match=(
            r"monitaudit sink failure\(s\): "
            r"FailingSink"
        ),
    ) as error_info:
        logger.info(
            "raise test",
            module="test_module",
            function="test_function",
        )

    assert failing_sink.calls == 1

    # The healthy sink must still have been called.
    assert len(good_sink.logs) == 1

    cause = error_info.value.__cause__

    assert isinstance(
        cause,
        RuntimeError,
    )

    assert str(cause) == "write failed"


def test_multiple_sink_failures_raise_mode_lists_all_sinks(
    context: LogContext,
) -> None:
    class FirstFailingSink(Sink):
        def write(
            self,
            log: BaseLog,
        ) -> None:
            raise ValueError(
                "first"
            )

    class SecondFailingSink(Sink):
        def write(
            self,
            log: BaseLog,
        ) -> None:
            raise OSError(
                "second"
            )

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

    assert str(
        error_info.value
    ) == (
        "monitaudit sink failure(s): "
        "FirstFailingSink, SecondFailingSink"
    )

    assert len(
        good_sink.logs
    ) == 1

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
        in captured.err
    )


def test_report_sink_failure_handles_broken_exception_string(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = FailingSink()

    exception = BrokenStringException()

    monitauditLogger._report_sink_failure(
        sink=sink,
        exception=exception,
    )

    captured = capsys.readouterr()

    assert (
        "<exception message unavailable>"
        in captured.err
    )