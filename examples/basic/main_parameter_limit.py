"""
monitaudit traced-parameter length-limit example.

Purpose
-------
Demonstrates how monitaudit limits the length of captured parameters before
trace records are written to the configured sinks.

The monitaudit configuration is loaded from:

    examples/config/main_parameter_limit.yaml

For this example the configured maximum parameter length should be:

    max_parameter_length: 50

The traced function receives the original parameter values.

monitaudit applies the parameter limit only to the captured representation
stored in the function_start and function_end trace records.

Demonstrates
------------
- @mta.trace
- automatic parameter capture
- max_parameter_length
- short parameter preservation
- exact-boundary parameter handling
- long parameter truncation
- recursive nested-value truncation
- function_start parameters
- function_end parameters
- original function arguments remaining unchanged
- JsonSink inspection
- FileSink inspection

Test values
-----------
The example uses:

    short_value
        5 characters

    exact_value
        exactly 50 characters

    long_value
        100 characters

    nested["message"]
        100 characters

Expected behaviour
------------------
The short value should remain unchanged.

The exact-boundary value should remain unchanged if the configured limit is
50 characters.

The long value should be limited by monitaudit.

The nested long value should also be limited because parameter limiting is
recursive.

The exact output of a truncated string depends on the implementation of
limit_parameters(). This example therefore focuses on validating the
configured behaviour rather than modifying the original function arguments.

Important
---------
Parameter limiting applies to the captured monitaudit trace parameters.

It must not modify the values received by the actual Python function.

For example:

    long_value

inside process() must still contain all 100 original characters.

Security
--------
Parameter length limiting is not a security feature.

It limits the amount of captured data. Sensitive parameter protection is
handled separately by monitaudit's redaction functionality.
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
    / "main_parameter_limit.yaml"
)

MAX_PARAMETER_LENGTH = 50

SHORT_VALUE = "short"

EXACT_VALUE = (
    "x" * MAX_PARAMETER_LENGTH
)

LONG_VALUE = (
    "y" * 100
)


def main() -> None:
    mta = build_monitaudit()

    @mta.trace
    def process(
        short_value: str,
        exact_value: str,
        long_value: str,
        nested: dict[str, object],
    ) -> None:
        """
        Receive the original parameter values.

        The assertions prove that monitaudit parameter limiting does not
        mutate the actual arguments passed to the Python function.
        """

        assert short_value == SHORT_VALUE

        assert len(
            exact_value
        ) == MAX_PARAMETER_LENGTH

        assert exact_value == EXACT_VALUE

        assert len(
            long_value
        ) == 100

        assert long_value == LONG_VALUE

        assert (
            nested["message"]
            == LONG_VALUE
        )

        nested_message = nested[
            "message"
        ]

        assert isinstance(
            nested_message,
            str,
        )

        assert len(
            nested_message
        ) == 100

        mta.info(
            "Function received original parameter values",
            short_length=len(short_value),
            exact_length=len(exact_value),
            long_length=len(long_value),
            nested_length=len(nested_message),
        )

    mta.info(
        "Parameter-limit example started",
        example="main_parameter_limit",
        max_parameter_length=MAX_PARAMETER_LENGTH,
    )

    process(
        short_value=SHORT_VALUE,
        exact_value=EXACT_VALUE,
        long_value=LONG_VALUE,
        nested={
            "message": LONG_VALUE,
        },
    )

    mta.info(
        "Parameter-limit example completed",
        example="main_parameter_limit",
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit parameter-limit example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] @mta.trace\n"
        "  [x] automatic parameter capture\n"
        "  [x] max_parameter_length\n"
        "  [x] short parameter preservation\n"
        "  [x] exact-boundary parameter handling\n"
        "  [x] long parameter limiting\n"
        "  [x] recursive nested parameter limiting\n"
        "  [x] original function arguments remain unchanged\n"
        "  [x] function_start parameters\n"
        "  [x] function_end parameters\n"
        "\n"
        "Configured parameter limit:\n"
        "\n"
        "  max_parameter_length = 50\n"
        "\n"
        "Input values:\n"
        "\n"
        "  short_value\n"
        "      length = 5\n"
        "\n"
        "  exact_value\n"
        "      length = 50\n"
        "\n"
        "  long_value\n"
        "      length = 100\n"
        "\n"
        "  nested.message\n"
        "      length = 100\n"
        "\n"
        "Expected behaviour:\n"
        "\n"
        "  short_value\n"
        "      -> remains unchanged\n"
        "\n"
        "  exact_value\n"
        "      -> remains unchanged at the configured boundary\n"
        "\n"
        "  long_value\n"
        "      -> captured representation is limited\n"
        "\n"
        "  nested.message\n"
        "      -> captured representation is recursively limited\n"
        "\n"
        "Important distinction:\n"
        "\n"
        "  Inside process():\n"
        "      long_value still has 100 characters\n"
        "      nested.message still has 100 characters\n"
        "\n"
        "  Inside monitaudit trace parameters:\n"
        "      oversized captured values are limited\n"
        "\n"
        "Expected trace lifecycle:\n"
        "\n"
        "  process function_start\n"
        "      parameters captured and limited\n"
        "\n"
        "  process function_end\n"
        "      same limited parameter representation\n"
        "\n"
        "  function_error = 0\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect trace execution\n"
        "\n"
        "  FileSink\n"
        "    -> examples/output/main_parameter_limit.log\n"
        "\n"
        "  JsonSink\n"
        "    -> examples/output/main_parameter_limit.jsonl\n"
        "\n"
        "In JSON find records where:\n"
        "\n"
        '  function = "process"\n'
        "\n"
        "Then inspect:\n"
        "\n"
        "  parameters.short_value\n"
        "  parameters.exact_value\n"
        "  parameters.long_value\n"
        "  parameters.nested.message\n"
        "\n"
        "Security note:\n"
        "\n"
        "  Parameter limiting controls captured size.\n"
        "\n"
        "  It does NOT replace redaction.\n"
        "\n"
        "  Sensitive values should still be protected by\n"
        "  monitaudit's redaction rules.\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_parameter_limit.yaml\n"
        "\n"
        "Required configuration:\n"
        "  parameters: true\n"
        "  max_parameter_length: 50\n"
        "\n"
        "Run:\n"
        "  rm -f examples/output/main_parameter_limit.jsonl\n"
        "  rm -f examples/output/main_parameter_limit.log\n"
        "\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_parameter_limit.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()