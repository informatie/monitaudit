from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from monitaudit.models.context import LogContext
from monitaudit.models.log import (
    ErrorLog,
    InfoLog,
)
from monitaudit.utilities.helpers import (
    _serialize_traceback,
    _stringify_mapping,
    _stringify_value,
    _to_json,
)


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
    )


def test_serialize_traceback_without_traceback(
    context: LogContext,
) -> None:
    log = InfoLog(
        message="test",
        context=context,
    )

    result = _serialize_traceback(log)

    assert result is None


def test_serialize_traceback_empty_traceback(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="error",
        context=context,
        traceback=[],
    )

    result = _serialize_traceback(log)

    assert result is None


def test_serialize_traceback_single_line(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="error",
        context=context,
        traceback=[
            "ValueError: failed\n",
        ],
    )

    result = _serialize_traceback(log)

    assert result == "ValueError: failed\n"


def test_serialize_traceback_multiple_lines(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="error",
        context=context,
        traceback=[
            "Traceback:\n",
            "  example.py\n",
            "ValueError: failed\n",
        ],
    )

    result = _serialize_traceback(log)

    assert result == (
        "Traceback:\n"
        "  example.py\n"
        "ValueError: failed\n"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hello", "hello"),
        (42, "42"),
        (1.5, "1.5"),
        (True, "True"),
        (False, "False"),
        (None, "None"),
    ],
)
def test_stringify_value_scalar(
    value: Any,
    expected: str,
) -> None:
    result = _stringify_value(value)

    assert result == expected


def test_stringify_value_dictionary() -> None:
    value = {
        "name": "monitaudit",
        "count": 42,
    }

    result = _stringify_value(value)

    assert json.loads(result) == value


def test_stringify_value_list() -> None:
    value = [
        "one",
        "two",
        3,
    ]

    result = _stringify_value(value)

    assert json.loads(result) == value


def test_stringify_value_tuple() -> None:
    value = (
        "one",
        "two",
        3,
    )

    result = _stringify_value(value)

    assert json.loads(result) == [
        "one",
        "two",
        3,
    ]


def test_stringify_value_dictionary_is_sorted() -> None:
    value = {
        "z": 1,
        "a": 2,
        "m": 3,
    }

    result = _stringify_value(value)

    assert result == (
        '{"a": 2, "m": 3, "z": 1}'
    )


def test_stringify_value_uses_default_str() -> None:
    value = {
        "path": Path(
            "/tmp/example"
        ),
    }

    result = _stringify_value(value)

    assert json.loads(result) == {
        "path": "/tmp/example",
    }


def test_stringify_mapping_empty_dictionary() -> None:
    result = _stringify_mapping({})

    assert result == {}


def test_stringify_mapping_scalar_values() -> None:
    values = {
        "string": "hello",
        "integer": 42,
        "boolean": True,
        "none": None,
    }

    result = _stringify_mapping(
        values
    )

    assert result == {
        "string": "hello",
        "integer": "42",
        "boolean": "True",
        "none": "None",
    }


def test_stringify_mapping_container_values() -> None:
    values = {
        "dictionary": {
            "name": "monitaudit",
        },
        "list": [
            1,
            2,
            3,
        ],
        "tuple": (
            "one",
            "two",
        ),
    }

    result = _stringify_mapping(
        values
    )

    assert json.loads(
        result["dictionary"]
    ) == {
        "name": "monitaudit",
    }

    assert json.loads(
        result["list"]
    ) == [
        1,
        2,
        3,
    ]

    assert json.loads(
        result["tuple"]
    ) == [
        "one",
        "two",
    ]


def test_to_json_empty_dictionary_returns_none() -> None:
    result = _to_json({})

    assert result is None


def test_to_json_simple_dictionary() -> None:
    values = {
        "name": "monitaudit",
        "count": 42,
        "enabled": True,
    }

    result = _to_json(values)

    assert result is not None

    assert json.loads(result) == values


def test_to_json_sorts_keys() -> None:
    values = {
        "z": 1,
        "a": 2,
        "m": 3,
    }

    result = _to_json(values)

    assert result == (
        '{"a": 2, "m": 3, "z": 1}'
    )


def test_to_json_uses_default_str() -> None:
    values = {
        "path": Path(
            "/tmp/example"
        ),
    }

    result = _to_json(values)

    assert result is not None

    assert json.loads(result) == {
        "path": "/tmp/example",
    }


def test_to_json_nested_structure() -> None:
    values = {
        "application": "monitaudit",
        "config": {
            "enabled": True,
            "count": 42,
        },
        "items": [
            "one",
            "two",
        ],
    }

    result = _to_json(values)

    assert result is not None

    assert json.loads(result) == values