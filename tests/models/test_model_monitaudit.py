# tests/models/test_monitaudit.py

from __future__ import annotations

import importlib
from typing import Any, cast

import pytest

monitaudit_module = importlib.import_module(
    "monitaudit.models.monitaudit"
)

from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)
from monitaudit.models.log import (
    CriticalLog,
    DebugLog,
    ErrorLog,
    InfoLog,
    WarningLog,
)
from monitaudit.models.monitaudit import (
    Monitaudit,
    _current_call_id,
)


class FakeLogger:
    def __init__(
        self,
        context: object,
        *sinks: object,
        sink_failure_mode: str = "continue",
    ) -> None:
        self.context = context
        self.sinks = sinks
        self.sink_failure_mode = sink_failure_mode

        self.debug_calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.info_calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.warning_calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.error_calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.critical_calls: list[
            tuple[str, dict[str, Any]]
        ] = []

        self.debug_result = cast(
            DebugLog,
            object(),
        )
        self.info_result = cast(
            InfoLog,
            object(),
        )
        self.warning_result = cast(
            WarningLog,
            object(),
        )
        self.error_result = cast(
            ErrorLog,
            object(),
        )
        self.critical_result = cast(
            CriticalLog,
            object(),
        )

    def debug(
        self,
        message: str,
        **kwargs: Any,
    ) -> DebugLog:
        self.debug_calls.append(
            (
                message,
                dict(kwargs),
            )
        )
        return self.debug_result

    def info(
        self,
        message: str,
        **kwargs: Any,
    ) -> InfoLog:
        self.info_calls.append(
            (
                message,
                dict(kwargs),
            )
        )
        return self.info_result

    def warning(
        self,
        message: str,
        **kwargs: Any,
    ) -> WarningLog:
        self.warning_calls.append(
            (
                message,
                dict(kwargs),
            )
        )
        return self.warning_result

    def error(
        self,
        message: str,
        **kwargs: Any,
    ) -> ErrorLog:
        self.error_calls.append(
            (
                message,
                dict(kwargs),
            )
        )
        return self.error_result

    def critical(
        self,
        message: str,
        **kwargs: Any,
    ) -> CriticalLog:
        self.critical_calls.append(
            (
                message,
                dict(kwargs),
            )
        )
        return self.critical_result


@pytest.fixture(autouse=True)
def reset_current_call_id() -> None:
    token = _current_call_id.set(
        None
    )

    try:
        yield
    finally:
        _current_call_id.reset(
            token
        )


@pytest.fixture
def fake_logger_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> list[FakeLogger]:
    instances: list[FakeLogger] = []

    def create_logger(
        context: object,
        *sinks: object,
        sink_failure_mode: str = "continue",
    ) -> FakeLogger:
        logger = FakeLogger(
            context,
            *sinks,
            sink_failure_mode=sink_failure_mode,
        )
        instances.append(logger)
        return logger

    monkeypatch.setattr(
        monitaudit_module,
        "monitauditLogger",
        create_logger,
    )

    return instances


def build_test_monitaudit(
    fake_logger_factory: list[FakeLogger],
    **kwargs: Any,
) -> tuple[Monitaudit, FakeLogger]:
    values: dict[str, Any] = {
        "application": "test-application",
        "environment": "dev",
    }
    values.update(kwargs)

    audit = Monitaudit(
        **values
    )

    assert len(
        fake_logger_factory
    ) == 1

    return (
        audit,
        fake_logger_factory[0],
    )


class TestConstruction:
    def test_constructs_context(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        assert (
            audit.context.application
            == "test-application"
        )
        assert (
            audit.context.environment
            == "dev"
        )
        assert audit.context.run_id is None
        assert audit.context.attributes == {}

    def test_generates_correlation_id(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        assert isinstance(
            audit.correlation_id,
            str,
        )
        assert audit.correlation_id

    def test_preserves_explicit_correlation_id(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            correlation_id="correlation-123",
        )

        assert (
            audit.correlation_id
            == "correlation-123"
        )

    def test_preserves_run_id(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            run_id="run-123",
        )

        assert audit.run_id == "run-123"

    def test_copies_context_attributes(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        attributes = {
            "region": "eu",
        }

        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            context_attributes=attributes,
        )

        assert (
            audit.context.attributes
            == attributes
        )
        assert (
            audit.context.attributes
            is not attributes
        )

    def test_context_attributes_are_independent(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        attributes = {
            "region": "eu",
        }

        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            context_attributes=attributes,
        )

        attributes["region"] = "us"

        assert (
            audit.context.attributes[
                "region"
            ]
            == "eu"
        )

    def test_default_options(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        assert audit.timer is True
        assert audit.parameters is True
        assert (
            audit.max_parameter_length
            == 1000
        )

    def test_custom_options(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=False,
            max_parameter_length=250,
        )

        assert audit.timer is False
        assert audit.parameters is False
        assert (
            audit.max_parameter_length
            == 250
        )

    def test_rejects_negative_parameter_length(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        with pytest.raises(
            ValueError
        ) as exception_info:
            Monitaudit(
                "test-application",
                "dev",
                max_parameter_length=-1,
            )

        assert (
            str(exception_info.value)
            == (
                "max_parameter_length must "
                "be 0 or greater."
            )
        )
        assert fake_logger_factory == []

    def test_zero_parameter_length_is_allowed(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            max_parameter_length=0,
        )

        assert (
            audit.max_parameter_length
            == 0
        )

    def test_constructs_logger_with_context(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
        )

        assert logger.context is audit.context
        assert audit.logger is logger

    def test_passes_sinks_to_logger(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        first_sink = object()
        second_sink = object()

        audit = Monitaudit(
            "test-application",
            "dev",
            first_sink,  # type: ignore[arg-type]
            second_sink,  # type: ignore[arg-type]
        )

        logger = fake_logger_factory[0]

        assert audit.logger is logger
        assert logger.sinks == (
            first_sink,
            second_sink,
        )

    def test_passes_sink_failure_mode(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        _, logger = build_test_monitaudit(
            fake_logger_factory,
            sink_failure_mode="raise",
        )

        assert (
            logger.sink_failure_mode
            == "raise"
        )


class TestProperties:
    def test_correlation_id_delegates_to_context(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            correlation_id="correlation-1",
        )

        assert (
            audit.correlation_id
            == audit.context.correlation_id
        )

    def test_run_id_delegates_to_context(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            run_id="run-1",
        )

        assert (
            audit.run_id
            == audit.context.run_id
        )

    def test_current_call_id_defaults_to_none(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        assert (
            audit.current_call_id
            is None
        )

    def test_current_call_id_reads_context_variable(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        token = _current_call_id.set(
            "call-123"
        )

        try:
            assert (
                audit.current_call_id
                == "call-123"
            )
        finally:
            _current_call_id.reset(
                token
            )


class TestDirectLogging:
    @pytest.mark.parametrize(
        (
            "method_name",
            "calls_attribute",
            "result_attribute",
        ),
        [
            (
                "debug",
                "debug_calls",
                "debug_result",
            ),
            (
                "info",
                "info_calls",
                "info_result",
            ),
            (
                "warning",
                "warning_calls",
                "warning_result",
            ),
        ],
    )
    def test_standard_method_delegation(
        self,
        fake_logger_factory: list[FakeLogger],
        method_name: str,
        calls_attribute: str,
        result_attribute: str,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
        )

        token = _current_call_id.set(
            "active-call"
        )

        try:
            method = getattr(
                audit,
                method_name,
            )

            result = method(
                "test message",
                customer_id=42,
            )
        finally:
            _current_call_id.reset(
                token
            )

        calls = getattr(
            logger,
            calls_attribute,
        )

        assert calls == [
            (
                "test message",
                {
                    "call_id": "active-call",
                    "customer_id": 42,
                },
            )
        ]

        assert result is getattr(
            logger,
            result_attribute,
        )

    @pytest.mark.parametrize(
        (
            "method_name",
            "calls_attribute",
            "result_attribute",
        ),
        [
            (
                "error",
                "error_calls",
                "error_result",
            ),
            (
                "critical",
                "critical_calls",
                "critical_result",
            ),
        ],
    )
    def test_exception_method_delegation(
        self,
        fake_logger_factory: list[FakeLogger],
        method_name: str,
        calls_attribute: str,
        result_attribute: str,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
        )

        exception = ValueError(
            "failure"
        )

        token = _current_call_id.set(
            "active-call"
        )

        try:
            method = getattr(
                audit,
                method_name,
            )

            result = method(
                "operation failed",
                exception=exception,
                record_id=10,
            )
        finally:
            _current_call_id.reset(
                token
            )

        calls = getattr(
            logger,
            calls_attribute,
        )

        assert calls == [
            (
                "operation failed",
                {
                    "exception": exception,
                    "call_id": "active-call",
                    "record_id": 10,
                },
            )
        ]

        assert result is getattr(
            logger,
            result_attribute,
        )


class TestDuration:
    def test_none_start_returns_none(
        self,
    ) -> None:
        assert (
            Monitaudit._duration_ms(
                None
            )
            is None
        )

    def test_calculates_milliseconds(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            monitaudit_module,
            "perf_counter",
            lambda: 10.125678,
        )

        result = Monitaudit._duration_ms(
            10.0
        )

        assert result == 125.678

    def test_rounds_to_three_decimal_places(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            monitaudit_module,
            "perf_counter",
            lambda: 1.1234567,
        )

        result = Monitaudit._duration_ms(
            1.0
        )

        assert result == 123.457

    def test_zero_duration(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            monitaudit_module,
            "perf_counter",
            lambda: 5.0,
        )

        assert (
            Monitaudit._duration_ms(
                5.0
            )
            == 0.0
        )


class TestSuccessfulTrace:
    def test_trace_returns_function_result(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def add(
            first: int,
            second: int,
        ) -> int:
            return first + second

        assert add(
            2,
            3,
        ) == 5

    def test_trace_emits_start_and_end(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process(
            value: int,
        ) -> int:
            return value * 2

        result = process(5)

        assert result == 10
        assert logger.error_calls == []
        assert len(logger.info_calls) == 2

        start_message, start_fields = (
            logger.info_calls[0]
        )
        end_message, end_fields = (
            logger.info_calls[1]
        )

        assert (
            start_message
            == "process started"
        )
        assert (
            start_fields["event"]
            == FUNCTION_START
        )
        assert (
            end_message
            == "process completed"
        )
        assert (
            end_fields["event"]
            == FUNCTION_END
        )

        assert (
            start_fields["call_id"]
            == "call-1"
        )
        assert (
            end_fields["call_id"]
            == "call-1"
        )
        assert (
            start_fields[
                "parent_call_id"
            ]
            is None
        )
        assert (
            end_fields[
                "parent_call_id"
            ]
            is None
        )
        assert (
            end_fields["duration_ms"]
            is None
        )

    def test_trace_uses_function_metadata(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process_record() -> None:
            pass

        process_record()

        for _, fields in logger.info_calls:
            assert (
                fields["module"]
                == __name__
            )
            assert (
                fields["function"]
                == "process_record"
            )

    def test_trace_sets_current_call_id_inside_function(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        observed: list[str | None] = []

        @audit.trace
        def process() -> None:
            observed.append(
                audit.current_call_id
            )

        process()

        assert observed == [
            "call-1",
        ]

    def test_trace_restores_current_call_id_after_success(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process() -> None:
            assert (
                audit.current_call_id
                == "call-1"
            )

        process()

        assert (
            audit.current_call_id
            is None
        )


class TestTraceTiming:
    def test_timer_records_duration(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=True,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        values = iter(
            [
                10.0,
                10.125,
            ]
        )

        monkeypatch.setattr(
            monitaudit_module,
            "perf_counter",
            lambda: next(values),
        )

        @audit.trace
        def process() -> None:
            pass

        process()

        _, end_fields = (
            logger.info_calls[1]
        )

        assert (
            end_fields["duration_ms"]
            == 125.0
        )

    def test_disabled_timer_does_not_call_perf_counter(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        monkeypatch.setattr(
            monitaudit_module,
            "perf_counter",
            lambda: pytest.fail(
                "perf_counter must not be called"
            ),
        )

        @audit.trace
        def process() -> None:
            pass

        process()

        _, end_fields = (
            logger.info_calls[1]
        )

        assert (
            end_fields["duration_ms"]
            is None
        )


class TestFailingTrace:
    def test_reraises_original_exception(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        expected = ValueError(
            "invalid value"
        )

        @audit.trace
        def process() -> None:
            raise expected

        with pytest.raises(
            ValueError
        ) as exception_info:
            process()

        assert (
            exception_info.value
            is expected
        )

    def test_emits_start_and_error(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        expected = RuntimeError(
            "failure"
        )

        @audit.trace
        def process() -> None:
            raise expected

        with pytest.raises(
            RuntimeError
        ):
            process()

        assert len(logger.info_calls) == 1
        assert len(logger.error_calls) == 1

        start_message, start_fields = (
            logger.info_calls[0]
        )
        error_message, error_fields = (
            logger.error_calls[0]
        )

        assert (
            start_message
            == "process started"
        )
        assert (
            start_fields["event"]
            == FUNCTION_START
        )
        assert (
            error_message
            == "process failed"
        )
        assert (
            error_fields["event"]
            == FUNCTION_ERROR
        )
        assert (
            error_fields["exception"]
            is expected
        )
        assert (
            error_fields["call_id"]
            == "call-1"
        )
        assert (
            error_fields["duration_ms"]
            is None
        )

    def test_does_not_emit_end_on_failure(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process() -> None:
            raise ValueError(
                "failure"
            )

        with pytest.raises(
            ValueError
        ):
            process()

        assert [
            fields["event"]
            for _, fields
            in logger.info_calls
        ] == [
            FUNCTION_START,
        ]

    def test_restores_call_id_after_failure(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process() -> None:
            raise ValueError(
                "failure"
            )

        with pytest.raises(
            ValueError
        ):
            process()

        assert (
            audit.current_call_id
            is None
        )


class TestParameterCapture:
    def test_captures_arguments_and_defaults(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=True,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process(
            customer_id: int,
            region: str = "eu",
        ) -> None:
            pass

        process(42)

        expected = {
            "customer_id": 42,
            "region": "eu",
        }

        assert (
            logger.info_calls[0][1][
                "parameters"
            ]
            == expected
        )
        assert (
            logger.info_calls[1][1][
                "parameters"
            ]
            == expected
        )

    def test_parameters_disabled_skips_capture_pipeline(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        monkeypatch.setattr(
            monitaudit_module,
            "redact_parameters",
            lambda _value: pytest.fail(
                "redaction must not run"
            ),
        )

        @audit.trace
        def process(
            password: str,
        ) -> None:
            pass

        process("secret")

        assert (
            logger.info_calls[0][1][
                "parameters"
            ]
            == {}
        )
        assert (
            logger.info_calls[1][1][
                "parameters"
            ]
            == {}
        )

    def test_parameter_pipeline_order(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            max_parameter_length=25,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        calls: list[
            tuple[str, Any]
        ] = []

        def fake_redact(
            values: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append(
                (
                    "redact",
                    values,
                )
            )
            return {
                "redacted": True,
            }

        def fake_json_safe(
            values: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append(
                (
                    "json_safe",
                    values,
                )
            )
            return {
                "safe": True,
            }

        def fake_limit(
            values: dict[str, Any],
            max_length: int,
        ) -> dict[str, Any]:
            calls.append(
                (
                    "limit",
                    (
                        values,
                        max_length,
                    ),
                )
            )
            return {
                "limited": True,
            }

        monkeypatch.setattr(
            monitaudit_module,
            "redact_parameters",
            fake_redact,
        )
        monkeypatch.setattr(
            monitaudit_module,
            "json_safe_dict",
            fake_json_safe,
        )
        monkeypatch.setattr(
            monitaudit_module,
            "limit_parameters",
            fake_limit,
        )

        @audit.trace
        def process(
            value: str,
        ) -> None:
            pass

        process("original")

        assert calls == [
            (
                "redact",
                {
                    "value": "original",
                },
            ),
            (
                "json_safe",
                {
                    "redacted": True,
                },
            ),
            (
                "limit",
                (
                    {
                        "safe": True,
                    },
                    25,
                ),
            ),
        ]

        assert (
            logger.info_calls[0][1][
                "parameters"
            ]
            == {
                "limited": True,
            }
        )

    def test_sensitive_parameters_are_redacted(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def authenticate(
            username: str,
            password: str,
        ) -> None:
            pass

        authenticate(
            "dirk",
            "secret",
        )

        captured = (
            logger.info_calls[0][1][
                "parameters"
            ]
        )

        assert captured == {
            "username": "dirk",
            "password": "***",
        }

    def test_long_parameters_are_limited(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            max_parameter_length=20,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process(
            value: str,
        ) -> None:
            pass

        process(
            "abcdefghijklmnopqrstuvwxyz"
        )

        captured = (
            logger.info_calls[0][1][
                "parameters"
            ]
        )

        assert (
            captured["value"]
            .endswith(
                "...<truncated>"
            )
        )


class TestNestedTracing:
    def test_nested_calls_use_parent_call_id(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=False,
        )

        identifiers = iter(
            [
                "outer-call",
                "inner-call",
            ]
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: next(
                identifiers
            ),
        )

        @audit.trace
        def inner() -> None:
            assert (
                audit.current_call_id
                == "inner-call"
            )

        @audit.trace
        def outer() -> None:
            assert (
                audit.current_call_id
                == "outer-call"
            )
            inner()
            assert (
                audit.current_call_id
                == "outer-call"
            )

        outer()

        start_calls = {
            message: fields
            for message, fields
            in logger.info_calls
            if fields["event"]
            == FUNCTION_START
        }

        assert (
            start_calls[
                "outer started"
            ]["parent_call_id"]
            is None
        )
        assert (
            start_calls[
                "inner started"
            ]["parent_call_id"]
            == "outer-call"
        )

        assert (
            audit.current_call_id
            is None
        )

    def test_multiple_sequential_calls_get_different_ids(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=False,
        )

        identifiers = iter(
            [
                "call-1",
                "call-2",
            ]
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: next(
                identifiers
            ),
        )

        @audit.trace
        def process() -> None:
            pass

        process()
        process()

        start_ids = [
            fields["call_id"]
            for _, fields
            in logger.info_calls
            if fields["event"]
            == FUNCTION_START
        ]

        assert start_ids == [
            "call-1",
            "call-2",
        ]


class TestDecoratorMetadata:
    def test_preserves_function_name(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        def process() -> None:
            pass

        wrapped = audit.trace(
            process
        )

        assert (
            wrapped.__name__
            == "process"
        )

    def test_preserves_docstring(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        def process() -> None:
            """Process records."""

        wrapped = audit.trace(
            process
        )

        assert (
            wrapped.__doc__
            == "Process records."
        )

    def test_preserves_wrapped_reference(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, _ = build_test_monitaudit(
            fake_logger_factory,
        )

        def process() -> None:
            pass

        wrapped = audit.trace(
            process
        )

        assert (
            wrapped.__wrapped__
            is process
        )


class TestFailureIsolation:
    def test_start_logging_failure_restores_context(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        expected = RuntimeError(
            "start logging failed"
        )

        def failing_info(
            _message: str,
            **_kwargs: Any,
        ) -> InfoLog:
            raise expected

        logger.info = failing_info

        executed = False

        @audit.trace
        def process() -> None:
            nonlocal executed
            executed = True

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            process()

        assert (
            exception_info.value
            is expected
        )
        assert executed is False
        assert (
            audit.current_call_id
            is None
        )

    def test_end_logging_failure_restores_context(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        expected = RuntimeError(
            "end logging failed"
        )
        calls = 0

        def conditional_info(
            _message: str,
            **_kwargs: Any,
        ) -> InfoLog:
            nonlocal calls
            calls += 1

            if calls == 2:
                raise expected

            return logger.info_result

        logger.info = conditional_info

        @audit.trace
        def process() -> str:
            return "completed"

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            process()

        assert (
            exception_info.value
            is expected
        )
        assert (
            audit.current_call_id
            is None
        )

    def test_error_logging_failure_replaces_function_exception_but_restores_context(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        logging_error = RuntimeError(
            "error logging failed"
        )

        def failing_error(
            _message: str,
            **_kwargs: Any,
        ) -> ErrorLog:
            raise logging_error

        logger.error = failing_error

        @audit.trace
        def process() -> None:
            raise ValueError(
                "function failed"
            )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            process()

        assert (
            exception_info.value
            is logging_error
        )
        assert (
            audit.current_call_id
            is None
        )


class TestBindingFailures:
    def test_invalid_arguments_fail_before_call_id_is_set(
        self,
        fake_logger_factory: list[FakeLogger],
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            parameters=True,
        )

        @audit.trace
        def process(
            value: int,
        ) -> None:
            pass

        with pytest.raises(
            TypeError
        ):
            process()  # type: ignore[call-arg]

        assert (
            audit.current_call_id
            is None
        )
        assert logger.info_calls == []
        assert logger.error_calls == []

    def test_parameters_disabled_leaves_argument_error_to_function_call(
        self,
        fake_logger_factory: list[FakeLogger],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        audit, logger = build_test_monitaudit(
            fake_logger_factory,
            timer=False,
            parameters=False,
        )

        monkeypatch.setattr(
            monitaudit_module,
            "uuid4",
            lambda: "call-1",
        )

        @audit.trace
        def process(
            value: int,
        ) -> None:
            pass

        with pytest.raises(
            TypeError
        ):
            process()  # type: ignore[call-arg]

        assert len(logger.info_calls) == 1
        assert len(logger.error_calls) == 1
        assert (
            logger.error_calls[0][1][
                "event"
            ]
            == FUNCTION_ERROR
        )
        assert (
            audit.current_call_id
            is None
        )