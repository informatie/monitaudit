# src/monitaudit/utilities/json_safe.py

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

JsonValue = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)


def json_safe(
    value: Any,
) -> JsonValue:
    if value is None:
        return None

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Enum):
        return json_safe(value.value)

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, (Path, UUID)):
        return str(value)

    if isinstance(value, BaseModel):
        return json_safe(
            value.model_dump(mode="json")
        )

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, bytes):
        return repr(value)

    return _safe_repr(value)


def json_safe_dict(
    values: dict[str, Any],
) -> dict[str, JsonValue]:
    return {
        str(key): json_safe(value)
        for key, value in values.items()
    }


def _safe_repr(
    value: Any,
) -> str:
    try:
        return repr(value)
    except Exception:
        return (
            f"<unserializable "
            f"{type(value).__name__}>"
        )