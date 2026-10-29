from __future__ import annotations

from typing import Any


SENSITIVE_PARAMETERS = frozenset(
    {
        # Passwords
        "password",
        "passwd",
        "pwd",
        "passphrase",

        # Secrets and keys
        "secret",
        "api_key",
        "apikey",
        "private_key",
        "access_key",
        "secret_key",

        # Tokens
        "token",
        "pat",

        # Authentication
        "authorization",
        "auth",
        "credential",
        "credentials",

        # Sessions and cookies
        "cookie",
        "cookies",
        "session_id",
        "sessionid",

        # Connections
        "connection_string",
        "connectionstring",
        "dsn",
        "database_url",
        "database_uri",
        "db_url",
        "db_uri",
        "jdbc_url",
        "odbc_connection_string",

        # PostgreSQL
        "pgpassword",
        "pgpass",
    }
)

SENSITIVE_SUFFIXES = (
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

REDACTED_VALUE = "***"


def redact_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        key: REDACTED_VALUE if _is_sensitive(key) else _redact_value(value)
        for key, value in parameters.items()
    }


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_VALUE
                if _is_sensitive(str(key))
                else _redact_value(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_redact_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)

    if isinstance(value, set):
        return {_redact_value(item) for item in value}

    if isinstance(value, frozenset):
        return frozenset(_redact_value(item) for item in value)

    return value


def _is_sensitive(name: str) -> bool:
    name = name.casefold()

    return (
        name in SENSITIVE_PARAMETERS
        or name.endswith(SENSITIVE_SUFFIXES)
    )