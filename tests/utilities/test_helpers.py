# tests/utilities/test_helpers.py

from __future__ import annotations

import json
from typing import Any

import pytest

from monitaudit.utilities.helpers import (
    _serialize_traceback,
    _stringify_mapping,
    _stringify_value,
    _to_json,
)


class TestSerializeTraceback:
    def test_returns_none_when_traceback_attribute_is_missing(
        self,
    ) -> None:
        class Log:
            pass

        log = Log()

        result = _serialize_traceback(log)  # type: ignore[arg-type]

        assert result is None

    def test_returns_none_when_traceback_is_none(
        self,
    ) -> None:
        class Log:
            traceback = None

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result is None

    def test_returns_none_when_traceback_is_empty_list(
        self,
    ) -> None:
        class Log:
            traceback: list[str] = []

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result is None

    def test_returns_none_when_traceback_is_empty_tuple(
        self,
    ) -> None:
        class Log:
            traceback: tuple[str, ...] = ()

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result is None

    def test_returns_single_traceback_line(
        self,
    ) -> None:
        class Log:
            traceback = [
                "ValueError: invalid value\n"
            ]

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result == "ValueError: invalid value\n"

    def test_joins_multiple_traceback_lines(
        self,
    ) -> None:
        class Log:
            traceback = [
                "Traceback (most recent call last):\n",
                '  File "main.py", line 10\n',
                "ValueError: invalid value\n",
            ]

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result == (
            "Traceback (most recent call last):\n"
            '  File "main.py", line 10\n'
            "ValueError: invalid value\n"
        )

    def test_preserves_traceback_content_exactly(
        self,
    ) -> None:
        class Log:
            traceback = [
                "line 1\n",
                "\tline 2\n",
                "line 3",
            ]

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result == (
            "line 1\n"
            "\tline 2\n"
            "line 3"
        )

    def test_does_not_add_newline_between_lines(
        self,
    ) -> None:
        class Log:
            traceback = [
                "first",
                "second",
            ]

        result = _serialize_traceback(  # type: ignore[arg-type]
            Log()
        )

        assert result == "firstsecond"


class TestStringifyValue:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, "None"),
            (True, "True"),
            (False, "False"),
            (0, "0"),
            (1, "1"),
            (-1, "-1"),
            (1.5, "1.5"),
            ("hello", "hello"),
            ("", ""),
        ],
    )
    def test_stringifies_scalar_values(
        self,
        value: Any,
        expected: str,
    ) -> None:
        result = _stringify_value(value)

        assert result == expected

    def test_stringifies_dictionary_as_json(
        self,
    ) -> None:
        value = {
            "name": "test",
            "count": 5,
        }

        result = _stringify_value(value)

        assert result == (
            '{"count": 5, "name": "test"}'
        )

    def test_dictionary_json_keys_are_sorted(
        self,
    ) -> None:
        value = {
            "z": 1,
            "a": 2,
            "m": 3,
        }

        result = _stringify_value(value)

        assert result == (
            '{"a": 2, "m": 3, "z": 1}'
        )

    def test_stringifies_nested_dictionary(
        self,
    ) -> None:
        value = {
            "outer": {
                "value": 42,
            }
        }

        result = _stringify_value(value)

        assert result == (
            '{"outer": {"value": 42}}'
        )

    def test_stringifies_list_as_json(
        self,
    ) -> None:
        value = [
            "alpha",
            "beta",
            3,
        ]

        result = _stringify_value(value)

        assert result == (
            '["alpha", "beta", 3]'
        )

    def test_stringifies_empty_list_as_json(
        self,
    ) -> None:
        result = _stringify_value([])

        assert result == "[]"

    def test_stringifies_empty_dictionary_as_json(
        self,
    ) -> None:
        result = _stringify_value({})

        assert result == "{}"

    def test_stringifies_tuple_as_json(
        self,
    ) -> None:
        result = _stringify_value(
            (
                "alpha",
                "beta",
                3,
            )
        )

        assert result == (
            '["alpha", "beta", 3]'
        )

    def test_stringifies_empty_tuple_as_json(
        self,
    ) -> None:
        result = _stringify_value(())

        assert result == "[]"

    def test_uses_string_fallback_for_object_in_dictionary(
        self,
    ) -> None:
        class CustomValue:
            def __str__(self) -> str:
                return "custom-value"

        value = {
            "value": CustomValue(),
        }

        result = _stringify_value(value)

        assert result == (
            '{"value": "custom-value"}'
        )

    def test_uses_string_fallback_for_object_in_list(
        self,
    ) -> None:
        class CustomValue:
            def __str__(self) -> str:
                return "custom-value"

        result = _stringify_value(
            [CustomValue()]
        )

        assert result == '["custom-value"]'

    def test_scalar_custom_object_uses_str(
        self,
    ) -> None:
        class CustomValue:
            def __str__(self) -> str:
                return "custom-value"

        result = _stringify_value(
            CustomValue()
        )

        assert result == "custom-value"


class TestStringifyMapping:
    def test_empty_mapping_returns_empty_mapping(
        self,
    ) -> None:
        result = _stringify_mapping({})

        assert result == {}

    def test_stringifies_mapping_values(
        self,
    ) -> None:
        values = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
        }

        result = _stringify_mapping(values)

        assert result == {
            "string": "value",
            "integer": "42",
            "float": "3.14",
            "boolean": "True",
            "none": "None",
        }

    def test_stringifies_collection_values(
        self,
    ) -> None:
        values = {
            "dictionary": {
                "b": 2,
                "a": 1,
            },
            "list": [
                1,
                2,
                3,
            ],
            "tuple": (
                "a",
                "b",
            ),
        }

        result = _stringify_mapping(values)

        assert result == {
            "dictionary": '{"a": 1, "b": 2}',
            "list": "[1, 2, 3]",
            "tuple": '["a", "b"]',
        }

    def test_converts_integer_key_to_string(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            123: "value",
        }

        result = _stringify_mapping(values)

        assert result == {
            "123": "value",
        }

    def test_converts_none_key_to_string(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            None: "value",
        }

        result = _stringify_mapping(values)

        assert result == {
            "None": "value",
        }

    def test_converts_boolean_key_to_string(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            True: "value",
        }

        result = _stringify_mapping(values)

        assert result == {
            "True": "value",
        }

    def test_returns_new_dictionary(
        self,
    ) -> None:
        values = {
            "value": "test",
        }

        result = _stringify_mapping(values)

        assert result == values
        assert result is not values

    def test_does_not_modify_original_mapping(
        self,
    ) -> None:
        values: dict[str, Any] = {
            "value": 42,
            "nested": {
                "a": 1,
            },
        }

        original = {
            "value": 42,
            "nested": {
                "a": 1,
            },
        }

        _stringify_mapping(values)

        assert values == original

    def test_custom_value_uses_string_conversion(
        self,
    ) -> None:
        class CustomValue:
            def __str__(self) -> str:
                return "custom"

        result = _stringify_mapping(
            {
                "item": CustomValue(),
            }
        )

        assert result == {
            "item": "custom",
        }

    def test_nested_values_are_json_strings(
        self,
    ) -> None:
        result = _stringify_mapping(
            {
                "parameters": {
                    "customer_id": 10,
                    "active": True,
                },
            }
        )

        assert result == {
            "parameters": (
                '{"active": true, '
                '"customer_id": 10}'
            )
        }


class TestToJson:
    @pytest.mark.parametrize(
        "values",
        [
            {},
        ],
    )
    def test_empty_mapping_returns_none(
        self,
        values: dict[str, Any],
    ) -> None:
        result = _to_json(values)

        assert result is None

    def test_serialises_simple_mapping(
        self,
    ) -> None:
        values = {
            "name": "test",
            "count": 10,
        }

        result = _to_json(values)

        assert result == (
            '{"count": 10, "name": "test"}'
        )

    def test_sorts_keys(
        self,
    ) -> None:
        values = {
            "z": 1,
            "a": 2,
            "m": 3,
        }

        result = _to_json(values)

        assert result == (
            '{"a": 2, "m": 3, "z": 1}'
        )

    def test_serialises_nested_mapping(
        self,
    ) -> None:
        values = {
            "outer": {
                "inner": "value",
            }
        }

        result = _to_json(values)

        assert result == (
            '{"outer": {"inner": "value"}}'
        )

    def test_serialises_list(
        self,
    ) -> None:
        values = {
            "items": [
                1,
                2,
                3,
            ]
        }

        result = _to_json(values)

        assert result == (
            '{"items": [1, 2, 3]}'
        )

    def test_serialises_tuple_as_json_array(
        self,
    ) -> None:
        values = {
            "items": (
                "a",
                "b",
            )
        }

        result = _to_json(values)

        assert result == (
            '{"items": ["a", "b"]}'
        )

    def test_serialises_boolean_values(
        self,
    ) -> None:
        values = {
            "enabled": True,
            "disabled": False,
        }

        result = _to_json(values)

        assert result == (
            '{"disabled": false, '
            '"enabled": true}'
        )

    def test_serialises_none_as_json_null(
        self,
    ) -> None:
        values = {
            "value": None,
        }

        result = _to_json(values)

        assert result == (
            '{"value": null}'
        )

    def test_uses_str_for_non_json_value(
        self,
    ) -> None:
        class CustomValue:
            def __str__(self) -> str:
                return "custom-value"

        values = {
            "value": CustomValue(),
        }

        result = _to_json(values)

        assert result == (
            '{"value": "custom-value"}'
        )

    def test_result_is_valid_json(
        self,
    ) -> None:
        values = {
            "application": "monitaudit",
            "count": 10,
            "active": True,
            "metadata": {
                "environment": "dev",
            },
        }

        result = _to_json(values)

        assert result is not None

        decoded = json.loads(result)

        assert decoded == values

    def test_does_not_modify_original_mapping(
        self,
    ) -> None:
        values = {
            "z": 1,
            "a": {
                "value": 2,
            },
        }

        original = {
            "z": 1,
            "a": {
                "value": 2,
            },
        }

        _to_json(values)

        assert values == original


class TestCollectionBehaviour:
    def test_stringify_set_behaviour_matches_json_dumps(
        self,
    ) -> None:
        values = {
            1,
            2,
            3,
        }

        result = _stringify_value(values)

        assert result == json.dumps(
            values,
            default=str,
            sort_keys=True,
        )

    def test_stringify_frozenset_behaviour_matches_json_dumps(
        self,
    ) -> None:
        values = frozenset(
            {
                "a",
                "b",
            }
        )

        result = _stringify_value(values)

        assert result == json.dumps(
            values,
            default=str,
            sort_keys=True,
        )


class TestDeterministicSerialisation:
    def test_dictionary_stringification_is_deterministic(
        self,
    ) -> None:
        first = {
            "z": 3,
            "a": 1,
            "m": 2,
        }

        second = {
            "m": 2,
            "z": 3,
            "a": 1,
        }

        assert (
            _stringify_value(first)
            == _stringify_value(second)
        )

    def test_to_json_is_deterministic_for_mapping_order(
        self,
    ) -> None:
        first = {
            "z": 3,
            "a": 1,
            "m": 2,
        }

        second = {
            "m": 2,
            "z": 3,
            "a": 1,
        }

        assert _to_json(first) == _to_json(
            second
        )

    def test_stringify_mapping_preserves_input_iteration_order(
        self,
    ) -> None:
        values = {
            "third": 3,
            "first": 1,
            "second": 2,
        }

        result = _stringify_mapping(values)

        assert list(result) == [
            "third",
            "first",
            "second",
        ]