# tests/models/test_mapping.py

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

import monitaudit.models.mapping as mapping_module
from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext
from monitaudit.models.mapping import (
    LOG_FIELD_NAMES,
    log_record,
)

TIMESTAMP = datetime(
    2026,
    11,
    2,
    19,
    30,
    tzinfo=UTC,
)


def make_context(
    **overrides: Any,
) -> LogContext:
    values: dict[str, Any] = {
        "application": "test-application",
        "environment": "dev",
        "correlation_id": "correlation-1",
        "run_id": "run-1",
        "attributes": {
            "region": "eu",
        },
    }

    values.update(overrides)

    return LogContext(
        **values
    )


def make_log(
    **overrides: Any,
) -> BaseLog:
    values: dict[str, Any] = {
        "timestamp": TIMESTAMP,
        "level": "INFO",
        "context": make_context(),
        "module": "example.module",
        "function": "process",
        "call_id": "call-1",
        "parent_call_id": "parent-1",
        "event": "base-event",
        "message": "Processing completed",
        "parameters": {
            "customer_id": 42,
        },
        "duration_ms": 125.5,
        "error_type": None,
        "error_message": None,
        "traceback": None,
        "attributes": {
            "event": "attribute-event",
            "batch": "nightly",
        },
    }

    values.update(overrides)

    return BaseLog(
        **values
    )


class TestLogFieldNames:
    def test_log_field_names_is_tuple(
        self,
    ) -> None:
        assert isinstance(
            LOG_FIELD_NAMES,
            tuple,
        )

    def test_log_field_names_are_unique(
        self,
    ) -> None:
        assert len(
            LOG_FIELD_NAMES
        ) == len(
            set(LOG_FIELD_NAMES)
        )

    def test_log_field_names_contains_only_strings(
        self,
    ) -> None:
        assert all(
            isinstance(
                field_name,
                str,
            )
            for field_name
            in LOG_FIELD_NAMES
        )

    def test_expected_log_field_names(
        self,
    ) -> None:
        assert LOG_FIELD_NAMES == (
            "timestamp",
            "level",
            "application",
            "environment",
            "module",
            "function",
            "correlation_id",
            "run_id",
            "call_id",
            "parent_call_id",
            "event",
            "message",
            "parameters",
            "attributes",
            "duration_ms",
            "error_type",
            "error_message",
            "traceback",
        )

    def test_log_field_count(
        self,
    ) -> None:
        assert len(
            LOG_FIELD_NAMES
        ) == 18


class TestLogRecord:
    def test_returns_dictionary(
        self,
    ) -> None:
        result = log_record(
            make_log()
        )

        assert isinstance(
            result,
            dict,
        )

    def test_record_keys_match_canonical_fields(
        self,
    ) -> None:
        result = log_record(
            make_log()
        )

        assert tuple(
            result
        ) == LOG_FIELD_NAMES

    def test_record_contains_every_canonical_field(
        self,
    ) -> None:
        result = log_record(
            make_log()
        )

        assert set(
            result
        ) == set(
            LOG_FIELD_NAMES
        )

    def test_record_has_no_additional_fields(
        self,
    ) -> None:
        result = log_record(
            make_log()
        )

        assert len(
            result
        ) == len(
            LOG_FIELD_NAMES
        )


class TestWhenMapping:
    def test_maps_timestamp(
        self,
    ) -> None:
        result = log_record(
            make_log()
        )

        assert (
            result["timestamp"]
            == TIMESTAMP
        )


class TestSeverityMapping:
    def test_maps_level(
        self,
    ) -> None:
        result = log_record(
            make_log(
                level="WARNING",
            )
        )

        assert (
            result["level"]
            == "WARNING"
        )


class TestLocationMapping:
    def test_maps_application_from_context(
        self,
    ) -> None:
        context = make_context(
            application="orders",
        )

        result = log_record(
            make_log(
                context=context,
            )
        )

        assert (
            result["application"]
            == "orders"
        )

    def test_maps_environment_from_context(
        self,
    ) -> None:
        context = make_context(
            environment="prod",
        )

        result = log_record(
            make_log(
                context=context,
            )
        )

        assert (
            result["environment"]
            == "prod"
        )

    def test_maps_module(
        self,
    ) -> None:
        result = log_record(
            make_log(
                module="orders.processor",
            )
        )

        assert (
            result["module"]
            == "orders.processor"
        )

    def test_maps_function(
        self,
    ) -> None:
        result = log_record(
            make_log(
                function="process_order",
            )
        )

        assert (
            result["function"]
            == "process_order"
        )

    def test_optional_location_values_can_be_none(
        self,
    ) -> None:
        result = log_record(
            make_log(
                module=None,
                function=None,
            )
        )

        assert (
            result["module"]
            is None
        )
        assert (
            result["function"]
            is None
        )


class TestExecutionMapping:
    def test_maps_correlation_id_from_context(
        self,
    ) -> None:
        context = make_context(
            correlation_id="correlation-123",
        )

        result = log_record(
            make_log(
                context=context,
            )
        )

        assert (
            result["correlation_id"]
            == "correlation-123"
        )

    def test_maps_run_id_from_context(
        self,
    ) -> None:
        context = make_context(
            run_id="run-123",
        )

        result = log_record(
            make_log(
                context=context,
            )
        )

        assert (
            result["run_id"]
            == "run-123"
        )

    def test_maps_none_run_id(
        self,
    ) -> None:
        context = make_context(
            run_id=None,
        )

        result = log_record(
            make_log(
                context=context,
            )
        )

        assert (
            result["run_id"]
            is None
        )

    def test_maps_call_id(
        self,
    ) -> None:
        result = log_record(
            make_log(
                call_id="call-123",
            )
        )

        assert (
            result["call_id"]
            == "call-123"
        )

    def test_maps_parent_call_id(
        self,
    ) -> None:
        result = log_record(
            make_log(
                parent_call_id="parent-123",
            )
        )

        assert (
            result["parent_call_id"]
            == "parent-123"
        )

    def test_optional_call_ids_can_be_none(
        self,
    ) -> None:
        result = log_record(
            make_log(
                call_id=None,
                parent_call_id=None,
            )
        )

        assert (
            result["call_id"]
            is None
        )
        assert (
            result["parent_call_id"]
            is None
        )


class TestEventMapping:
    def test_event_comes_from_attributes(
        self,
    ) -> None:
        log = make_log(
            event="base-event",
            attributes={
                "event": "attributes-event",
            },
        )

        result = log_record(
            log
        )

        assert (
            result["event"]
            == "attributes-event"
        )

    def test_base_log_event_field_is_not_used(
        self,
    ) -> None:
        log = make_log(
            event="base-event",
            attributes={},
        )

        result = log_record(
            log
        )

        assert (
            log.event
            == "base-event"
        )
        assert (
            result["event"]
            is None
        )

    def test_missing_attribute_event_becomes_none(
        self,
    ) -> None:
        result = log_record(
            make_log(
                attributes={
                    "batch": "nightly",
                }
            )
        )

        assert (
            result["event"]
            is None
        )

    def test_none_attribute_event_is_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                attributes={
                    "event": None,
                }
            )
        )

        assert (
            result["event"]
            is None
        )

    def test_empty_attribute_event_is_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                attributes={
                    "event": "",
                }
            )
        )

        assert (
            result["event"]
            == ""
        )


class TestWhatMapping:
    def test_maps_message(
        self,
    ) -> None:
        result = log_record(
            make_log(
                message="Application started",
            )
        )

        assert (
            result["message"]
            == "Application started"
        )

    def test_maps_parameters(
        self,
    ) -> None:
        parameters = {
            "customer_id": 42,
            "region": "eu",
        }

        result = log_record(
            make_log(
                parameters=parameters,
            )
        )

        assert (
            result["parameters"]
            == parameters
        )

    def test_parameters_are_same_log_mapping(
        self,
    ) -> None:
        log = make_log()

        result = log_record(
            log
        )

        assert (
            result["parameters"]
            is log.parameters
        )

    def test_maps_attributes(
        self,
    ) -> None:
        attributes = {
            "event": "function_end",
            "batch": "nightly",
        }

        log = make_log(
            attributes=attributes,
        )

        result = log_record(
            log
        )

        assert (
            result["attributes"]
            == attributes
        )

    def test_attributes_are_same_log_mapping(
        self,
    ) -> None:
        log = make_log()

        result = log_record(
            log
        )

        assert (
            result["attributes"]
            is log.attributes
        )

    def test_empty_parameters_are_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                parameters={},
            )
        )

        assert (
            result["parameters"]
            == {}
        )

    def test_empty_attributes_are_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                attributes={},
            )
        )

        assert (
            result["attributes"]
            == {}
        )


class TestPerformanceMapping:
    def test_maps_duration(
        self,
    ) -> None:
        result = log_record(
            make_log(
                duration_ms=25.5,
            )
        )

        assert (
            result["duration_ms"]
            == 25.5
        )

    def test_none_duration_is_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                duration_ms=None,
            )
        )

        assert (
            result["duration_ms"]
            is None
        )

    def test_zero_duration_is_preserved(
        self,
    ) -> None:
        result = log_record(
            make_log(
                duration_ms=0,
            )
        )

        assert (
            result["duration_ms"]
            == 0
        )


class TestFailureMapping:
    def test_maps_error_type(
        self,
    ) -> None:
        result = log_record(
            make_log(
                error_type="ValueError",
            )
        )

        assert (
            result["error_type"]
            == "ValueError"
        )

    def test_maps_error_message(
        self,
    ) -> None:
        result = log_record(
            make_log(
                error_message="Invalid value",
            )
        )

        assert (
            result["error_message"]
            == "Invalid value"
        )

    def test_maps_traceback(
        self,
    ) -> None:
        traceback_lines = [
            "Traceback:\n",
            "ValueError: Invalid value\n",
        ]

        log = make_log(
            traceback=traceback_lines,
        )

        result = log_record(
            log
        )

        assert (
            result["traceback"]
            == traceback_lines
        )

    def test_traceback_is_same_log_list(
        self,
    ) -> None:
        log = make_log(
            traceback=[
                "ValueError: failure\n",
            ]
        )

        result = log_record(
            log
        )

        assert (
            result["traceback"]
            is log.traceback
        )

    def test_failure_fields_can_all_be_none(
        self,
    ) -> None:
        result = log_record(
            make_log(
                error_type=None,
                error_message=None,
                traceback=None,
            )
        )

        assert (
            result["error_type"]
            is None
        )
        assert (
            result["error_message"]
            is None
        )
        assert (
            result["traceback"]
            is None
        )


class TestCompleteRecord:
    def test_complete_canonical_record(
        self,
    ) -> None:
        context = LogContext(
            application="orders",
            environment="prod",
            correlation_id="correlation-123",
            run_id="run-456",
            attributes={
                "region": "eu",
            },
        )

        traceback_lines = [
            "Traceback:\n",
            "ValueError: invalid order\n",
        ]

        log = BaseLog(
            timestamp=TIMESTAMP,
            level="ERROR",
            context=context,
            module="orders.processor",
            function="process_order",
            call_id="call-001",
            parent_call_id="parent-001",
            event="base-event",
            message="Order processing failed",
            parameters={
                "order_id": 12345,
            },
            duration_ms=145.25,
            error_type="ValueError",
            error_message="invalid order",
            traceback=traceback_lines,
            attributes={
                "event": "function_error",
                "retry": False,
            },
        )

        result = log_record(
            log
        )

        assert result == {
            "timestamp": TIMESTAMP,
            "level": "ERROR",
            "application": "orders",
            "environment": "prod",
            "module": "orders.processor",
            "function": "process_order",
            "correlation_id": (
                "correlation-123"
            ),
            "run_id": "run-456",
            "call_id": "call-001",
            "parent_call_id": (
                "parent-001"
            ),
            "event": "function_error",
            "message": (
                "Order processing failed"
            ),
            "parameters": {
                "order_id": 12345,
            },
            "attributes": {
                "event": "function_error",
                "retry": False,
            },
            "duration_ms": 145.25,
            "error_type": "ValueError",
            "error_message": (
                "invalid order"
            ),
            "traceback": traceback_lines,
        }

        assert tuple(
            result
        ) == LOG_FIELD_NAMES


class TestRecordOrderGuard:
    def test_current_record_order_matches_constant(
        self,
    ) -> None:
        record = log_record(
            make_log()
        )

        assert tuple(
            record.keys()
        ) == LOG_FIELD_NAMES

    def test_guard_detects_changed_field_definition(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        modified_names = (
            "message",
            *LOG_FIELD_NAMES,
        )

        monkeypatch.setattr(
            mapping_module,
            "LOG_FIELD_NAMES",
            modified_names,
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            mapping_module.log_record(
                make_log()
            )

        assert (
            str(exception_info.value)
            == (
                "Canonical log record does not "
                "match LOG_FIELD_NAMES."
            )
        )

    def test_guard_detects_same_fields_in_wrong_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        modified_names = tuple(
            reversed(
                LOG_FIELD_NAMES
            )
        )

        monkeypatch.setattr(
            mapping_module,
            "LOG_FIELD_NAMES",
            modified_names,
        )

        with pytest.raises(
            RuntimeError,
            match=(
                "Canonical log record does not "
                "match LOG_FIELD_NAMES"
            ),
        ):
            mapping_module.log_record(
                make_log()
            )


class TestRecordIsolation:
    def test_returns_new_record_each_time(
        self,
    ) -> None:
        log = make_log()

        first = log_record(
            log
        )
        second = log_record(
            log
        )

        assert first == second
        assert first is not second

    def test_modifying_top_level_record_does_not_modify_log(
        self,
    ) -> None:
        log = make_log()

        record = log_record(
            log
        )

        record["message"] = (
            "changed"
        )

        assert (
            log.message
            == "Processing completed"
        )


class TestEventConsistency:
    def test_event_and_attributes_event_match_when_configured_identically(
        self,
    ) -> None:
        log = make_log(
            event="function_start",
            attributes={
                "event": "function_start",
            },
        )

        result = log_record(
            log
        )

        assert (
            result["event"]
            == log.attributes["event"]
        )

    def test_mapping_prefers_attribute_event_over_model_event(
        self,
    ) -> None:
        log = make_log(
            event="function_start",
            attributes={
                "event": "function_end",
            },
        )

        result = log_record(
            log
        )

        assert (
            log.event
            == "function_start"
        )
        assert (
            result["event"]
            == "function_end"
        )