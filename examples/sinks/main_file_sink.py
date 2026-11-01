"""
monitaudit FileSink example.

Purpose
-------
Demonstrates monitaudit's human-readable text-file logging through FileSink.

The monitaudit configuration is loaded from:

    examples/config/main_file_sink.yaml

The configured FileSink writes to:

    examples/output/main_file_sink.log

The example produces several different log records:

- INFO
- WARNING
- traced function_start
- normal logging inside a traced function
- traced function_end
- ERROR with exception information and traceback

Demonstrates
------------
- FileSink
- human-readable text logging
- append-only file writes
- structured parameters
- structured attributes
- @mta.trace
- function_start
- function_end
- call_id
- parent_call_id
- duration_ms
- error_type
- error_message
- traceback
- multiple writes to the same file

Use this example when
---------------------
- validating FileSink
- checking human-readable log formatting
- checking append behaviour
- checking parameter formatting
- checking module/function formatting
- checking trace records in a text file
- checking ERROR formatting
- checking traceback formatting

Expected result
---------------
The log file should exist at:

    examples/output/main_file_sink.log

Running this script multiple times should append new records rather than
overwrite the existing file.

The error example should produce additional lines containing:

    error_type=ValueError
    error_message=FileSink example failure
    traceback:

Important
---------
FileSink opens its target using append mode.

For a clean demonstration, remove the previous output first:

    rm -f examples/output/main_file_sink.log
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
    / "main_file_sink.yaml"
)

LOG_PATH = Path(
    "examples/output/main_file_sink.log"
)


def count_log_lines() -> int:
    """
    Count the number of physical lines currently stored in the log file.

    Error records may occupy multiple physical lines because FileSink writes
    error_type, error_message and traceback beneath the main log line.
    """

    if not LOG_PATH.is_file():
        return 0

    return len(
        LOG_PATH.read_text(
            encoding="utf-8",
        ).splitlines()
    )


def main() -> None:
    lines_before = count_log_lines()

    mta = build_monitaudit()

    mta.info(
        "FileSink example started",
        example="main_file_sink",
        lines_before=lines_before,
    )

    mta.info(
        "Structured information record",
        workspace=301,
        status="running",
        attempt=1,
    )

    mta.warning(
        "Demonstration warning",
        workspace=302,
        reason="This warning is intentional",
    )

    @mta.trace
    def calculate(
        first: int,
        second: int,
        operation: str = "add",
    ) -> int:
        """
        Produce trace output in the readable FileSink log.
        """

        mta.info(
            "Calculation running",
            first=first,
            second=second,
            operation=operation,
        )

        return first + second

    result = calculate(
        first=20,
        second=22,
    )

    mta.info(
        "Calculation result received",
        result=result,
    )

    try:
        raise ValueError(
            "FileSink example failure"
        )

    except ValueError as exception:
        mta.error(
            "Demonstration error captured",
            exception=exception,
            component="main_file_sink",
        )

    mta.info(
        "FileSink example completed",
        example="main_file_sink",
    )

    lines_after = count_log_lines()

    added_lines = (
        lines_after
        - lines_before
    )

    print(
        "\n"
        "FileSink write statistics:\n"
        f"  lines before = {lines_before}\n"
        f"  lines after  = {lines_after}\n"
        f"  lines added  = {added_lines}\n"
    )

    if lines_after <= lines_before:
        raise AssertionError(
            "FileSink did not append output."
        )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit FileSink example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] human-readable FileSink output\n"
        "  [x] append-only file logging\n"
        "  [x] INFO logging\n"
        "  [x] WARNING logging\n"
        "  [x] structured attributes\n"
        "  [x] @mta.trace\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] parameter capture\n"
        "  [x] default parameter capture\n"
        "  [x] call_id\n"
        "  [x] duration_ms\n"
        "  [x] ERROR logging\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "\n"
        "Output file:\n"
        "\n"
        "  examples/output/main_file_sink.log\n"
        "\n"
        "Expected normal log structure:\n"
        "\n"
        "  timestamp\n"
        "  level\n"
        "  application\n"
        "  environment\n"
        "  correlation_id\n"
        "  run_id\n"
        "  module.function\n"
        "  message\n"
        "  parameters\n"
        "\n"
        "Expected trace flow:\n"
        "\n"
        "  calculate started\n"
        "      Calculation running\n"
        "  calculate completed\n"
        "\n"
        "Expected calculate parameters:\n"
        "\n"
        "  first     = 20\n"
        "  second    = 22\n"
        "  operation = add\n"
        "\n"
        "Expected ERROR section:\n"
        "\n"
        "  error_type=ValueError\n"
        "  error_message=FileSink example failure\n"
        "  traceback:\n"
        "  ...\n"
        "  ValueError: FileSink example failure\n"
        "\n"
        "Append behaviour:\n"
        "\n"
        "  Running the example again should ADD output to the\n"
        "  existing file rather than replace it.\n"
        "\n"
        "  Note that the physical line count is larger than the\n"
        "  number of monitaudit records when traceback information\n"
        "  is present.\n"
        "\n"
        "For a clean run:\n"
        "\n"
        "  rm -f examples/output/main_file_sink.log\n"
        "\n"
        "Useful shell commands:\n"
        "\n"
        "  cat examples/output/main_file_sink.log\n"
        "\n"
        "  tail -n 20 examples/output/main_file_sink.log\n"
        "\n"
        "  grep 'ERROR' examples/output/main_file_sink.log\n"
        "\n"
        "  grep 'error_type=' examples/output/main_file_sink.log\n"
        "\n"
        "  grep 'traceback:' examples/output/main_file_sink.log\n"
        "\n"
        "Important comparison with JsonSink:\n"
        "\n"
        "  FileSink\n"
        "    -> optimised for human-readable inspection\n"
        "\n"
        "  JsonSink\n"
        "    -> structured JSONL suitable for programmatic analysis\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_file_sink.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_file_sink.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()