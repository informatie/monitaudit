from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel

from monitaudit.utilities.json_safe import (
    _safe_repr,
    json_safe,
    json_safe_dict,
)


class ExampleEnum(Enum):
    FIRST = "first"
    NUMBER = 42


class ExampleModel(BaseModel):
    name: str
    count: int


class ExampleObject:
    def __repr__(self) -> str:
        return "ExampleObject()"


class BrokenRepr:
    def __repr__(self) -> str:
        raise RuntimeError(
            "repr failed"
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        0,
        1,
        -1,
        42,
        1.5,
        -3.14,
        "",
        "hello",
    ],
)
def test_json_safe_preserves_primitive_values(
    value: Any,
) -> None:
    result = json_safe(value)

    assert result == value


def test_json_safe_string_enum() -> None:
    result = json_safe(
        ExampleEnum.FIRST
    )

    assert result == "first"


def test_json_safe_integer_enum() -> None:
    result = json_safe(
        ExampleEnum.NUMBER
    )

    assert result == 42


def test_json_safe_datetime() -> None:
    value = datetime(
        2026,
        10,
        23,
        12,
        30,
        15,
    )

    result = json_safe(value)

    assert result == value.isoformat()


def test_json_safe_date() -> None:
    value = date(
        2026,
        10,
        23,
    )

    result = json_safe(value)

    assert result == "2026-10-23"


def test_json_safe_time() -> None:
    value = time(
        12,
        30,
        15,
    )

    result = json_safe(value)

    assert result == "12:30:15"


def test_json_safe_path() -> None:
    value = Path(
        "/tmp/example.txt"
    )

    result = json_safe(value)

    assert result == str(value)


def test_json_safe_uuid() -> None:
    value = UUID(
        "12345678-1234-5678-1234-567812345678"
    )

    result = json_safe(value)

    assert (
        result
        == "12345678-1234-5678-1234-567812345678"
    )


def test_json_safe_pydantic_model() -> None:
    value = ExampleModel(
        name="example",
        count=42,
    )

    result = json_safe(value)

    assert result == {
        "name": "example",
        "count": 42,
    }


def test_json_safe_dictionary() -> None:
    value = {
        "name": "example",
        "count": 42,
        "enabled": True,
    }

    result = json_safe(value)

    assert result == value


def test_json_safe_dictionary_converts_keys_to_strings() -> None:
    value = {
        1: "one",
        2: "two",
    }

    result = json_safe(value)

    assert result == {
        "1": "one",
        "2": "two",
    }


def test_json_safe_nested_dictionary() -> None:
    value = {
        "outer": {
            "path": Path("/tmp/test"),
            "enum": ExampleEnum.FIRST,
            "uuid": UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
        }
    }

    result = json_safe(value)

    assert result == {
        "outer": {
            "path": "/tmp/test",
            "enum": "first",
            "uuid": (
                "12345678-1234-5678-1234-567812345678"
            ),
        }
    }


def test_json_safe_list() -> None:
    value = [
        "hello",
        42,
        True,
        None,
    ]

    result = json_safe(value)

    assert result == value
    assert isinstance(result, list)


def test_json_safe_tuple_becomes_list() -> None:
    value = (
        "hello",
        42,
    )

    result = json_safe(value)

    assert result == [
        "hello",
        42,
    ]

    assert isinstance(
        result,
        list,
    )


def test_json_safe_set_becomes_list() -> None:
    value = {
        "one",
        "two",
        "three",
    }

    result = json_safe(value)

    assert isinstance(
        result,
        list,
    )

    assert set(result) == value


def test_json_safe_frozenset_becomes_list() -> None:
    value = frozenset(
        {
            "one",
            "two",
            "three",
        }
    )

    result = json_safe(value)

    assert isinstance(
        result,
        list,
    )

    assert set(result) == set(value)


def test_json_safe_container_values_are_recursive() -> None:
    value = [
        Path("/tmp/example"),
        ExampleEnum.FIRST,
        {
            "uuid": UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
        },
    ]

    result = json_safe(value)

    assert result == [
        "/tmp/example",
        "first",
        {
            "uuid": (
                "12345678-1234-5678-1234-567812345678"
            ),
        },
    ]


def test_json_safe_bytes() -> None:
    value = b"hello"

    result = json_safe(value)

    assert result == repr(value)
    assert result == "b'hello'"


def test_json_safe_unknown_object_uses_repr() -> None:
    value = ExampleObject()

    result = json_safe(value)

    assert result == "ExampleObject()"


def test_safe_repr_returns_repr() -> None:
    value = ExampleObject()

    result = _safe_repr(value)

    assert result == "ExampleObject()"


def test_safe_repr_handles_broken_repr() -> None:
    value = BrokenRepr()

    result = _safe_repr(value)

    assert result == (
        "<unserializable BrokenRepr>"
    )


def test_json_safe_handles_object_with_broken_repr() -> None:
    value = BrokenRepr()

    result = json_safe(value)

    assert result == (
        "<unserializable BrokenRepr>"
    )


def test_json_safe_dict_empty_dictionary() -> None:
    result = json_safe_dict({})

    assert result == {}


def test_json_safe_dict_preserves_safe_values() -> None:
    values = {
        "string": "hello",
        "integer": 42,
        "float": 1.5,
        "boolean": True,
        "none": None,
    }

    result = json_safe_dict(
        values
    )

    assert result == values


def test_json_safe_dict_converts_values() -> None:
    values = {
        "path": Path("/tmp/example"),
        "uuid": UUID(
            "12345678-1234-5678-1234-567812345678"
        ),
        "enum": ExampleEnum.FIRST,
    }

    result = json_safe_dict(
        values
    )

    assert result == {
        "path": "/tmp/example",
        "uuid": (
            "12345678-1234-5678-1234-567812345678"
        ),
        "enum": "first",
    }


def test_json_safe_dict_converts_keys_to_strings() -> None:
    # The function annotation specifies str keys,
    # but this verifies runtime robustness.
    values: dict[Any, Any] = {
        1: "one",
        2: "two",
    }

    result = json_safe_dict(
        values
    )

    assert result == {
        "1": "one",
        "2": "two",
    }


def test_json_safe_deeply_nested_structure() -> None:
    value = {
        "level1": {
            "level2": [
                {
                    "path": Path(
                        "/tmp/example"
                    ),
                    "enum": ExampleEnum.FIRST,
                },
                (
                    UUID(
                        "12345678-1234-5678-1234-567812345678"
                    ),
                ),
            ]
        }
    }

    result = json_safe(value)

    assert result == {
        "level1": {
            "level2": [
                {
                    "path": "/tmp/example",
                    "enum": "first",
                },
                [
                    (
                        "12345678-1234-5678-"
                        "1234-567812345678"
                    )
                ],
            ]
        }
    }


def test_json_safe_pydantic_model_with_nested_values() -> None:
    class NestedModel(BaseModel):
        path: Path
        created: datetime

    value = NestedModel(
        path=Path("/tmp/example"),
        created=datetime(
            2026,
            10,
            23,
            12,
            30,
        ),
    )

    result = json_safe(value)

    assert result == {
        "path": "/tmp/example",
        "created": (
            "2026-10-23T12:30:00"
        ),
    }


def test_json_safe_does_not_modify_original_dictionary() -> None:
    value = {
        "path": Path("/tmp/example"),
        "nested": {
            "enum": ExampleEnum.FIRST,
        },
    }

    original_path = value["path"]
    original_enum = (
        value["nested"]["enum"]
    )

    result = json_safe(value)

    assert value["path"] is original_path

    assert (
        value["nested"]["enum"]
        is original_enum
    )

    assert result == {
        "path": "/tmp/example",
        "nested": {
            "enum": "first",
        },
    }


def test_json_safe_returns_new_dictionary() -> None:
    value = {
        "name": "test",
    }

    result = json_safe(value)

    assert result == value
    assert result is not value


def test_json_safe_returns_new_list() -> None:
    value = [
        "one",
        "two",
    ]

    result = json_safe(value)

    assert result == value
    assert result is not value