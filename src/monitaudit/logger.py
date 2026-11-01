# src/monitaudit/logger.py

from __future__ import annotations

import inspect
import sys
import traceback
from types import FrameType
from typing import (
    Any,
    Final,
    Literal,
    TypeAlias,
    cast,
)

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

SinkFailureMode: TypeAlias = Literal[
    "continue",
    "raise",
]

StandardLog: TypeAlias = (
    DebugLog
    | InfoLog
    | WarningLog
)

StandardLogType: TypeAlias = (
    type[DebugLog]
    | type[InfoLog]
    | type[WarningLog]
)

ExceptionLog: TypeAlias = (
    ErrorLog
    | CriticalLog
)

ExceptionLogType: TypeAlias = (
    type[ErrorLog]
    | type[CriticalLog]
)

SinkFailure: TypeAlias = tuple[
    Sink,
    Exception,
]


_INTERNAL_CALLER_MODULES: Final[frozenset[str]] = (
    frozenset(
        {
            "monitaudit.logger",
            "monitaudit.models.monitaudit",
        }
    )
)


class monitauditLogger:
    def __init__(
        self,
        context: LogContext,
        *sinks: Sink,
        sink_failure_mode: SinkFailureMode = "continue",
    ) -> None:
        self._validate_context(context)
        self._validate_sinks(sinks)
        self._validate_sink_failure_mode(
            sink_failure_mode
        )

        self.context: LogContext = context
        self.sinks: tuple[Sink, ...] = tuple(sinks)
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
        log = self._log(
            DebugLog,
            message,
            call_id=call_id,
            parent_call_id=parent_call_id,
            parameters=parameters,
            duration_ms=duration_ms,
            module=module,
            function=function,
            attributes=attributes,
        )

        return cast(
            DebugLog,
            log,
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
        log = self._log(
            InfoLog,
            message,
            call_id=call_id,
            parent_call_id=parent_call_id,
            parameters=parameters,
            duration_ms=duration_ms,
            module=module,
            function=function,
            attributes=attributes,
        )

        return cast(
            InfoLog,
            log,
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
        log = self._log(
            WarningLog,
            message,
            call_id=call_id,
            parent_call_id=parent_call_id,
            parameters=parameters,
            duration_ms=duration_ms,
            module=module,
            function=function,
            attributes=attributes,
        )

        return cast(
            WarningLog,
            log,
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
        log = self._log_exception(
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
        )

        return cast(
            ErrorLog,
            log,
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
        log = self._log_exception(
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
        )

        return cast(
            CriticalLog,
            log,
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
        (
            resolved_module,
            resolved_function,
        ) = self._resolve_caller(
            module=module,
            function=function,
        )

        log: StandardLog = log_type(
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
        (
            resolved_module,
            resolved_function,
        ) = self._resolve_caller(
            module=module,
            function=function,
        )

        (
            error_type,
            error_message,
            traceback_lines,
        ) = self._serialize_exception(
            exception
        )

        log: ExceptionLog = log_type(
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
    def _validate_context(
        context: LogContext,
    ) -> None:
        if not isinstance(context, LogContext):
            raise TypeError(
                "context must be a LogContext instance; "
                f"received {type(context).__name__}."
            )

    @staticmethod
    def _validate_sinks(
        sinks: tuple[Sink, ...],
    ) -> None:
        for sink in sinks:
            if not isinstance(sink, Sink):
                raise TypeError(
                    "All sinks must inherit from Sink; "
                    f"received {type(sink).__name__}."
                )

    @staticmethod
    def _validate_sink_failure_mode(
        sink_failure_mode: str,
    ) -> None:
        if sink_failure_mode not in (
            "continue",
            "raise",
        ):
            raise ValueError(
                "sink_failure_mode must be "
                "'continue' or 'raise'; "
                f"received {sink_failure_mode!r}."
            )

    @staticmethod
    def _prepare_parameters(
        parameters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Convert parameters to JSON-safe values.

        Parameter redaction and size limiting are performed by
        Monitaudit.trace(). This method provides the final safety
        boundary before parameters are stored in the log model.
        """

        if not parameters:
            return {}

        prepared = json_safe_dict(
            dict(parameters)
        )

        return dict(prepared)

    @staticmethod
    def _prepare_attributes(
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert structured attributes to JSON-safe values.

        The resulting mapping is independent from the caller-owned
        top-level dictionary.
        """

        if not attributes:
            return {}

        prepared = json_safe_dict(
            dict(attributes)
        )

        return dict(prepared)

    @staticmethod
    def _safe_exception_text(
        exception: BaseException,
    ) -> str:
        """
        Return an exception message without allowing a faulty
        __str__ implementation to break logging.
        """

        try:
            return str(exception)

        except Exception:
            return (
                "<exception message unavailable>"
            )

    @classmethod
    def _serialize_exception(
        cls,
        exception: BaseException | None,
    ) -> tuple[
        str | None,
        str | None,
        list[str],
    ]:
        """
        Convert an exception into serialisable error fields.

        Raw exceptions are not stored in log models or sent to sinks.
        """

        if exception is None:
            return None, None, []

        error_type = type(exception).__name__

        error_message = cls._safe_exception_text(
            exception
        )

        try:
            formatted_traceback = (
                traceback.format_exception(
                    type(exception),
                    exception,
                    exception.__traceback__,
                )
            )

            traceback_lines: list[str] = list(
                formatted_traceback
            )

        except Exception:
            traceback_lines = [
                f"{error_type}: {error_message}\n"
            ]

        return (
            error_type,
            error_message,
            traceback_lines,
        )

    @classmethod
    def _report_sink_failure(
        cls,
        *,
        sink: Sink,
        exception: Exception,
    ) -> None:
        """
        Report a sink failure directly to stderr.

        Monitaudit is deliberately not used for this message because
        that could recursively invoke the failing sink.
        """

        try:
            sink_name = type(sink).__name__
            exception_name = type(exception).__name__

            exception_message = (
                cls._safe_exception_text(
                    exception
                )
            )

            message = (
                "monitaudit sink failure: "
                f"{sink_name}: "
                f"{exception_name}: "
                f"{exception_message}"
            )

            print(
                message,
                file=sys.stderr,
            )

        except Exception:
            # Failure diagnostics must never interrupt sink fan-out.
            pass

    def _write(
        self,
        log: BaseLog,
    ) -> None:
        """
        Send a log record to all configured sinks.

        continue:
            Sink failures are reported and isolated.

        raise:
            All sinks are attempted first. A RuntimeError is raised
            afterwards if one or more sinks failed.
        """

        failures: list[SinkFailure] = []

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

            first_exception = failures[0][1]

            raise RuntimeError(
                "monitaudit sink failure(s): "
                f"{sink_names}"
            ) from first_exception

    def _resolve_caller(
        self,
        *,
        module: str | None,
        function: str | None,
    ) -> tuple[
        str | None,
        str | None,
    ]:
        """
        Resolve missing source-location values.

        Explicit values are preserved, including empty strings.
        Only None triggers caller detection.
        """

        if (
            module is not None
            and function is not None
        ):
            return module, function

        (
            detected_module,
            detected_function,
        ) = self._caller()

        resolved_module: str | None = (
            module
            if module is not None
            else detected_module
        )

        resolved_function: str | None = (
            function
            if function is not None
            else detected_function
        )

        return (
            resolved_module,
            resolved_function,
        )

    @staticmethod
    def _caller() -> tuple[
        str | None,
        str | None,
    ]:
        """
        Find the first caller outside Monitaudit's known internal
        logging and tracing modules.
        """

        frame: FrameType | None = (
            inspect.currentframe()
        )

        if frame is None:
            return None, None

        caller: FrameType | None = None

        try:
            caller = frame.f_back

            while caller is not None:
                module_value: object = (
                    caller.f_globals.get(
                        "__name__"
                    )
                )

                module: str | None

                if isinstance(module_value, str):
                    module = module_value
                else:
                    module = None

                function: str = (
                    caller.f_code.co_name
                )

                if not monitauditLogger._is_internal_module(
                    module
                ):
                    return (
                        module,
                        function,
                    )

                caller = caller.f_back

            return None, None

        finally:
            del caller
            del frame

    @staticmethod
    def _is_internal_module(
        module: str | None,
    ) -> bool:
        if module is None:
            return False

        return module in _INTERNAL_CALLER_MODULES