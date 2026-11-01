"""
monitaudit exact-name sensitive-parameter redaction example.

Purpose
-------
Demonstrates how monitaudit automatically redacts traced parameters whose names
exactly match entries in SENSITIVE_PARAMETERS.

The monitaudit configuration is loaded from:

    examples/config/main_redaction_exact_names.yaml

This example passes several deliberately sensitive parameters to a traced
function:

    password
    secret
    api_key
    token
    authorization

monitaudit should replace their captured trace values with:

    ***

A normal non-sensitive parameter named:

    visible

must remain unchanged.

The traced Python function itself must continue receiving the original,
unredacted values.

Demonstrates
------------
- @mta.trace
- automatic parameter capture
- exact sensitive-name detection
- password redaction
- secret redaction
- API-key redaction
- token redaction
- authorization redaction
- preservation of non-sensitive parameters
- original values remaining available inside the function
- function_start parameters
- function_end parameters
- JsonSink inspection
- FileSink inspection

Use this example when
---------------------
- validating SENSITIVE_PARAMETERS
- testing changes to redaction.py
- checking exact-name redaction
- verifying captured trace parameters
- checking JsonSink output for leaked sensitive values
- checking FileSink output for leaked sensitive values
- comparing exact-name redaction with suffix-based redaction

Expected redaction
------------------
Captured monitaudit parameters should contain:

    password      = ***
    secret        = ***
    api_key       = ***
    token         = ***
    authorization = ***
    visible       = visible-value

The Python function itself should receive:

    password      = password-value
    secret        = secret-value
    api_key       = api-key-value
    token         = token-value
    authorization = authorization-value
    visible       = visible-value

Important
---------
Redaction applies to the parameter representation captured by monitaudit.

It does not modify the actual function arguments.

Security
--------
Do not deliberately put sensitive values into log messages or exception
messages.

Parameter redaction protects traced parameters based on their parameter
names. It does not sanitise arbitrary message text.
"""

from __future__ import annotations

from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"


from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


CONFIG_PATH = (
    CONFIG_DIR
    / "main_redaction_exact_names.yaml"
)


def main() -> None:
    mta = build_monitaudit()

    @mta.trace
    def demo(
        password: str,
        secret: str,
        api_key: str,
        token: str,
        authorization: str,
        visible: str,
    ) -> None:
        """
        Demonstrate exact-name sensitive parameter redaction.

        These assertions prove that redaction does not modify the actual
        values supplied to the Python function.
        """

        assert password == "password-value"
        assert secret == "secret-value"
        assert api_key == "api-key-value"
        assert token == "token-value"

        assert (
            authorization
            == "authorization-value"
        )

        assert visible == "visible-value"

        # Only log the deliberately non-sensitive value.
        #
        # Sensitive values should not be manually added to messages or
        # structured log attributes.
        mta.info(
            "Function received original values",
            visible=visible,
        )

    mta.info(
        "Exact-name redaction example started",
        example="main_redaction_exact_names",
    )

    demo(
        password="password-value",
        secret="secret-value",
        api_key="api-key-value",
        token="token-value",
        authorization="authorization-value",
        visible="visible-value",
    )

    mta.info(
        "Exact-name redaction example completed"
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit exact-name redaction example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] @mta.trace parameter capture\n"
        "  [x] exact sensitive-name detection\n"
        "  [x] password redaction\n"
        "  [x] secret redaction\n"
        "  [x] api_key redaction\n"
        "  [x] token redaction\n"
        "  [x] authorization redaction\n"
        "  [x] non-sensitive parameter preservation\n"
        "  [x] Python function receives original values\n"
        "\n"
        "Expected captured trace parameters:\n"
        "\n"
        '  password      = "***"\n'
        '  secret        = "***"\n'
        '  api_key       = "***"\n'
        '  token         = "***"\n'
        '  authorization = "***"\n'
        '  visible       = "visible-value"\n'
        "\n"
        "Expected values inside demo():\n"
        "\n"
        "  password      = password-value\n"
        "  secret        = secret-value\n"
        "  api_key       = api-key-value\n"
        "  token         = token-value\n"
        "  authorization = authorization-value\n"
        "  visible       = visible-value\n"
        "\n"
        "Important distinction:\n"
        "\n"
        "  Python function arguments\n"
        "      -> original values\n"
        "\n"
        "  monitaudit trace parameters\n"
        "      -> sensitive values replaced with ***\n"
        "\n"
        "Expected trace lifecycle:\n"
        "\n"
        "  demo function_start\n"
        "      parameters contain redacted values\n"
        "\n"
        "  demo function_end\n"
        "      parameters contain redacted values\n"
        "\n"
        "  function_error = 0\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect normal trace hierarchy\n"
        "\n"
        "  FileSink\n"
        "    -> examples/output/main_redaction_exact_names.log\n"
        "\n"
        "  JsonSink\n"
        "    -> examples/output/main_redaction_exact_names.jsonl\n"
        "\n"
        "In JSON find records where:\n"
        "\n"
        '  function = "demo"\n'
        "\n"
        "Then inspect:\n"
        "  - attributes.event\n"
        "  - parameters.password\n"
        "  - parameters.secret\n"
        "  - parameters.api_key\n"
        "  - parameters.token\n"
        "  - parameters.authorization\n"
        "  - parameters.visible\n"
        "\n"
        "Security verification:\n"
        "\n"
        "  These original sensitive values must NOT occur in\n"
        "  the captured demo trace parameters:\n"
        "\n"
        "    password-value\n"
        "    secret-value\n"
        "    api-key-value\n"
        "    token-value\n"
        "    authorization-value\n"
        "\n"
        "  Instead each should be represented by:\n"
        "\n"
        "    ***\n"
        "\n"
        "  This non-sensitive value should remain visible:\n"
        "\n"
        "    visible-value\n"
        "\n"
        "Compare with:\n"
        "  main_redaction_suffixes.py\n"
        "\n"
        "  Exact-name example:\n"
        "    password\n"
        "    secret\n"
        "    api_key\n"
        "    token\n"
        "    authorization\n"
        "\n"
        "  Suffix example:\n"
        "    database_password\n"
        "    service_api_key\n"
        "    github_token\n"
        "    client_secret\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_redaction_exact_names.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_redaction_exact_names.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()