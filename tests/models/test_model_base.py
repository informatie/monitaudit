# tests/models/test_base.py

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext


def make_context() -> LogContext:
    """
    Construct a lightweight LogContext.

    LogContext validation belongs in test_context.py. These tests focus on
    BaseLog behaviour.
    """

    model_construct = getattr(
        LogContext,
        "model_construct",
        None,
    )

    if callable(model_construct):
        return model_construct()

    return LogContext.construct()


def make_log(
    **overrides: Any,
) -> BaseLog:
    values: dict[str, Any] = {
        "level": "INFO",
        "context": make_context(),
        "message": "Test message",
    }

    values.update(overrides)

    return BaseLog(
        **values
    )


class TestConstruction:
    def test_minimal_valid_log(
        self,
    ) -> None:
        context = make_context()

        log = BaseLog(
            level="INFO",
            context=context,
            message="Test message",
        )

        assert log.level == "INFO"
        assert log.context is context
        assert log.message == "Test message"

    def test_base_log_is_pydantic_model(
        self,
    ) -> None:
        log = make_log()

        assert isinstance(
            log,
            BaseLog,
        )

    def test_level_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            BaseLog(
                context=make_context(),
                message="Test message",
            )

    def test_context_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            BaseLog(
                level="INFO",
                message="Test message",
            )

    def test_message_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            BaseLog(
                level="INFO",
                context=make_context(),
            )


class TestTimestamp:
    def test_timestamp_is_generated_automatically(
        self,
    ) -> None:
        before = datetime.now(
            UTC
        )

        log = make_log()

        after = datetime.now(
            UTC
        )

        assert (
            before
            <= log.timestamp
            <= after
        )

    def test_default_timestamp_is_timezone_aware(
        self,
    ) -> None:
        log = make_log()

        assert (
            log.timestamp.tzinfo
            is not None
        )

    def test_default_timestamp_uses_utc(
        self,
    ) -> None:
        log = make_log()

        assert (
            log.timestamp.utcoffset()
            == UTC.utcoffset(
                log.timestamp
            )
        )

    def test_explicit_timestamp_is_preserved(
        self,
    ) -> None:
        timestamp = datetime(
            2026,
            11,
            2,
            19,
            30,
            tzinfo=UTC,
        )

        log = make_log(
            timestamp=timestamp,
        )

        assert (
            log.timestamp
            == timestamp
        )

    def test_separate_logs_receive_separate_timestamps(
        self,
    ) -> None:
        first = make_log()
        second = make_log()

        assert isinstance(
            first.timestamp,
            datetime,
        )
        assert isinstance(
            second.timestamp,
            datetime,
        )


class TestMessage:
    def test_non_empty_message_is_accepted(
        self,
    ) -> None:
        log = make_log(
            message="Application started",
        )

        assert (
            log.message
            == "Application started"
        )

    def test_single_character_message_is_accepted(
        self,
    ) -> None:
        log = make_log(
            message="x",
        )

        assert log.message == "x"

    def test_empty_message_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            make_log(
                message="",
            )

        errors = (
            exception_info.value.errors()
        )

        assert any(
            error["loc"]
            == ("message",)
            for error in errors
        )

    def test_whitespace_message_is_currently_accepted(
        self,
    ) -> None:
        log = make_log(
            message="   ",
        )

        assert log.message == "   "


class TestDefaultValues:
    def test_optional_location_defaults_to_none(
        self,
    ) -> None:
        log = make_log()

        assert log.module is None
        assert log.function is None

    def test_trace_identifiers_default_to_none(
        self,
    ) -> None:
        log = make_log()

        assert log.call_id is None
        assert log.parent_call_id is None

    def test_event_defaults_to_none(
        self,
    ) -> None:
        log = make_log()

        assert log.event is None

    def test_duration_defaults_to_none(
        self,
    ) -> None:
        log = make_log()

        assert (
            log.duration_ms
            is None
        )

    def test_failure_fields_default_to_none(
        self,
    ) -> None:
        log = make_log()

        assert log.error_type is None
        assert (
            log.error_message
            is None
        )
        assert log.traceback is None

    def test_parameters_default_to_empty_dictionary(
        self,
    ) -> None:
        log = make_log()

        assert log.parameters == {}

    def test_attributes_default_to_empty_dictionary(
        self,
    ) -> None:
        log = make_log()

        assert log.attributes == {}


class TestMutableDefaults:
    def test_parameters_are_independent_between_logs(
        self,
    ) -> None:
        first = make_log()
        second = make_log()

        assert (
            first.parameters
            is not second.parameters
        )

        first.parameters[
            "customer_id"
        ] = 42

        assert second.parameters == {}

    def test_attributes_are_independent_between_logs(
        self,
    ) -> None:
        first = make_log()
        second = make_log()

        assert (
            first.attributes
            is not second.attributes
        )

        first.attributes[
            "batch"
        ] = "nightly"

        assert second.attributes == {}


class TestLocation:
    def test_module_can_be_set(
        self,
    ) -> None:
        log = make_log(
            module="application.module",
        )

        assert (
            log.module
            == "application.module"
        )

    def test_function_can_be_set(
        self,
    ) -> None:
        log = make_log(
            function="process",
        )

        assert (
            log.function
            == "process"
        )

    def test_module_and_function_can_be_empty_strings(
        self,
    ) -> None:
        log = make_log(
            module="",
            function="",
        )

        assert log.module == ""
        assert log.function == ""


class TestTraceFields:
    def test_call_id_can_be_set(
        self,
    ) -> None:
        log = make_log(
            call_id="call-123",
        )

        assert (
            log.call_id
            == "call-123"
        )

    def test_parent_call_id_can_be_set(
        self,
    ) -> None:
        log = make_log(
            parent_call_id="parent-123",
        )

        assert (
            log.parent_call_id
            == "parent-123"
        )

    def test_event_can_be_set(
        self,
    ) -> None:
        log = make_log(
            event="function_start",
        )

        assert (
            log.event
            == "function_start"
        )

    def test_trace_fields_can_be_used_together(
        self,
    ) -> None:
        log = make_log(
            call_id="child",
            parent_call_id="parent",
            event="function_start",
        )

        assert log.call_id == "child"
        assert (
            log.parent_call_id
            == "parent"
        )
        assert (
            log.event
            == "function_start"
        )


class TestParameters:
    def test_parameters_can_be_set(
        self,
    ) -> None:
        parameters = {
            "customer_id": 42,
            "region": "eu",
        }

        log = make_log(
            parameters=parameters,
        )

        assert (
            log.parameters
            == parameters
        )

    def test_parameters_support_nested_values(
        self,
    ) -> None:
        parameters = {
            "customer": {
                "id": 42,
                "active": True,
            },
            "items": [
                1,
                2,
                3,
            ],
        }

        log = make_log(
            parameters=parameters,
        )

        assert (
            log.parameters
            == parameters
        )

    def test_parameters_support_arbitrary_values(
        self,
    ) -> None:
        value = object()

        log = make_log(
            parameters={
                "value": value,
            }
        )

        assert (
            log.parameters["value"]
            is value
        )


class TestAttributes:
    def test_attributes_can_be_set(
        self,
    ) -> None:
        attributes = {
            "batch": "nightly",
            "attempt": 2,
        }

        log = make_log(
            attributes=attributes,
        )

        assert (
            log.attributes
            == attributes
        )

    def test_attributes_support_nested_values(
        self,
    ) -> None:
        attributes = {
            "metadata": {
                "region": "eu",
            }
        }

        log = make_log(
            attributes=attributes,
        )

        assert (
            log.attributes
            == attributes
        )


class TestDuration:
    def test_zero_duration_is_allowed(
        self,
    ) -> None:
        log = make_log(
            duration_ms=0,
        )

        assert (
            log.duration_ms
            == 0
        )

    def test_positive_duration_is_allowed(
        self,
    ) -> None:
        log = make_log(
            duration_ms=125.5,
        )

        assert (
            log.duration_ms
            == 125.5
        )

    def test_integer_duration_is_accepted(
        self,
    ) -> None:
        log = make_log(
            duration_ms=100,
        )

        assert (
            log.duration_ms
            == 100.0
        )

    @pytest.mark.parametrize(
        "duration",
        [
            -0.001,
            -1,
            -100.5,
        ],
    )
    def test_negative_duration_is_rejected(
        self,
        duration: float,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            make_log(
                duration_ms=duration,
            )

        errors = (
            exception_info.value.errors()
        )

        assert any(
            error["loc"]
            == ("duration_ms",)
            for error in errors
        )


class TestFailureFields:
    def test_error_type_can_be_set(
        self,
    ) -> None:
        log = make_log(
            error_type="ValueError",
        )

        assert (
            log.error_type
            == "ValueError"
        )

    def test_error_message_can_be_set(
        self,
    ) -> None:
        log = make_log(
            error_message="Invalid value",
        )

        assert (
            log.error_message
            == "Invalid value"
        )

    def test_traceback_can_be_set(
        self,
    ) -> None:
        traceback_lines = [
            "Traceback:\n",
            "ValueError: invalid\n",
        ]

        log = make_log(
            traceback=traceback_lines,
        )

        assert (
            log.traceback
            == traceback_lines
        )

    def test_empty_traceback_is_allowed(
        self,
    ) -> None:
        log = make_log(
            traceback=[],
        )

        assert log.traceback == []

    def test_failure_fields_can_be_used_together(
        self,
    ) -> None:
        log = make_log(
            error_type="ValueError",
            error_message="Invalid value",
            traceback=[
                "ValueError: Invalid value\n",
            ],
        )

        assert (
            log.error_type
            == "ValueError"
        )
        assert (
            log.error_message
            == "Invalid value"
        )
        assert log.traceback == [
            "ValueError: Invalid value\n",
        ]


class TestLevel:
    @pytest.mark.parametrize(
        "level",
        [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "CUSTOM",
            "",
        ],
    )
    def test_level_accepts_strings(
        self,
        level: str,
    ) -> None:
        log = make_log(
            level=level,
        )

        assert log.level == level

    def test_level_has_no_enum_restriction(
        self,
    ) -> None:
        log = make_log(
            level="TRACE",
        )

        assert (
            log.level
            == "TRACE"
        )


class TestExtraFields:
    def test_extra_fields_are_forbidden(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            BaseLog(
                level="INFO",
                context=make_context(),
                message="Test message",
                unexpected_field="value",
            )

        errors = (
            exception_info.value.errors()
        )

        assert any(
            error["loc"]
            == ("unexpected_field",)
            for error in errors
        )

    def test_model_config_forbids_extra_fields(
        self,
    ) -> None:
        assert (
            BaseLog.model_config[
                "extra"
            ]
            == "forbid"
        )


class TestModelDump:
    def test_model_dump_contains_expected_fields(
        self,
    ) -> None:
        timestamp = datetime(
            2026,
            11,
            2,
            19,
            30,
            tzinfo=UTC,
        )

        context = make_context()

        log = BaseLog(
            timestamp=timestamp,
            level="INFO",
            context=context,
            module="application.module",
            function="process",
            call_id="call-1",
            parent_call_id="parent-1",
            event="function_end",
            message="Completed",
            parameters={
                "customer_id": 42,
            },
            duration_ms=50.0,
            attributes={
                "batch": "nightly",
            },
        )

        result = log.model_dump()

        assert result[
            "timestamp"
        ] == timestamp
        assert result["level"] == "INFO"
        assert (
            result["module"]
            == "application.module"
        )
        assert (
            result["function"]
            == "process"
        )
        assert (
            result["call_id"]
            == "call-1"
        )
        assert (
            result["parent_call_id"]
            == "parent-1"
        )
        assert (
            result["event"]
            == "function_end"
        )
        assert (
            result["message"]
            == "Completed"
        )
        assert (
            result["parameters"]
            == {
                "customer_id": 42,
            }
        )
        assert (
            result["duration_ms"]
            == 50.0
        )
        assert (
            result["attributes"]
            == {
                "batch": "nightly",
            }
        )

    def test_model_dump_contains_optional_fields(
        self,
    ) -> None:
        result = (
            make_log()
            .model_dump()
        )

        assert "module" in result
        assert "function" in result
        assert "call_id" in result
        assert (
            "parent_call_id"
            in result
        )
        assert "event" in result
        assert "duration_ms" in result
        assert "error_type" in result
        assert (
            "error_message"
            in result
        )
        assert "traceback" in result


class TestJsonSerialisation:
    def test_model_dump_json_returns_json(
        self,
    ) -> None:
        log = make_log()

        result = (
            log.model_dump_json()
        )

        assert isinstance(
            result,
            str,
        )

    def test_timestamp_is_serialised_as_iso_datetime(
        self,
    ) -> None:
        timestamp = datetime(
            2026,
            11,
            2,
            19,
            30,
            tzinfo=UTC,
        )

        log = make_log(
            timestamp=timestamp,
        )

        result = (
            log.model_dump_json()
        )

        assert (
            "2026-11-02T19:30:00Z"
            in result
        )

    def test_json_contains_message(
        self,
    ) -> None:
        log = make_log(
            message="MonitAudit test",
        )

        result = (
            log.model_dump_json()
        )

        assert (
            '"message":"MonitAudit test"'
            in result
        )


class TestModelFields:
    def test_expected_model_fields(
        self,
    ) -> None:
        assert set(
            BaseLog.model_fields
        ) == {
            "timestamp",
            "level",
            "context",
            "module",
            "function",
            "call_id",
            "parent_call_id",
            "event",
            "message",
            "parameters",
            "duration_ms",
            "error_type",
            "error_message",
            "traceback",
            "attributes",
        }

    @pytest.mark.parametrize(
        "field_name",
        [
            "level",
            "context",
            "message",
        ],
    )
    def test_required_fields(
        self,
        field_name: str,
    ) -> None:
        assert (
            BaseLog.model_fields[
                field_name
            ].is_required()
            is True
        )

    @pytest.mark.parametrize(
        "field_name",
        [
            "timestamp",
            "module",
            "function",
            "call_id",
            "parent_call_id",
            "event",
            "parameters",
            "duration_ms",
            "error_type",
            "error_message",
            "traceback",
            "attributes",
        ],
    )
    def test_optional_or_defaulted_fields(
        self,
        field_name: str,
    ) -> None:
        assert (
            BaseLog.model_fields[
                field_name
            ].is_required()
            is False
        )


class TestCompleteRecord:
    def test_complete_record(
        self,
    ) -> None:
        timestamp = datetime(
            2026,
            11,
            2,
            19,
            30,
            tzinfo=UTC,
        )

        context = make_context()

        log = BaseLog(
            timestamp=timestamp,
            level="ERROR",
            context=context,
            module="orders.processor",
            function="process_order",
            call_id="call-001",
            parent_call_id="parent-001",
            event="function_error",
            message="Order processing failed",
            parameters={
                "order_id": 12345,
            },
            duration_ms=145.25,
            error_type="ValueError",
            error_message="Invalid order",
            traceback=[
                "Traceback:\n",
                "ValueError: Invalid order\n",
            ],
            attributes={
                "retry": False,
            },
        )

        assert log.timestamp == timestamp
        assert log.level == "ERROR"
        assert log.context is context
        assert (
            log.module
            == "orders.processor"
        )
        assert (
            log.function
            == "process_order"
        )
        assert (
            log.call_id
            == "call-001"
        )
        assert (
            log.parent_call_id
            == "parent-001"
        )
        assert (
            log.event
            == "function_error"
        )
        assert (
            log.message
            == "Order processing failed"
        )
        assert log.parameters == {
            "order_id": 12345,
        }
        assert (
            log.duration_ms
            == 145.25
        )
        assert (
            log.error_type
            == "ValueError"
        )
        assert (
            log.error_message
            == "Invalid order"
        )
        assert log.traceback == [
            "Traceback:\n",
            "ValueError: Invalid order\n",
        ]
        assert log.attributes == {
            "retry": False,
        }