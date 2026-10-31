"""
monitaudit all-sinks example.

Purpose
-------
Demonstrates sending the same monitaudit records to all configured sink types.

The monitaudit configuration is loaded from:

    examples/config/main_all_sinks.yaml

This example is intended to exercise:

- ConsoleSink
- FileSink
- JsonSink
- DeltaSink

The same monitaudit instance writes each log record to every enabled sink.

The example produces:

- normal INFO logging
- structured attributes
- a traced operation
- function_start
- normal logging inside the trace
- function_end
- automatic parameter capture
- duration_ms
- one handled ERROR with traceback

Demonstrates
------------
- build_monitaudit()
- multiple sinks active simultaneously
- ConsoleSink
- FileSink
- JsonSink
- DeltaSink
- sink fan-out
- structured logging
- @obs.trace
- call_id
- parent_call_id
- function_start
- function_end
- duration_ms
- parameters
- ERROR logging
- error_type
- error_message
- traceback

Use this example when
---------------------
- checking all sinks together
- validating a release manually
- comparing output between sink implementations
- testing monitauditLogger sink fan-out
- checking that one log reaches every configured destination
- checking trace information across sink formats

Expected behaviour
------------------
A single call such as:

    obs.info("...")

is created once by monitauditLogger and then written to every configured sink.

Conceptually:

                    monitaudit
                       |
                       v
                monitauditLogger
                       |
          +------------+------------+------------+
          |            |            |            |
          v            v            v            v
      ConsoleSink   FileSink     JsonSink     DeltaSink

The content representation differs by sink, but the underlying monitaudit
record should describe the same application event.

Important
---------
DeltaSink requires Spark.

This example therefore starts/configures Spark when DeltaSink is enabled.

For local execution the matching YAML should use:

    is_databricks: false

For a Databricks variant use:

    is_databricks: true

and configure an appropriate catalog.schema.table destination.
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
    / "main_all_sinks.yaml"
)

DELTA_TABLE = "main.logging.monitaudit_all_sinks"

DELTA_PATH = Path(
    DELTA_TABLE.replace(
        ".",
        "/",
    )
)

JSON_PATH = Path(
    "var/log/examples/main_all_sinks.jsonl"
)

FILE_PATH = Path(
    "var/log/examples/main_all_sinks.log"
)


def count_json_records() -> int:
    if not JSON_PATH.is_file():
        return 0

    return sum(
        1
        for line in JSON_PATH.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    )


def count_file_lines() -> int:
    if not FILE_PATH.is_file():
        return 0

    return len(
        FILE_PATH.read_text(
            encoding="utf-8",
        ).splitlines()
    )


def main() -> None:
    json_before = count_json_records()
    file_before = count_file_lines()

    obs = build_monitaudit(
        CONFIG_PATH
    )

    obs.info(
        "All-sinks example started",
        example="main_all_sinks",
        delta_table=DELTA_TABLE,
    )

    obs.info(
        "Structured record sent to all sinks",
        workspace=301,
        element_code="E001",
        status="running",
    )

    @obs.trace
    def operation(
        value: int,
        multiplier: int = 2,
    ) -> int:
        """
        Generate trace records that are sent to all configured sinks.
        """

        obs.info(
            "Operation running",
            value=value,
            multiplier=multiplier,
        )

        return value * multiplier

    result = operation(
        value=21,
    )

    obs.info(
        "Operation result received",
        result=result,
    )

    try:
        raise ValueError(
            "All-sinks demonstration failure"
        )

    except ValueError as exception:
        obs.error(
            "Demonstration error sent to all sinks",
            exception=exception,
            component="main_all_sinks",
        )

    obs.warning(
        "All-sinks demonstration warning",
        reason="Intentional example warning",
    )

    obs.info(
        "All-sinks example completed",
        example="main_all_sinks",
    )

    json_after = count_json_records()
    file_after = count_file_lines()

    print(
        "\n"
        "File/JSON verification:\n"
        f"  JSON records before = {json_before}\n"
        f"  JSON records after  = {json_after}\n"
        f"  JSON records added  = {json_after - json_before}\n"
        "\n"
        f"  File lines before   = {file_before}\n"
        f"  File lines after    = {file_after}\n"
        f"  File lines added    = {file_after - file_before}\n"
    )

    if json_after <= json_before:
        raise AssertionError(
            "JsonSink did not append records."
        )

    if file_after <= file_before:
        raise AssertionError(
            "FileSink did not append output."
        )

    #
    # Find the configured DeltaSink.
    #
    delta_sink = next(
        (
            sink
            for sink in obs.logger.sinks
            if getattr(
                sink,
                "table",
                None,
            )
            == DELTA_TABLE
        ),
        None,
    )

    if delta_sink is None:
        raise RuntimeError(
            "Configured DeltaSink was not found."
        )

    spark = delta_sink.spark

    #
    # Local mode writes to:
    #
    #     main/logging/monitaudit_all_sinks
    #
    delta_records = (
        spark.read
        .format("delta")
        .load(str(DELTA_PATH))
        .filter(
            f"correlation_id = "
            f"'{obs.correlation_id}'"
        )
    )

    delta_count = delta_records.count()

    print(
        "\n"
        "Delta verification:\n"
        f"  table          = {DELTA_TABLE}\n"
        f"  path           = {DELTA_PATH}\n"
        f"  correlation_id = {obs.correlation_id}\n"
        f"  records        = {delta_count}\n"
    )

    if delta_count < 1:
        raise AssertionError(
            "DeltaSink did not contain records "
            "for this execution."
        )

    print(
        "\n"
        "Delta records for this execution:"
    )

    delta_records.select(
        "timestamp",
        "level",
        "message",
        "function",
        "call_id",
        "parent_call_id",
        "duration_ms",
        "parameters",
        "attributes",
        "error_type",
        "error_message",
    ).orderBy(
        "timestamp"
    ).show(
        200,
        truncate=False,
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit all-sinks example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ConsoleSink\n"
        "  [x] FileSink\n"
        "  [x] JsonSink\n"
        "  [x] DeltaSink\n"
        "  [x] monitauditLogger sink fan-out\n"
        "  [x] structured INFO logging\n"
        "  [x] WARNING logging\n"
        "  [x] ERROR logging\n"
        "  [x] @obs.trace\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] automatic parameter capture\n"
        "  [x] default parameter capture\n"
        "  [x] call_id\n"
        "  [x] parent_call_id\n"
        "  [x] duration_ms\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "\n"
        "Expected sink fan-out:\n"
        "\n"
        "                    monitaudit\n"
        "                       |\n"
        "                       v\n"
        "                monitauditLogger\n"
        "                       |\n"
        "          +------------+------------+------------+\n"
        "          |            |            |            |\n"
        "          v            v            v            v\n"
        "       Console       File         JSON         Delta\n"
        "\n"
        "Expected trace flow:\n"
        "\n"
        "  operation started\n"
        "      Operation running\n"
        "  operation completed\n"
        "\n"
        "Expected trace parameters:\n"
        "\n"
        "  value      = 21\n"
        "  multiplier = 2\n"
        "\n"
        "Expected result:\n"
        "\n"
        "  21 * 2 = 42\n"
        "\n"
        "Expected ERROR record:\n"
        "\n"
        "  level         = ERROR\n"
        "  error_type    = ValueError\n"
        "  error_message = All-sinks demonstration failure\n"
        "  traceback     = populated\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> output displayed during execution\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_all_sinks.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_all_sinks.jsonl\n"
        "\n"
        "  DeltaSink\n"
        "    -> main/logging/monitaudit_all_sinks\n"
        "\n"
        "Important consistency check:\n"
        "\n"
        "  Find the same event in JSON and Delta using:\n"
        "\n"
        "      correlation_id\n"
        "      call_id\n"
        "      message\n"
        "\n"
        "  These identifiers make it possible to compare the same\n"
        "  monitaudit record across different persisted sinks.\n"
        "\n"
        "Append behaviour:\n"
        "\n"
        "  FileSink, JsonSink and DeltaSink append output.\n"
        "  Running this example repeatedly therefore adds records.\n"
        "\n"
        "For a clean local test remove previous output first:\n"
        "\n"
        "  rm -f var/log/examples/main_all_sinks.log\n"
        "  rm -f var/log/examples/main_all_sinks.jsonl\n"
        "  rm -rf main/logging/monitaudit_all_sinks\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_all_sinks.yaml\n"
        "\n"
        "Required local settings:\n"
        "  is_databricks: false\n"
        "  console_sink.enabled: true\n"
        "  file_sink.enabled: true\n"
        "  json_sink.enabled: true\n"
        "  delta_sink.enabled: true\n"
        "  delta_sink.table:\n"
        "    main.logging.monitaudit_all_sinks\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_all_sinks.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()