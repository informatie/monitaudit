"""
Complete monitaudit demonstration.

Purpose
-------
Provides one manual acceptance example covering the major monitaudit features
that are currently implemented.

This example combines normal logging, nested tracing, automatic parameters
capture, sensitive-data redaction, return values and handled failures.

Demonstrates
------------
- build_monitaudit()
- normal logging
- structured attributes
- @mta.trace
- nested traces
- call_id
- parent_call_id
- duration_ms
- parameters capture
- default parameters
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
- verifying monitaudit.yaml after configuration changes
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
- validating async @mta.trace behaviour

Use the focused examples and automated pytest suite for those cases.
"""

from __future__ import annotations

from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"


from typing import Any

from monitaudit.models.monitaudit import Monitaudit
from monitaudit.utilities.build_monitaudit import build_monitaudit


def run_demo(mta: Monitaudit) -> None:
    @mta.trace
    def authenticate(
        username: str,
        password: str,
        access_token: str,
    ) -> None:
        assert password == "secret-password"
        assert access_token == "secret-token"

        mta.info(
            "User authenticated",
            username=username,
        )

    @mta.trace
    def check_database(
        database: str,
        database_password: str,
        options: dict[str, Any],
        timeout: int = 30,
    ) -> int:
        assert database_password == "database-secret"

        mta.info(
            "Executing database check",
            database=database,
            timeout=timeout,
        )

        return 42

    @mta.trace
    def validate_result(
        row_count: int,
    ) -> None:
        mta.info(
            "Validating query result",
            row_count=row_count,
        )

        if row_count < 1:
            raise ValueError(
                "Query returned no records"
            )

    @mta.trace
    def failing_operation(
        operation_id: int,
    ) -> None:
        mta.info(
            "Executing operation",
            operation_id=operation_id,
        )

        raise RuntimeError(
            f"Operation {operation_id} failed"
        )

    @mta.trace
    def process() -> None:
        mta.info("Process started")

        authenticate(
            username="service_account",
            password="secret-password",
            access_token="secret-token",
        )

        row_count = check_database(
            database="oracle",
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

        validate_result(row_count)

        mta.info(
            "Database query completed",
            row_count=row_count,
        )

        try:
            failing_operation(123)
        except RuntimeError:
            mta.warning(
                "Expected demonstration failure handled",
                operation_id=123,
            )

        mta.info("Process completed")

    process()


def main() -> None:
    mta = build_monitaudit()

    mta.info(
        "monitaudit demonstration started",
    )

    run_demo(mta)

    mta.info(
        "monitaudit demonstration completed",
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit demonstration completed\n"
        "============================================================\n"
        "\n"
        "Features demonstrated:\n"
        "  [x] normal logging\n"
        "  [x] structured attributes\n"
        "  [x] @mta.trace\n"
        "  [x] nested traces\n"
        "  [x] call_id\n"
        "  [x] parent_call_id\n"
        "  [x] automatic parameters capture\n"
        "  [x] default parameters\n"
        "  [x] execution duration\n"
        "  [x] password redaction\n"
        "  [x] token redaction\n"
        "  [x] nested secret redaction\n"
        "  [x] successful function_end\n"
        "  [x] function_error\n"
        "  [x] handled exception\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> output shown above\n"
        "    -> inspect nested indentation\n"
        "\n"
        "  FileSink\n"
        "    -> configured file_sink.path\n"
        "\n"
        "  JsonSink\n"
        "    -> configured json_sink.path\n"
        "    -> inspect context, parameters and attributes\n"
        "\n"
        "  DeltaSink\n"
        "    -> configured delta_sink.table\n"
        "    -> inspect trace IDs, duration, parameters,\n"
        "       context attributes, event attributes and errors\n"
        "\n"
        "monitaudit.utilitiesuration:\n"
        "  config/monitaudit/monitaudit.yaml\n"
        "\n"
        "Security check:\n"
        "  Sensitive traced parameters should contain *** instead\n"
        "  of their original values.\n"
        "\n"
        "Automated verification:\n"
        "  uv run pytest\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()