"""
monitaudit JsonSink example.

Purpose
-------
Demonstrates monitaudit logging to an append-only JSON Lines (JSONL) file.

The monitaudit configuration is loaded from:

    examples/config/main_json_sink.yaml

The configured JsonSink writes to:

    var/log/examples/main_json_sink.jsonl

JSON Lines format
-----------------
JsonSink writes one complete JSON object per line.

Conceptually:

    {"level": "INFO", ...}
    {"level": "INFO", ...}
    {"level": "WARNING", ...}
    {"level": "ERROR", ...}

Every line can therefore be parsed independently as JSON.

Running the example multiple times appends new records to the existing file.
The existing records are not overwritten.

Demonstrates
------------
- JsonSink
- JSON Lines output
- append-only writes
- multiple log records
- structured attributes
- nested structured attributes
- @obs.trace
- function_start
- function_end
- automatic parameter capture
- call_id
- parent_call_id
- duration_ms
- ERROR serialisation
- error_type
- error_message
- traceback

Use this example when
---------------------
- validating JsonSink
- checking JSON serialisation
- checking append behaviour
- inspecting structured monitaudit records
- testing model_dump_json()
- validating trace records in JSON
- checking exception fields in JSON
- preparing JSONL for Spark analysis

Expected result
---------------
The output file should contain multiple lines:

    var/log/examples/main_json_sink.jsonl

Every non-empty line should be independently valid JSON.

Running this example again should increase the number of lines rather than
replace the existing file.

Important
---------
JsonSink uses append mode.

If you want to inspect only records from the current execution, delete the
existing JSONL file before running this example:

    rm -f var/log/examples/main_json_sink.jsonl
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
    / "main_json_sink.yaml"
)

JSON_PATH = Path(
    "var/log/examples/main_json_sink.jsonl"
)


def count_json_lines() -> int:
    """
    Count non-empty records currently stored in the JSONL file.
    """

    if not JSON_PATH.is_file():
        return 0

    return sum(
        1
        for line in JSON_PATH.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    )


def main() -> None:
    records_before = count_json_lines()

    obs = build_monitaudit(
        CONFIG_PATH
    )

    obs.info(
        "JsonSink example started",
        example="main_json_sink",
        records_before=records_before,
    )

    obs.info(
        "Structured information record",
        record_number=1,
        workspace=301,
        status="started",
    )

    obs.warning(
        "Structured warning record",
        record_number=2,
        workspace=302,
        details={
            "source": "example",
            "retry": 2,
        },
    )

    @obs.trace
    def calculate(
        first: int,
        second: int,
        operation: str = "add",
    ) -> int:
        """
        Produce function_start/function_end records in JSON.
        """

        obs.info(
            "Calculation running",
            first=first,
            second=second,
            operation=operation,
        )

        if operation != "add":
            raise ValueError(
                f"Unsupported operation: {operation}"
            )

        return first + second

    result = calculate(
        first=20,
        second=22,
    )

    obs.info(
        "Calculation completed",
        result=result,
    )

    try:
        raise RuntimeError(
            "JsonSink demonstration failure"
        )

    except RuntimeError as exception:
        obs.error(
            "Demonstration error captured",
            exception=exception,
            example="main_json_sink",
        )

    obs.info(
        "JsonSink example completed",
        example="main_json_sink",
    )

    records_after = count_json_lines()

    added_records = (
        records_after
        - records_before
    )

    print(
        "\n"
        "JsonSink write statistics:\n"
        f"  records before = {records_before}\n"
        f"  records after  = {records_after}\n"
        f"  records added  = {added_records}\n"
    )

    if records_after <= records_before:
        raise AssertionError(
            "JsonSink did not append JSONL records."
        )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit JsonSink example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] JSON Lines output\n"
        "  [x] append-only writes\n"
        "  [x] multiple JSON records\n"
        "  [x] structured attributes\n"
        "  [x] nested structured attributes\n"
        "  [x] @obs.trace\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] automatic parameter capture\n"
        "  [x] default parameter capture\n"
        "  [x] call_id\n"
        "  [x] duration_ms\n"
        "  [x] ERROR serialisation\n"
        "  [x] error_type\n"
        "  [x] error_message\n"
        "  [x] traceback\n"
        "\n"
        "Output file:\n"
        "\n"
        "  var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "Important JSONL property:\n"
        "\n"
        "  Every line is one complete JSON object.\n"
        "\n"
        "  Line 1 -> valid JSON record\n"
        "  Line 2 -> valid JSON record\n"
        "  Line 3 -> valid JSON record\n"
        "  ...\n"
        "\n"
        "Expected trace records for calculate():\n"
        "\n"
        "  calculate function_start\n"
        "      parameters.first     = 20\n"
        "      parameters.second    = 22\n"
        "      parameters.operation = add\n"
        "\n"
        "  calculate function_end\n"
        "      duration_ms = populated\n"
        "\n"
        "Expected ERROR record:\n"
        "\n"
        "  level         = ERROR\n"
        "  error_type    = RuntimeError\n"
        "  error_message = JsonSink demonstration failure\n"
        "  traceback     = populated\n"
        "\n"
        "Append verification:\n"
        "\n"
        "  Running this script again should ADD records.\n"
        "  Existing records should remain in the file.\n"
        "\n"
        "For a clean run first execute:\n"
        "\n"
        "  rm -f var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "Useful shell verification:\n"
        "\n"
        "  wc -l var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "  tail -n 5 var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "With jq installed:\n"
        "\n"
        "  jq -c . var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "For trace records only:\n"
        "\n"
        "  jq -c '\n"
        "    select(.attributes.event != null)\n"
        "    | {\n"
        "        function,\n"
        "        event: .attributes.event,\n"
        "        call_id,\n"
        "        parent_call_id,\n"
        "        parameters,\n"
        "        duration_ms\n"
        "      }\n"
        "  ' var/log/examples/main_json_sink.jsonl\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_json_sink.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_json_sink.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()