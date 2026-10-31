"""
monitaudit sensitive-parameter suffix redaction example.

Purpose
-------
Demonstrates how monitaudit automatically redacts traced parameters whose names
end with one of the configured sensitive suffixes.

The monitaudit configuration is loaded from:

    examples/config/main_redaction_suffixes.yaml

This example deliberately uses parameter names that are not necessarily exact
sensitive names, but whose suffixes identify them as sensitive.

Examples:

    database_password
    service_api_key
    github_token
    client_secret

monitaudit should replace their captured values with:

    ***

The traced function itself still receives the original values.

Demonstrates
------------
- @obs.trace parameter capture
- sensitive suffix matching
- password suffix redaction
- API-key suffix redaction
- token suffix redaction
- secret suffix redaction
- preservation of non-sensitive values
- original parameter values remaining available to the function
- JsonSink inspection
- FileSink inspection

Use this example when
---------------------
- validating SENSITIVE_SUFFIXES
- testing changes to redaction.py
- checking suffix-based redaction
- verifying captured trace parameters
- checking JsonSink output for leaked values
- checking FileSink output for leaked values

Expected redaction
------------------
The following parameters should be redacted:

    database_password -> ***
    service_api_key   -> ***
    github_token      -> ***
    client_secret     -> ***

The following parameter should remain visible:

    visible           -> visible-value

Important
---------
Redaction affects the captured trace representation.

It does not change the arguments received by the actual Python function.

The function therefore still receives:

    database_password = database-secret
    service_api_key   = api-secret
    github_token      = token-secret
    client_secret     = client-secret
    visible           = visible-value

Security
--------
Do not deliberately place secrets in log messages or exception messages.

Trace-parameter redaction protects captured parameters based on parameter
names. It does not sanitise arbitrary strings in messages.
"""

from __future__ import annotations

from pathlib import Path

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_redaction_suffixes.yaml"
)


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def demo(
        database_password: str,
        service_api_key: str,
        github_token: str,
        client_secret: str,
        visible: str,
    ) -> None:
        """
        Demonstrate suffix-based parameter redaction.

        Assertions prove that the function receives the original values.
        """

        assert (
            database_password
            == "database-secret"
        )

        assert (
            service_api_key
            == "api-secret"
        )

        assert (
            github_token
            == "token-secret"
        )

        assert (
            client_secret
            == "client-secret"
        )

        assert visible == "visible-value"

        obs.info(
            "Function received original parameter values",
            visible=visible,
        )

    obs.info(
        "Redaction suffix example started",
        example="main_redaction_suffixes",
    )

    demo(
        database_password="database-secret",
        service_api_key="api-secret",
        github_token="token-secret",
        client_secret="client-secret",
        visible="visible-value",
    )

    obs.info(
        "Redaction suffix example completed"
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit redaction-suffix example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] traced parameter capture\n"
        "  [x] suffix-based redaction\n"
        "  [x] _password suffix\n"
        "  [x] _api_key suffix\n"
        "  [x] _token suffix\n"
        "  [x] _secret suffix\n"
        "  [x] non-sensitive value remains visible\n"
        "  [x] function receives original values\n"
        "\n"
        "Expected captured trace parameters:\n"
        "\n"
        '  database_password = "***"\n'
        '  service_api_key   = "***"\n'
        '  github_token      = "***"\n'
        '  client_secret     = "***"\n'
        "  visible           = \"visible-value\"\n"
        "\n"
        "Expected original function values:\n"
        "\n"
        "  database_password = database-secret\n"
        "  service_api_key   = api-secret\n"
        "  github_token      = token-secret\n"
        "  client_secret     = client-secret\n"
        "  visible           = visible-value\n"
        "\n"
        "Important distinction:\n"
        "\n"
        "  function arguments\n"
        "      -> original values\n"
        "\n"
        "  captured monitaudit parameters\n"
        "      -> sensitive values replaced with ***\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect trace hierarchy\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_redaction_suffixes.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_redaction_suffixes.jsonl\n"
        "\n"
        "In JSON find the demo trace and inspect:\n"
        "  - function\n"
        "  - attributes.event\n"
        "  - parameters.database_password\n"
        "  - parameters.service_api_key\n"
        "  - parameters.github_token\n"
        "  - parameters.client_secret\n"
        "  - parameters.visible\n"
        "\n"
        "Security verification:\n"
        "\n"
        "  These values must NOT occur inside captured parameters:\n"
        "\n"
        "    database-secret\n"
        "    api-secret\n"
        "    token-secret\n"
        "    client-secret\n"
        "\n"
        "  Instead they should appear as:\n"
        "\n"
        "    ***\n"
        "\n"
        "  The non-sensitive value should remain:\n"
        "\n"
        "    visible-value\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_redaction_suffixes.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_redaction_suffixes.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()