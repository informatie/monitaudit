"""
monitaudit Databricks DeltaSink example.

Purpose
-------
Demonstrates writing monitaudit log records to a managed Delta table on
Databricks.

The monitaudit configuration is loaded from:

    examples/config/main_delta_databricks.yaml

For this example the configuration must contain:

    is_databricks: true

and:

    delta_sink:
        enabled: true

monitaudit therefore uses the existing Databricks Spark session through
run_dbx() rather than creating a local Spark session.

The configured Delta table is:

    main.logging.monitaudit_delta_databricks

Demonstrates
------------
- Databricks Spark session usage
- DeltaSink in Databricks mode
- catalog/schema/table handling
- Delta table initialisation
- append-mode Delta writes
- structured monitaudit records
- @obs.trace
- function_start
- function_end
- automatic parameter capture
- default parameter capture
- call_id
- parent_call_id
- duration_ms
- ERROR records
- error_type
- error_message
- traceback
- reading monitaudit records back with Spark SQL

Use this example when
---------------------
- running monitaudit on Databricks
- validating DeltaSink Databricks mode
- validating saveAsTable()
- checking monitaudit's Delta schema
- checking trace records in Delta
- checking exception records in Delta
- validating catalog.schema.table configuration

Expected behaviour
------------------
DeltaSink should use:

    run_dbx()

because:

    is_databricks: true

The table should be addressed as:

    main.logging.monitaudit_delta_databricks

The example writes normal logs, trace records and one handled ERROR record.

It then queries the Delta table using Spark SQL and displays records belonging
to the current monitaudit correlation_id.

Important
---------
This example is specifically intended to run inside Databricks.

It is not the local Delta example.

For local Spark/Delta testing use:

    examples/main_delta_local.py
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
    / "main_delta_databricks.yaml"
)

DELTA_TABLE = (
    "main.logging."
    "monitaudit_delta_databricks"
)


def main() -> None:
    obs = build_observability(
        CONFIG_PATH
    )

    obs.info(
        "Databricks DeltaSink example started",
        example="main_delta_databricks",
        delta_table=DELTA_TABLE,
    )

    obs.info(
        "Structured Databricks Delta record",
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
        Generate trace records for inspection in the Delta table.
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

    try:
        raise RuntimeError(
            "Databricks DeltaSink demonstration failure"
        )

    except RuntimeError as exception:
        obs.error(
            "Demonstration error captured",
            exception=exception,
            component="main_delta_databricks",
        )

    obs.warning(
        "Example warning written to Databricks Delta",
        reason="Intentional demonstration warning",
    )

    obs.info(
        "Databricks DeltaSink example completed",
        example="main_delta_databricks",
    )

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
            "Configured Databricks DeltaSink "
            "was not found."
        )

    spark = delta_sink.spark

    #
    # Read only records belonging to this monitaudit instance.
    #
    # Using correlation_id keeps previous runs of this example from
    # contaminating the verification result.
    #
    dataframe = spark.sql(
        f"""
        SELECT
            timestamp,
            level,
            message,
            application,
            environment,
            correlation_id,
            run_id,
            call_id,
            parent_call_id,
            duration_ms,
            module,
            function,
            parameters,
            attributes,
            error_type,
            error_message,
            traceback

        FROM `{DELTA_TABLE.split('.')[0]}`.
             `{DELTA_TABLE.split('.')[1]}`.
             `{DELTA_TABLE.split('.')[2]}`

        WHERE correlation_id = '{obs.correlation_id}'

        ORDER BY timestamp
        """
    )

    print(
        "\n"
        "============================================================"
    )
    print(
        " Databricks monitaudit records"
    )
    print(
        "============================================================"
    )

    dataframe.show(
        200,
        truncate=False,
    )

    record_count = dataframe.count()

    if record_count < 1:
        raise AssertionError(
            "No monitaudit records were found "
            "for the current correlation_id."
        )

    trace_records = dataframe.filter(
        dataframe.function
        == "calculate"
    )

    print(
        "\n"
        "calculate() trace records:"
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

    error_records = dataframe.filter(
        dataframe.level
        == "ERROR"
    )

    print(
        "\n"
        "ERROR records:"
    )

    error_records.select(
        "timestamp",
        "message",
        "error_type",
        "error_message",
        "traceback",
    ).show(
        50,
        truncate=False,
    )

    print(
        "\n"
        "Databricks Delta verification:\n"
        f"  table          = {DELTA_TABLE}\n"
        f"  correlation_id = {obs.correlation_id}\n"
        f"  records        = {record_count}\n"
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit Databricks DeltaSink example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] Databricks Spark session\n"
        "  [x] is_databricks = true\n"
        "  [x] DeltaSink Databricks mode\n"
        "  [x] catalog.schema.table addressing\n"
        "  [x] managed Delta table writes\n"
        "  [x] structured INFO records\n"
        "  [x] WARNING record\n"
        "  [x] @obs.trace\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] automatic parameters\n"
        "  [x] default parameters\n"
        "  [x] call_id\n"
        "  [x] parent_call_id\n"
        "  [x] duration_ms\n"
        "  [x] ERROR record\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "  [x] Spark SQL read-back\n"
        "\n"
        "Configured Delta table:\n"
        "\n"
        "  main.logging.monitaudit_delta_databricks\n"
        "\n"
        "Expected trace lifecycle:\n"
        "\n"
        "  calculate function_start\n"
        "      first     = 20\n"
        "      second    = 22\n"
        "      operation = add\n"
        "\n"
        "  calculate function_end\n"
        "      same call_id as function_start\n"
        "      duration_ms populated\n"
        "\n"
        "Expected error record:\n"
        "\n"
        "  level         = ERROR\n"
        "  error_type    = RuntimeError\n"
        "  error_message = Databricks DeltaSink "
        "demonstration failure\n"
        "  traceback     = populated\n"
        "\n"
        "Important verification technique:\n"
        "\n"
        "  The example filters the Delta table using the current\n"
        "  monitaudit correlation_id.\n"
        "\n"
        "  This separates records from this execution from records\n"
        "  written by previous executions of the example.\n"
        "\n"
        "Useful Databricks SQL:\n"
        "\n"
        "  SELECT *\n"
        "  FROM main.logging.monitaudit_delta_databricks\n"
        "  ORDER BY timestamp DESC;\n"
        "\n"
        "Inspect:\n"
        "  - application\n"
        "  - environment\n"
        "  - correlation_id\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - function\n"
        "  - duration_ms\n"
        "  - parameters\n"
        "  - attributes\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "\n"
        "Difference from local Delta example:\n"
        "\n"
        "  main_delta_local.py\n"
        "      -> is_databricks = false\n"
        "      -> get_spark_session()\n"
        "      -> writes to local Delta path\n"
        "\n"
        "  main_delta_databricks.py\n"
        "      -> is_databricks = true\n"
        "      -> run_dbx()\n"
        "      -> writes with saveAsTable()\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_delta_databricks.yaml\n"
        "\n"
        "Required settings:\n"
        "  is_databricks: true\n"
        "  delta_sink.enabled: true\n"
        "  delta_sink.table:\n"
        "    main.logging.monitaudit_delta_databricks\n"
        "\n"
        "Run this example from the Databricks environment where\n"
        "the configured catalogue/schema/table can be created and\n"
        "written by the active Spark identity.\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()