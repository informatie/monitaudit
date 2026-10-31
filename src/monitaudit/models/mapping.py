# src/monitaudit/models/mapping.py

from __future__ import annotations

from typing import Any

from monitaudit.models.base import BaseLog


LOG_FIELD_NAMES: tuple[str, ...] = (
    # WHEN
    "timestamp",

    # SEVERITY
    "level",

    # WHERE
    "application",
    "environment",
    "module",
    "function",

    # WHICH EXECUTION
    "correlation_id",
    "run_id",
    "call_id",
    "parent_call_id",

    # WHAT
    "event",
    "message",
    "parameters",
    "attributes",

    # PERFORMANCE
    "duration_ms",

    # FAILURE
    "error_type",
    "error_message",
    "traceback",
)


def log_record(
    log: BaseLog,
) -> dict[str, Any]:
    record = {
        # WHEN
        "timestamp": log.timestamp,

        # SEVERITY
        "level": log.level,

        # WHERE
        "application": log.context.application,
        "environment": log.context.environment,
        "module": log.module,
        "function": log.function,

        # WHICH EXECUTION
        "correlation_id": log.context.correlation_id,
        "run_id": log.context.run_id,
        "call_id": log.call_id,
        "parent_call_id": log.parent_call_id,

        # WHAT
        "event": log.attributes.get("event"),
        "message": log.message,
        "parameters": log.parameters,
        "attributes": log.attributes,

        # PERFORMANCE
        "duration_ms": log.duration_ms,

        # FAILURE
        "error_type": getattr(
            log,
            "error_type",
            None,
        ),
        "error_message": getattr(
            log,
            "error_message",
            None,
        ),
        "traceback": getattr(
            log,
            "traceback",
            None,
        ),
    }

    if tuple(record) != LOG_FIELD_NAMES:
        raise RuntimeError(
            "Canonical log record does not match LOG_FIELD_NAMES."
        )

    return record