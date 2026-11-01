from __future__ import annotations

import json
from typing import Any

from monitaudit.models.base import BaseLog


def _serialize_traceback(log: BaseLog) -> str | None:
    traceback_lines = getattr(log, "traceback", None)

    if not traceback_lines:
        return None

    return "".join(traceback_lines)


def _stringify_mapping(values: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): _stringify_value(value)
        for key, value in values.items()
    }


def _stringify_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set, frozenset)):
        return json.dumps(
            value,
            default=str,
            sort_keys=True,
        )

    return str(value)


def _to_json(values: dict[str, Any]) -> str | None:
    if not values:
        return None

    return json.dumps(
        values,
        default=str,
        sort_keys=True,
    )