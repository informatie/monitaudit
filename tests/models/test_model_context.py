# tests/models/test_context.py

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from monitaudit.models.context import LogContext


def make_context(
    **overrides: Any,
) -> LogContext:
    values: dict[str, Any] = {
        "application": "test-application",
        "environment": "dev",
    }

    values.update(overrides)

    return LogContext(
        **values
    )


class TestConstruction:
    def test_minimal_valid_context(
        self,
    ) -> None:
        context = LogContext(
            application="test-application",
            environment="dev",
        )

        assert (
            context.application
            == "test-application"
        )
        assert context.environment == "dev"

    def test_application_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            LogContext(
                environment="dev",
            )

        assert any(
            error["loc"]
            == ("application",)
            for error
            in exception_info.value.errors()
        )

    def test_environment_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            LogContext(
                application="test-application",
            )

        assert any(
            error["loc"]
            == ("environment",)
            for error
            in exception_info.value.errors()
        )


class TestApplication:
    def test_application_is_preserved(
        self,
    ) -> None:
        context = make_context(
            application="monitaudit-example",
        )

        assert (
            context.application
            == "monitaudit-example"
        )

    def test_single_character_application_is_valid(
        self,
    ) -> None:
        context = make_context(
            application="a",
        )

        assert context.application == "a"

    def test_empty_application_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            make_context(
                application="",
            )

        assert any(
            error["loc"]
            == ("application",)
            for error
            in exception_info.value.errors()
        )

    def test_whitespace_application_is_currently_allowed(
        self,
    ) -> None:
        context = make_context(
            application="   ",
        )

        assert context.application == "   "


class TestEnvironment:
    @pytest.mark.parametrize(
        "environment",
        [
            "dev",
            "acc",
            "prod",
            "local",
            "custom",
        ],
    )
    def test_environment_string_is_preserved(
        self,
        environment: str,
    ) -> None:
        context = make_context(
            environment=environment,
        )

        assert (
            context.environment
            == environment
        )

    def test_single_character_environment_is_valid(
        self,
    ) -> None:
        context = make_context(
            environment="x",
        )

        assert context.environment == "x"

    def test_empty_environment_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            make_context(
                environment="",
            )

        assert any(
            error["loc"]
            == ("environment",)
            for error
            in exception_info.value.errors()
        )

    def test_whitespace_environment_is_currently_allowed(
        self,
    ) -> None:
        context = make_context(
            environment="   ",
        )

        assert context.environment == "   "


class TestCorrelationId:
    def test_correlation_id_is_generated(
        self,
    ) -> None:
        context = make_context()

        assert isinstance(
            context.correlation_id,
            str,
        )

        assert context.correlation_id

    def test_generated_correlation_id_is_valid_uuid(
        self,
    ) -> None:
        context = make_context()

        identifier = UUID(
            context.correlation_id
        )

        assert (
            str(identifier)
            == context.correlation_id
        )

    def test_generated_correlation_id_uses_uuid4(
        self,
    ) -> None:
        context = make_context()

        identifier = UUID(
            context.correlation_id
        )

        assert identifier.version == 4

    def test_each_context_gets_new_correlation_id(
        self,
    ) -> None:
        first = make_context()
        second = make_context()

        assert (
            first.correlation_id
            != second.correlation_id
        )

    def test_explicit_correlation_id_is_preserved(
        self,
    ) -> None:
        context = make_context(
            correlation_id="correlation-123",
        )

        assert (
            context.correlation_id
            == "correlation-123"
        )

    def test_correlation_id_is_not_restricted_to_uuid(
        self,
    ) -> None:
        context = make_context(
            correlation_id="custom-correlation-id",
        )

        assert (
            context.correlation_id
            == "custom-correlation-id"
        )

    def test_empty_explicit_correlation_id_is_currently_allowed(
        self,
    ) -> None:
        context = make_context(
            correlation_id="",
        )

        assert context.correlation_id == ""


class TestRunId:
    def test_run_id_defaults_to_none(
        self,
    ) -> None:
        context = make_context()

        assert context.run_id is None

    def test_run_id_can_be_set(
        self,
    ) -> None:
        context = make_context(
            run_id="run-123",
        )

        assert context.run_id == "run-123"

    def test_empty_run_id_is_currently_allowed(
        self,
    ) -> None:
        context = make_context(
            run_id="",
        )

        assert context.run_id == ""

    def test_run_id_can_explicitly_be_none(
        self,
    ) -> None:
        context = make_context(
            run_id=None,
        )

        assert context.run_id is None


class TestAttributes:
    def test_attributes_default_to_empty_dictionary(
        self,
    ) -> None:
        context = make_context()

        assert context.attributes == {}

    def test_attributes_can_be_set(
        self,
    ) -> None:
        context = make_context(
            attributes={
                "region": "eu",
                "retry": False,
            }
        )

        assert context.attributes == {
            "region": "eu",
            "retry": False,
        }

    def test_attributes_support_nested_values(
        self,
    ) -> None:
        attributes = {
            "metadata": {
                "region": "eu",
                "active": True,
            },
            "items": [
                1,
                2,
                3,
            ],
        }

        context = make_context(
            attributes=attributes,
        )

        assert (
            context.attributes
            == attributes
        )

    def test_attributes_support_arbitrary_values(
        self,
    ) -> None:
        value = object()

        context = make_context(
            attributes={
                "value": value,
            }
        )

        assert (
            context.attributes["value"]
            is value
        )

    def test_attribute_defaults_are_independent(
        self,
    ) -> None:
        first = make_context()
        second = make_context()

        assert (
            first.attributes
            is not second.attributes
        )

    def test_mutating_one_default_attribute_mapping_does_not_change_another(
        self,
    ) -> None:
        first = make_context()
        second = make_context()

        first.attributes[
            "region"
        ] = "eu"

        assert second.attributes == {}


class TestFrozenModel:
    def test_model_is_configured_as_frozen(
        self,
    ) -> None:
        assert (
            LogContext.model_config[
                "frozen"
            ]
            is True
        )

    def test_application_cannot_be_reassigned(
        self,
    ) -> None:
        context = make_context()

        with pytest.raises(
            ValidationError,
        ):
            context.application = "changed"

    def test_environment_cannot_be_reassigned(
        self,
    ) -> None:
        context = make_context()

        with pytest.raises(
            ValidationError,
        ):
            context.environment = "prod"

    def test_correlation_id_cannot_be_reassigned(
        self,
    ) -> None:
        context = make_context()

        with pytest.raises(
            ValidationError,
        ):
            context.correlation_id = "changed"

    def test_run_id_cannot_be_reassigned(
        self,
    ) -> None:
        context = make_context()

        with pytest.raises(
            ValidationError,
        ):
            context.run_id = "changed"

    def test_attributes_reference_cannot_be_reassigned(
        self,
    ) -> None:
        context = make_context()

        with pytest.raises(
            ValidationError,
        ):
            context.attributes = {
                "new": "value",
            }

    def test_nested_attributes_remain_mutable(
        self,
    ) -> None:
        """
        frozen=True prevents field assignment, but it does not recursively
        freeze mutable values stored inside fields.
        """

        context = make_context()

        context.attributes[
            "region"
        ] = "eu"

        assert context.attributes == {
            "region": "eu",
        }


class TestExtraFields:
    def test_extra_fields_are_forbidden(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            LogContext(
                application="test-application",
                environment="dev",
                unexpected="value",
            )

        assert any(
            error["loc"]
            == ("unexpected",)
            for error
            in exception_info.value.errors()
        )

    def test_model_config_forbids_extra_fields(
        self,
    ) -> None:
        assert (
            LogContext.model_config[
                "extra"
            ]
            == "forbid"
        )


class TestModelFields:
    def test_expected_fields(
        self,
    ) -> None:
        assert set(
            LogContext.model_fields
        ) == {
            "application",
            "environment",
            "correlation_id",
            "run_id",
            "attributes",
        }

    @pytest.mark.parametrize(
        "field_name",
        [
            "application",
            "environment",
        ],
    )
    def test_required_fields(
        self,
        field_name: str,
    ) -> None:
        assert (
            LogContext.model_fields[
                field_name
            ].is_required()
            is True
        )

    @pytest.mark.parametrize(
        "field_name",
        [
            "correlation_id",
            "run_id",
            "attributes",
        ],
    )
    def test_defaulted_fields_are_not_required(
        self,
        field_name: str,
    ) -> None:
        assert (
            LogContext.model_fields[
                field_name
            ].is_required()
            is False
        )


class TestModelDump:
    def test_model_dump_contains_all_fields(
        self,
    ) -> None:
        context = LogContext(
            application="orders",
            environment="prod",
            correlation_id="correlation-1",
            run_id="run-1",
            attributes={
                "region": "eu",
            },
        )

        assert context.model_dump() == {
            "application": "orders",
            "environment": "prod",
            "correlation_id": "correlation-1",
            "run_id": "run-1",
            "attributes": {
                "region": "eu",
            },
        }

    def test_default_run_id_is_serialised_as_none(
        self,
    ) -> None:
        context = make_context(
            correlation_id="correlation-1",
        )

        result = context.model_dump()

        assert result["run_id"] is None

    def test_default_attributes_are_serialised(
        self,
    ) -> None:
        context = make_context(
            correlation_id="correlation-1",
        )

        result = context.model_dump()

        assert result["attributes"] == {}


class TestJsonSerialisation:
    def test_model_dump_json_returns_string(
        self,
    ) -> None:
        context = make_context()

        result = context.model_dump_json()

        assert isinstance(
            result,
            str,
        )

    def test_json_contains_application(
        self,
    ) -> None:
        context = make_context(
            application="monitaudit",
        )

        result = context.model_dump_json()

        assert (
            '"application":"monitaudit"'
            in result
        )

    def test_json_contains_environment(
        self,
    ) -> None:
        context = make_context(
            environment="prod",
        )

        result = context.model_dump_json()

        assert (
            '"environment":"prod"'
            in result
        )

    def test_json_contains_explicit_correlation_id(
        self,
    ) -> None:
        context = make_context(
            correlation_id="correlation-123",
        )

        result = context.model_dump_json()

        assert (
            '"correlation_id":"correlation-123"'
            in result
        )


class TestCompleteContext:
    def test_complete_context(
        self,
    ) -> None:
        context = LogContext(
            application="orders",
            environment="prod",
            correlation_id="correlation-123",
            run_id="run-456",
            attributes={
                "region": "eu-west",
                "job": "order-processing",
                "attempt": 2,
            },
        )

        assert context.application == "orders"
        assert context.environment == "prod"
        assert (
            context.correlation_id
            == "correlation-123"
        )
        assert context.run_id == "run-456"
        assert context.attributes == {
            "region": "eu-west",
            "job": "order-processing",
            "attempt": 2,
        }