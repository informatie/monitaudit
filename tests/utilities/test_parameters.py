from __future__ import annotations

from typing import Any

import pytest

from monitaudit.utilities.parameters import (
    _limit_value,
    _truncate,
    limit_parameters,
)


TRUNCATED_SUFFIX = "...<truncated>"


class ExampleObject:
    def __repr__(self) -> str:
        return "ExampleObjectWithLongRepresentation()"


def test_limit_parameters_empty_dict() -> None:
    result = limit_parameters(
        {},
        max_length=100,
    )

    assert result == {}


def test_limit_parameters_preserves_parameter_names() -> None:
    parameters = {
        "first": "one",
        "second": "two",
    }

    result = limit_parameters(
        parameters,
        max_length=100,
    )

    assert result == parameters


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
    ],
)
def test_scalar_values_are_not_modified(
    value: Any,
) -> None:
    result = _limit_value(
        value,
        max_length=5,
    )

    assert result == value


def test_string_shorter_than_max_length_is_unchanged() -> None:
    result = _truncate(
        "hello",
        max_length=10,
    )

    assert result == "hello"


def test_string_equal_to_max_length_is_unchanged() -> None:
    value = "1234567890"

    result = _truncate(
        value,
        max_length=10,
    )

    assert result == value


def test_long_string_is_truncated() -> None:
    value = "abcdefghijklmnopqrstuvwxyz"

    result = _truncate(
        value,
        max_length=20,
    )

    assert result.endswith(
        TRUNCATED_SUFFIX
    )

    assert len(result) == 20


def test_truncated_string_contains_expected_prefix() -> None:
    value = "abcdefghijklmnopqrstuvwxyz"

    max_length = 20

    result = _truncate(
        value,
        max_length=max_length,
    )

    expected_prefix_length = (
        max_length
        - len(TRUNCATED_SUFFIX)
    )

    assert result == (
        value[:expected_prefix_length]
        + TRUNCATED_SUFFIX
    )


def test_limit_parameters_truncates_strings() -> None:
    parameters = {
        "short": "hello",
        "long": "abcdefghijklmnopqrstuvwxyz",
    }

    result = limit_parameters(
        parameters,
        max_length=20,
    )

    assert result["short"] == "hello"

    assert result["long"].endswith(
        TRUNCATED_SUFFIX
    )

    assert len(result["long"]) == 20


def test_nested_dictionary_is_processed() -> None:
    parameters = {
        "config": {
            "short": "hello",
            "long": "abcdefghijklmnopqrstuvwxyz",
        }
    }

    result = limit_parameters(
        parameters,
        max_length=20,
    )

    assert result["config"]["short"] == "hello"

    assert result["config"]["long"].endswith(
        TRUNCATED_SUFFIX
    )


def test_nested_dictionary_keys_are_converted_to_strings() -> None:
    parameters = {
        "config": {
            123: "hello",
            True: "world",
        }
    }

    result = limit_parameters(
        parameters,
        max_length=100,
    )

    assert "123" in result["config"]
    assert "True" in result["config"]


def test_list_is_processed_recursively() -> None:
    parameters = {
        "values": [
            "hello",
            "abcdefghijklmnopqrstuvwxyz",
            42,
            None,
        ]
    }

    result = limit_parameters(
        parameters,
        max_length=20,
    )

    assert result["values"][0] == "hello"

    assert result["values"][1].endswith(
        TRUNCATED_SUFFIX
    )

    assert result["values"][2] == 42
    assert result["values"][3] is None


def test_tuple_is_converted_to_list() -> None:
    value = (
        "hello",
        "world",
    )

    result = _limit_value(
        value,
        max_length=100,
    )

    assert result == [
        "hello",
        "world",
    ]

    assert isinstance(result, list)


def test_tuple_values_are_processed_recursively() -> None:
    value = (
        "hello",
        "abcdefghijklmnopqrstuvwxyz",
    )

    result = _limit_value(
        value,
        max_length=20,
    )

    assert result[0] == "hello"

    assert result[1].endswith(
        TRUNCATED_SUFFIX
    )


def test_set_is_converted_to_list() -> None:
    value = {
        "one",
        "two",
        "three",
    }

    result = _limit_value(
        value,
        max_length=100,
    )

    assert isinstance(result, list)

    assert set(result) == value


def test_set_values_are_processed_recursively() -> None:
    value = {
        "abcdefghijklmnopqrstuvwxyz",
    }

    result = _limit_value(
        value,
        max_length=20,
    )

    assert len(result) == 1

    assert result[0].endswith(
        TRUNCATED_SUFFIX
    )


def test_custom_object_uses_repr() -> None:
    value = ExampleObject()

    result = _limit_value(
        value,
        max_length=100,
    )

    assert result == (
        "ExampleObjectWithLongRepresentation()"
    )


def test_custom_object_repr_is_truncated() -> None:
    value = ExampleObject()

    result = _limit_value(
        value,
        max_length=20,
    )

    assert isinstance(result, str)

    assert result.endswith(
        TRUNCATED_SUFFIX
    )

    assert len(result) == 20


def test_deeply_nested_structure_is_processed() -> None:
    parameters = {
        "level1": {
            "level2": {
                "level3": [
                    "abcdefghijklmnopqrstuvwxyz",
                    {
                        "value": (
                            "abcdefghijklmnopqrstuvwxyz",
                        )
                    },
                ]
            }
        }
    }

    result = limit_parameters(
        parameters,
        max_length=20,
    )

    level3 = (
        result["level1"]["level2"]["level3"]
    )

    assert level3[0].endswith(
        TRUNCATED_SUFFIX
    )

    nested_value = level3[1]["value"]

    assert isinstance(
        nested_value,
        list,
    )

    assert nested_value[0].endswith(
        TRUNCATED_SUFFIX
    )


def test_limit_parameters_does_not_modify_original_dict() -> None:
    parameters = {
        "value": "abcdefghijklmnopqrstuvwxyz",
        "nested": {
            "value": "abcdefghijklmnopqrstuvwxyz",
        },
    }

    original_top_value = parameters["value"]
    original_nested_value = (
        parameters["nested"]["value"]
    )

    result = limit_parameters(
        parameters,
        max_length=20,
    )

    assert parameters["value"] == original_top_value

    assert (
        parameters["nested"]["value"]
        == original_nested_value
    )

    assert result["value"] != parameters["value"]

    assert (
        result["nested"]["value"]
        != parameters["nested"]["value"]
    )


def test_limit_parameters_returns_new_dictionary() -> None:
    parameters = {
        "value": "hello",
    }

    result = limit_parameters(
        parameters,
        max_length=100,
    )

    assert result == parameters
    assert result is not parameters


def test_nested_dictionary_is_new_dictionary() -> None:
    parameters = {
        "nested": {
            "value": "hello",
        }
    }

    result = limit_parameters(
        parameters,
        max_length=100,
    )

    assert (
        result["nested"]
        == parameters["nested"]
    )

    assert (
        result["nested"]
        is not parameters["nested"]
    )


@pytest.mark.parametrize(
    ("value", "max_length"),
    [
        ("", 20),
        ("a", 20),
        ("12345", 5),
        ("1234567890", 10),
    ],
)
def test_values_within_limit_remain_unchanged(
    value: str,
    max_length: int,
) -> None:
    assert (
        _truncate(
            value,
            max_length=max_length,
        )
        == value
    )