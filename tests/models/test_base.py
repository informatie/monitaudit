from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )


def test_base_log_required_fields(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test message",
        context=context,
    )

    assert log.level == "INFO"
    assert log.message == "test message"
    assert log.context == context


def test_timestamp_is_generated(
    context: LogContext,
) -> None:
    before = datetime.now(timezone.utc)

    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
    )

    after = datetime.now(timezone.utc)

    assert before <= log.timestamp <= after


def test_generated_timestamp_is_timezone_aware(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
    )

    assert log.timestamp.tzinfo is not None
    assert log.timestamp.utcoffset() is not None


def test_generated_timestamp_is_utc(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
    )

    assert (
        log.timestamp.utcoffset()
        == timezone.utc.utcoffset(None)
    )


def test_explicit_timestamp_is_preserved(
    context: LogContext,
) -> None:
    timestamp = datetime(
        2026,
        10,
        23,
        12,
        30,
        15,
        tzinfo=timezone.utc,
    )

    log = BaseLog(
        timestamp=timestamp,
        level="INFO",
        message="test",
        context=context,
    )

    assert log.timestamp == timestamp


def test_optional_fields_default_to_none(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
    )

    assert log.call_id is None
    assert log.parent_call_id is None
    assert log.duration_ms is None
    assert log.module is None
    assert log.function is None


def test_dictionary_fields_default_to_empty(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
    )

    assert log.parameters == {}
    assert log.attributes == {}


def test_parameters_default_factory_creates_independent_dicts(
    context: LogContext,
) -> None:
    first = BaseLog(
        level="INFO",
        message="first",
        context=context,
    )

    second = BaseLog(
        level="INFO",
        message="second",
        context=context,
    )

    assert first.parameters is not second.parameters

    first.parameters["value"] = 1

    assert first.parameters == {
        "value": 1,
    }

    assert second.parameters == {}


def test_attributes_default_factory_creates_independent_dicts(
    context: LogContext,
) -> None:
    first = BaseLog(
        level="INFO",
        message="first",
        context=context,
    )

    second = BaseLog(
        level="INFO",
        message="second",
        context=context,
    )

    assert first.attributes is not second.attributes

    first.attributes["event"] = "test"

    assert first.attributes == {
        "event": "test",
    }

    assert second.attributes == {}


def test_all_common_fields_are_preserved(
    context: LogContext,
) -> None:
    timestamp = datetime(
        2026,
        10,
        23,
        12,
        30,
        tzinfo=timezone.utc,
    )

    log = BaseLog(
        timestamp=timestamp,
        level="WARNING",
        message="test message",
        context=context,
        call_id="call-123",
        parent_call_id="parent-456",
        parameters={
            "name": "monitaudit",
            "attempt": 2,
        },
        duration_ms=12.5,
        module="example.module",
        function="example_function",
        attributes={
            "event": "custom",
        },
    )

    assert log.timestamp == timestamp
    assert log.level == "WARNING"
    assert log.message == "test message"
    assert log.context == context
    assert log.call_id == "call-123"

    assert (
        log.parent_call_id
        == "parent-456"
    )

    assert log.parameters == {
        "name": "monitaudit",
        "attempt": 2,
    }

    assert log.duration_ms == 12.5
    assert log.module == "example.module"
    assert log.function == "example_function"

    assert log.attributes == {
        "event": "custom",
    }


def test_level_is_required(
    context: LogContext,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        BaseLog(
            message="test",
            context=context,
        )


def test_message_is_required(
    context: LogContext,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        BaseLog(
            level="INFO",
            context=context,
        )


def test_context_is_required() -> None:
    with pytest.raises(
        ValidationError,
    ):
        BaseLog(
            level="INFO",
            message="test",
        )


def test_zero_duration_is_valid(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
        duration_ms=0,
    )

    assert log.duration_ms == 0


def test_positive_duration_is_valid(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
        duration_ms=123.456,
    )

    assert log.duration_ms == 123.456


def test_negative_duration_is_rejected(
    context: LogContext,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        BaseLog(
            level="INFO",
            message="test",
            context=context,
            duration_ms=-0.001,
        )


def test_extra_fields_are_rejected(
    context: LogContext,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        BaseLog(
            level="INFO",
            message="test",
            context=context,
            unknown_field="value",
        )


def test_parameters_support_arbitrary_values(
    context: LogContext,
) -> None:
    parameters = {
        "string": "hello",
        "integer": 42,
        "float": 1.5,
        "boolean": True,
        "none": None,
        "nested": {
            "value": "test",
        },
        "items": [
            1,
            2,
            3,
        ],
    }

    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
        parameters=parameters,
    )

    assert log.parameters == parameters


def test_attributes_support_arbitrary_values(
    context: LogContext,
) -> None:
    attributes = {
        "event": "function_start",
        "attempt": 2,
        "enabled": True,
        "nested": {
            "name": "monitaudit",
        },
    }

    log = BaseLog(
        level="INFO",
        message="test",
        context=context,
        attributes=attributes,
    )

    assert log.attributes == attributes


def test_model_dump_contains_expected_fields(
    context: LogContext,
) -> None:
    timestamp = datetime(
        2026,
        10,
        23,
        12,
        30,
        tzinfo=timezone.utc,
    )

    log = BaseLog(
        timestamp=timestamp,
        level="INFO",
        message="test",
        context=context,
        call_id="call-123",
        parent_call_id="parent-456",
        parameters={
            "value": 42,
        },
        duration_ms=10.5,
        module="example.module",
        function="example_function",
        attributes={
            "event": "test",
        },
    )

    result = log.model_dump()

    assert result == {
        "timestamp": timestamp,
        "level": "INFO",
        "message": "test",
        "context": {
            "application": "monitaudit-test",
            "environment": "dev",
            "correlation_id": "correlation-123",
            "run_id": "run-456",
            "attributes": {},
        },
        "call_id": "call-123",
        "parent_call_id": "parent-456",
        "parameters": {
            "value": 42,
        },
        "duration_ms": 10.5,
        "module": "example.module",
        "function": "example_function",
        "attributes": {
            "event": "test",
        },
    }


def test_model_dump_json_contains_expected_values(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="monitaudit started",
        context=context,
        parameters={
            "attempt": 2,
        },
    )

    result = log.model_dump_json()

    assert '"level":"INFO"' in result

    assert (
        '"message":"monitaudit started"'
        in result
    )

    assert (
        '"application":"monitaudit-test"'
        in result
    )

    assert (
        '"correlation_id":"correlation-123"'
        in result
    )

    assert '"attempt":2' in result


def test_explicit_parameters_are_not_shared(
    context: LogContext,
) -> None:
    first_parameters = {
        "value": 1,
    }

    second_parameters = {
        "value": 2,
    }

    first = BaseLog(
        level="INFO",
        message="first",
        context=context,
        parameters=first_parameters,
    )

    second = BaseLog(
        level="INFO",
        message="second",
        context=context,
        parameters=second_parameters,
    )

    assert first.parameters == {
        "value": 1,
    }

    assert second.parameters == {
        "value": 2,
    }


def test_call_relationship_fields(
    context: LogContext,
) -> None:
    log = BaseLog(
        level="INFO",
        message="child call",
        context=context,
        call_id="child-123",
        parent_call_id="parent-456",
    )

    assert log.call_id == "child-123"

    assert (
        log.parent_call_id
        == "parent-456"
    )