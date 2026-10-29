from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from monitaudit.utilities.redaction import (
    REDACTED_VALUE,
    SENSITIVE_PARAMETERS,
    SENSITIVE_SUFFIXES,
    _is_sensitive,
    _redact_value,
    redact_parameters,
)


@pytest.mark.parametrize(
    "name",
    sorted(SENSITIVE_PARAMETERS),
)
def test_all_sensitive_parameters_are_detected(
    name: str,
) -> None:
    assert _is_sensitive(name) is True


@pytest.mark.parametrize(
    "suffix",
    SENSITIVE_SUFFIXES,
)
def test_all_sensitive_suffixes_are_detected(
    suffix: str,
) -> None:
    name = f"example{suffix}"

    assert _is_sensitive(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "PASSWORD",
        "Password",
        "PassWord",
        "API_KEY",
        "Api_Key",
        "TOKEN",
        "Authorization",
        "CONNECTION_STRING",
        "PGPASSWORD",
    ],
)
def test_sensitive_detection_is_case_insensitive(
    name: str,
) -> None:
    assert _is_sensitive(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "username",
        "application",
        "environment",
        "hostname",
        "database",
        "table",
        "query",
        "message",
        "path",
        "correlation_id",
    ],
)
def test_non_sensitive_parameter_is_not_detected(
    name: str,
) -> None:
    assert _is_sensitive(name) is False


def test_redact_parameters_redacts_sensitive_values() -> None:
    parameters = {
        "username": "alice",
        "password": "secret-password",
        "api_key": "abc123",
        "token": "token-value",
    }

    result = redact_parameters(parameters)

    assert result == {
        "username": "alice",
        "password": REDACTED_VALUE,
        "api_key": REDACTED_VALUE,
        "token": REDACTED_VALUE,
    }


def test_redact_parameters_supports_suffixes() -> None:
    parameters = {
        "database_password": "database-secret",
        "github_token": "github-secret",
        "service_api_key": "service-secret",
        "azure_private_key": "private-secret",
        "postgres_connection_string": "connection-secret",
        "username": "alice",
    }

    result = redact_parameters(parameters)

    assert result == {
        "database_password": REDACTED_VALUE,
        "github_token": REDACTED_VALUE,
        "service_api_key": REDACTED_VALUE,
        "azure_private_key": REDACTED_VALUE,
        "postgres_connection_string": REDACTED_VALUE,
        "username": "alice",
    }


def test_redact_parameters_is_case_insensitive() -> None:
    parameters = {
        "PASSWORD": "one",
        "Password": "two",
        "API_KEY": "three",
        "GitHub_Token": "four",
    }

    result = redact_parameters(parameters)

    assert result == {
        "PASSWORD": REDACTED_VALUE,
        "Password": REDACTED_VALUE,
        "API_KEY": REDACTED_VALUE,
        "GitHub_Token": REDACTED_VALUE,
    }


def test_redact_parameters_empty_dict() -> None:
    assert redact_parameters({}) == {}


def test_redact_parameters_preserves_non_sensitive_values() -> None:
    parameters: dict[str, Any] = {
        "username": "alice",
        "number": 42,
        "enabled": True,
        "nothing": None,
        "ratio": 1.5,
    }

    result = redact_parameters(parameters)

    assert result == parameters


def test_nested_dictionary_is_redacted() -> None:
    parameters = {
        "database": {
            "host": "localhost",
            "username": "alice",
            "password": "database-password",
            "port": 5432,
        }
    }

    result = redact_parameters(parameters)

    assert result == {
        "database": {
            "host": "localhost",
            "username": "alice",
            "password": REDACTED_VALUE,
            "port": 5432,
        }
    }


def test_deeply_nested_dictionary_is_redacted() -> None:
    parameters = {
        "config": {
            "database": {
                "authentication": {
                    "username": "alice",
                    "password": "secret",
                    "api_key": "key",
                }
            }
        }
    }

    result = redact_parameters(parameters)

    assert result == {
        "config": {
            "database": {
                "authentication": {
                    "username": "alice",
                    "password": REDACTED_VALUE,
                    "api_key": REDACTED_VALUE,
                }
            }
        }
    }


def test_dictionary_key_suffix_is_redacted() -> None:
    parameters = {
        "config": {
            "database_password": "secret",
            "service_token": "secret-token",
            "normal_value": "visible",
        }
    }

    result = redact_parameters(parameters)

    assert result == {
        "config": {
            "database_password": REDACTED_VALUE,
            "service_token": REDACTED_VALUE,
            "normal_value": "visible",
        }
    }


def test_list_values_are_redacted_recursively() -> None:
    parameters = {
        "connections": [
            {
                "username": "alice",
                "password": "first",
            },
            {
                "username": "bob",
                "password": "second",
            },
        ]
    }

    result = redact_parameters(parameters)

    assert result == {
        "connections": [
            {
                "username": "alice",
                "password": REDACTED_VALUE,
            },
            {
                "username": "bob",
                "password": REDACTED_VALUE,
            },
        ]
    }


def test_tuple_values_are_redacted_recursively() -> None:
    value = (
        {
            "username": "alice",
            "password": "secret",
        },
        {
            "token": "secret-token",
        },
    )

    result = _redact_value(value)

    assert isinstance(result, tuple)

    assert result == (
        {
            "username": "alice",
            "password": REDACTED_VALUE,
        },
        {
            "token": REDACTED_VALUE,
        },
    )


def test_set_values_are_preserved_as_set() -> None:
    value = {
        "one",
        "two",
        "three",
    }

    result = _redact_value(value)

    assert isinstance(result, set)
    assert result == value


def test_frozenset_values_are_preserved_as_frozenset() -> None:
    value = frozenset(
        {
            "one",
            "two",
            "three",
        }
    )

    result = _redact_value(value)

    assert isinstance(result, frozenset)
    assert result == value


def test_nested_structures_are_redacted() -> None:
    parameters = {
        "configuration": [
            {
                "database": {
                    "username": "alice",
                    "password": "secret",
                }
            },
            {
                "service": {
                    "api_key": "secret-key",
                    "endpoint": "example",
                }
            },
        ]
    }

    result = redact_parameters(parameters)

    assert result == {
        "configuration": [
            {
                "database": {
                    "username": "alice",
                    "password": REDACTED_VALUE,
                }
            },
            {
                "service": {
                    "api_key": REDACTED_VALUE,
                    "endpoint": "example",
                }
            },
        ]
    }


def test_sensitive_parent_key_redacts_entire_value() -> None:
    parameters = {
        "password": {
            "nested": "value",
            "another": "value",
        }
    }

    result = redact_parameters(parameters)

    assert result == {
        "password": REDACTED_VALUE,
    }


def test_sensitive_list_parameter_redacts_entire_list() -> None:
    parameters = {
        "credentials": [
            "username",
            "password",
        ]
    }

    result = redact_parameters(parameters)

    assert result == {
        "credentials": REDACTED_VALUE,
    }


def test_sensitive_none_value_is_still_redacted() -> None:
    parameters = {
        "password": None,
    }

    result = redact_parameters(parameters)

    assert result == {
        "password": REDACTED_VALUE,
    }


def test_nested_non_string_dictionary_keys_are_supported() -> None:
    parameters = {
        "data": {
            123: "value",
            "password": "secret",
        }
    }

    result = redact_parameters(parameters)

    assert result == {
        "data": {
            123: "value",
            "password": REDACTED_VALUE,
        }
    }


def test_redaction_does_not_modify_original_dictionary() -> None:
    parameters = {
        "username": "alice",
        "password": "secret",
        "nested": {
            "api_key": "key",
            "visible": "hello",
        },
    }

    original = deepcopy(parameters)

    result = redact_parameters(parameters)

    assert parameters == original

    assert result != parameters

    assert result["password"] == REDACTED_VALUE

    assert (
        result["nested"]["api_key"]
        == REDACTED_VALUE
    )


def test_redaction_creates_new_top_level_dictionary() -> None:
    parameters = {
        "username": "alice",
    }

    result = redact_parameters(parameters)

    assert result == parameters
    assert result is not parameters


def test_redaction_creates_new_nested_dictionary() -> None:
    parameters = {
        "config": {
            "username": "alice",
        }
    }

    result = redact_parameters(parameters)

    assert result["config"] == parameters["config"]
    assert result["config"] is not parameters["config"]


def test_redact_value_returns_scalar_unchanged() -> None:
    assert _redact_value("hello") == "hello"
    assert _redact_value(42) == 42
    assert _redact_value(1.5) == 1.5
    assert _redact_value(True) is True
    assert _redact_value(None) is None


@pytest.mark.parametrize(
    "name",
    [
        "my_password",
        "database_passwd",
        "admin_pwd",
        "user_passphrase",
        "client_secret",
        "access_token",
        "service_api_key",
        "service_apikey",
        "azure_access_key",
        "azure_secret_key",
        "ssh_private_key",
        "postgres_connection_string",
    ],
)
def test_recognised_sensitive_suffixes(
    name: str,
) -> None:
    assert _is_sensitive(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "password_hint",
        "token_count",
        "secret_name",
        "api_key_name",
        "password_enabled",
        "token_type",
    ],
)
def test_sensitive_word_not_at_end_is_not_suffix_match(
    name: str,
) -> None:
    assert _is_sensitive(name) is False