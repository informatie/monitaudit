# tests/models/test_model_log.py

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext
from monitaudit.models.log import (
    CriticalLog,
    DebugLog,
    ErrorLog,
    InfoLog,
    WarningLog,
)


def make_context() -> LogContext:
    return LogContext(
        application="test-application",
        environment="dev",
        correlation_id="correlation-1",
    )


def make_log(
    log_type: type[BaseLog],
    **overrides: Any,
) -> BaseLog:
    values: dict[str, Any] = {
        "context": make_context(),
        "message": "Test message",
    }

    values.update(overrides)

    return log_type(**values)


STANDARD_LOG_TYPES: list[tuple[type[BaseLog], str]] = [
    (DebugLog, "DEBUG"),
    (InfoLog, "INFO"),
    (WarningLog, "WARNING"),
]

EXCEPTION_LOG_TYPES: list[tuple[type[BaseLog], str]] = [
    (ErrorLog, "ERROR"),
    (CriticalLog, "CRITICAL"),
]

ALL_LOG_TYPES: list[tuple[type[BaseLog], str]] = (
    STANDARD_LOG_TYPES
    + EXCEPTION_LOG_TYPES
)


class TestInheritance:
    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_log_type_inherits_from_base_log(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        assert issubclass(
            log_type,
            BaseLog,
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_instance_is_base_log(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        assert isinstance(
            log,
            BaseLog,
        )


class TestDefaultLevels:
    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_default_level(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        log = make_log(log_type)

        assert log.level == expected_level

    def test_debug_level(
        self,
    ) -> None:
        log = make_log(DebugLog)

        assert log.level == "DEBUG"

    def test_info_level(
        self,
    ) -> None:
        log = make_log(InfoLog)

        assert log.level == "INFO"

    def test_warning_level(
        self,
    ) -> None:
        log = make_log(WarningLog)

        assert log.level == "WARNING"

    def test_error_level(
        self,
    ) -> None:
        log = make_log(ErrorLog)

        assert log.level == "ERROR"

    def test_critical_level(
        self,
    ) -> None:
        log = make_log(CriticalLog)

        assert log.level == "CRITICAL"


class TestExplicitCorrectLevels:
    @pytest.mark.parametrize(
        ("log_type", "level"),
        ALL_LOG_TYPES,
    )
    def test_explicit_correct_level_is_allowed(
        self,
        log_type: type[BaseLog],
        level: str,
    ) -> None:
        log = make_log(
            log_type,
            level=level,
        )

        assert log.level == level


class TestIncorrectLevels:
    @pytest.mark.parametrize(
        (
            "log_type",
            "expected_level",
            "invalid_level",
        ),
        [
            (DebugLog, "DEBUG", "INFO"),
            (InfoLog, "INFO", "DEBUG"),
            (WarningLog, "WARNING", "ERROR"),
            (ErrorLog, "ERROR", "WARNING"),
            (CriticalLog, "CRITICAL", "ERROR"),
        ],
    )
    def test_rejects_wrong_level(
        self,
        log_type: type[BaseLog],
        expected_level: str,
        invalid_level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            make_log(
                log_type,
                level=invalid_level,
            )

        errors = exception_info.value.errors()

        assert any(
            error["loc"] == ("level",)
            for error in errors
        )

        assert expected_level in str(
            exception_info.value
        )

    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_level_is_case_sensitive(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                level=expected_level.lower(),
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_empty_level_is_rejected(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                level="",
            )


class TestRequiredBaseFields:
    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_context_is_required(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            log_type(
                message="Test message",
            )

        assert any(
            error["loc"] == ("context",)
            for error in exception_info.value.errors()
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_message_is_required(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ) as exception_info:
            log_type(
                context=make_context(),
            )

        assert any(
            error["loc"] == ("message",)
            for error in exception_info.value.errors()
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_empty_message_is_rejected(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                message="",
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_single_character_message_is_allowed(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            message="x",
        )

        assert log.message == "x"


class TestBaseLogFields:
    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_inherited_fields_can_be_populated(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        log = make_log(
            log_type,
            module="application.module",
            function="process",
            call_id="call-1",
            parent_call_id="parent-1",
            event="custom-event",
            parameters={
                "customer_id": 42,
            },
            duration_ms=125.5,
            attributes={
                "region": "eu",
            },
        )

        assert log.level == expected_level
        assert log.module == "application.module"
        assert log.function == "process"
        assert log.call_id == "call-1"
        assert log.parent_call_id == "parent-1"
        assert log.event == "custom-event"

        assert log.parameters == {
            "customer_id": 42,
        }

        assert log.duration_ms == 125.5

        assert log.attributes == {
            "region": "eu",
        }

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_inherited_fields_have_expected_defaults(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        assert log.module is None
        assert log.function is None
        assert log.call_id is None
        assert log.parent_call_id is None
        assert log.event is None
        assert log.parameters == {}
        assert log.duration_ms is None
        assert log.attributes == {}

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_zero_duration_is_allowed(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            duration_ms=0,
        )

        assert log.duration_ms == 0

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_negative_duration_is_rejected(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                duration_ms=-1,
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_extra_fields_are_rejected(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                unexpected="value",
            )


class TestMutableDefaults:
    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_parameters_default_is_independent(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        first = make_log(log_type)
        second = make_log(log_type)

        assert first.parameters is not second.parameters

        first.parameters["value"] = 1

        assert second.parameters == {}

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_attributes_default_is_independent(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        first = make_log(log_type)
        second = make_log(log_type)

        assert first.attributes is not second.attributes

        first.attributes["value"] = 1

        assert second.attributes == {}


class TestStandardLogs:
    @pytest.mark.parametrize(
        ("log_type", "_level"),
        STANDARD_LOG_TYPES,
    )
    def test_standard_log_inherits_failure_defaults(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        assert log.error_type is None
        assert log.error_message is None
        assert log.traceback is None

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        STANDARD_LOG_TYPES,
    )
    def test_standard_log_can_explicitly_have_error_fields(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            error_type="ValueError",
            error_message="failure",
            traceback=[
                "ValueError: failure\n",
            ],
        )

        assert log.error_type == "ValueError"
        assert log.error_message == "failure"

        assert log.traceback == [
            "ValueError: failure\n",
        ]

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        STANDARD_LOG_TYPES,
    )
    def test_standard_log_allows_none_traceback(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            traceback=None,
        )

        assert log.traceback is None


class TestExceptionLogs:
    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_exception_fields_default_to_none(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        assert log.error_type is None
        assert log.error_message is None

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_defaults_to_empty_list(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        assert log.traceback == []

        assert isinstance(
            log.traceback,
            list,
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_default_is_independent(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        first = make_log(log_type)
        second = make_log(log_type)

        assert first.traceback is not second.traceback

        assert first.traceback is not None

        first.traceback.append(
            "first traceback\n"
        )

        assert second.traceback == []

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_exception_fields_can_be_populated(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        traceback_lines = [
            "Traceback (most recent call last):\n",
            "ValueError: invalid value\n",
        ]

        log = make_log(
            log_type,
            error_type="ValueError",
            error_message="invalid value",
            traceback=traceback_lines,
        )

        assert log.error_type == "ValueError"
        assert log.error_message == "invalid value"

        assert log.traceback == traceback_lines

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_tuple_is_converted_to_list(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            traceback=(
                "first\n",
                "second\n",
            ),
        )

        assert log.traceback == [
            "first\n",
            "second\n",
        ]

        assert isinstance(
            log.traceback,
            list,
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_empty_tuple_is_converted_to_empty_list(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(
            log_type,
            traceback=(),
        )

        assert log.traceback == []

        assert isinstance(
            log.traceback,
            list,
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_none_is_rejected(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                traceback=None,
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_rejects_non_sequence_value(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                traceback=123,
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_rejects_dictionary(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                traceback={
                    "line": "failure",
                },
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_rejects_string_as_list(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                traceback="ValueError: failure",
            )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_traceback_rejects_invalid_item_type(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_log(
                log_type,
                traceback=[
                    "first\n",
                    123,
                ],
            )


class TestErrorLog:
    def test_complete_error_log(
        self,
    ) -> None:
        log = make_log(
            ErrorLog,
            message="Processing failed",
            error_type="ValueError",
            error_message="Invalid value",
            traceback=[
                "Traceback:\n",
                "ValueError: Invalid value\n",
            ],
        )

        assert log.level == "ERROR"
        assert log.message == "Processing failed"
        assert log.error_type == "ValueError"
        assert log.error_message == "Invalid value"

        assert log.traceback == [
            "Traceback:\n",
            "ValueError: Invalid value\n",
        ]

    def test_error_type_can_be_none(
        self,
    ) -> None:
        log = make_log(
            ErrorLog,
            error_type=None,
        )

        assert log.error_type is None

    def test_error_message_can_be_none(
        self,
    ) -> None:
        log = make_log(
            ErrorLog,
            error_message=None,
        )

        assert log.error_message is None


class TestCriticalLog:
    def test_complete_critical_log(
        self,
    ) -> None:
        log = make_log(
            CriticalLog,
            message="Application cannot continue",
            error_type="RuntimeError",
            error_message="Fatal failure",
            traceback=[
                "RuntimeError: Fatal failure\n",
            ],
        )

        assert log.level == "CRITICAL"
        assert (
            log.message
            == "Application cannot continue"
        )
        assert log.error_type == "RuntimeError"
        assert log.error_message == "Fatal failure"

        assert log.traceback == [
            "RuntimeError: Fatal failure\n",
        ]

    def test_error_type_can_be_none(
        self,
    ) -> None:
        log = make_log(
            CriticalLog,
            error_type=None,
        )

        assert log.error_type is None

    def test_error_message_can_be_none(
        self,
    ) -> None:
        log = make_log(
            CriticalLog,
            error_message=None,
        )

        assert log.error_message is None


class TestModelFields:
    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_level_field_is_not_required(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        field = log_type.model_fields["level"]

        assert field.is_required() is False
        assert field.default == expected_level

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_exception_traceback_field_is_not_required(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        assert (
            log_type.model_fields[
                "traceback"
            ].is_required()
            is False
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        STANDARD_LOG_TYPES,
    )
    def test_standard_traceback_default_is_none(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        assert (
            log_type.model_fields[
                "traceback"
            ].default
            is None
        )


class TestSerialisation:
    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_model_dump_contains_fixed_level(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        log = make_log(log_type)

        result = log.model_dump()

        assert (
            result["level"]
            == expected_level
        )

    @pytest.mark.parametrize(
        ("log_type", "expected_level"),
        ALL_LOG_TYPES,
    )
    def test_json_contains_fixed_level(
        self,
        log_type: type[BaseLog],
        expected_level: str,
    ) -> None:
        log = make_log(log_type)

        result = log.model_dump_json()

        assert (
            f'"level":"{expected_level}"'
            in result
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_exception_model_dump_contains_empty_traceback_by_default(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        result = log.model_dump()

        assert result["traceback"] == []

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        EXCEPTION_LOG_TYPES,
    )
    def test_exception_json_contains_empty_traceback_by_default(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        result = log.model_dump_json()

        assert (
            '"traceback":[]'
            in result
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        STANDARD_LOG_TYPES,
    )
    def test_standard_json_contains_null_traceback_by_default(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        log = make_log(log_type)

        result = log.model_dump_json()

        assert (
            '"traceback":null'
            in result
        )


class TestTypeDistinction:
    def test_all_log_types_are_distinct_classes(
        self,
    ) -> None:
        log_types = {
            DebugLog,
            InfoLog,
            WarningLog,
            ErrorLog,
            CriticalLog,
        }

        assert len(log_types) == 5

    def test_debug_log_is_not_info_log(
        self,
    ) -> None:
        log = make_log(DebugLog)

        assert not isinstance(
            log,
            InfoLog,
        )

    def test_info_log_is_not_warning_log(
        self,
    ) -> None:
        log = make_log(InfoLog)

        assert not isinstance(
            log,
            WarningLog,
        )

    def test_error_log_is_not_critical_log(
        self,
    ) -> None:
        log = make_log(ErrorLog)

        assert not isinstance(
            log,
            CriticalLog,
        )

    @pytest.mark.parametrize(
        ("log_type", "_level"),
        ALL_LOG_TYPES,
    )
    def test_every_specialised_log_is_base_log(
        self,
        log_type: type[BaseLog],
        _level: str,
    ) -> None:
        assert isinstance(
            make_log(log_type),
            BaseLog,
        )