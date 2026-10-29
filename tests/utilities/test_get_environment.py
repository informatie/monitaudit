from __future__ import annotations

import pytest

from monitaudit.utilities.get_environment import (
    _ALLOWED_ENVIRONMENTS,
    get_environment,
)


def test_allowed_environments() -> None:
    assert _ALLOWED_ENVIRONMENTS == {
        "dev",
        "acc",
        "prod",
    }


def test_default_environment_is_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "monitaudit_ENV",
        raising=False,
    )

    result = get_environment()

    assert result == "dev"


@pytest.mark.parametrize(
    "environment",
    [
        "dev",
        "acc",
        "prod",
    ],
)
def test_valid_environments(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        environment,
    )

    result = get_environment()

    assert result == environment


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ("DEV", "dev"),
        ("ACC", "acc"),
        ("PROD", "prod"),
        ("Dev", "dev"),
        ("Acc", "acc"),
        ("Prod", "prod"),
        ("dEv", "dev"),
        ("pRoD", "prod"),
    ],
)
def test_environment_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    expected: str,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        environment,
    )

    result = get_environment()

    assert result == expected


@pytest.mark.parametrize(
    "environment",
    [
        "test",
        "local",
        "development",
        "acceptance",
        "production",
        "qa",
        "staging",
        "invalid",
    ],
)
def test_invalid_environment_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        environment,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported monitaudit environment:"
        ),
    ):
        get_environment()


def test_invalid_environment_error_contains_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        "INVALID",
    )

    with pytest.raises(
        ValueError,
    ) as error_info:
        get_environment()

    assert str(error_info.value) == (
        "Unsupported monitaudit environment: "
        "'invalid'"
    )


def test_empty_environment_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        "",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported monitaudit environment:"
        ),
    ):
        get_environment()


def test_environment_with_leading_space_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        " dev",
    )

    with pytest.raises(
        ValueError,
    ):
        get_environment()


def test_environment_with_trailing_space_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        "prod ",
    )

    with pytest.raises(
        ValueError,
    ):
        get_environment()


def test_environment_variable_is_not_modified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "monitaudit_ENV",
        "PROD",
    )

    result = get_environment()

    assert result == "prod"

    import os

    assert os.environ["monitaudit_ENV"] == "PROD"