# tests/utilities/test_redaction.py

from __future__ import annotations

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


class TestConstants:
    def test_redacted_value(self) -> None:
        assert REDACTED_VALUE == "***"

    def test_sensitive_parameters_is_frozenset(
        self,
    ) -> None:
        assert isinstance(
            SENSITIVE_PARAMETERS,
            frozenset,
        )

    def test_sensitive_suffixes_is_tuple(
        self,
    ) -> None:
        assert isinstance(
            SENSITIVE_SUFFIXES,
            tuple,
        )

    def test_sensitive_parameters_are_not_empty(
        self,
    ) -> None:
        assert SENSITIVE_PARAMETERS

    def test_sensitive_suffixes_are_not_empty(
        self,
    ) -> None:
        assert SENSITIVE_SUFFIXES

    def test_sensitive_parameters_are_unique(
        self,
    ) -> None:
        assert len(SENSITIVE_PARAMETERS) == len(
            set(SENSITIVE_PARAMETERS)
        )

    def test_sensitive_suffixes_are_unique(
        self,
    ) -> None:
        assert len(SENSITIVE_SUFFIXES) == len(
            set(SENSITIVE_SUFFIXES)
        )

    def test_sensitive_parameters_are_lowercase(
        self,
    ) -> None:
        assert all(
            value == value.casefold()
            for value in SENSITIVE_PARAMETERS
        )

    def test_sensitive_suffixes_are_lowercase(
        self,
    ) -> None:
        assert all(
            value == value.casefold()
            for value in SENSITIVE_SUFFIXES
        )

    def test_sensitive_suffixes_start_with_underscore(
        self,
    ) -> None:
        assert all(
            suffix.startswith("_")
            for suffix in SENSITIVE_SUFFIXES
        )


class TestSensitiveParameterDefinitions:
    def test_exact_sensitive_parameter_set(
        self,
    ) -> None:
        assert SENSITIVE_PARAMETERS == frozenset(
            {
                "password",
                "passwd",
                "pwd",
                "passphrase",
                "secret",
                "api_key",
                "apikey",
                "private_key",
                "access_key",
                "secret_key",
                "token",
                "pat",
                "authorization",
                "auth",
                "credential",
                "credentials",
                "cookie",
                "cookies",
                "session_id",
                "sessionid",
                "connection_string",
                "connectionstring",
                "dsn",
                "database_url",
                "database_uri",
                "db_url",
                "db_uri",
                "jdbc_url",
                "odbc_connection_string",
                "pgpassword",
                "pgpass",
            }
        )

    def test_exact_sensitive_suffixes(
        self,
    ) -> None:
        assert SENSITIVE_SUFFIXES == (
            "_password",
            "_passwd",
            "_pwd",
            "_passphrase",
            "_secret",
            "_token",
            "_api_key",
            "_apikey",
            "_access_key",
            "_secret_key",
            "_private_key",
            "_connection_string",
        )


class TestIsSensitive:
    @pytest.mark.parametrize(
        "name",
        sorted(SENSITIVE_PARAMETERS),
    )
    def test_every_configured_parameter_is_sensitive(
        self,
        name: str,
    ) -> None:
        assert _is_sensitive(name) is True

    @pytest.mark.parametrize(
        "suffix",
        SENSITIVE_SUFFIXES,
    )
    def test_every_configured_suffix_is_sensitive(
        self,
        suffix: str,
    ) -> None:
        assert (
            _is_sensitive(
                f"application{suffix}"
            )
            is True
        )

    @pytest.mark.parametrize(
        "name",
        [
            "PASSWORD",
            "Password",
            "PaSsWoRd",
            "TOKEN",
            "Token",
            "API_KEY",
            "Api_Key",
            "SECRET",
            "Authorization",
            "CONNECTION_STRING",
            "PgPassword",
        ],
    )
    def test_detection_is_case_insensitive(
        self,
        name: str,
    ) -> None:
        assert _is_sensitive(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "database_PASSWORD",
            "client_TOKEN",
            "service_SECRET",
            "user_PWD",
            "service_API_KEY",
            "client_PRIVATE_KEY",
            "database_CONNECTION_STRING",
        ],
    )
    def test_suffix_detection_is_case_insensitive(
        self,
        name: str,
    ) -> None:
        assert _is_sensitive(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "username",
            "user",
            "name",
            "application",
            "environment",
            "message",
            "value",
            "identifier",
            "customer_id",
            "token_count",
            "password_length",
            "secret_name",
            "api_key_name",
            "connection_string_name",
        ],
    )
    def test_non_sensitive_names_are_not_sensitive(
        self,
        name: str,
    ) -> None:
        assert _is_sensitive(name) is False

    def test_sensitive_suffix_must_be_at_end(
        self,
    ) -> None:
        assert (
            _is_sensitive(
                "password_length"
            )
            is False
        )

    def test_sensitive_word_inside_name_is_not_enough(
        self,
    ) -> None:
        assert (
            _is_sensitive(
                "my_password_value"
            )
            is False
        )

    def test_exact_password_is_sensitive(
        self,
    ) -> None:
        assert _is_sensitive("password") is True

    def test_prefixed_password_is_sensitive(
        self,
    ) -> None:
        assert (
            _is_sensitive(
                "database_password"
            )
            is True
        )


class TestRedactParameters:
    def test_empty_parameters_return_empty_dictionary(
        self,
    ) -> None:
        result = redact_parameters({})

        assert result == {}

    def test_returns_new_dictionary(
        self,
    ) -> None:
        parameters = {
            "username": "dirk",
        }

        result = redact_parameters(
            parameters
        )

        assert result == parameters
        assert result is not parameters

    @pytest.mark.parametrize(
        "name",
        sorted(SENSITIVE_PARAMETERS),
    )
    def test_redacts_every_sensitive_parameter(
        self,
        name: str,
    ) -> None:
        result = redact_parameters(
            {
                name: "sensitive-value",
            }
        )

        assert result == {
            name: REDACTED_VALUE,
        }

    @pytest.mark.parametrize(
        "suffix",
        SENSITIVE_SUFFIXES,
    )
    def test_redacts_every_sensitive_suffix(
        self,
        suffix: str,
    ) -> None:
        name = f"service{suffix}"

        result = redact_parameters(
            {
                name: "sensitive-value",
            }
        )

        assert result == {
            name: REDACTED_VALUE,
        }

    def test_preserves_non_sensitive_parameter(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "username": "dirk",
            }
        )

        assert result == {
            "username": "dirk",
        }

    def test_redacts_only_sensitive_parameters(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "username": "dirk",
                "password": "secret-password",
                "customer_id": 42,
                "api_key": "secret-key",
                "environment": "dev",
            }
        )

        assert result == {
            "username": "dirk",
            "password": REDACTED_VALUE,
            "customer_id": 42,
            "api_key": REDACTED_VALUE,
            "environment": "dev",
        }

    def test_top_level_detection_is_case_insensitive(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "PASSWORD": "password",
                "Token": "token",
                "API_KEY": "key",
            }
        )

        assert result == {
            "PASSWORD": REDACTED_VALUE,
            "Token": REDACTED_VALUE,
            "API_KEY": REDACTED_VALUE,
        }

    def test_preserves_original_key_spelling(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "PASSWORD": "value",
            }
        )

        assert list(result) == [
            "PASSWORD"
        ]

        assert (
            result["PASSWORD"]
            == REDACTED_VALUE
        )

    def test_sensitive_value_is_not_examined(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "password": {
                    "nested": "secret",
                }
            }
        )

        assert result == {
            "password": REDACTED_VALUE,
        }

    def test_sensitive_scalar_values_under_safe_keys_are_preserved(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "message": "password",
                "value": "secret",
            }
        )

        assert result == {
            "message": "password",
            "value": "secret",
        }


class TestNestedDictionaryRedaction:
    def test_redacts_nested_sensitive_key(
        self,
    ) -> None:
        parameters = {
            "database": {
                "username": "user",
                "password": "top-secret",
            }
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "database": {
                "username": "user",
                "password": REDACTED_VALUE,
            }
        }

    def test_redacts_deeply_nested_sensitive_key(
        self,
    ) -> None:
        parameters = {
            "configuration": {
                "database": {
                    "credentials": {
                        "username": "user",
                        "password": "secret",
                    }
                }
            }
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "configuration": {
                "database": {
                    "credentials": REDACTED_VALUE,
                }
            }
        }

    def test_redacts_multiple_nested_sensitive_values(
        self,
    ) -> None:
        parameters = {
            "database": {
                "password": "password-value",
                "connection_string": "connection-value",
            },
            "service": {
                "api_key": "api-value",
                "token": "token-value",
            },
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "database": {
                "password": REDACTED_VALUE,
                "connection_string": REDACTED_VALUE,
            },
            "service": {
                "api_key": REDACTED_VALUE,
                "token": REDACTED_VALUE,
            },
        }

    def test_nested_dictionary_key_detection_is_case_insensitive(
        self,
    ) -> None:
        parameters = {
            "configuration": {
                "PASSWORD": "value",
                "Api_Key": "value",
            }
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "configuration": {
                "PASSWORD": REDACTED_VALUE,
                "Api_Key": REDACTED_VALUE,
            }
        }

    def test_nested_non_string_key_is_stringified_for_detection(
        self,
    ) -> None:
        parameters = {
            "values": {
                42: "value",
            }
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "values": {
                42: "value",
            }
        }

    def test_nested_original_key_type_is_preserved(
        self,
    ) -> None:
        parameters = {
            "values": {
                42: "value",
            }
        }

        result = redact_parameters(
            parameters
        )

        nested = result["values"]

        assert isinstance(
            nested,
            dict,
        )
        assert 42 in nested


class TestListRedaction:
    def test_preserves_list_type(
        self,
    ) -> None:
        value = [
            "one",
            "two",
        ]

        result = _redact_value(value)

        assert isinstance(result, list)
        assert result == value

    def test_redacts_dictionary_inside_list(
        self,
    ) -> None:
        parameters = {
            "items": [
                {
                    "username": "user",
                    "password": "secret",
                }
            ]
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "items": [
                {
                    "username": "user",
                    "password": REDACTED_VALUE,
                }
            ]
        }

    def test_redacts_deeply_nested_list_values(
        self,
    ) -> None:
        parameters = {
            "items": [
                [
                    {
                        "token": "secret-token",
                    }
                ]
            ]
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "items": [
                [
                    {
                        "token": REDACTED_VALUE,
                    }
                ]
            ]
        }


class TestTupleRedaction:
    def test_preserves_tuple_type(
        self,
    ) -> None:
        value = (
            "one",
            "two",
        )

        result = _redact_value(value)

        assert isinstance(result, tuple)
        assert result == value

    def test_redacts_dictionary_inside_tuple(
        self,
    ) -> None:
        value = (
            {
                "password": "secret",
            },
            {
                "username": "user",
            },
        )

        result = _redact_value(value)

        assert result == (
            {
                "password": REDACTED_VALUE,
            },
            {
                "username": "user",
            },
        )


class TestSetRedaction:
    def test_preserves_set_type(
        self,
    ) -> None:
        value = {
            "one",
            "two",
        }

        result = _redact_value(value)

        assert isinstance(result, set)
        assert result == value

    def test_scalar_set_values_are_preserved(
        self,
    ) -> None:
        value = {
            "password",
            "token",
            "normal",
        }

        result = _redact_value(value)

        assert result == value

    def test_sensitive_strings_in_set_are_not_redacted_by_value(
        self,
    ) -> None:
        result = redact_parameters(
            {
                "values": {
                    "password",
                    "secret",
                    "token",
                }
            }
        )

        assert result == {
            "values": {
                "password",
                "secret",
                "token",
            }
        }


class TestFrozenSetRedaction:
    def test_preserves_frozenset_type(
        self,
    ) -> None:
        value = frozenset(
            {
                "one",
                "two",
            }
        )

        result = _redact_value(value)

        assert isinstance(
            result,
            frozenset,
        )
        assert result == value

    def test_frozenset_values_are_processed(
        self,
    ) -> None:
        value = frozenset(
            {
                "password",
                "normal",
            }
        )

        result = _redact_value(value)

        assert result == value


class TestRedactValueScalars:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            True,
            False,
            0,
            1,
            -1,
            1.5,
            "",
            "hello",
            b"bytes",
        ],
    )
    def test_scalar_values_are_returned_unchanged(
        self,
        value: Any,
    ) -> None:
        result = _redact_value(value)

        assert result == value

    def test_arbitrary_object_is_returned_unchanged(
        self,
    ) -> None:
        value = object()

        result = _redact_value(value)

        assert result is value


class TestNestedCollections:
    def test_dictionary_inside_list_inside_tuple(
        self,
    ) -> None:
        value = (
            [
                {
                    "username": "user",
                    "password": "secret",
                }
            ],
        )

        result = _redact_value(value)

        assert result == (
            [
                {
                    "username": "user",
                    "password": REDACTED_VALUE,
                }
            ],
        )

    def test_mixed_nested_structure(
        self,
    ) -> None:
        parameters = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret",
                    "content_type": "application/json",
                },
                "body": [
                    {
                        "user": "dirk",
                        "password": "secret-password",
                    },
                    {
                        "service_token": "token-value",
                        "value": 42,
                    },
                ],
            },
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "request": {
                "headers": {
                    "authorization": REDACTED_VALUE,
                    "content_type": "application/json",
                },
                "body": [
                    {
                        "user": "dirk",
                        "password": REDACTED_VALUE,
                    },
                    {
                        "service_token": REDACTED_VALUE,
                        "value": 42,
                    },
                ],
            },
        }


class TestInputImmutability:
    def test_top_level_dictionary_is_not_modified(
        self,
    ) -> None:
        parameters = {
            "username": "user",
            "password": "secret",
        }

        original = {
            "username": "user",
            "password": "secret",
        }

        redact_parameters(parameters)

        assert parameters == original

    def test_nested_dictionary_is_not_modified(
        self,
    ) -> None:
        nested = {
            "username": "user",
            "password": "secret",
        }

        parameters = {
            "database": nested,
        }

        redact_parameters(parameters)

        assert nested == {
            "username": "user",
            "password": "secret",
        }

    def test_nested_list_is_not_modified(
        self,
    ) -> None:
        values = [
            {
                "password": "secret",
            }
        ]

        parameters = {
            "values": values,
        }

        redact_parameters(parameters)

        assert values == [
            {
                "password": "secret",
            }
        ]

    def test_nested_tuple_is_not_modified(
        self,
    ) -> None:
        values = (
            {
                "token": "secret",
            },
        )

        parameters = {
            "values": values,
        }

        redact_parameters(parameters)

        assert values == (
            {
                "token": "secret",
            },
        )

    def test_result_nested_dictionary_is_new(
        self,
    ) -> None:
        nested = {
            "username": "user",
        }

        result = redact_parameters(
            {
                "database": nested,
            }
        )

        assert (
            result["database"]
            is not nested
        )

    def test_result_nested_list_is_new(
        self,
    ) -> None:
        nested = [
            "one",
            "two",
        ]

        result = redact_parameters(
            {
                "values": nested,
            }
        )

        assert result["values"] is not nested

    def test_result_nested_tuple_is_new(
        self,
    ) -> None:
        nested = (
            "one",
            "two",
        )

        result = redact_parameters(
            {
                "values": nested,
            }
        )

        assert result["values"] is not nested

    def test_result_nested_set_is_new(
        self,
    ) -> None:
        nested = {
            "one",
            "two",
        }

        result = redact_parameters(
            {
                "values": nested,
            }
        )

        assert result["values"] is not nested

    def test_result_nested_frozenset_is_new(
        self,
    ) -> None:
        nested = frozenset(
            {
                "one",
                "two",
            }
        )

        result = redact_parameters(
            {
                "values": nested,
            }
        )

        assert result["values"] is not nested


class TestSuffixBehaviour:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (
                "database_password",
                True,
            ),
            (
                "database_passwd",
                True,
            ),
            (
                "database_pwd",
                True,
            ),
            (
                "database_passphrase",
                True,
            ),
            (
                "service_secret",
                True,
            ),
            (
                "service_token",
                True,
            ),
            (
                "service_api_key",
                True,
            ),
            (
                "service_apikey",
                True,
            ),
            (
                "service_access_key",
                True,
            ),
            (
                "service_secret_key",
                True,
            ),
            (
                "service_private_key",
                True,
            ),
            (
                "database_connection_string",
                True,
            ),
            (
                "password_value",
                False,
            ),
            (
                "token_value",
                False,
            ),
            (
                "secret_value",
                False,
            ),
        ],
    )
    def test_suffix_matching(
        self,
        name: str,
        expected: bool,
    ) -> None:
        assert _is_sensitive(name) is expected


class TestRealisticParameterRedaction:
    def test_database_configuration(
        self,
    ) -> None:
        parameters = {
            "host": "db.example.test",
            "port": 5432,
            "database": "application",
            "username": "application-user",
            "password": "super-secret",
            "ssl": True,
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "host": "db.example.test",
            "port": 5432,
            "database": "application",
            "username": "application-user",
            "password": REDACTED_VALUE,
            "ssl": True,
        }

    def test_api_configuration(
        self,
    ) -> None:
        parameters = {
            "endpoint": "service",
            "api_key": "api-secret",
            "timeout": 30,
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "endpoint": "service",
            "api_key": REDACTED_VALUE,
            "timeout": 30,
        }

    def test_databricks_style_parameters(
        self,
    ) -> None:
        parameters = {
            "server_hostname": "workspace",
            "http_path": "sql/warehouse",
            "access_token": "secret-token",
            "catalog": "main",
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "server_hostname": "workspace",
            "http_path": "sql/warehouse",
            "access_token": REDACTED_VALUE,
            "catalog": "main",
        }

    def test_jdbc_parameters(
        self,
    ) -> None:
        parameters = {
            "jdbc_url": "jdbc:example",
            "driver": "example.Driver",
            "username": "user",
            "password": "secret",
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "jdbc_url": REDACTED_VALUE,
            "driver": "example.Driver",
            "username": "user",
            "password": REDACTED_VALUE,
        }

    def test_postgresql_parameters(
        self,
    ) -> None:
        parameters = {
            "PGPASSWORD": "secret",
            "PGPASS": "secret-file",
            "PGHOST": "localhost",
        }

        result = redact_parameters(
            parameters
        )

        assert result == {
            "PGPASSWORD": REDACTED_VALUE,
            "PGPASS": REDACTED_VALUE,
            "PGHOST": "localhost",
        }