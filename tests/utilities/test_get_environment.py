# tests/utilities/test_get_environment.py

from __future__ import annotations

import pytest

from monitaudit.utilities.get_environment import (
    _ALLOWED_ENVIRONMENTS,
    get_environment,
)


@pytest.fixture(autouse=True)
def clean_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Ensure environment tests are isolated from the host environment.
    """

    monkeypatch.delenv(
        "MONITAUDIT_ENV",
        raising=False,
    )
    monkeypatch.delenv(
        "ENV",
        raising=False,
    )


class TestDefaultEnvironment:
    def test_defaults_to_dev_when_variables_are_missing(
        self,
    ) -> None:
        result = get_environment()

        assert result == "dev"

    def test_uses_dev_when_monitaudit_env_is_missing_and_env_is_missing(
        self,
    ) -> None:
        result = get_environment()

        assert result == "dev"


class TestMonitauditEnvironment:
    @pytest.mark.parametrize(
        "environment",
        [
            "acc",
            "prod",
        ],
    )
    def test_uses_monitaudit_env_for_non_dev_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            environment,
        )

        result = get_environment()

        assert result == environment

    @pytest.mark.parametrize(
        ("configured", "expected"),
        [
            ("ACC", "acc"),
            ("Acc", "acc"),
            ("PRoD", "prod"),
            ("PROD", "prod"),
        ],
    )
    def test_monitaudit_env_is_case_insensitive(
        self,
        monkeypatch: pytest.MonkeyPatch,
        configured: str,
        expected: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            configured,
        )

        result = get_environment()

        assert result == expected


class TestEnvironmentFallback:
    @pytest.mark.parametrize(
        "environment",
        [
            "dev",
            "acc",
            "prod",
        ],
    )
    def test_uses_env_when_monitaudit_env_is_dev(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )
        monkeypatch.setenv(
            "ENV",
            environment,
        )

        result = get_environment()

        assert result == environment

    @pytest.mark.parametrize(
        ("configured", "expected"),
        [
            ("DEV", "dev"),
            ("Dev", "dev"),
            ("ACC", "acc"),
            ("Acc", "acc"),
            ("PROD", "prod"),
            ("Prod", "prod"),
        ],
    )
    def test_env_is_case_insensitive(
        self,
        monkeypatch: pytest.MonkeyPatch,
        configured: str,
        expected: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )
        monkeypatch.setenv(
            "ENV",
            configured,
        )

        result = get_environment()

        assert result == expected

    def test_uppercase_monitaudit_dev_also_uses_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "DEV",
        )
        monkeypatch.setenv(
            "ENV",
            "prod",
        )

        result = get_environment()

        assert result == "prod"

    def test_mixed_case_monitaudit_dev_also_uses_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "DeV",
        )
        monkeypatch.setenv(
            "ENV",
            "acc",
        )

        result = get_environment()

        assert result == "acc"

    def test_env_defaults_to_dev_when_monitaudit_env_is_dev(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )

        result = get_environment()

        assert result == "dev"


class TestEnvironmentPrecedence:
    @pytest.mark.parametrize(
        ("monitaudit_env", "env", "expected"),
        [
            ("acc", "dev", "acc"),
            ("acc", "prod", "acc"),
            ("prod", "dev", "prod"),
            ("prod", "acc", "prod"),
        ],
    )
    def test_non_dev_monitaudit_env_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        monitaudit_env: str,
        env: str,
        expected: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            monitaudit_env,
        )
        monkeypatch.setenv(
            "ENV",
            env,
        )

        result = get_environment()

        assert result == expected

    @pytest.mark.parametrize(
        ("monitaudit_env", "env", "expected"),
        [
            ("dev", "acc", "acc"),
            ("dev", "prod", "prod"),
            ("DEV", "ACC", "acc"),
            ("DEV", "PROD", "prod"),
        ],
    )
    def test_dev_monitaudit_env_defers_to_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        monitaudit_env: str,
        env: str,
        expected: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            monitaudit_env,
        )
        monkeypatch.setenv(
            "ENV",
            env,
        )

        result = get_environment()

        assert result == expected

    def test_invalid_env_is_ignored_when_monitaudit_env_is_acc(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "acc",
        )
        monkeypatch.setenv(
            "ENV",
            "invalid",
        )

        result = get_environment()

        assert result == "acc"

    def test_invalid_env_is_ignored_when_monitaudit_env_is_prod(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "prod",
        )
        monkeypatch.setenv(
            "ENV",
            "invalid",
        )

        result = get_environment()

        assert result == "prod"


class TestInvalidEnvironments:
    @pytest.mark.parametrize(
        "environment",
        [
            "",
            "test",
            "local",
            "development",
            "acceptance",
            "production",
            "qa",
            "uat",
            "DEVX",
            "123",
        ],
    )
    def test_rejects_invalid_monitaudit_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            environment,
        )

        with pytest.raises(
            ValueError,
            match="Unsupported monitaudit environment",
        ):
            get_environment()

    @pytest.mark.parametrize(
        "environment",
        [
            "",
            "test",
            "local",
            "development",
            "acceptance",
            "production",
            "qa",
            "uat",
            "123",
        ],
    )
    def test_rejects_invalid_env_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )
        monkeypatch.setenv(
            "ENV",
            environment,
        )

        with pytest.raises(
            ValueError,
            match="Unsupported monitaudit environment",
        ):
            get_environment()

    def test_error_contains_invalid_monitaudit_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "stage",
        )

        with pytest.raises(ValueError) as exception_info:
            get_environment()

        assert (
            str(exception_info.value)
            == "Unsupported monitaudit environment: 'stage'"
        )

    def test_error_contains_invalid_env_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )
        monkeypatch.setenv(
            "ENV",
            "stage",
        )

        with pytest.raises(ValueError) as exception_info:
            get_environment()

        assert (
            str(exception_info.value)
            == "Unsupported monitaudit environment: 'stage'"
        )

    def test_invalid_environment_is_lowercased_in_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "STAGE",
        )

        with pytest.raises(ValueError) as exception_info:
            get_environment()

        assert (
            str(exception_info.value)
            == "Unsupported monitaudit environment: 'stage'"
        )


class TestWhitespaceBehaviour:
    @pytest.mark.parametrize(
        "environment",
        [
            " dev",
            "dev ",
            " dev ",
            " acc",
            "acc ",
            " prod ",
            "\tdev",
            "dev\n",
        ],
    )
    def test_environment_values_are_not_stripped(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            environment,
        )

        with pytest.raises(ValueError):
            get_environment()

    def test_env_fallback_values_are_not_stripped(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )
        monkeypatch.setenv(
            "ENV",
            " prod ",
        )

        with pytest.raises(ValueError) as exception_info:
            get_environment()

        assert (
            str(exception_info.value)
            == "Unsupported monitaudit environment: ' prod '"
        )


class TestAllowedEnvironments:
    def test_allowed_environments_contains_expected_values(
        self,
    ) -> None:
        assert _ALLOWED_ENVIRONMENTS == {
            "dev",
            "acc",
            "prod",
        }

    def test_allowed_environments_contains_only_strings(
        self,
    ) -> None:
        assert all(
            isinstance(environment, str)
            for environment in _ALLOWED_ENVIRONMENTS
        )

    @pytest.mark.parametrize(
        "environment",
        sorted(_ALLOWED_ENVIRONMENTS),
    )
    def test_every_allowed_environment_can_be_returned(
        self,
        monkeypatch: pytest.MonkeyPatch,
        environment: str,
    ) -> None:
        if environment == "dev":
            monkeypatch.setenv(
                "MONITAUDIT_ENV",
                "dev",
            )
            monkeypatch.setenv(
                "ENV",
                "dev",
            )
        else:
            monkeypatch.setenv(
                "MONITAUDIT_ENV",
                environment,
            )

        assert get_environment() == environment