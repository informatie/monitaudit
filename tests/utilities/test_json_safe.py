# tests/utilities/test_json_safe.py

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
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


class StringEnum(Enum):
    FIRST = "first"
    SECOND = "second"


class IntegerEnum(Enum):
    ONE = 1
    TWO = 2


class NestedEnum(Enum):
    VALUES = ("one", "two")


class ExampleModel(BaseModel):
    name: str
    count: int


class ComplexModel(BaseModel):
    identifier: UUID
    created_at: datetime
    path: Path


class CustomObject:
    def __repr__(self) -> str:
        return "<CustomObject>"


class FaultyRepr:
    def __repr__(self) -> str:
        raise RuntimeError("repr failed")


class AnotherFaultyRepr:
    def __repr__(self) -> str:
        raise ValueError("cannot represent object")


class TestJsonSafePrimitives:
    def test_none_is_preserved(
        self,
    ) -> None:
        assert json_safe(None) is None

    @pytest.mark.parametrize(
        "value",
        [
            True,
            False,
        ],
    )
    def test_boolean_is_preserved(
        self,
        value: bool,
    ) -> None:
        result = json_safe(value)

        assert result is value

    @pytest.mark.parametrize(
        "value",
        [
            0,
            1,
            -1,
            42,
            -1000,
        ],
    )
    def test_integer_is_preserved(
        self,
        value: int,
    ) -> None:
        result = json_safe(value)

        assert result == value
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "value",
        [
            0.0,
            1.5,
            -1.5,
            3.14159,
        ],
    )
    def test_float_is_preserved(
        self,
        value: float,
    ) -> None:
        result = json_safe(value)

        assert result == value
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "hello",
            "MonitAudit",
            "value with spaces",
        ],
    )
    def test_string_is_preserved(
        self,
        value: str,
    ) -> None:
        result = json_safe(value)

        assert result == value
        assert isinstance(result, str)

    def test_string_identity_is_preserved(
        self,
    ) -> None:
        value = "monitaudit-value"

        result = json_safe(value)

        assert result is value


class TestJsonSafeEnums:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (
                StringEnum.FIRST,
                "first",
            ),
            (
                StringEnum.SECOND,
                "second",
            ),
            (
                IntegerEnum.ONE,
                1,
            ),
            (
                IntegerEnum.TWO,
                2,
            ),
        ],
    )
    def test_enum_uses_enum_value(
        self,
        value: Enum,
        expected: Any,
    ) -> None:
        assert json_safe(value) == expected

    def test_enum_value_is_processed_recursively(
        self,
    ) -> None:
        result = json_safe(
            NestedEnum.VALUES
        )

        assert result == [
            "one",
            "two",
        ]


class TestJsonSafeDateTime:
    def test_datetime_uses_isoformat(
        self,
    ) -> None:
        value = datetime(
            2026,
            11,
            2,
            19,
            29,
            30,
            123456,
        )

        result = json_safe(value)

        assert result == value.isoformat()

    def test_timezone_aware_datetime_uses_isoformat(
        self,
    ) -> None:
        value = datetime(
            2026,
            11,
            2,
            18,
            30,
            0,
            tzinfo=UTC,
        )

        result = json_safe(value)

        assert result == value.isoformat()

    def test_date_uses_isoformat(
        self,
    ) -> None:
        value = date(
            2026,
            11,
            2,
        )

        result = json_safe(value)

        assert result == "2026-11-02"

    def test_time_uses_isoformat(
        self,
    ) -> None:
        value = time(
            19,
            29,
            30,
            123456,
        )

        result = json_safe(value)

        assert result == value.isoformat()

    def test_timezone_aware_time_uses_isoformat(
        self,
    ) -> None:
        value = time(
            19,
            29,
            30,
            tzinfo=UTC,
        )

        result = json_safe(value)

        assert result == value.isoformat()


class TestJsonSafePath:
    def test_path_is_converted_to_string(
        self,
    ) -> None:
        value = Path(
            "/tmp/monitaudit/example.json"
        )

        result = json_safe(value)

        assert result == str(value)

    def test_relative_path_is_converted_to_string(
        self,
    ) -> None:
        value = Path(
            "output/json_sink/application.jsonl"
        )

        result = json_safe(value)

        assert result == (
            "output/json_sink/application.jsonl"
        )


class TestJsonSafeUUID:
    def test_uuid_is_converted_to_string(
        self,
    ) -> None:
        value = UUID(
            "12345678-1234-5678-1234-567812345678"
        )

        result = json_safe(value)

        assert result == (
            "12345678-1234-5678-1234-567812345678"
        )


class TestJsonSafePydanticModel:
    def test_pydantic_model_becomes_dictionary(
        self,
    ) -> None:
        model = ExampleModel(
            name="example",
            count=42,
        )

        result = json_safe(model)

        assert result == {
            "name": "example",
            "count": 42,
        }

    def test_pydantic_model_is_json_safe(
        self,
    ) -> None:
        model = ComplexModel(
            identifier=UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            created_at=datetime(
                2026,
                11,
                2,
                19,
                30,
                0,
            ),
            path=Path(
                "output/example.json"
            ),
        )

        result = json_safe(model)

        assert result == {
            "identifier": (
                "12345678-1234-5678-1234-567812345678"
            ),
            "created_at": "2026-11-02T19:30:00",
            "path": "output/example.json",
        }

    def test_pydantic_model_result_can_be_json_encoded(
        self,
    ) -> None:
        model = ComplexModel(
            identifier=UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            created_at=datetime(
                2026,
                11,
                2,
                19,
                30,
                0,
            ),
            path=Path(
                "output/example.json"
            ),
        )

        result = json_safe(model)

        encoded = json.dumps(result)

        assert isinstance(encoded, str)


class TestJsonSafeDictionary:
    def test_empty_dictionary_returns_empty_dictionary(
        self,
    ) -> None:
        result = json_safe({})

        assert result == {}

    def test_dictionary_values_are_processed(
        self,
    ) -> None:
        values = {
            "integer": 42,
            "path": Path("output/test.log"),
            "date": date(
                2026,
                11,
                2,
            ),
        }

        result = json_safe(values)

        assert result == {
            "integer": 42,
            "path": "output/test.log",
            "date": "2026-11-02",
        }

    def test_dictionary_keys_are_converted_to_strings(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            10: "integer",
            True: "boolean",
            None: "none",
        }

        result = json_safe(values)

        assert result == {
            "10": "integer",
            "True": "boolean",
            "None": "none",
        }

    def test_nested_dictionary_is_processed_recursively(
        self,
    ) -> None:
        values = {
            "outer": {
                "inner": {
                    "path": Path(
                        "example.txt"
                    ),
                }
            }
        }

        result = json_safe(values)

        assert result == {
            "outer": {
                "inner": {
                    "path": "example.txt",
                }
            }
        }

    def test_returns_new_dictionary(
        self,
    ) -> None:
        values = {
            "value": 42,
        }

        result = json_safe(values)

        assert result == values
        assert result is not values

    def test_does_not_modify_original_dictionary(
        self,
    ) -> None:
        path = Path(
            "output/example.json"
        )

        values = {
            "path": path,
        }

        result = json_safe(values)

        assert values == {
            "path": path,
        }

        assert result == {
            "path": "output/example.json",
        }


class TestJsonSafeList:
    def test_empty_list_returns_empty_list(
        self,
    ) -> None:
        result = json_safe([])

        assert result == []

    def test_list_values_are_processed(
        self,
    ) -> None:
        values = [
            42,
            Path("example.txt"),
            date(
                2026,
                11,
                2,
            ),
        ]

        result = json_safe(values)

        assert result == [
            42,
            "example.txt",
            "2026-11-02",
        ]

    def test_returns_new_list(
        self,
    ) -> None:
        values = [
            1,
            2,
            3,
        ]

        result = json_safe(values)

        assert result == values
        assert result is not values


class TestJsonSafeTuple:
    def test_empty_tuple_becomes_empty_list(
        self,
    ) -> None:
        assert json_safe(()) == []

    def test_tuple_becomes_list(
        self,
    ) -> None:
        result = json_safe(
            (
                1,
                2,
                3,
            )
        )

        assert result == [
            1,
            2,
            3,
        ]

    def test_tuple_values_are_processed_recursively(
        self,
    ) -> None:
        result = json_safe(
            (
                Path("one.txt"),
                UUID(
                    "12345678-1234-5678-1234-567812345678"
                ),
            )
        )

        assert result == [
            "one.txt",
            (
                "12345678-1234-5678-1234-"
                "567812345678"
            ),
        ]


class TestJsonSafeSet:
    def test_empty_set_becomes_empty_list(
        self,
    ) -> None:
        result = json_safe(set())

        assert result == []

    def test_set_becomes_list(
        self,
    ) -> None:
        values = {
            1,
            2,
            3,
        }

        result = json_safe(values)

        assert isinstance(result, list)
        assert set(result) == {
            1,
            2,
            3,
        }

    def test_set_values_are_processed_recursively(
        self,
    ) -> None:
        values = {
            Path("one.txt"),
            Path("two.txt"),
        }

        result = json_safe(values)

        assert isinstance(result, list)
        assert set(result) == {
            "one.txt",
            "two.txt",
        }


class TestJsonSafeFrozenSet:
    def test_empty_frozenset_becomes_empty_list(
        self,
    ) -> None:
        result = json_safe(
            frozenset()
        )

        assert result == []

    def test_frozenset_becomes_list(
        self,
    ) -> None:
        values = frozenset(
            {
                "a",
                "b",
            }
        )

        result = json_safe(values)

        assert isinstance(result, list)
        assert set(result) == {
            "a",
            "b",
        }


class TestJsonSafeBytes:
    def test_bytes_use_repr(
        self,
    ) -> None:
        value = b"hello"

        result = json_safe(value)

        assert result == "b'hello'"

    def test_empty_bytes_use_repr(
        self,
    ) -> None:
        result = json_safe(b"")

        assert result == "b''"

    def test_binary_bytes_use_repr(
        self,
    ) -> None:
        value = bytes(
            [
                0,
                1,
                255,
            ]
        )

        result = json_safe(value)

        assert result == repr(value)

    def test_bytearray_uses_safe_repr_fallback(
        self,
    ) -> None:
        value = bytearray(
            b"hello"
        )

        result = json_safe(value)

        assert result == repr(value)


class TestJsonSafeUnknownObjects:
    def test_unknown_object_uses_repr(
        self,
    ) -> None:
        value = CustomObject()

        result = json_safe(value)

        assert result == "<CustomObject>"

    def test_unknown_object_returns_string(
        self,
    ) -> None:
        result = json_safe(
            CustomObject()
        )

        assert isinstance(result, str)

    def test_faulty_repr_uses_safe_fallback(
        self,
    ) -> None:
        result = json_safe(
            FaultyRepr()
        )

        assert result == (
            "<unserializable FaultyRepr>"
        )


class TestJsonSafeNestedStructures:
    def test_complex_nested_structure(
        self,
    ) -> None:
        identifier = UUID(
            "12345678-1234-5678-1234-567812345678"
        )

        values = {
            "application": "monitaudit",
            "enabled": True,
            "parameters": {
                "identifier": identifier,
                "created": datetime(
                    2026,
                    11,
                    2,
                    19,
                    30,
                ),
                "paths": [
                    Path("one.txt"),
                    Path("two.txt"),
                ],
                "flags": (
                    True,
                    False,
                ),
            },
        }

        result = json_safe(values)

        assert result == {
            "application": "monitaudit",
            "enabled": True,
            "parameters": {
                "identifier": (
                    "12345678-1234-5678-1234-"
                    "567812345678"
                ),
                "created": "2026-11-02T19:30:00",
                "paths": [
                    "one.txt",
                    "two.txt",
                ],
                "flags": [
                    True,
                    False,
                ],
            },
        }

    def test_complex_result_can_be_json_encoded(
        self,
    ) -> None:
        values = {
            "path": Path("output/file.log"),
            "date": date(
                2026,
                11,
                2,
            ),
            "uuid": UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            "tuple": (
                1,
                2,
            ),
            "object": CustomObject(),
        }

        result = json_safe(values)

        encoded = json.dumps(result)

        assert isinstance(encoded, str)


class TestJsonSafeDict:
    def test_empty_dictionary_returns_empty_dictionary(
        self,
    ) -> None:
        values: dict[str, Any] = {}

        result = json_safe_dict(values)

        assert result == {}

    def test_values_are_converted(
        self,
    ) -> None:
        values = {
            "path": Path("output/example.log"),
            "date": date(
                2026,
                11,
                2,
            ),
            "integer": 42,
        }

        result = json_safe_dict(values)

        assert result == {
            "path": "output/example.log",
            "date": "2026-11-02",
            "integer": 42,
        }

    def test_keys_are_converted_to_strings(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            1: "one",
            None: "none",
        }

        result = json_safe_dict(values)

        assert result == {
            "1": "one",
            "None": "none",
        }

    def test_returns_new_dictionary(
        self,
    ) -> None:
        values = {
            "value": "test",
        }

        result = json_safe_dict(values)

        assert result == values
        assert result is not values

    def test_nested_values_are_processed(
        self,
    ) -> None:
        values = {
            "parameters": {
                "path": Path(
                    "output/example.log"
                ),
                "items": (
                    1,
                    2,
                ),
            }
        }

        result = json_safe_dict(values)

        assert result == {
            "parameters": {
                "path": "output/example.log",
                "items": [
                    1,
                    2,
                ],
            }
        }

    def test_does_not_modify_input(
        self,
    ) -> None:
        path = Path(
            "output/example.log"
        )

        values = {
            "path": path,
        }

        result = json_safe_dict(values)

        assert values == {
            "path": path,
        }

        assert result == {
            "path": "output/example.log",
        }


class TestSafeRepr:
    def test_uses_repr(
        self,
    ) -> None:
        value = CustomObject()

        result = _safe_repr(value)

        assert result == "<CustomObject>"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (
                42,
                "42",
            ),
            (
                "hello",
                "'hello'",
            ),
            (
                None,
                "None",
            ),
            (
                True,
                "True",
            ),
        ],
    )
    def test_returns_normal_repr(
        self,
        value: Any,
        expected: str,
    ) -> None:
        assert _safe_repr(value) == expected

    def test_handles_runtime_error_from_repr(
        self,
    ) -> None:
        result = _safe_repr(
            FaultyRepr()
        )

        assert result == (
            "<unserializable FaultyRepr>"
        )

    def test_handles_other_exception_from_repr(
        self,
    ) -> None:
        result = _safe_repr(
            AnotherFaultyRepr()
        )

        assert result == (
            "<unserializable AnotherFaultyRepr>"
        )


class TestJsonCompatibility:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            True,
            False,
            42,
            3.14,
            "hello",
            Path("example.txt"),
            date(
                2026,
                11,
                2,
            ),
            datetime(
                2026,
                11,
                2,
                19,
                30,
            ),
            UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            [
                1,
                2,
                3,
            ],
            (
                1,
                2,
                3,
            ),
            {
                "value": 42,
            },
            CustomObject(),
            FaultyRepr(),
        ],
    )
    def test_result_is_accepted_by_json_dumps(
        self,
        value: Any,
    ) -> None:
        result = json_safe(value)

        encoded = json.dumps(result)

        assert isinstance(encoded, str)

    def test_json_safe_dict_result_is_accepted_by_json_dumps(
        self,
    ) -> None:
        values = {
            "path": Path("example.txt"),
            "timestamp": datetime(
                2026,
                11,
                2,
                19,
                30,
            ),
            "identifier": UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            "custom": CustomObject(),
            "faulty": FaultyRepr(),
        }

        result = json_safe_dict(values)

        encoded = json.dumps(result)

        assert isinstance(encoded, str)