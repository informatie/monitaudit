# tests/test_logger.py

from __future__ import annotations

import builtins
from typing import Any

import pytest

import monitaudit.logger as logger_module
from monitaudit.logger import (
    _INTERNAL_CALLER_MODULES,
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


class RecordingSink(Sink):
    """Sink that records every received log."""

    def __init__(self) -> None:
        self.logs: list[BaseLog] = []

    def write(self, log: BaseLog) -> None:
        self.logs.append(log)


class FailingSink(Sink):
    """Sink that records attempts and then raises an exception."""

    def __init__(
        self,
        exception: Exception | None = None,
    ) -> None:
        self.exception = exception or RuntimeError(
            "sink write failed"
        )
        self.logs: list[BaseLog] = []
        self.write_count = 0

    def write(self, log: BaseLog) -> None:
        self.write_count += 1
        self.logs.append(log)
        raise self.exception


class AnotherFailingSink(Sink):
    """Second failing sink used to verify failure aggregation."""

    def __init__(self) -> None:
        self.logs: list[BaseLog] = []
        self.write_count = 0

    def write(self, log: BaseLog) -> None:
        self.write_count += 1
        self.logs.append(log)
        raise ValueError("second sink failure")


class FaultyStringException(Exception):
    """Exception whose string conversion fails."""

    def __str__(self) -> str:
        raise RuntimeError("broken exception __str__")


@pytest.fixture
def context() -> LogContext:
    """
    Create a minimal valid LogContext without depending on its required
    application-specific fields.

    LogContext validation is tested in its own model test file. These tests
    focus on logger behaviour.
    """

    model_construct = getattr(
        LogContext,
        "model_construct",
        None,
    )

    if callable(model_construct):
        return model_construct()

    construct = getattr(
        LogContext,
        "construct",
        None,
    )

    if callable(construct):
        return construct()

    return object.__new__(LogContext)


@pytest.fixture
def recording_sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def logger(
    context: LogContext,
    recording_sink: RecordingSink,
) -> monitauditLogger:
    return monitauditLogger(
        context,
        recording_sink,
    )


def raise_value_error() -> None:
    raise ValueError("invalid value")


def capture_exception() -> ValueError:
    try:
        raise_value_error()
    except ValueError as exception:
        return exception

    raise AssertionError("Expected ValueError was not raised")


class TestInitialisation:
    def test_initialises_with_context_and_no_sinks(
        self,
        context: LogContext,
    ) -> None:
        logger = monitauditLogger(context)

        assert logger.context is context
        assert logger.sinks == ()
        assert logger.sink_failure_mode == "continue"

    def test_initialises_with_one_sink(
        self,
        context: LogContext,
        recording_sink: RecordingSink,
    ) -> None:
        logger = monitauditLogger(
            context,
            recording_sink,
        )

        assert logger.context is context
        assert logger.sinks == (recording_sink,)
        assert logger.sink_failure_mode == "continue"

    def test_initialises_with_multiple_sinks(
        self,
        context: LogContext,
    ) -> None:
        first_sink = RecordingSink()
        second_sink = RecordingSink()

        logger = monitauditLogger(
            context,
            first_sink,
            second_sink,
            sink_failure_mode="raise",
        )

        assert logger.sinks == (
            first_sink,
            second_sink,
        )
        assert logger.sink_failure_mode == "raise"

    @pytest.mark.parametrize(
        "invalid_context",
        [
            None,
            object(),
            {},
            "context",
            123,
        ],
    )
    def DJ_test_rejects_invalid_context(
        self,
        invalid_context: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "context must be a LogContext instance; "
                "received"
            ),
        ):
            monitauditLogger(  # type: ignore[arg-type]
                invalid_context
            )

    def DJ_test_context_error_identifies_received_type(
        self,
    ) -> None:
        with pytest.raises(TypeError) as exception_info:
            monitauditLogger("invalid")  # type: ignore[arg-type]

        assert (
            str(exception_info.value)
            == (
                "context must be a LogContext instance; "
                "received str."
            )
        )

    @pytest.mark.parametrize(
        "invalid_sink",
        [
            None,
            object(),
            {},
            "sink",
            123,
        ],
    )
    def DJ_test_rejects_invalid_sink(
        self,
        context: LogContext,
        invalid_sink: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="All sinks must inherit from Sink",
        ):
            monitauditLogger(  # type: ignore[arg-type]
                context,
                invalid_sink,
            )

    def DJ_test_sink_error_identifies_received_type(
        self,
        context: LogContext,
    ) -> None:
        with pytest.raises(TypeError) as exception_info:
            monitauditLogger(  # type: ignore[arg-type]
                context,
                "invalid",
            )

        assert (
            str(exception_info.value)
            == (
                "All sinks must inherit from Sink; "
                "received str."
            )
        )

    @pytest.mark.parametrize(
        "sink_failure_mode",
        [
            "",
            "CONTINUE",
            "RAISE",
            "ignore",
            "fail",
            None,
            1,
        ],
    )
    def test_rejects_invalid_sink_failure_mode(
        self,
        context: LogContext,
        sink_failure_mode: object,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "sink_failure_mode must be "
                "'continue' or 'raise'"
            ),
        ):
            monitauditLogger(
                context,
                sink_failure_mode=sink_failure_mode,  # type: ignore[arg-type]
            )

    def test_sink_failure_mode_error_includes_value(
        self,
        context: LogContext,
    ) -> None:
        with pytest.raises(ValueError) as exception_info:
            monitauditLogger(
                context,
                sink_failure_mode="invalid",  # type: ignore[arg-type]
            )

        assert (
            str(exception_info.value)
            == (
                "sink_failure_mode must be "
                "'continue' or 'raise'; "
                "received 'invalid'."
            )
        )

    @pytest.mark.parametrize(
        "sink_failure_mode",
        [
            "continue",
            "raise",
        ],
    )
    def test_accepts_supported_sink_failure_modes(
        self,
        context: LogContext,
        sink_failure_mode: str,
    ) -> None:
        logger = monitauditLogger(
            context,
            sink_failure_mode=sink_failure_mode,  # type: ignore[arg-type]
        )

        assert logger.sink_failure_mode == sink_failure_mode


class TestStandardLogging:
    @pytest.mark.parametrize(
        ("method_name", "expected_type"),
        [
            ("debug", DebugLog),
            ("info", InfoLog),
            ("warning", WarningLog),
        ],
    )
    def test_returns_expected_log_type(
        self,
        logger: monitauditLogger,
        recording_sink: RecordingSink,
        method_name: str,
        expected_type: type[BaseLog],
    ) -> None:
        method = getattr(logger, method_name)

        result = method(
            "test message",
            module="tests.module",
            function="test_function",
        )

        assert isinstance(result, expected_type)
        assert recording_sink.logs == [result]

    @pytest.mark.parametrize(
        ("method_name", "expected_type"),
        [
            ("debug", DebugLog),
            ("info", InfoLog),
            ("warning", WarningLog),
        ],
    )
    def test_populates_common_fields(
        self,
        logger: monitauditLogger,
        recording_sink: RecordingSink,
        method_name: str,
        expected_type: type[BaseLog],
    ) -> None:
        method = getattr(logger, method_name)

        result = method(
            "structured message",
            call_id="call-123",
            parent_call_id="parent-456",
            parameters={
                "count": 12,
                "enabled": True,
            },
            duration_ms=125.5,
            module="sample.module",
            function="sample_function",
            customer_id=1001,
            batch="nightly",
        )

        assert isinstance(result, expected_type)
        assert result.message == "structured message"
        assert result.context is logger.context
        assert result.call_id == "call-123"
        assert result.parent_call_id == "parent-456"
        assert result.parameters == {
            "count": 12,
            "enabled": True,
        }
        assert result.duration_ms == 125.5
        assert result.module == "sample.module"
        assert result.function == "sample_function"
        assert result.attributes == {
            "customer_id": 1001,
            "batch": "nightly",
        }
        assert recording_sink.logs == [result]

    @pytest.mark.parametrize(
        "method_name",
        [
            "debug",
            "info",
            "warning",
        ],
    )
    def test_uses_empty_mappings_when_data_is_omitted(
        self,
        logger: monitauditLogger,
        method_name: str,
    ) -> None:
        method = getattr(logger, method_name)

        result = method(
            "message",
            module="module",
            function="function",
        )

        assert result.parameters == {}
        assert result.attributes == {}

    def test_log_without_sinks_returns_log(
        self,
        context: LogContext,
    ) -> None:
        logger = monitauditLogger(context)

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert isinstance(result, InfoLog)
        assert result.message == "message"

    def test_each_log_is_written_once_to_each_sink(
        self,
        context: LogContext,
    ) -> None:
        first_sink = RecordingSink()
        second_sink = RecordingSink()

        logger = monitauditLogger(
            context,
            first_sink,
            second_sink,
        )

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert first_sink.logs == [result]
        assert second_sink.logs == [result]
        assert first_sink.logs[0] is second_sink.logs[0]


class TestExceptionLogging:
    @pytest.mark.parametrize(
        ("method_name", "expected_type"),
        [
            ("error", ErrorLog),
            ("critical", CriticalLog),
        ],
    )
    def test_returns_expected_exception_log_type(
        self,
        logger: monitauditLogger,
        recording_sink: RecordingSink,
        method_name: str,
        expected_type: type[BaseLog],
    ) -> None:
        method = getattr(logger, method_name)

        result = method(
            "operation failed",
            module="tests.module",
            function="test_function",
        )

        assert isinstance(result, expected_type)
        assert recording_sink.logs == [result]

    @pytest.mark.parametrize(
        ("method_name", "expected_type"),
        [
            ("error", ErrorLog),
            ("critical", CriticalLog),
        ],
    )
    def test_populates_exception_fields(
        self,
        logger: monitauditLogger,
        method_name: str,
        expected_type: type[BaseLog],
    ) -> None:
        exception = capture_exception()
        method = getattr(logger, method_name)

        result = method(
            "operation failed",
            exception=exception,
            call_id="call-1",
            parent_call_id="parent-1",
            parameters={"record_id": 10},
            duration_ms=55.25,
            module="sample.module",
            function="process_record",
            recoverable=False,
        )

        assert isinstance(result, expected_type)
        assert result.message == "operation failed"
        assert result.call_id == "call-1"
        assert result.parent_call_id == "parent-1"
        assert result.parameters == {"record_id": 10}
        assert result.duration_ms == 55.25
        assert result.module == "sample.module"
        assert result.function == "process_record"
        assert result.attributes == {"recoverable": False}
        assert result.error_type == "ValueError"
        assert result.error_message == "invalid value"
        assert result.traceback
        assert any(
            "ValueError: invalid value" in line
            for line in result.traceback
        )
        assert any(
            "raise_value_error" in line
            for line in result.traceback
        )

    @pytest.mark.parametrize(
        "method_name",
        [
            "error",
            "critical",
        ],
    )
    def test_supports_missing_exception(
        self,
        logger: monitauditLogger,
        method_name: str,
    ) -> None:
        method = getattr(logger, method_name)

        result = method(
            "failure without exception",
            module="module",
            function="function",
        )

        assert result.error_type is None
        assert result.error_message is None
        assert result.traceback == []

    @pytest.mark.parametrize(
        "method_name",
        [
            "error",
            "critical",
        ],
    )
    def test_handles_exception_with_faulty_string_conversion(
        self,
        logger: monitauditLogger,
        method_name: str,
    ) -> None:
        exception = FaultyStringException()
        method = getattr(logger, method_name)

        result = method(
            "failure",
            exception=exception,
            module="module",
            function="function",
        )

        assert result.error_type == "FaultyStringException"
        assert (
            result.error_message
            == "<exception message unavailable>"
        )
        assert isinstance(result.traceback, list)

    def test_serialize_exception_without_traceback(
        self,
    ) -> None:
        exception = ValueError("not raised")

        error_type, error_message, traceback_lines = (
            monitauditLogger._serialize_exception(exception)
        )

        assert error_type == "ValueError"
        assert error_message == "not raised"
        assert traceback_lines
        assert any(
            "ValueError: not raised" in line
            for line in traceback_lines
        )

    def test_serialize_exception_falls_back_when_formatter_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exception = ValueError("formatter failed")

        def fail_format_exception(
            *_args: object,
            **_kwargs: object,
        ) -> list:
            raise RuntimeError("formatting failed")

        monkeypatch.setattr(
            logger_module.traceback,
            "format_exception",
            fail_format_exception,
        )

        error_type, error_message, traceback_lines = (
            monitauditLogger._serialize_exception(exception)
        )

        assert error_type == "ValueError"
        assert error_message == "formatter failed"
        assert traceback_lines == [
            "ValueError: formatter failed\n"
        ]

    def test_raw_exception_is_not_stored_in_log(
        self,
        logger: monitauditLogger,
    ) -> None:
        exception = ValueError("sensitive exception")

        result = logger.error(
            "operation failed",
            exception=exception,
            module="module",
            function="function",
        )

        values = vars(result)

        assert all(
            value is not exception
            for value in values.values()
        )


class TestParameterPreparation:
    @pytest.mark.parametrize(
        "parameters",
        [
            None,
            {},
        ],
    )
    def test_empty_parameters_return_new_empty_mapping(
        self,
        parameters: dict[str, Any] | None,
    ) -> None:
        result = monitauditLogger._prepare_parameters(
            parameters
        )

        assert result == {}
        assert result is not parameters

    def test_parameters_are_processed_with_json_safe_dict(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        received: list[dict[str, Any]] = []

        def fake_json_safe_dict(
            value: dict[str, Any],
        ) -> dict[str, Any]:
            received.append(value)
            return {"converted": True}

        monkeypatch.setattr(
            logger_module,
            "json_safe_dict",
            fake_json_safe_dict,
        )

        parameters = {"value": object()}

        result = monitauditLogger._prepare_parameters(
            parameters
        )

        assert result == {"converted": True}
        assert received == [parameters]
        assert received[0] is not parameters

    def test_prepared_parameters_are_independent_from_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def identity_json_safe_dict(
            value: dict[str, Any],
        ) -> dict[str, Any]:
            return value

        monkeypatch.setattr(
            logger_module,
            "json_safe_dict",
            identity_json_safe_dict,
        )

        parameters = {"value": 10}

        result = monitauditLogger._prepare_parameters(
            parameters
        )

        assert result == parameters
        assert result is not parameters

        result["value"] = 20

        assert parameters == {"value": 10}


class TestAttributePreparation:
    def test_empty_attributes_return_new_empty_mapping(
        self,
    ) -> None:
        attributes: dict[str, Any] = {}

        result = monitauditLogger._prepare_attributes(
            attributes
        )

        assert result == {}
        assert result is not attributes

    def test_attributes_are_processed_with_json_safe_dict(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        received: list[dict[str, Any]] = []

        def fake_json_safe_dict(
            value: dict[str, Any],
        ) -> dict[str, Any]:
            received.append(value)
            return {"converted": "yes"}

        monkeypatch.setattr(
            logger_module,
            "json_safe_dict",
            fake_json_safe_dict,
        )

        attributes = {"value": object()}

        result = monitauditLogger._prepare_attributes(
            attributes
        )

        assert result == {"converted": "yes"}
        assert received == [attributes]
        assert received[0] is not attributes

    def test_prepared_attributes_are_independent_from_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def identity_json_safe_dict(
            value: dict[str, Any],
        ) -> dict[str, Any]:
            return value

        monkeypatch.setattr(
            logger_module,
            "json_safe_dict",
            identity_json_safe_dict,
        )

        attributes = {"value": 10}

        result = monitauditLogger._prepare_attributes(
            attributes
        )

        assert result == attributes
        assert result is not attributes

        result["value"] = 20

        assert attributes == {"value": 10}


class TestSafeExceptionText:
    def test_returns_exception_message(
        self,
    ) -> None:
        result = monitauditLogger._safe_exception_text(
            ValueError("invalid value")
        )

        assert result == "invalid value"

    def test_returns_fallback_when_exception_string_fails(
        self,
    ) -> None:
        result = monitauditLogger._safe_exception_text(
            FaultyStringException()
        )

        assert result == "<exception message unavailable>"


class TestExceptionSerialisation:
    def test_none_returns_empty_error_fields(
        self,
    ) -> None:
        result = monitauditLogger._serialize_exception(
            None
        )

        assert result == (
            None,
            None,
            [],
        )

    def test_serialises_exception_type_and_message(
        self,
    ) -> None:
        exception = RuntimeError("runtime failed")

        (
            error_type,
            error_message,
            traceback_lines,
        ) = monitauditLogger._serialize_exception(
            exception
        )

        assert error_type == "RuntimeError"
        assert error_message == "runtime failed"
        assert isinstance(traceback_lines, list)

    def test_serialises_raised_exception_traceback(
        self,
    ) -> None:
        exception = capture_exception()

        (
            error_type,
            error_message,
            traceback_lines,
        ) = monitauditLogger._serialize_exception(
            exception
        )

        assert error_type == "ValueError"
        assert error_message == "invalid value"
        assert traceback_lines
        assert any(
            "raise_value_error" in line
            for line in traceback_lines
        )
        assert any(
            "ValueError: invalid value" in line
            for line in traceback_lines
        )


class TestSinkWriting:
    def test_continue_mode_writes_to_all_sinks(
        self,
        context: LogContext,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        first_sink = RecordingSink()
        failing_sink = FailingSink(
            ValueError("write unavailable")
        )
        final_sink = RecordingSink()

        logger = monitauditLogger(
            context,
            first_sink,
            failing_sink,
            final_sink,
            sink_failure_mode="continue",
        )

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert first_sink.logs == [result]
        assert failing_sink.logs == [result]
        assert failing_sink.write_count == 1
        assert final_sink.logs == [result]

        captured = capsys.readouterr()

        assert captured.out == ""
        assert (
            "monitaudit sink failure: "
            "FailingSink: ValueError: "
            "write unavailable"
        ) in captured.err

    def test_continue_mode_does_not_raise(
        self,
        context: LogContext,
    ) -> None:
        failing_sink = FailingSink()

        logger = monitauditLogger(
            context,
            failing_sink,
            sink_failure_mode="continue",
        )

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert isinstance(result, InfoLog)
        assert failing_sink.write_count == 1

    def test_raise_mode_attempts_all_sinks_before_raising(
        self,
        context: LogContext,
    ) -> None:
        first_failing_sink = FailingSink(
            ValueError("first failure")
        )
        successful_sink = RecordingSink()
        second_failing_sink = AnotherFailingSink()

        logger = monitauditLogger(
            context,
            first_failing_sink,
            successful_sink,
            second_failing_sink,
            sink_failure_mode="raise",
        )

        with pytest.raises(RuntimeError) as exception_info:
            logger.info(
                "message",
                module="module",
                function="function",
            )

        assert first_failing_sink.write_count == 1
        assert len(successful_sink.logs) == 1
        assert second_failing_sink.write_count == 1

        assert (
            str(exception_info.value)
            == (
                "monitaudit sink failure(s): "
                "FailingSink, AnotherFailingSink"
            )
        )

    def test_raise_mode_chains_first_sink_exception(
        self,
        context: LogContext,
    ) -> None:
        first_exception = ValueError("first failure")
        second_exception = RuntimeError("second failure")

        first_sink = FailingSink(first_exception)
        second_sink = FailingSink(second_exception)

        logger = monitauditLogger(
            context,
            first_sink,
            second_sink,
            sink_failure_mode="raise",
        )

        with pytest.raises(RuntimeError) as exception_info:
            logger.info(
                "message",
                module="module",
                function="function",
            )

        assert exception_info.value.__cause__ is first_exception

    def test_raise_mode_does_not_raise_when_all_sinks_succeed(
        self,
        context: LogContext,
    ) -> None:
        first_sink = RecordingSink()
        second_sink = RecordingSink()

        logger = monitauditLogger(
            context,
            first_sink,
            second_sink,
            sink_failure_mode="raise",
        )

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert first_sink.logs == [result]
        assert second_sink.logs == [result]

    def test_repeated_sink_instance_is_called_repeatedly(
        self,
        context: LogContext,
    ) -> None:
        sink = RecordingSink()

        logger = monitauditLogger(
            context,
            sink,
            sink,
        )

        result = logger.info(
            "message",
            module="module",
            function="function",
        )

        assert sink.logs == [
            result,
            result,
        ]


class TestSinkFailureReporting:
    def test_reports_sink_name_exception_type_and_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = FailingSink()
        exception = ValueError("cannot write")

        monitauditLogger._report_sink_failure(
            sink=sink,
            exception=exception,
        )

        captured = capsys.readouterr()

        assert captured.out == ""
        assert (
            captured.err
            == (
                "monitaudit sink failure: "
                "FailingSink: "
                "ValueError: "
                "cannot write\n"
            )
        )

    def test_handles_exception_with_faulty_string_conversion(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = FailingSink()

        monitauditLogger._report_sink_failure(
            sink=sink,
            exception=FaultyStringException(),
        )

        captured = capsys.readouterr()

        assert (
            "<exception message unavailable>"
            in captured.err
        )

    def test_reporting_failure_never_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def broken_print(
            *_args: object,
            **_kwargs: object,
        ) -> None:
            raise RuntimeError("stderr unavailable")

        monkeypatch.setattr(
            builtins,
            "print",
            broken_print,
        )

        monitauditLogger._report_sink_failure(
            sink=FailingSink(),
            exception=ValueError("write failed"),
        )

    def test_reporting_does_not_use_logger_sinks(
        self,
        context: LogContext,
    ) -> None:
        failing_sink = FailingSink()

        logger = monitauditLogger(
            context,
            failing_sink,
            sink_failure_mode="continue",
        )

        logger.info(
            "message",
            module="module",
            function="function",
        )

        assert failing_sink.write_count == 1


class TestCallerResolution:
    def test_preserves_explicit_module_and_function(
        self,
        logger: monitauditLogger,
    ) -> None:
        result = logger._resolve_caller(
            module="explicit.module",
            function="explicit_function",
        )

        assert result == (
            "explicit.module",
            "explicit_function",
        )

    def test_preserves_explicit_empty_strings(
        self,
        logger: monitauditLogger,
    ) -> None:
        result = logger._resolve_caller(
            module="",
            function="",
        )

        assert result == (
            "",
            "",
        )

    def test_does_not_call_caller_when_both_values_are_explicit(
        self,
        logger: monitauditLogger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fail_caller() -> tuple[str | None, str | None]:
            raise AssertionError("_caller must not be called")

        monkeypatch.setattr(
            logger,
            "_caller",
            fail_caller,
        )

        result = logger._resolve_caller(
            module="module",
            function="function",
        )

        assert result == (
            "module",
            "function",
        )

    def test_detects_both_missing_values(
        self,
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

        result = logger._resolve_caller(
            module=None,
            function=None,
        )

        assert result == (
            "detected.module",
            "detected_function",
        )

    def test_detects_only_missing_module(
        self,
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

        result = logger._resolve_caller(
            module=None,
            function="explicit_function",
        )

        assert result == (
            "detected.module",
            "explicit_function",
        )

    def test_detects_only_missing_function(
        self,
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

        result = logger._resolve_caller(
            module="explicit.module",
            function=None,
        )

        assert result == (
            "explicit.module",
            "detected_function",
        )

    def test_public_log_method_detects_external_caller(
        self,
        logger: monitauditLogger,
    ) -> None:
        result = logger.info("message")

        assert result.module == __name__
        assert (
            result.function
            == (
                "test_public_log_method_"
                "detects_external_caller"
            )
        )

    def test_explicit_location_is_used_by_public_method(
        self,
        logger: monitauditLogger,
    ) -> None:
        result = logger.info(
            "message",
            module="",
            function="",
        )

        assert result.module == ""
        assert result.function == ""


class TestCallerInspection:
    def test_caller_returns_external_test_frame(
        self,
    ) -> None:
        module, function = monitauditLogger._caller()

        assert module == __name__
        assert function == "test_caller_returns_external_test_frame"

    def test_caller_returns_none_when_current_frame_is_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            logger_module.inspect,
            "currentframe",
            lambda: None,
        )

        result = monitauditLogger._caller()

        assert result == (
            None,
            None,
        )

    def test_caller_handles_non_string_module_name(
        self,
    ) -> None:
        original_name = globals().get("__name__")

        try:
            globals()["__name__"] = 123

            module, function = monitauditLogger._caller()

            assert module is None
            assert (
                function
                == "test_caller_handles_non_string_module_name"
            )

        finally:
            globals()["__name__"] = original_name


class TestInternalModuleDetection:
    @pytest.mark.parametrize(
        "module",
        sorted(_INTERNAL_CALLER_MODULES),
    )
    def test_known_internal_modules_are_internal(
        self,
        module: str,
    ) -> None:
        assert (
            monitauditLogger._is_internal_module(module)
            is True
        )

    @pytest.mark.parametrize(
        "module",
        [
            None,
            "",
            "__main__",
            "tests.test_logger",
            "monitaudit",
            "monitaudit.logger.extra",
            "monitaudit.models",
        ],
    )
    def test_other_modules_are_not_internal(
        self,
        module: str | None,
    ) -> None:
        assert (
            monitauditLogger._is_internal_module(module)
            is False
        )

    def test_internal_module_collection_is_immutable(
        self,
    ) -> None:
        assert isinstance(
            _INTERNAL_CALLER_MODULES,
            frozenset,
        )

        with pytest.raises(AttributeError):
            _INTERNAL_CALLER_MODULES.add(  # type: ignore[attr-defined]
                "another.module"
            )


class TestPrivateLoggingHelpers:
    def test_log_creates_and_writes_standard_log(
        self,
        logger: monitauditLogger,
        recording_sink: RecordingSink,
    ) -> None:
        result = logger._log(
            InfoLog,
            "message",
            call_id="call",
            parent_call_id="parent",
            parameters={"value": 1},
            duration_ms=10.0,
            module="module",
            function="function",
            attributes={"attribute": "value"},
        )

        assert isinstance(result, InfoLog)
        assert result.message == "message"
        assert result.call_id == "call"
        assert result.parent_call_id == "parent"
        assert result.parameters == {"value": 1}
        assert result.duration_ms == 10.0
        assert result.module == "module"
        assert result.function == "function"
        assert result.attributes == {
            "attribute": "value"
        }
        assert recording_sink.logs == [result]

    def test_log_exception_creates_and_writes_exception_log(
        self,
        logger: monitauditLogger,
        recording_sink: RecordingSink,
    ) -> None:
        exception = capture_exception()

        result = logger._log_exception(
            ErrorLog,
            "failed",
            exception=exception,
            call_id="call",
            parent_call_id="parent",
            parameters={"value": 1},
            duration_ms=10.0,
            module="module",
            function="function",
            attributes={"attribute": "value"},
        )

        assert isinstance(result, ErrorLog)
        assert result.error_type == "ValueError"
        assert result.error_message == "invalid value"
        assert result.traceback
        assert recording_sink.logs == [result]

    def test_log_prepares_parameters_and_attributes(
        self,
        logger: monitauditLogger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        prepared_parameters = {"prepared_parameter": True}
        prepared_attributes = {"prepared_attribute": True}

        monkeypatch.setattr(
            logger,
            "_prepare_parameters",
            lambda _value: prepared_parameters,
        )
        monkeypatch.setattr(
            logger,
            "_prepare_attributes",
            lambda _value: prepared_attributes,
        )

        result = logger._log(
            DebugLog,
            "message",
            call_id=None,
            parent_call_id=None,
            parameters={"original": "parameter"},
            duration_ms=None,
            module="module",
            function="function",
            attributes={"original": "attribute"},
        )

        assert result.parameters == prepared_parameters
        assert result.attributes == prepared_attributes

    def test_log_exception_prepares_parameters_and_attributes(
        self,
        logger: monitauditLogger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        prepared_parameters = {"prepared_parameter": True}
        prepared_attributes = {"prepared_attribute": True}

        monkeypatch.setattr(
            logger,
            "_prepare_parameters",
            lambda _value: prepared_parameters,
        )
        monkeypatch.setattr(
            logger,
            "_prepare_attributes",
            lambda _value: prepared_attributes,
        )

        result = logger._log_exception(
            CriticalLog,
            "message",
            exception=None,
            call_id=None,
            parent_call_id=None,
            parameters={"original": "parameter"},
            duration_ms=None,
            module="module",
            function="function",
            attributes={"original": "attribute"},
        )

        assert result.parameters == prepared_parameters
        assert result.attributes == prepared_attributes


class TestPublicMethodDelegation:
    @pytest.mark.parametrize(
        ("method_name", "expected_log_type"),
        [
            ("debug", DebugLog),
            ("info", InfoLog),
            ("warning", WarningLog),
        ],
    )
    def test_standard_method_delegates_to_log(
        self,
        logger: monitauditLogger,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        expected_log_type: type[BaseLog],
    ) -> None:
        captured: dict[str, Any] = {}
        sentinel = object()

        def fake_log(
            log_type: object,
            message: str,
            **kwargs: Any,
        ) -> object:
            captured["log_type"] = log_type
            captured["message"] = message
            captured.update(kwargs)
            return sentinel

        monkeypatch.setattr(
            logger,
            "_log",
            fake_log,
        )

        method = getattr(logger, method_name)

        result = method(
            "message",
            call_id="call",
            parent_call_id="parent",
            parameters={"value": 1},
            duration_ms=10.5,
            module="module",
            function="function",
            custom="attribute",
        )

        assert result is sentinel
        assert captured == {
            "log_type": expected_log_type,
            "message": "message",
            "call_id": "call",
            "parent_call_id": "parent",
            "parameters": {"value": 1},
            "duration_ms": 10.5,
            "module": "module",
            "function": "function",
            "attributes": {
                "custom": "attribute",
            },
        }

    @pytest.mark.parametrize(
        ("method_name", "expected_log_type"),
        [
            ("error", ErrorLog),
            ("critical", CriticalLog),
        ],
    )
    def test_exception_method_delegates_to_log_exception(
        self,
        logger: monitauditLogger,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        expected_log_type: type[BaseLog],
    ) -> None:
        captured: dict[str, Any] = {}
        sentinel = object()
        exception = ValueError("failure")

        def fake_log_exception(
            log_type: object,
            message: str,
            **kwargs: Any,
        ) -> object:
            captured["log_type"] = log_type
            captured["message"] = message
            captured.update(kwargs)
            return sentinel

        monkeypatch.setattr(
            logger,
            "_log_exception",
            fake_log_exception,
        )

        method = getattr(logger, method_name)

        result = method(
            "message",
            exception=exception,
            call_id="call",
            parent_call_id="parent",
            parameters={"value": 1},
            duration_ms=10.5,
            module="module",
            function="function",
            custom="attribute",
        )

        assert result is sentinel
        assert captured == {
            "log_type": expected_log_type,
            "message": "message",
            "exception": exception,
            "call_id": "call",
            "parent_call_id": "parent",
            "parameters": {"value": 1},
            "duration_ms": 10.5,
            "module": "module",
            "function": "function",
            "attributes": {
                "custom": "attribute",
            },
        }