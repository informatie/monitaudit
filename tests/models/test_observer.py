from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

import monitaudit.models.monitaudit as monitaudit_module
from monitaudit.models.monitaudit import Observability
from monitaudit.sinks.base import Sink


class MemorySink(Sink):
    def __init__(self) -> None:
        self.logs: list[object] = []

    def write(self, log: object) -> None:
        self.logs.append(log)  # type: ignore[arg-type]


@pytest.fixture
def sink() -> MemorySink:
    return MemorySink()


@pytest.fixture
def monitaudit(
    sink: MemorySink,
) -> Observability:
    return Observability(
        "monitaudit-test",
        "dev",
        sink,
        correlation_id="correlation-123",
        run_id="run-456",
    )


def test_constructor_creates_context(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        correlation_id="correlation-123",
        run_id="run-456",
        context_attributes={
            "team": "platform",
        },
    )

    assert monitaudit.context.application == "monitaudit-test"
    assert monitaudit.context.environment == "dev"

    assert (
        monitaudit.context.correlation_id
        == "correlation-123"
    )

    assert monitaudit.context.run_id == "run-456"

    assert monitaudit.context.attributes == {
        "team": "platform",
    }


def test_constructor_generates_correlation_id_when_missing(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
    )

    assert monitaudit.correlation_id
    assert isinstance(
        monitaudit.correlation_id,
        str,
    )


def test_constructor_defaults(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
    )

    assert monitaudit.timer is True
    assert monitaudit.parameters is True
    assert monitaudit.max_parameter_length == 1000


def test_constructor_custom_settings(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        timer=False,
        parameters=False,
        max_parameter_length=500,
    )

    assert monitaudit.timer is False
    assert monitaudit.parameters is False
    assert monitaudit.max_parameter_length == 500


def test_sink_failure_mode_is_forwarded_to_logger(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        sink_failure_mode="raise",
    )

    assert (
        monitaudit.logger.sink_failure_mode
        == "raise"
    )


def test_correlation_id_property(
    monitaudit: Observability,
) -> None:
    assert (
        monitaudit.correlation_id
        == "correlation-123"
    )


def test_run_id_property(
    monitaudit: Observability,
) -> None:
    assert monitaudit.run_id == "run-456"


def test_current_call_id_is_none_outside_trace(
    monitaudit: Observability,
) -> None:
    assert monitaudit.current_call_id is None


@pytest.mark.parametrize(
    ("method_name", "level"),
    [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
    ],
)
def test_direct_logging_methods(
    monitaudit: Observability,
    sink: MemorySink,
    method_name: str,
    level: str,
) -> None:
    method = getattr(
        monitaudit,
        method_name,
    )

    log = method(
        "test message",
        event="custom",
        count=2,
    )

    assert log.level == level
    assert log.message == "test message"
    assert log.call_id is None

    assert log.attributes == {
        "event": "custom",
        "count": 2,
    }

    assert sink.logs[-1] is log


def test_direct_error_logging(
    monitaudit: Observability,
) -> None:
    exception = ValueError(
        "invalid value"
    )

    log = monitaudit.error(
        "failed",
        exception=exception,
        event="custom",
    )

    assert log.level == "ERROR"
    assert log.message == "failed"
    assert log.error_type == "ValueError"
    assert log.error_message == "invalid value"

    assert log.attributes == {
        "event": "custom",
    }


def test_direct_critical_logging(
    monitaudit: Observability,
) -> None:
    exception = RuntimeError(
        "critical failure"
    )

    log = monitaudit.critical(
        "failed",
        exception=exception,
    )

    assert log.level == "CRITICAL"
    assert log.error_type == "RuntimeError"

    assert (
        log.error_message
        == "critical failure"
    )


def test_direct_log_inside_trace_uses_current_call_id(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    captured_call_id: str | None = None

    @monitaudit.trace
    def operation() -> None:
        nonlocal captured_call_id

        captured_call_id = (
            monitaudit.current_call_id
        )

        monitaudit.info(
            "inside operation"
        )

    operation()

    assert captured_call_id is not None

    inside_log = next(
        log
        for log in sink.logs
        if log.message == "inside operation"
    )

    assert (
        inside_log.call_id
        == captured_call_id
    )


def test_duration_none_returns_none() -> None:
    assert (
        Observability._duration_ms(None)
        is None
    )


def test_duration_calculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        monitaudit_module,
        "perf_counter",
        MagicMock(
            return_value=10.125456,
        ),
    )

    result = Observability._duration_ms(
        10.0
    )

    assert result == 125.456


def test_trace_returns_function_result(
    monitaudit: Observability,
) -> None:
    @monitaudit.trace
    def add(
        first: int,
        second: int,
    ) -> int:
        return first + second

    assert add(2, 3) == 5


def test_trace_preserves_function_metadata(
    monitaudit: Observability,
) -> None:
    @monitaudit.trace
    def example() -> None:
        """Example documentation."""

    assert example.__name__ == "example"

    assert example.__doc__ == (
        "Example documentation."
    )


def test_trace_writes_start_and_end_logs(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> str:
        return "done"

    result = operation()

    assert result == "done"
    assert len(sink.logs) == 2

    start = sink.logs[0]
    end = sink.logs[1]

    assert start.level == "INFO"
    assert start.message == "operation started"

    assert start.attributes["event"] == (
        "function_start"
    )

    assert end.level == "INFO"

    assert (
        end.message
        == "operation completed"
    )

    assert end.attributes["event"] == (
        "function_end"
    )


def test_trace_start_and_end_share_call_id(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        pass

    operation()

    start = sink.logs[0]
    end = sink.logs[1]

    assert start.call_id is not None
    assert start.call_id == end.call_id


def test_root_trace_has_no_parent_call_id(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        pass

    operation()

    assert sink.logs[0].parent_call_id is None
    assert sink.logs[1].parent_call_id is None


def test_trace_sets_module_and_function(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        pass

    operation()

    for log in sink.logs:
        assert log.module == __name__
        assert log.function == "operation"


def test_trace_captures_parameters(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation(
        name: str,
        count: int,
    ) -> None:
        pass

    operation(
        "monitaudit",
        42,
    )

    expected = {
        "name": "monitaudit",
        "count": 42,
    }

    assert sink.logs[0].parameters == expected
    assert sink.logs[1].parameters == expected


def test_trace_applies_default_parameters(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation(
        name: str = "monitaudit",
        count: int = 42,
    ) -> None:
        pass

    operation()

    assert sink.logs[0].parameters == {
        "name": "monitaudit",
        "count": 42,
    }


def test_trace_can_disable_parameters(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        parameters=False,
    )

    @monitaudit.trace
    def operation(
        password: str,
        value: str,
    ) -> None:
        pass

    operation(
        "secret",
        "visible",
    )

    assert sink.logs[0].parameters == {}
    assert sink.logs[1].parameters == {}


def test_trace_redacts_sensitive_parameters(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation(
        username: str,
        password: str,
        api_key: str,
    ) -> None:
        pass

    operation(
        username="alice",
        password="super-secret",
        api_key="secret-key",
    )

    parameters = sink.logs[0].parameters

    assert parameters == {
        "username": "alice",
        "password": "***",
        "api_key": "***",
    }


def test_trace_redacts_nested_sensitive_parameters(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation(
        config: dict[str, object],
    ) -> None:
        pass

    operation(
        {
            "username": "alice",
            "password": "secret",
            "nested": {
                "token": "secret-token",
            },
        }
    )

    parameters = sink.logs[0].parameters

    assert parameters == {
        "config": {
            "username": "alice",
            "password": "***",
            "nested": {
                "token": "***",
            },
        },
    }


def test_trace_converts_parameters_to_json_safe_values(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation(
        path: Path,
        values: set[int],
    ) -> None:
        pass

    operation(
        Path("/tmp/example"),
        {1, 2, 3},
    )

    parameters = sink.logs[0].parameters

    assert parameters["path"] == (
        "/tmp/example"
    )

    assert sorted(
        parameters["values"]
    ) == [
        1,
        2,
        3,
    ]


def test_trace_limits_long_parameters(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        max_parameter_length=20,
    )

    @monitaudit.trace
    def operation(
        value: str,
    ) -> None:
        pass

    operation(
        "abcdefghijklmnopqrstuvwxyz"
    )

    value = sink.logs[0].parameters[
        "value"
    ]

    assert len(value) == 20

    assert value.endswith(
        "...<truncated>"
    )


def test_trace_records_duration_when_enabled(
    sink: MemorySink,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        timer=True,
    )

    counter = iter(
        [
            10.0,
            10.125,
        ]
    )

    monkeypatch.setattr(
        monitaudit_module,
        "perf_counter",
        lambda: next(counter),
    )

    @monitaudit.trace
    def operation() -> None:
        pass

    operation()

    assert sink.logs[0].duration_ms is None
    assert sink.logs[1].duration_ms == 125.0


def test_trace_duration_disabled(
    sink: MemorySink,
) -> None:
    monitaudit = Observability(
        "monitaudit-test",
        "dev",
        sink,
        timer=False,
    )

    @monitaudit.trace
    def operation() -> None:
        pass

    operation()

    assert sink.logs[0].duration_ms is None
    assert sink.logs[1].duration_ms is None


def test_trace_failure_logs_error(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        raise ValueError(
            "operation failed"
        )

    with pytest.raises(
        ValueError,
        match="operation failed",
    ):
        operation()

    assert len(sink.logs) == 2

    start = sink.logs[0]
    error = sink.logs[1]

    assert start.attributes["event"] == (
        "function_start"
    )

    assert error.level == "ERROR"

    assert (
        error.message
        == "operation failed"
    )

    assert error.attributes["event"] == (
        "function_error"
    )

    assert error.error_type == "ValueError"

    assert (
        error.error_message
        == "operation failed"
    )

    assert error.traceback


def test_trace_failure_preserves_original_exception(
    monitaudit: Observability,
) -> None:
    exception = ValueError(
        "original error"
    )

    @monitaudit.trace
    def operation() -> None:
        raise exception

    with pytest.raises(
        ValueError,
    ) as error_info:
        operation()

    assert error_info.value is exception


def test_trace_failure_uses_same_call_id(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        raise RuntimeError(
            "failed"
        )

    with pytest.raises(RuntimeError):
        operation()

    assert (
        sink.logs[0].call_id
        == sink.logs[1].call_id
    )


def test_trace_restores_call_id_after_success(
    monitaudit: Observability,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        assert (
            monitaudit.current_call_id
            is not None
        )

    operation()

    assert monitaudit.current_call_id is None


def test_trace_restores_call_id_after_failure(
    monitaudit: Observability,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        assert (
            monitaudit.current_call_id
            is not None
        )

        raise ValueError("failed")

    with pytest.raises(ValueError):
        operation()

    assert monitaudit.current_call_id is None


def test_nested_trace_parent_child_relationship(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def child() -> None:
        pass

    @monitaudit.trace
    def parent() -> None:
        child()

    parent()

    assert len(sink.logs) == 4

    parent_start = sink.logs[0]
    child_start = sink.logs[1]
    child_end = sink.logs[2]
    parent_end = sink.logs[3]

    assert parent_start.call_id is not None
    assert child_start.call_id is not None

    assert (
        child_start.parent_call_id
        == parent_start.call_id
    )

    assert (
        child_end.parent_call_id
        == parent_start.call_id
    )

    assert (
        child_start.call_id
        == child_end.call_id
    )

    assert (
        parent_start.call_id
        == parent_end.call_id
    )

    assert parent_start.parent_call_id is None
    assert parent_end.parent_call_id is None


def test_nested_trace_restores_parent_call_id(
    monitaudit: Observability,
) -> None:
    parent_id: str | None = None
    after_child_id: str | None = None

    @monitaudit.trace
    def child() -> None:
        assert (
            monitaudit.current_call_id
            is not None
        )

    @monitaudit.trace
    def parent() -> None:
        nonlocal parent_id
        nonlocal after_child_id

        parent_id = monitaudit.current_call_id

        child()

        after_child_id = (
            monitaudit.current_call_id
        )

    parent()

    assert parent_id is not None

    assert (
        after_child_id
        == parent_id
    )

    assert monitaudit.current_call_id is None


def test_nested_trace_restores_parent_after_child_failure(
    monitaudit: Observability,
) -> None:
    parent_id: str | None = None
    restored_id: str | None = None

    @monitaudit.trace
    def child() -> None:
        raise ValueError(
            "child failed"
        )

    @monitaudit.trace
    def parent() -> None:
        nonlocal parent_id
        nonlocal restored_id

        parent_id = monitaudit.current_call_id

        try:
            child()
        except ValueError:
            restored_id = (
                monitaudit.current_call_id
            )

    parent()

    assert parent_id is not None

    assert restored_id == parent_id

    assert monitaudit.current_call_id is None


def test_each_root_trace_gets_unique_call_id(
    monitaudit: Observability,
    sink: MemorySink,
) -> None:
    @monitaudit.trace
    def operation() -> None:
        pass

    operation()
    first_call_id = sink.logs[0].call_id

    sink.logs.clear()

    operation()
    second_call_id = sink.logs[0].call_id

    assert first_call_id is not None
    assert second_call_id is not None

    assert (
        first_call_id
        != second_call_id
    )


def test_wrapper_preserves_signature(
    monitaudit: Observability,
) -> None:
    import inspect

    def operation(
        first: int,
        second: str = "test",
    ) -> str:
        return f"{first}:{second}"

    wrapped = monitaudit.trace(
        operation
    )

    assert (
        inspect.signature(wrapped)
        == inspect.signature(operation)
    )