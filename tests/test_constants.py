# tests/test_constants.py

from __future__ import annotations

import pytest

from monitaudit import constants
from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)


class TestFunctionConstants:
    def test_function_start_value(self) -> None:
        assert FUNCTION_START == "function_start"

    def test_function_end_value(self) -> None:
        assert FUNCTION_END == "function_end"

    def test_function_error_value(self) -> None:
        assert FUNCTION_ERROR == "function_error"

    @pytest.mark.parametrize(
        ("constant", "expected"),
        [
            (
                FUNCTION_START,
                "function_start",
            ),
            (
                FUNCTION_END,
                "function_end",
            ),
            (
                FUNCTION_ERROR,
                "function_error",
            ),
        ],
    )
    def test_function_constant_values(
        self,
        constant: str,
        expected: str,
    ) -> None:
        assert constant == expected

    @pytest.mark.parametrize(
        "constant",
        [
            FUNCTION_START,
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_function_constants_are_strings(
        self,
        constant: str,
    ) -> None:
        assert isinstance(constant, str)

    def test_function_constants_have_unique_values(
        self,
    ) -> None:
        values = {
            FUNCTION_START,
            FUNCTION_END,
            FUNCTION_ERROR,
        }

        assert len(values) == 3

    @pytest.mark.parametrize(
        "constant",
        [
            FUNCTION_START,
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_function_constants_are_not_empty(
        self,
        constant: str,
    ) -> None:
        assert constant

    @pytest.mark.parametrize(
        "constant",
        [
            FUNCTION_START,
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_function_constants_are_lowercase(
        self,
        constant: str,
    ) -> None:
        assert constant == constant.lower()


class TestPublicApi:
    def test_all_exports_expected_names(
        self,
    ) -> None:
        assert constants.__all__ == [
            "FUNCTION_END",
            "FUNCTION_ERROR",
            "FUNCTION_START",
        ]

    def test_all_contains_no_duplicate_names(
        self,
    ) -> None:
        assert len(constants.__all__) == len(
            set(constants.__all__)
        )

    @pytest.mark.parametrize(
        "name",
        constants.__all__,
    )
    def test_all_exported_names_exist(
        self,
        name: str,
    ) -> None:
        assert hasattr(constants, name)

    @pytest.mark.parametrize(
        "name",
        constants.__all__,
    )
    def test_all_exported_values_are_strings(
        self,
        name: str,
    ) -> None:
        value = getattr(
            constants,
            name,
        )

        assert isinstance(value, str)

    def test_all_exposes_only_function_constants(
        self,
    ) -> None:
        assert set(constants.__all__) == {
            "FUNCTION_START",
            "FUNCTION_END",
            "FUNCTION_ERROR",
        }


class TestWildcardImportContract:
    def test_public_exports_match_constant_mapping(
        self,
    ) -> None:
        exported = {
            name: getattr(constants, name)
            for name in constants.__all__
        }

        assert exported == {
            "FUNCTION_END": "function_end",
            "FUNCTION_ERROR": "function_error",
            "FUNCTION_START": "function_start",
        }