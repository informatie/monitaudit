# src/monitaudit/integrations/structlog.py

from __future__ import annotations

import sys
from collections.abc import MutableMapping
from types import TracebackType
from typing import Any, Never, Protocol, TypeAlias, cast

import structlog


ExcInfo: TypeAlias = tuple[
    type[BaseException],
    BaseException,
    TracebackType | None,
]

ResolvedException: TypeAlias = tuple[
    BaseException | None,
    TracebackType | None,
]


class MonitAuditLike(Protocol):
    """Minimum MonitAudit API required by the structlog adapter."""

    def debug(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...

    def info(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...

    def warning(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...

    def error(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...

    def critical(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...

    def exception(
        self,
        message: str,
        *,
        exception: BaseException,
        traceback: TracebackType | None = None,
        correlation_id: str | None = None,
        **fields: Any,
    ) -> None: ...


class MonitAuditProcessor:
    """Terminal structlog processor forwarding events to MonitAudit.

    Normal events are forwarded to the matching MonitAudit level method.
    Events containing valid exception information are forwarded through
    ``MonitAudit.exception()``.

    The processor preserves:

    - an incoming correlation ID without modifying it;
    - the original exception instance;
    - an explicit traceback supplied by structlog;
    - structured event fields;
    - fields that collide with MonitAudit API parameter names.

    MonitAudit remains responsible for:

    - correlation-ID validation and generation;
    - contextual correlation-ID fallback;
    - redaction;
    - JSON-safe conversion;
    - traceback formatting;
    - sink-failure isolation;
    - final event delivery.

    This processor is terminal. It raises ``structlog.DropEvent`` only after
    MonitAudit has successfully accepted the event.
    """

    _METHOD_ALIASES = {
        "warn": "warning",
        "fatal": "critical",
        "exception": "error",
    }

    _SUPPORTED_LEVELS = frozenset(
        {
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        }
    )

    _NORMAL_RESERVED_FIELDS = frozenset(
        {
            "message",
            "correlation_id",
        }
    )

    _EXCEPTION_RESERVED_FIELDS = frozenset(
        {
            "message",
            "correlation_id",
            "exception",
            "traceback",
        }
    )

    _COLLISION_FIELD = "structlog_reserved_fields"
    _NON_STRING_FIELD = "structlog_non_string_fields"

    def __init__(
        self,
        monitaudit: MonitAuditLike,
        *,
        default_level: str = "info",
    ) -> None:
        self._monitaudit = monitaudit
        self._default_level = self._validate_default_level(
            default_level
        )

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> Never:
        del logger

        data = dict(event_dict)

        message = self._resolve_message(
            data.pop("event", "")
        )

        correlation_id = self._resolve_correlation_id(
            data.pop("correlation_id", None)
        )

        exc_info = data.pop("exc_info", None)

        level = self._resolve_level(method_name)
        self._remove_matching_level(data, level)

        exception, traceback = self._resolve_exc_info(
            exc_info
        )

        if exception is not None:
            fields = self._prepare_fields(
                data,
                reserved=self._EXCEPTION_RESERVED_FIELDS,
            )

            self._monitaudit.exception(
                message,
                exception=exception,
                traceback=traceback,
                correlation_id=correlation_id,
                **fields,
            )
        else:
            fields = self._prepare_fields(
                data,
                reserved=self._NORMAL_RESERVED_FIELDS,
            )

            log_method = cast(
                Any,
                getattr(self._monitaudit, level),
            )

            log_method(
                message,
                correlation_id=correlation_id,
                **fields,
            )

        raise structlog.DropEvent

    def _resolve_level(
        self,
        method_name: Any,
    ) -> str:
        if not isinstance(method_name, str):
            return self._default_level

        normalized = self._normalize_level(method_name)

        if normalized in self._SUPPORTED_LEVELS:
            return normalized

        return self._default_level

    @classmethod
    def _validate_default_level(
        cls,
        level: str,
    ) -> str:
        if not isinstance(level, str):
            raise TypeError(
                "default_level must be a string"
            )

        normalized = cls._normalize_level(level)

        if normalized not in cls._SUPPORTED_LEVELS:
            supported = ", ".join(
                sorted(cls._SUPPORTED_LEVELS)
            )

            raise ValueError(
                f"Invalid default_level {level!r}; "
                f"expected one of: {supported}"
            )

        return normalized

    @classmethod
    def _normalize_level(
        cls,
        level: str,
    ) -> str:
        normalized = level.strip().lower()

        return cls._METHOD_ALIASES.get(
            normalized,
            normalized,
        )

    @staticmethod
    def _resolve_message(
        event: Any,
    ) -> str:
        if event is None:
            return ""

        if isinstance(event, str):
            return event

        try:
            return str(event)
        except BaseException:
            return "<unprintable structlog event>"

    @staticmethod
    def _resolve_correlation_id(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                "structlog correlation_id must be "
                "a string or None"
            )

        if not value.strip():
            return None

        return value

    @staticmethod
    def _resolve_exc_info(
        exc_info: Any,
    ) -> ResolvedException:
        if exc_info is None or exc_info is False:
            return None, None

        if exc_info is True:
            _, exception, traceback = sys.exc_info()

            if exception is None:
                return None, None

            return exception, traceback

        if isinstance(exc_info, BaseException):
            return (
                exc_info,
                exc_info.__traceback__,
            )

        if not isinstance(exc_info, tuple):
            return None, None

        if len(exc_info) != 3:
            return None, None

        exception_type, exception, traceback = exc_info

        if not isinstance(exception_type, type):
            return None, None

        if not issubclass(
            exception_type,
            BaseException,
        ):
            return None, None

        if not isinstance(
            exception,
            exception_type,
        ):
            return None, None

        if (
            traceback is not None
            and not isinstance(
                traceback,
                TracebackType,
            )
        ):
            return None, None

        return exception, traceback

    @classmethod
    def _prepare_fields(
        cls,
        data: dict[Any, Any],
        *,
        reserved: frozenset[str],
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        collisions: dict[str, Any] = {}
        non_string_fields: list[tuple[Any, Any]] = []

        for key, value in data.items():
            if not isinstance(key, str):
                non_string_fields.append(
                    (key, value)
                )
                continue

            if key in reserved:
                collisions[key] = value
                continue

            fields[key] = value

        if collisions:
            collision_key = cls._unique_field_name(
                fields,
                cls._COLLISION_FIELD,
            )
            fields[collision_key] = collisions

        if non_string_fields:
            non_string_key = cls._unique_field_name(
                fields,
                cls._NON_STRING_FIELD,
            )
            fields[non_string_key] = (
                non_string_fields
            )

        return fields

    @staticmethod
    def _unique_field_name(
        fields: dict[str, Any],
        preferred_name: str,
    ) -> str:
        if preferred_name not in fields:
            return preferred_name

        suffix = 2

        while True:
            candidate = (
                f"{preferred_name}_{suffix}"
            )

            if candidate not in fields:
                return candidate

            suffix += 1

    @staticmethod
    def _remove_matching_level(
        data: dict[Any, Any],
        resolved_level: str,
    ) -> None:
        level = data.get("level")

        if not isinstance(level, str):
            return

        normalized = (
            MonitAuditProcessor._normalize_level(
                level
            )
        )

        if normalized == resolved_level:
            data.pop("level", None)