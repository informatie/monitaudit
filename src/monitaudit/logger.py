# src/monitaudit/logger.py

from __future__ import annotations

import inspect
import sys
import traceback
from typing import Any, Literal, cast

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
from monitaudit.utilities.json_safe import json_safe_dict


SinkFailureMode = Literal[
    "continue",
    "raise",
]

StandardLog = DebugLog | InfoLog | WarningLog
StandardLogType = (
    type[DebugLog]
    | type[InfoLog]
    | type[WarningLog]
)

ExceptionLog = ErrorLog | CriticalLog
ExceptionLogType = (
    type[ErrorLog]
    | type[CriticalLog]
)


class monitauditLogger:
    def __init__(
        self,
        context: LogContext,
        *sinks: Sink,
        sink_failure_mode: SinkFailureMode = "continue",
    ) -> None:
        self.context: LogContext = context
        self.sinks: tuple[Sink, ...] = sinks
        self.sink_failure_mode: SinkFailureMode = (
            sink_failure_mode
        )

    def debug(
        self,
        message: str,
        *,
        call_id: str | None = None,
        parent_call_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        module: str | None = None,
        function: str | None = None,
        **attributes: Any,
    ) -> DebugLog:
        return cast(
            DebugLog,
            self._log(
                DebugLog,
                message,
                call_id=call_id,
                parent_call_id=parent_call_id,
                parameters=parameters,
                duration_ms=duration_ms,
                module=module,
                function=function,
                attributes=attributes,
            ),
        )

    def info(
        self,
        message: str,
        *,
        call_id: str | None = None,
        parent_call_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        module: str | None = None,
        function: str | None = None,
        **attributes: Any,
    ) -> InfoLog:
        return cast(
            InfoLog,
            self._log(
                InfoLog,
                message,
                call_id=call_id,
                parent_call_id=parent_call_id,
                parameters=parameters,
                duration_ms=duration_ms,
                module=module,
                function=function,
                attributes=attributes,
            ),
        )

    def warning(
        self,
        message: str,
        *,
        call_id: str | None = None,
        parent_call_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        module: str | None = None,
        function: str | None = None,
        **attributes: Any,
    ) -> WarningLog:
        return cast(
            WarningLog,
            self._log(
                WarningLog,
                message,
                call_id=call_id,
                parent_call_id=parent_call_id,
                parameters=parameters,
                duration_ms=duration_ms,
                module=module,
                function=function,
                attributes=attributes,
            ),
        )

    def error(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        call_id: str | None = None,
        parent_call_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        module: str | None = None,
        function: str | None = None,
        **attributes: Any,
    ) -> ErrorLog:
        return cast(
            ErrorLog,
            self._log_exception(
                ErrorLog,
                message,
                exception=exception,
                call_id=call_id,
                parent_call_id=parent_call_id,
                parameters=parameters,
                duration_ms=duration_ms,
                module=module,
                function=function,
                attributes=attributes,
            ),
        )

    def critical(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        call_id: str | None = None,
        parent_call_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        module: str | None = None,
        function: str | None = None,
        **attributes: Any,
    ) -> CriticalLog:
        return cast(
            CriticalLog,
            self._log_exception(
                CriticalLog,
                message,
                exception=exception,
                call_id=call_id,
                parent_call_id=parent_call_id,
                parameters=parameters,
                duration_ms=duration_ms,
                module=module,
                function=function,
                attributes=attributes,
            ),
        )

    def _log(
        self,
        log_type: StandardLogType,
        message: str,
        *,
        call_id: str | None,
        parent_call_id: str | None,
        parameters: dict[str, Any] | None,
        duration_ms: float | None,
        module: str | None,
        function: str | None,
        attributes: dict[str, Any],
    ) -> StandardLog:
        resolved_module, resolved_function = self._resolve_caller(
            module=module,
            function=function,
        )

        log = log_type(
            message=message,
            context=self.context,
            call_id=call_id,
            parent_call_id=parent_call_id,
            parameters=self._prepare_parameters(
                parameters
            ),
            duration_ms=duration_ms,
            module=resolved_module,
            function=resolved_function,
            attributes=self._prepare_attributes(
                attributes
            ),
        )

        self._write(log)

        return log

    def _log_exception(
        self,
        log_type: ExceptionLogType,
        message: str,
        *,
        exception: BaseException | None,
        call_id: str | None,
        parent_call_id: str | None,
        parameters: dict[str, Any] | None,
        duration_ms: float | None,
        module: str | None,
        function: str | None,
        attributes: dict[str, Any],
    ) -> ExceptionLog:
        resolved_module, resolved_function = self._resolve_caller(
            module=module,
            function=function,
        )

        (
            error_type,
            error_message,
            traceback_lines,
        ) = self._serialize_exception(exception)

        log = log_type(
            message=message,
            context=self.context,
            call_id=call_id,
            parent_call_id=parent_call_id,
            parameters=self._prepare_parameters(
                parameters
            ),
            duration_ms=duration_ms,
            module=resolved_module,
            function=resolved_function,
            attributes=self._prepare_attributes(
                attributes
            ),
            error_type=error_type,
            error_message=error_message,
            traceback=traceback_lines,
        )

        self._write(log)

        return log

    @staticmethod
    def _prepare_parameters(
        parameters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Convert parameters to JSON-safe values.

        Parameter redaction and size limiting are performed by
        Observability.trace(). This method provides the final safety
        boundary before parameters are stored in the log model.
        """
        if not parameters:
            return {}

        return json_safe_dict(parameters)

    @staticmethod
    def _prepare_attributes(
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert arbitrary structured attributes to JSON-safe values.

        This protects all sinks from unsupported objects such as Path,
        UUID, datetime, Enum, set, Pydantic models, and custom classes.
        """
        if not attributes:
            return {}

        return json_safe_dict(attributes)

    @staticmethod
    def _serialize_exception(
        exception: BaseException | None,
    ) -> tuple[
        str | None,
        str | None,
        list[str],
    ]:
        """
        Convert an exception into serialisable error fields.

        The raw exception object is never stored in a log model or
        passed to a sink.
        """
        if exception is None:
            return None, None, []

        return (
            type(exception).__name__,
            str(exception),
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            ),
        )

    @staticmethod
    def _report_sink_failure(
        *,
        sink: Sink,
        exception: Exception,
    ) -> None:
        print(
            (
                "monitaudit sink failure: "
                f"{type(sink).__name__}: "
                f"{type(exception).__name__}: "
                f"{exception}"
            ),
            file=sys.stderr,
        )

    def _write(
        self,
        log: BaseLog,
    ) -> None:
        failures: list[
            tuple[Sink, Exception]
        ] = []

        for sink in self.sinks:
            try:
                sink.write(log)

            except Exception as exception:
                failures.append(
                    (
                        sink,
                        exception,
                    )
                )

                self._report_sink_failure(
                    sink=sink,
                    exception=exception,
                )

        if (
            failures
            and self.sink_failure_mode == "raise"
        ):
            sink_names = ", ".join(
                type(sink).__name__
                for sink, _ in failures
            )

            raise RuntimeError(
                f"monitaudit sink failure(s): {sink_names}"
            ) from failures[0][1]

    def _resolve_caller(
        self,
        *,
        module: str | None,
        function: str | None,
    ) -> tuple[
        str | None,
        str | None,
    ]:
        if (
            module is not None
            and function is not None
        ):
            return module, function

        (
            detected_module,
            detected_function,
        ) = self._caller()

        return (
            module or detected_module,
            function or detected_function,
        )

    @staticmethod
    def _caller() -> tuple[
        str | None,
        str | None,
    ]:
        frame = inspect.currentframe()

        if frame is None:
            return None, None

        try:
            caller = frame.f_back

            while caller is not None:
                module = caller.f_globals.get(
                    "__name__"
                )
                function = (
                    caller.f_code.co_name
                )

                if module not in {
                    __name__,
                    "monitaudit.models.monitaudit",
                }:
                    return module, function

                caller = caller.f_back

            return None, None

        finally:
            del frame