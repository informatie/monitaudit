# src/monitaudit/models/monitaudit.py

from __future__ import annotations

import inspect
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from time import perf_counter
from typing import Any, ParamSpec, TypeVar
from uuid import uuid4

from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)
from monitaudit.logger import (
    SinkFailureMode,
    monitauditLogger,
)
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
from monitaudit.utilities.parameters import limit_parameters
from monitaudit.utilities.redaction import redact_parameters


P = ParamSpec("P")
R = TypeVar("R")


_current_call_id: ContextVar[str | None] = ContextVar(
    "monitaudit_current_call_id",
    default=None,
)


class Monitaudit:
    def __init__(
        self,
        application: str,
        environment: str,
        *sinks: Sink,
        correlation_id: str | None = None,
        run_id: str | None = None,
        context_attributes: dict[str, Any] | None = None,
        timer: bool = True,
        parameters: bool = True,
        max_parameter_length: int = 1000,
        sink_failure_mode: SinkFailureMode = "continue",
    ) -> None:
        if max_parameter_length < 0:
            raise ValueError(
                "max_parameter_length must be 0 or greater."
            )

        if correlation_id is None:
            self.context = LogContext(
                application=application,
                environment=environment,
                run_id=run_id,
                attributes=(
                    dict(context_attributes)
                    if context_attributes is not None
                    else {}
                ),
            )
        else:
            self.context = LogContext(
                application=application,
                environment=environment,
                correlation_id=correlation_id,
                run_id=run_id,
                attributes=(
                    dict(context_attributes)
                    if context_attributes is not None
                    else {}
                ),
            )

        self.timer = timer
        self.parameters = parameters
        self.max_parameter_length = max_parameter_length

        self.logger = monitauditLogger(
            self.context,
            *sinks,
            sink_failure_mode=sink_failure_mode,
        )

    @property
    def correlation_id(self) -> str:
        return self.context.correlation_id

    @property
    def run_id(self) -> str | None:
        return self.context.run_id

    @property
    def current_call_id(self) -> str | None:
        return _current_call_id.get()

    def debug(
        self,
        message: str,
        **attributes: Any,
    ) -> DebugLog:
        return self.logger.debug(
            message,
            call_id=self.current_call_id,
            **attributes,
        )

    def info(
        self,
        message: str,
        **attributes: Any,
    ) -> InfoLog:
        return self.logger.info(
            message,
            call_id=self.current_call_id,
            **attributes,
        )

    def warning(
        self,
        message: str,
        **attributes: Any,
    ) -> WarningLog:
        return self.logger.warning(
            message,
            call_id=self.current_call_id,
            **attributes,
        )

    def error(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        **attributes: Any,
    ) -> ErrorLog:
        return self.logger.error(
            message,
            exception=exception,
            call_id=self.current_call_id,
            **attributes,
        )

    def critical(
        self,
        message: str,
        *,
        exception: BaseException | None = None,
        **attributes: Any,
    ) -> CriticalLog:
        return self.logger.critical(
            message,
            exception=exception,
            call_id=self.current_call_id,
            **attributes,
        )

    @staticmethod
    def _duration_ms(
        started_at: float | None,
    ) -> float | None:
        if started_at is None:
            return None

        return round(
            (perf_counter() - started_at) * 1000,
            3,
        )

    def trace(
        self,
        function: Callable[P, R],
    ) -> Callable[P, R]:
        signature = inspect.signature(
            function
        )

        module = function.__module__
        function_name = function.__name__

        @wraps(function)
        def wrapper(
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            if self.parameters:
                bound = signature.bind(
                    *args,
                    **kwargs,
                )

                bound.apply_defaults()

                captured_parameters = redact_parameters(
                    dict(bound.arguments)
                )

                captured_parameters = json_safe_dict(
                    captured_parameters
                )

                captured_parameters = limit_parameters(
                    captured_parameters,
                    self.max_parameter_length,
                )

            else:
                captured_parameters = {}

            parent_call_id = _current_call_id.get()
            call_id = str(uuid4())

            token = _current_call_id.set(
                call_id
            )

            started_at = (
                perf_counter()
                if self.timer
                else None
            )

            try:
                self.logger.info(
                    f"{function_name} started",
                    call_id=call_id,
                    parent_call_id=parent_call_id,
                    parameters=captured_parameters,
                    module=module,
                    function=function_name,
                    event=FUNCTION_START,
                )

                try:
                    result = function(
                        *args,
                        **kwargs,
                    )

                except Exception as exception:
                    self.logger.error(
                        f"{function_name} failed",
                        exception=exception,
                        call_id=call_id,
                        parent_call_id=parent_call_id,
                        parameters=captured_parameters,
                        duration_ms=self._duration_ms(
                            started_at
                        ),
                        module=module,
                        function=function_name,
                        event=FUNCTION_ERROR,
                    )

                    raise

                else:
                    self.logger.info(
                        f"{function_name} completed",
                        call_id=call_id,
                        parent_call_id=parent_call_id,
                        parameters=captured_parameters,
                        duration_ms=self._duration_ms(
                            started_at
                        ),
                        module=module,
                        function=function_name,
                        event=FUNCTION_END,
                    )

                    return result

            finally:
                _current_call_id.reset(
                    token
                )

        return wrapper