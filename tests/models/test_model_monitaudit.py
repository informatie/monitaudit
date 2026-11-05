# tests/models/test_model_monitaudit.py

from __future__ import annotations

from typing import Any, cast

import pytest

from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)
from monitaudit.models.monitaudit import Monitaudit


class RecordingLogger:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def _record(
        self,
        level: str,
        message: str,
        *,
        exception: BaseException | None = None,
        **attributes: Any,
    ) -> Any:
        record = {
            "level": level,
            "message": message,
            "exception": exception,
            **attributes,
        }

        self.records.append(record)

        return record

    def debug(
        self,
        message: str,
        **attributes: Any,
    ) -> Any:
        return self._record(
            "DEBUG",
            message,
            **attributes,
        )

    def info(
        self,
        message: str,
        **attributes: Any,
    ) -> Any:
        return self._record(
            "INFO",
            message,
            **attributes,
        )

    def warning(
        self,
        message: str,
        **attributes: Any,
    ) -> Any:
        return self._record(
            "WARNING",
            message,
            **attributes,
        )

    def error(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        **attributes: Any,
    ) -> Any:
        return self._record(
            "ERROR",
            message,
            exception=exception,
            **attributes,
        )

    def critical(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        **attributes: Any,
    ) -> Any:
        return self._record(
            "CRITICAL",
            message,
            exception=exception,
            **attributes,
        )


@pytest.fixture
def recording_logger() -> RecordingLogger:
    return RecordingLogger()


@pytest.fixture
def mta(
    recording_logger: RecordingLogger,
) -> Monitaudit:
    instance = Monitaudit.__new__(
        Monitaudit
    )

    instance.timer = False
    instance.show_parameters = True
    instance.max_parameter_length = 1000
    instance.logger = cast(
        Any,
        recording_logger,
    )

    return instance


class TestLogging:
    @pytest.mark.parametrize(
        ("method_name", "level"),
        [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
        ],
    )
    def test_log_level(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
        method_name: str,
        level: str,
    ) -> None:
        method = getattr(
            mta,
            method_name,
        )

        method(
            "Test message",
            project_id="A-1000007",
        )

        record = recording_logger.records[-1]

        assert record["level"] == level
        assert record["message"] == "Test message"
        assert (
            record["project_id"]
            == "A-1000007"
        )

    @pytest.mark.parametrize(
        ("method_name", "level"),
        [
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ],
    )
    def test_exception_is_preserved(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
        method_name: str,
        level: str,
    ) -> None:
        exception = ValueError(
            "invalid value"
        )

        method = getattr(
            mta,
            method_name,
        )

        method(
            "Operation failed",
            exception=exception,
        )

        record = recording_logger.records[-1]

        assert record["level"] == level
        assert record["exception"] is exception


class TestTrace:
    def test_trace_logs_start_and_end(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        @mta.trace
        def add(
            left: int,
            right: int = 2,
        ) -> int:
            return left + right

        assert add(3) == 5

        assert len(
            recording_logger.records
        ) == 2

        start, end = (
            recording_logger.records
        )

        assert start["event"] == FUNCTION_START
        assert end["event"] == FUNCTION_END

        assert start["function"] == "add"
        assert end["function"] == "add"

        assert start["parameters"] == {
            "left": 3,
            "right": 2,
        }

        assert (
            start["call_id"]
            == end["call_id"]
        )

    def test_trace_error_preserves_and_reraises_exception(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        expected = ValueError(
            "operation failed"
        )

        @mta.trace
        def fail() -> None:
            raise expected

        with pytest.raises(
            ValueError
        ) as exception_info:
            fail()

        assert (
            exception_info.value
            is expected
        )

        assert len(
            recording_logger.records
        ) == 2

        start, error = (
            recording_logger.records
        )

        assert start["event"] == FUNCTION_START
        assert error["event"] == FUNCTION_ERROR

        assert (
            error["exception"]
            is expected
        )

        assert (
            start["call_id"]
            == error["call_id"]
        )

    def test_nested_trace_preserves_parent_child_relationship(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        @mta.trace
        def inner() -> None:
            pass

        @mta.trace
        def outer() -> None:
            inner()

        outer()

        starts = [
            record
            for record in recording_logger.records
            if (
                record.get("event")
                == FUNCTION_START
            )
        ]

        assert len(starts) == 2

        outer_start = next(
            record
            for record in starts
            if record["function"] == "outer"
        )

        inner_start = next(
            record
            for record in starts
            if record["function"] == "inner"
        )

        assert outer_start["call_id"]
        assert inner_start["call_id"]

        assert (
            outer_start["call_id"]
            != inner_start["call_id"]
        )

        assert (
            outer_start["parent_call_id"]
            is None
        )

        assert (
            inner_start["parent_call_id"]
            == outer_start["call_id"]
        )

    def test_log_inside_trace_uses_trace_call_id(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        @mta.trace
        def operation() -> None:
            mta.info(
                "Inside operation"
            )

        operation()

        start = next(
            record
            for record in recording_logger.records
            if (
                record.get("event")
                == FUNCTION_START
            )
        )

        application_log = next(
            record
            for record in recording_logger.records
            if (
                record["message"]
                == "Inside operation"
            )
        )

        assert (
            application_log["call_id"]
            == start["call_id"]
        )

    def test_parameters_can_be_hidden(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        mta.show_parameters = False

        @mta.trace
        def authenticate(
            username: str,
            password: str,
        ) -> bool:
            return True

        assert authenticate(
            "zadmin",
            "secret",
        )

        for record in recording_logger.records:
            assert record["parameters"] == {}

    def test_sensitive_parameters_are_redacted(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        @mta.trace
        def authenticate(
            username: str,
            password: str,
        ) -> bool:
            return True

        authenticate(
            username="zadmin",
            password="very-secret",
        )

        parameters = (
            recording_logger.records[0][
                "parameters"
            ]
        )

        assert (
            parameters["username"]
            == "zadmin"
        )

        assert (
            parameters["password"]
            != "very-secret"
        )

    def test_parameter_length_is_limited(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        mta.max_parameter_length = 5

        @mta.trace
        def operation(
            value: str,
        ) -> None:
            pass

        operation(
            "1234567890"
        )

        parameters = (
            recording_logger.records[0][
                "parameters"
            ]
        )

        assert (
            parameters["value"]
            != "1234567890"
        )

    def test_trace_preserves_function_metadata(
        self,
        mta: Monitaudit,
    ) -> None:
        def operation(
            value: int,
        ) -> int:
            """Return the value."""
            return value

        traced = mta.trace(
            operation
        )

        assert (
            traced.__name__
            == operation.__name__
        )

        assert (
            traced.__doc__
            == operation.__doc__
        )

    def test_invalid_arguments_do_not_create_trace(
        self,
        mta: Monitaudit,
        recording_logger: RecordingLogger,
    ) -> None:
        @mta.trace
        def operation(
            required: int,
        ) -> int:
            return required

        with pytest.raises(
            TypeError,
        ):
            operation()

        assert (
            recording_logger.records
            == []
        )


class TestConfiguration:
    def test_negative_max_parameter_length_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "max_parameter_length "
                "must be 0 or greater"
            ),
        ):
            Monitaudit(
                application="test",
                environment="dev",
                max_parameter_length=-1,
            )