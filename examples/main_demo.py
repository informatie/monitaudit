"""
Complete monitaudit demonstration.

Purpose
-------
Provides one manual acceptance example covering the major monitaudit features
that are currently implemented.

This example combines normal logging, nested tracing, automatic parameter
capture, sensitive-data redaction, return values and handled failures.

The monitaudit configuration is loaded from:

    examples/config/main_demo.yaml

Demonstration index
-------------------
01: Build monitaudit from the example-specific YAML configuration.
02: Write normal log records with structured attributes.
03: Trace authentication and redact password and token parameters.
04: Trace a database check with defaults and nested secret redaction.
05: Return a value from a traced function and validate that value.
06: Create nested traces with call_id and parent_call_id relationships.
07: Record function_start and function_end with execution duration.
08: Generate function_error with exception details and traceback.
09: Catch the child failure and allow the parent trace to continue.
10: Complete the parent process successfully after handling the failure.

Demonstrates
------------
- build_observability()
- example-specific YAML configuration
- normal logging
- structured attributes
- @obs.trace
- nested traces
- call_id
- parent_call_id
- duration_ms
- parameter capture
- default parameter capture
- password/token/secret redaction
- nested redaction
- successful function completion
- return values
- function_error
- error_type
- error_message
- traceback
- parent continuation after a handled child error

Use this example when
---------------------
- manually validating an monitaudit release
- checking several configured sinks together
- verifying main_demo.yaml after configuration changes
- checking tracing after internal refactoring
- checking redaction changes
- checking error-storage changes
- demonstrating monitaudit to another developer

Do not use this example when
----------------------------
- diagnosing one isolated feature where a smaller example is clearer
- benchmarking logging performance
- load-testing DeltaSink
- verifying thread safety
- verifying multiprocessing
- validating async @obs.trace behaviour

Use the focused examples and automated pytest suite for those cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from monitaudit.models.monitaudit import Observability
from monitaudit.utilities.build_observability import (
    build_observability,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_demo.yaml"
)


def run_demo(
    obs: Observability,
) -> None:
    """
    Execute the complete monitaudit demonstration.

    The nested functions are deliberately defined here so they all use the
    same Observability instance and logging context.
    """

    @obs.trace
    def authenticate(
        username: str,
        password: str,
        access_token: str,
    ) -> None:
        """
        Demonstrate password and token parameter redaction.

        The function receives the original values. monitaudit only redacts the
        captured trace-parameter representation written to the sinks.
        """

        assert password == "secret-password"
        assert access_token == "secret-token"

        obs.info(
            "User authenticated",
            username=username,
        )

    @obs.trace
    def check_database(
        database: str,
        database_password: str,
        options: dict[str, Any],
        timeout: int = 30,
    ) -> int:
        """
        Demonstrate default parameters, nested redaction and return values.
        """

        assert database_password == "database-secret"
        assert timeout == 30

        assert (
            options["client_secret"]
            == "nested-secret"
        )

        connection = options["connection"]

        if not isinstance(
            connection,
            dict,
        ):
            raise ValueError(
                "Database connection options must be a mapping."
            )

        assert (
            connection["access_token"]
            == "nested-token"
        )

        obs.info(
            "Executing database check",
            database=database,
            timeout=timeout,
        )

        return 42

    @obs.trace
    def validate_result(
        row_count: int,
    ) -> None:
        """
        Validate the return value produced by check_database().
        """

        obs.info(
            "Validating query result",
            row_count=row_count,
        )

        if row_count < 1:
            raise ValueError(
                "Query returned no records"
            )

    @obs.trace
    def failing_operation(
        operation_id: int,
    ) -> None:
        """
        Deliberately fail to demonstrate function_error recording.
        """

        obs.info(
            "Executing operation",
            operation_id=operation_id,
        )

        raise RuntimeError(
            f"Operation {operation_id} failed"
        )

    @obs.trace
    def process() -> None:
        """
        Execute the parent trace and handle one expected child failure.
        """

        obs.info(
            "Process started"
        )

        authenticate(
            username="service_account",
            password="secret-password",
            access_token="secret-token",
        )

        row_count = check_database(
            database="relatics",
            database_password="database-secret",
            options={
                "retry": 3,
                "client_secret": "nested-secret",
                "connection": {
                    "host": "database01",
                    "access_token": "nested-token",
                },
            },
        )

        validate_result(
            row_count
        )

        obs.info(
            "Database query completed",
            row_count=row_count,
        )

        try:
            failing_operation(
                operation_id=123,
            )

        except RuntimeError as exception:
            obs.warning(
                "Expected demonstration failure handled",
                operation_id=123,
                error_type=type(exception).__name__,
                error_message=str(exception),
            )

        obs.info(
            "Process completed"
        )

    process()


def main() -> None:
    """
    Build monitaudit and run the complete demonstration.
    """

    obs = build_observability(
        CONFIG_PATH
    )

    obs.info(
        "monitaudit demonstration started",
        example="main_demo",
        config_path=str(CONFIG_PATH),
    )

    run_demo(
        obs
    )

    obs.info(
        "monitaudit demonstration completed",
        example="main_demo",
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit demonstration completed\n"
        "============================================================\n"
        "\n"
        "Demonstration index:\n"
        "  01. monitaudit built from example-specific YAML\n"
        "  02. Normal structured logging\n"
        "  03. Authentication parameter redaction\n"
        "  04. Database defaults and nested redaction\n"
        "  05. Traced return value and validation\n"
        "  06. Nested call_id and parent_call_id relationships\n"
        "  07. Trace timing and successful function_end\n"
        "  08. Deliberate child function_error\n"
        "  09. Parent catches and handles child failure\n"
        "  10. Parent process completes successfully\n"
        "\n"
        "Features demonstrated:\n"
        "  [x] normal logging\n"
        "  [x] structured attributes\n"
        "  [x] @obs.trace\n"
        "  [x] nested traces\n"
        "  [x] call_id\n"
        "  [x] parent_call_id\n"
        "  [x] automatic parameter capture\n"
        "  [x] default parameter capture\n"
        "  [x] execution duration\n"
        "  [x] password redaction\n"
        "  [x] token redaction\n"
        "  [x] nested secret redaction\n"
        "  [x] return values\n"
        "  [x] successful function_end\n"
        "  [x] function_error\n"
        "  [x] handled exception\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "\n"
        "Expected trace hierarchy:\n"
        "\n"
        "  process started\n"
        "      authenticate started\n"
        "          User authenticated\n"
        "      authenticate completed\n"
        "\n"
        "      check_database started\n"
        "          Executing database check\n"
        "      check_database completed\n"
        "\n"
        "      validate_result started\n"
        "          Validating query result\n"
        "      validate_result completed\n"
        "\n"
        "      failing_operation started\n"
        "          Executing operation\n"
        "      failing_operation failed\n"
        "\n"
        "      Expected demonstration failure handled\n"
        "      Process completed\n"
        "  process completed\n"
        "\n"
        "Expected error behaviour:\n"
        "  - failing_operation has function_error\n"
        "  - error_type is RuntimeError\n"
        "  - error_message is Operation 123 failed\n"
        "  - traceback is populated\n"
        "  - process catches the RuntimeError\n"
        "  - process finishes with function_end\n"
        "  - process does not finish with function_error\n"
        "\n"
        "Expected redacted parameters:\n"
        '  password          = "***"\n'
        '  access_token      = "***"\n'
        '  database_password = "***"\n'
        '  client_secret     = "***"\n'
        '  nested token      = "***"\n'
        "\n"
        "Expected visible parameters:\n"
        "  username     = service_account\n"
        "  database     = relatics\n"
        "  timeout      = 30\n"
        "  retry        = 3\n"
        "  host         = database01\n"
        "  operation_id = 123\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect nested indentation above\n"
        "\n"
        "  FileSink\n"
        "    -> logs/examples/main_demo.log\n"
        "\n"
        "  JsonSink\n"
        "    -> logs/examples/main_demo.jsonl\n"
        "    -> inspect context, parameters and attributes\n"
        "\n"
        "  DeltaSink\n"
        "    -> disabled in examples/config/main_demo.yaml\n"
        "\n"
        "JSON fields to inspect:\n"
        "  - level\n"
        "  - message\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - duration_ms\n"
        "  - parameters\n"
        "  - attributes.event\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_demo.yaml\n"
        "\n"
        "Security check:\n"
        "  Sensitive traced parameters should contain *** instead\n"
        "  of their original values.\n"
        "\n"
        "  Do not deliberately put secrets in log messages or\n"
        "  exception messages. Parameter redaction does not sanitise\n"
        "  arbitrary message text.\n"
        "\n"
        "Automated verification:\n"
        "  uv run pytest\n"
        "\n"
        "Run this demonstration:\n"
        "  monitaudit_ENV=dev uv run python examples/main_demo.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()