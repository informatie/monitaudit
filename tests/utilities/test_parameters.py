# tests/utilities/test_parameters.py

from __future__ import annotations

from typing import Any

import pytest

from monitaudit.utilities.parameters import (
    _limit_value,
    _truncate,
    limit_parameters,
)

TRUNCATION_SUFFIX = "...<truncated>"


class ExampleObject:
    def __repr__(self) -> str:
        return "ExampleObject(value='abcdefghijklmnopqrstuvwxyz')"


class ShortReprObject:
    def __repr__(self) -> str:
        return "short"


class TestTruncate:
    def test_returns_empty_string_unchanged(
        self,
    ) -> None:
        assert _truncate("", 10) == ""

    def test_returns_value_shorter_than_limit_unchanged(
        self,
    ) -> None:
        assert (
            _truncate(
                "hello",
                10,
            )
            == "hello"
        )

    def test_returns_value_exactly_at_limit_unchanged(
        self,
    ) -> None:
        value = "abcdefghij"

        result = _truncate(
            value,
            len(value),
        )

        assert result == value

    def test_truncates_value_exceeding_limit(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"
        max_length = 20

        result = _truncate(
            value,
            max_length,
        )

        expected = (
            value[
                : max_length
                - len(TRUNCATION_SUFFIX)
            ]
            + TRUNCATION_SUFFIX
        )

        assert result == expected

    def test_truncated_value_has_requested_length_when_limit_exceeds_suffix(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"
        max_length = 20

        result = _truncate(
            value,
            max_length,
        )

        assert len(result) == max_length

    def test_appends_exact_truncation_suffix(
        self,
    ) -> None:
        result = _truncate(
            "abcdefghijklmnopqrstuvwxyz",
            20,
        )

        assert result.endswith(
            TRUNCATION_SUFFIX
        )

    def test_preserves_expected_prefix(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"
        max_length = 20

        result = _truncate(
            value,
            max_length,
        )

        prefix_length = (
            max_length
            - len(TRUNCATION_SUFFIX)
        )

        assert result.startswith(
            value[:prefix_length]
        )

    def test_limit_equal_to_suffix_length(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"

        result = _truncate(
            value,
            len(TRUNCATION_SUFFIX),
        )

        assert result == TRUNCATION_SUFFIX

    def test_current_behaviour_when_limit_is_smaller_than_suffix(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"
        max_length = 5

        result = _truncate(
            value,
            max_length,
        )

        expected = (
            value[
                : max_length
                - len(TRUNCATION_SUFFIX)
            ]
            + TRUNCATION_SUFFIX
        )

        assert result == expected

    def test_zero_limit_current_behaviour(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"

        result = _truncate(
            value,
            0,
        )

        expected = (
            value[
                : -len(TRUNCATION_SUFFIX)
            ]
            + TRUNCATION_SUFFIX
        )

        assert result == expected

    def test_negative_limit_current_behaviour(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"

        result = _truncate(
            value,
            -5,
        )

        expected = (
            value[
                : -5
                - len(TRUNCATION_SUFFIX)
            ]
            + TRUNCATION_SUFFIX
        )

        assert result == expected


class TestLimitValueScalars:
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
            -100,
            0.0,
            1.5,
            -42.5,
        ],
    )
    def test_scalar_values_are_preserved(
        self,
        value: Any,
    ) -> None:
        result = _limit_value(
            value,
            5,
        )

        assert result == value

    def test_integer_is_not_converted_to_string(
        self,
    ) -> None:
        result = _limit_value(
            123456789,
            2,
        )

        assert result == 123456789
        assert isinstance(result, int)

    def test_float_is_not_converted_to_string(
        self,
    ) -> None:
        result = _limit_value(
            123456.789,
            2,
        )

        assert result == 123456.789
        assert isinstance(result, float)

    def test_boolean_is_not_converted_to_string(
        self,
    ) -> None:
        result = _limit_value(
            True,
            1,
        )

        assert result is True


class TestLimitValueString:
    def test_short_string_is_preserved(
        self,
    ) -> None:
        result = _limit_value(
            "hello",
            10,
        )

        assert result == "hello"

    def test_string_at_limit_is_preserved(
        self,
    ) -> None:
        result = _limit_value(
            "hello",
            5,
        )

        assert result == "hello"

    def test_long_string_is_truncated(
        self,
    ) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"

        result = _limit_value(
            value,
            20,
        )

        assert result == _truncate(
            value,
            20,
        )


class TestLimitValueDictionary:
    def test_empty_dictionary_returns_empty_dictionary(
        self,
    ) -> None:
        result = _limit_value(
            {},
            20,
        )

        assert result == {}

    def test_returns_new_dictionary(
        self,
    ) -> None:
        value = {
            "name": "test",
        }

        result = _limit_value(
            value,
            20,
        )

        assert result == value
        assert result is not value

    def test_dictionary_values_are_processed(
        self,
    ) -> None:
        value = {
            "short": "hello",
            "long": "abcdefghijklmnopqrstuvwxyz",
            "number": 42,
        }

        result = _limit_value(
            value,
            20,
        )

        assert result == {
            "short": "hello",
            "long": _truncate(
                "abcdefghijklmnopqrstuvwxyz",
                20,
            ),
            "number": 42,
        }

    def test_dictionary_keys_are_converted_to_strings(
        self,
    ) -> None:
        value: dict[Any, Any] = {
            42: "value",
            None: "other",
        }

        result = _limit_value(
            value,
            100,
        )

        assert result == {
            "42": "value",
            "None": "other",
        }

    def test_nested_dictionary_is_processed_recursively(
        self,
    ) -> None:
        value = {
            "outer": {
                "inner": {
                    "value": "abcdefghijklmnopqrstuvwxyz",
                }
            }
        }

        result = _limit_value(
            value,
            20,
        )

        assert result == {
            "outer": {
                "inner": {
                    "value": _truncate(
                        "abcdefghijklmnopqrstuvwxyz",
                        20,
                    ),
                }
            }
        }


class TestLimitValueList:
    def test_empty_list_returns_empty_list(
        self,
    ) -> None:
        result = _limit_value(
            [],
            20,
        )

        assert result == []

    def test_returns_new_list(
        self,
    ) -> None:
        value = [
            "one",
            "two",
        ]

        result = _limit_value(
            value,
            100,
        )

        assert result == value
        assert result is not value

    def test_list_items_are_processed(
        self,
    ) -> None:
        value = [
            "short",
            "abcdefghijklmnopqrstuvwxyz",
            42,
        ]

        result = _limit_value(
            value,
            20,
        )

        assert result == [
            "short",
            _truncate(
                "abcdefghijklmnopqrstuvwxyz",
                20,
            ),
            42,
        ]

    def test_nested_dictionary_in_list_is_processed(
        self,
    ) -> None:
        value = [
            {
                "message": "abcdefghijklmnopqrstuvwxyz",
            }
        ]

        result = _limit_value(
            value,
            20,
        )

        assert result == [
            {
                "message": _truncate(
                    "abcdefghijklmnopqrstuvwxyz",
                    20,
                ),
            }
        ]


class TestLimitValueTuple:
    def test_empty_tuple_becomes_empty_list(
        self,
    ) -> None:
        result = _limit_value(
            (),
            20,
        )

        assert result == []
        assert isinstance(result, list)

    def test_tuple_becomes_list(
        self,
    ) -> None:
        result = _limit_value(
            (
                "one",
                "two",
            ),
            20,
        )

        assert result == [
            "one",
            "two",
        ]
        assert isinstance(result, list)

    def test_tuple_values_are_processed_recursively(
        self,
    ) -> None:
        result = _limit_value(
            (
                "abcdefghijklmnopqrstuvwxyz",
                42,
            ),
            20,
        )

        assert result == [
            _truncate(
                "abcdefghijklmnopqrstuvwxyz",
                20,
            ),
            42,
        ]


class TestLimitValueSet:
    def test_empty_set_becomes_empty_list(
        self,
    ) -> None:
        result = _limit_value(
            set(),
            20,
        )

        assert result == []
        assert isinstance(result, list)

    def test_set_becomes_list(
        self,
    ) -> None:
        value = {
            1,
            2,
            3,
        }

        result = _limit_value(
            value,
            20,
        )

        assert isinstance(result, list)
        assert set(result) == {
            1,
            2,
            3,
        }

    def test_set_items_are_processed(
        self,
    ) -> None:
        value = {
            "abcdefghijklmnopqrstuvwxyz",
        }

        result = _limit_value(
            value,
            20,
        )

        assert result == [
            _truncate(
                "abcdefghijklmnopqrstuvwxyz",
                20,
            )
        ]


class TestUnsupportedValue:
    def test_object_uses_repr(
        self,
    ) -> None:
        value = ShortReprObject()

        result = _limit_value(
            value,
            100,
        )

        assert result == "short"

    def test_long_object_repr_is_truncated(
        self,
    ) -> None:
        value = ExampleObject()

        result = _limit_value(
            value,
            25,
        )

        assert result == _truncate(
            repr(value),
            25,
        )

    def test_bytes_use_repr(
        self,
    ) -> None:
        value = b"abcdefghijklmnopqrstuvwxyz"

        result = _limit_value(
            value,
            20,
        )

        assert result == _truncate(
            repr(value),
            20,
        )

    def test_frozenset_uses_repr(
        self,
    ) -> None:
        value = frozenset(
            {
                1,
                2,
            }
        )

        result = _limit_value(
            value,
            100,
        )

        assert result == repr(value)


class TestLimitParameters:
    def test_empty_parameters_return_empty_dictionary(
        self,
    ) -> None:
        result = limit_parameters(
            {},
            100,
        )

        assert result == {}

    def test_returns_new_dictionary(
        self,
    ) -> None:
        parameters = {
            "name": "value",
        }

        result = limit_parameters(
            parameters,
            100,
        )

        assert result == parameters
        assert result is not parameters

    def test_top_level_parameter_names_are_preserved(
        self,
    ) -> None:
        parameters = {
            "customer_id": 42,
            "customer_name": "test",
        }

        result = limit_parameters(
            parameters,
            100,
        )

        assert list(result) == [
            "customer_id",
            "customer_name",
        ]

    def test_limits_top_level_string_values(
        self,
    ) -> None:
        parameters = {
            "short": "hello",
            "long": "abcdefghijklmnopqrstuvwxyz",
        }

        result = limit_parameters(
            parameters,
            20,
        )

        assert result == {
            "short": "hello",
            "long": _truncate(
                "abcdefghijklmnopqrstuvwxyz",
                20,
            ),
        }

    def test_recursively_limits_parameters(
        self,
    ) -> None:
        parameters = {
            "name": "abcdefghijklmnopqrstuvwxyz",
            "configuration": {
                "message": "abcdefghijklmnopqrstuvwxyz",
                "count": 42,
            },
            "items": [
                "abcdefghijklmnopqrstuvwxyz",
                {
                    "description": (
                        "abcdefghijklmnopqrstuvwxyz"
                    ),
                },
            ],
            "values": (
                "abcdefghijklmnopqrstuvwxyz",
                True,
            ),
        }

        result = limit_parameters(
            parameters,
            20,
        )

        truncated = _truncate(
            "abcdefghijklmnopqrstuvwxyz",
            20,
        )

        assert result == {
            "name": truncated,
            "configuration": {
                "message": truncated,
                "count": 42,
            },
            "items": [
                truncated,
                {
                    "description": truncated,
                },
            ],
            "values": [
                truncated,
                True,
            ],
        }


class TestInputImmutability:
    def test_original_top_level_dictionary_is_not_modified(
        self,
    ) -> None:
        parameters = {
            "value": "abcdefghijklmnopqrstuvwxyz",
        }

        original = dict(parameters)

        limit_parameters(
            parameters,
            20,
        )

        assert parameters == original

    def test_original_nested_dictionary_is_not_modified(
        self,
    ) -> None:
        nested = {
            "value": "abcdefghijklmnopqrstuvwxyz",
        }

        parameters = {
            "nested": nested,
        }

        limit_parameters(
            parameters,
            20,
        )

        assert nested == {
            "value": "abcdefghijklmnopqrstuvwxyz",
        }

    def test_original_list_is_not_modified(
        self,
    ) -> None:
        nested = [
            "abcdefghijklmnopqrstuvwxyz",
        ]

        parameters = {
            "nested": nested,
        }

        limit_parameters(
            parameters,
            20,
        )

        assert nested == [
            "abcdefghijklmnopqrstuvwxyz",
        ]

    def test_nested_dictionary_result_is_new(
        self,
    ) -> None:
        nested = {
            "value": "hello",
        }

        result = limit_parameters(
            {
                "nested": nested,
            },
            100,
        )

        assert result["nested"] is not nested

    def test_nested_list_result_is_new(
        self,
    ) -> None:
        nested = [
            "hello",
        ]

        result = limit_parameters(
            {
                "nested": nested,
            },
            100,
        )

        assert result["nested"] is not nested


class TestBoundaryBehaviour:
    @pytest.mark.parametrize(
        "length",
        [
            1,
            5,
            10,
            20,
            100,
        ],
    )
    def test_string_with_exact_limit_is_unchanged(
        self,
        length: int,
    ) -> None:
        value = "x" * length

        result = _limit_value(
            value,
            length,
        )

        assert result == value

    @pytest.mark.parametrize(
        "length",
        [
            20,
            25,
            50,
            100,
        ],
    )
    def test_string_one_character_over_limit_is_truncated(
        self,
        length: int,
    ) -> None:
        value = "x" * (length + 1)

        result = _limit_value(
            value,
            length,
        )

        assert result.endswith(
            TRUNCATION_SUFFIX
        )
        assert len(result) == length


class TestMixedParameterStructure:
    def test_complex_parameter_tree(
        self,
    ) -> None:
        long_value = (
            "abcdefghijklmnopqrstuvwxyz"
        )
        truncated = _truncate(
            long_value,
            20,
        )

        parameters = {
            "application": "monitaudit",
            "count": 42,
            "enabled": True,
            "value": None,
            "description": long_value,
            "metadata": {
                "short": "value",
                "long": long_value,
                "items": [
                    long_value,
                    100,
                    False,
                ],
                "coordinates": (
                    long_value,
                    10,
                ),
            },
        }

        result = limit_parameters(
            parameters,
            20,
        )

        assert result == {
            "application": "monitaudit",
            "count": 42,
            "enabled": True,
            "value": None,
            "description": truncated,
            "metadata": {
                "short": "value",
                "long": truncated,
                "items": [
                    truncated,
                    100,
                    False,
                ],
                "coordinates": [
                    truncated,
                    10,
                ],
            },
        }