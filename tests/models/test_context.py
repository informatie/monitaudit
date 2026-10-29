from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from monitaudit.models.context import LogContext


def test_context_with_required_fields() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    assert context.application == "monitaudit-test"
    assert context.environment == "dev"
    assert context.run_id is None
    assert context.attributes == {}


def test_context_preserves_values() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="prod",
        correlation_id="correlation-123",
        run_id="run-456",
        attributes={
            "team": "platform",
            "version": 2,
        },
    )

    assert context.application == "monitaudit-test"
    assert context.environment == "prod"
    assert context.correlation_id == "correlation-123"
    assert context.run_id == "run-456"

    assert context.attributes == {
        "team": "platform",
        "version": 2,
    }


def test_correlation_id_is_generated() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    assert context.correlation_id

    UUID(
        context.correlation_id
    )


def test_generated_correlation_ids_are_unique() -> None:
    first = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    second = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    assert (
        first.correlation_id
        != second.correlation_id
    )


def test_explicit_correlation_id_is_preserved() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="custom-id",
    )

    assert (
        context.correlation_id
        == "custom-id"
    )


def test_run_id_defaults_to_none() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    assert context.run_id is None


def test_run_id_is_preserved() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        run_id="run-123",
    )

    assert context.run_id == "run-123"


def test_application_is_required() -> None:
    with pytest.raises(
        ValidationError,
    ):
        LogContext(
            environment="dev",
        )


def test_environment_is_required() -> None:
    with pytest.raises(
        ValidationError,
    ):
        LogContext(
            application="monitaudit-test",
        )


def test_empty_application_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
    ):
        LogContext(
            application="",
            environment="dev",
        )


def test_empty_environment_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
    ):
        LogContext(
            application="monitaudit-test",
            environment="",
        )


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
    ):
        LogContext(
            application="monitaudit-test",
            environment="dev",
            unknown_field="value",
        )


def test_context_is_frozen() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    with pytest.raises(
        ValidationError,
    ):
        context.application = "changed"


def test_environment_cannot_be_changed() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    with pytest.raises(
        ValidationError,
    ):
        context.environment = "prod"


def test_correlation_id_cannot_be_changed() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="original",
    )

    with pytest.raises(
        ValidationError,
    ):
        context.correlation_id = "changed"


def test_default_attributes_are_independent() -> None:
    first = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    second = LogContext(
        application="monitaudit-test",
        environment="dev",
    )

    assert first.attributes == {}
    assert second.attributes == {}

    assert (
        first.attributes
        is not second.attributes
    )


def test_attributes_are_preserved() -> None:
    attributes = {
        "team": "platform",
        "attempt": 2,
        "enabled": True,
    }

    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        attributes=attributes,
    )

    assert context.attributes == attributes


def test_nested_attributes_are_supported() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        attributes={
            "configuration": {
                "region": "west-europe",
                "retry": 3,
            },
            "tags": [
                "monitaudit",
                "test",
            ],
        },
    )

    assert context.attributes == {
        "configuration": {
            "region": "west-europe",
            "retry": 3,
        },
        "tags": [
            "monitaudit",
            "test",
        ],
    }


def test_model_dump_contains_expected_fields() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
        attributes={
            "team": "platform",
        },
    )

    result = context.model_dump()

    assert result == {
        "application": "monitaudit-test",
        "environment": "dev",
        "correlation_id": "correlation-123",
        "run_id": "run-456",
        "attributes": {
            "team": "platform",
        },
    }


def test_model_dump_json() -> None:
    context = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
        attributes={
            "team": "platform",
        },
    )

    result = context.model_dump_json()

    assert '"application":"monitaudit-test"' in result
    assert '"environment":"dev"' in result

    assert (
        '"correlation_id":"correlation-123"'
        in result
    )

    assert '"run_id":"run-456"' in result


def test_context_equality() -> None:
    first = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )

    second = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )

    assert first == second


def test_different_contexts_are_not_equal() -> None:
    first = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="first",
    )

    second = LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="second",
    )

    assert first != second