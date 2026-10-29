"""
monitaudit local DeltaSink example.

Purpose
-------
Demonstrates writing monitaudit log records to a local Delta Lake destination.

The monitaudit configuration is loaded from:

    examples/config/main_delta_local.yaml

For this example:

    is_databricks: false
    delta_sink.enabled: true

monitaudit therefore creates a local Spark session and configures Delta through
get_spark_session().

With the configured table:

    main.logging.monitaudit_delta_local

the current DeltaSink local-path implementation converts the table name to:

    main/logging/monitaudit_delta_local

Demonstrates
------------
- build_observability()
- local Spark session creation
- local Delta configuration
- DeltaSink table initialisation
- local Delta path generation
- INFO logging to Delta
- structured attributes
- traced function_start
- traced function_end
- parameter persistence
- duration_ms persistence
- reading the resulting Delta data back with Spark
- validating written records

Use this example when
---------------------
- validating DeltaSink locally
- checking Spark/Delta configuration
- checking the monitaudit Delta schema
- checking structured Delta records
- verifying local Delta writes
- testing table initialisation
- testing append behaviour
- checking trace data stored in Delta

Expected behaviour
------------------
monitaudit creates the local Delta destination when the DeltaSink is
initialised.

The example then writes several monitaudit records, including a traced
function.

After writing, the same Spark session is used to read the local Delta path.

Expected trace lifecycle:

    calculate function_start
    calculate function_end

Expected function_error count:

    0

Important
---------
The local implementation does not use saveAsTable().

It uses:

    dataframe.write
        .format("delta")
        .save(local_path)

where local_path is generated from:

    table.replace(".", "/")

For:

    main.logging.monitaudit_delta_local

the path becomes:

    main/logging/monitaudit_delta_local

This path is relative to the working directory from which the example is
executed.
"""

from __future__ import annotations

from pathlib import Path

from monitaudit.utilities.build_observability import (
    build_observability,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_delta_local.yaml"
)

DELTA_TABLE = "main.logging.monitaudit_delta_local"

DELTA_PATH = Path(
    DELTA_TABLE.replace(
        ".",
        "/",
    )
)


def main() -> None:
    obs = build_observability(
        CONFIG_PATH
    )

    obs.info(
        "Local DeltaSink example started",
        example="main_delta_local",
        delta_table=DELTA_TABLE,
        delta_path=str(DELTA_PATH),
    )

    obs.info(
        "Structured local Delta record",
        workspace=301,
        element_code="E001",
        status="processing",
    )

    @obs.trace
    def calculate(
        first: int,
        second: int,
        operation: str = "add",
    ) -> int:
        """
        Generate trace records that can be inspected in Delta.
        """

        obs.info(
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

    obs.info(
        "Calculation result received",
        result=result,
    )

    obs.warning(
        "Example warning written to Delta",
        reason="Intentional demonstration warning",
    )

    obs.info(
        "Local DeltaSink example completed",
        example="main_delta_local",
    )

    #
    # Locate the DeltaSink used by monitaudit.
    #
    # We deliberately identify the sink by its table attribute rather than
    # creating another SparkSession for verification.
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

    dataframe = (
        spark.read
        .format("delta")
        .load(str(DELTA_PATH))
    )

    print(
        "\n"
        "============================================================"
    )
    print(
        " Local Delta records"
    )
    print(
        "============================================================"
    )

    dataframe.orderBy(
        "timestamp"
    ).show(
        200,
        truncate=False,
    )

    record_count = dataframe.count()

    print(
        "\n"
        "Local Delta verification:\n"
        f"  Delta table = {DELTA_TABLE}\n"
        f"  Delta path  = {DELTA_PATH}\n"
        f"  row count   = {record_count}\n"
    )

    if record_count < 1:
        raise AssertionError(
            "No monitaudit records were found "
            "in the local Delta destination."
        )

    trace_records = dataframe.filter(
        dataframe.function
        == "calculate"
    )

    print(
        "Trace records for calculate():"
    )

    trace_records.select(
        "timestamp",
        "level",
        "function",
        "call_id",
        "parent_call_id",
        "duration_ms",
        "parameters",
        "attributes",
        "message",
    ).orderBy(
        "timestamp"
    ).show(
        50,
        truncate=False,
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit local DeltaSink example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] local Spark session\n"
        "  [x] Delta configuration\n"
        "  [x] DeltaSink initialisation\n"
        "  [x] local Delta destination\n"
        "  [x] append-mode monitaudit writes\n"
        "  [x] structured INFO records\n"
        "  [x] WARNING record\n"
        "  [x] @obs.trace\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] parameter storage\n"
        "  [x] call_id storage\n"
        "  [x] parent_call_id storage\n"
        "  [x] duration_ms storage\n"
        "  [x] Delta read-back verification\n"
        "\n"
        "Configured Delta table:\n"
        "\n"
        "  main.logging.monitaudit_delta_local\n"
        "\n"
        "Local Delta path:\n"
        "\n"
        "  main/logging/monitaudit_delta_local\n"
        "\n"
        "Why the path differs from the table name:\n"
        "\n"
        "  DeltaSink local mode performs:\n"
        "\n"
        '      table.replace(\".\", \"/\")\n'
        "\n"
        "Expected trace records:\n"
        "\n"
        "  calculate function_start\n"
        "      parameters.first     = 20\n"
        "      parameters.second    = 22\n"
        "      parameters.operation = add\n"
        "\n"
        "  calculate function_end\n"
        "      same call_id as START\n"
        "      duration_ms populated\n"
        "\n"
        "Expected errors:\n"
        "\n"
        "  function_error = 0\n"
        "\n"
        "Useful filesystem inspection:\n"
        "\n"
        "  find main/logging/monitaudit_delta_local -maxdepth 2 "
        "-type f\n"
        "\n"
        "Delta data can be inspected with Spark using:\n"
        "\n"
        "  spark.read\n"
        "      .format(\"delta\")\n"
        "      .load(\"main/logging/monitaudit_delta_local\")\n"
        "\n"
        "Append behaviour:\n"
        "\n"
        "  Running this example repeatedly appends additional\n"
        "  monitaudit records to the same Delta destination.\n"
        "\n"
        "For a completely clean local test, remove the old Delta\n"
        "directory before running the example again.\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_delta_local.yaml\n"
        "\n"
        "Required settings:\n"
        "  is_databricks: false\n"
        "  delta_sink.enabled: true\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_delta_local.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()