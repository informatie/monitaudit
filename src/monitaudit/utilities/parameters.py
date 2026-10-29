# src/monitaudit/utilities/parameters.py

from __future__ import annotations

from typing import Any


def limit_parameters(
    parameters: dict[str, Any],
    max_length: int,
) -> dict[str, Any]:
    return {
        name: _limit_value(
            value,
            max_length,
        )
        for name, value in parameters.items()
    }


def _limit_value(
    value: Any,
    max_length: int,
) -> Any:
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return value

    if isinstance(value, str):
        return _truncate(
            value,
            max_length,
        )

    if isinstance(value, dict):
        return {
            str(key): _limit_value(
                item,
                max_length,
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _limit_value(
                item,
                max_length,
            )
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _limit_value(
                item,
                max_length,
            )
            for item in value
        ]

    if isinstance(value, set):
        return [
            _limit_value(
                item,
                max_length,
            )
            for item in value
        ]

    return _truncate(
        repr(value),
        max_length,
    )


def _truncate(
    value: str,
    max_length: int,
) -> str:
    if len(value) <= max_length:
        return value

    suffix = "...<truncated>"

    return (
        value[
            : max_length - len(suffix)
        ]
        + suffix
    )
