"""
monitaudit JSON-safe parameter conversion example.

Purpose
-------
Demonstrates how monitaudit converts common Python and Pydantic values into
JSON-safe representations before captured trace parameters are written to
structured sinks such as JsonSink.

The monitaudit configuration is loaded from:

    examples/config/main_json_safe_types.yaml

The example passes one dictionary containing several different Python value
types to a traced function.

monitaudit's trace parameter pipeline processes those values before they are
stored in function_start/function_end records.

Demonstrates
------------
- @obs.trace
- automatic parameter capture
- recursive JSON-safe conversion
- datetime conversion
- date conversion
- time conversion
- pathlib.Path conversion
- UUID conversion
- Enum conversion
- Pydantic BaseModel conversion
- tuple conversion
- set conversion
- frozenset conversion
- bytes conversion
- custom object repr() conversion
- safe handling of a broken __repr__()
- nested dictionary conversion
- JsonSink-compatible parameters

Use this example when
---------------------
- validating json_safe.py
- checking JsonSink parameter serialisation
- testing Pydantic model conversion
- testing UUID/path/date/time handling
- validating set and tuple handling
- testing arbitrary application objects
- validating broken __repr__() handling

Expected conversions
--------------------
The captured trace parameters should conceptually contain:

    datetime_value
        -> ISO formatted string

    date_value
        -> ISO formatted string

    time_value
        -> ISO formatted string

    path_value
        -> string path

    uuid_value
        -> UUID string

    enum_value
        -> enum value

    model_value
        -> dictionary

    tuple_value
        -> list

    set_value
        -> list

    frozenset_value
        -> list

    bytes_value
        -> bytes repr string

    custom_value
        -> repr(custom_object)

    broken_repr_value
        -> "<unserializable BrokenRepr>"

Important
---------
Sets and frozensets are converted into lists.

Their ordering should not be considered part of the monitaudit contract.

The example therefore validates their contents rather than relying on a
specific list order.

The traced function itself receives the original Python objects. JSON-safe
conversion only affects the captured parameter representation.

Security
--------
JSON-safe conversion is not redaction.

Converting an object into a JSON-safe representation does not make sensitive
information safe to log. Sensitive parameters should still be protected by
monitaudit's redaction rules.
"""

from __future__ import annotations

from datetime import (
    date,
    datetime,
    time,
    timezone,
)
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_json_safe_types.yaml"
)


class State(Enum):
    READY = "ready"


class Payload(BaseModel):
    name: str
    count: int


class CustomObject:
    def __repr__(self) -> str:
        return "CustomObject(example)"


class BrokenRepr:
    def __repr__(self) -> str:
        raise RuntimeError(
            "repr failed"
        )


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def process(
        values: dict[str, object],
    ) -> None:
        """
        Receive the original Python objects.

        monitaudit converts the captured trace representation before writing
        the parameters to its sinks.
        """

        # Prove that the function itself receives original objects.
        assert isinstance(
            values["datetime_value"],
            datetime,
        )

        assert isinstance(
            values["date_value"],
            date,
        )

        assert isinstance(
            values["time_value"],
            time,
        )

        assert isinstance(
            values["path_value"],
            Path,
        )

        assert isinstance(
            values["uuid_value"],
            UUID,
        )

        assert (
            values["enum_value"]
            is State.READY
        )

        assert isinstance(
            values["model_value"],
            Payload,
        )

        assert isinstance(
            values["tuple_value"],
            tuple,
        )

        assert isinstance(
            values["set_value"],
            set,
        )

        assert isinstance(
            values["frozenset_value"],
            frozenset,
        )

        assert isinstance(
            values["bytes_value"],
            bytes,
        )

        assert isinstance(
            values["custom_value"],
            CustomObject,
        )

        assert isinstance(
            values["broken_repr_value"],
            BrokenRepr,
        )

        # Do not pass **values directly into obs.info().
        #
        # This example specifically demonstrates the @obs.trace parameter
        # conversion pipeline. The original objects remain available here.
        obs.info(
            "Original Python values received by function",
            value_count=len(values),
        )

    values: dict[str, object] = {
        "datetime_value": datetime(
            2026,
            10,
            23,
            12,
            30,
            tzinfo=timezone.utc,
        ),
        "date_value": date(
            2026,
            10,
            23,
        ),
        "time_value": time(
            12,
            30,
        ),
        "path_value": Path(
            "/tmp/example"
        ),
        "uuid_value": UUID(
            "12345678-1234-5678-1234-567812345678"
        ),
        "enum_value": State.READY,
        "model_value": Payload(
            name="example",
            count=2,
        ),
        "tuple_value": (
            1,
            2,
        ),
        "set_value": {
            1,
            2,
        },
        "frozenset_value": frozenset(
            {
                3,
                4,
            }
        ),
        "bytes_value": b"example",
        "custom_value": CustomObject(),
        "broken_repr_value": BrokenRepr(),
    }

    obs.info(
        "JSON-safe types example started",
        example="main_json_safe_types",
        value_count=len(values),
    )

    process(
        values
    )

    obs.info(
        "JSON-safe types example completed",
        value_count=len(values),
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit JSON-safe types example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] @obs.trace parameter capture\n"
        "  [x] recursive JSON-safe conversion\n"
        "  [x] datetime -> string\n"
        "  [x] date -> string\n"
        "  [x] time -> string\n"
        "  [x] Path -> string\n"
        "  [x] UUID -> string\n"
        "  [x] Enum -> value\n"
        "  [x] Pydantic model -> mapping\n"
        "  [x] tuple -> list\n"
        "  [x] set -> list\n"
        "  [x] frozenset -> list\n"
        "  [x] bytes -> repr string\n"
        "  [x] custom object -> repr string\n"
        "  [x] broken repr -> safe placeholder\n"
        "  [x] original objects remain available to function\n"
        "\n"
        "Expected captured values:\n"
        "\n"
        "  datetime_value\n"
        "    2026-10-23T12:30:00+00:00\n"
        "\n"
        "  date_value\n"
        "    2026-10-23\n"
        "\n"
        "  time_value\n"
        "    12:30:00\n"
        "\n"
        "  path_value\n"
        "    /tmp/example\n"
        "\n"
        "  uuid_value\n"
        "    12345678-1234-5678-1234-567812345678\n"
        "\n"
        "  enum_value\n"
        "    ready\n"
        "\n"
        "  model_value\n"
        '    {\"name\": \"example\", \"count\": 2}\n'
        "\n"
        "  tuple_value\n"
        "    [1, 2]\n"
        "\n"
        "  set_value\n"
        "    list containing 1 and 2\n"
        "\n"
        "  frozenset_value\n"
        "    list containing 3 and 4\n"
        "\n"
        "  bytes_value\n"
        "    b'example'\n"
        "\n"
        "  custom_value\n"
        "    CustomObject(example)\n"
        "\n"
        "  broken_repr_value\n"
        "    <unserializable BrokenRepr>\n"
        "\n"
        "Important distinction:\n"
        "\n"
        "  Inside process():\n"
        "      original Python objects\n"
        "\n"
        "  monitaudit trace parameters:\n"
        "      JSON-safe representations\n"
        "\n"
        "Expected trace lifecycle:\n"
        "\n"
        "  process function_start\n"
        "      parameters.values contains converted values\n"
        "\n"
        "  process function_end\n"
        "      parameters.values contains converted values\n"
        "\n"
        "  function_error = 0\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect normal trace execution\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_json_safe_types.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_json_safe_types.jsonl\n"
        "\n"
        "In JSON find records where:\n"
        "\n"
        '  function = \"process\"\n'
        "\n"
        "Then inspect:\n"
        "\n"
        "  parameters.values.datetime_value\n"
        "  parameters.values.date_value\n"
        "  parameters.values.time_value\n"
        "  parameters.values.path_value\n"
        "  parameters.values.uuid_value\n"
        "  parameters.values.enum_value\n"
        "  parameters.values.model_value\n"
        "  parameters.values.tuple_value\n"
        "  parameters.values.set_value\n"
        "  parameters.values.frozenset_value\n"
        "  parameters.values.bytes_value\n"
        "  parameters.values.custom_value\n"
        "  parameters.values.broken_repr_value\n"
        "\n"
        "Important set behaviour:\n"
        "\n"
        "  Do not depend on a specific order for set_value or\n"
        "  frozenset_value. Verify their contents instead.\n"
        "\n"
        "Important security note:\n"
        "\n"
        "  JSON-safe != redacted.\n"
        "\n"
        "  JSON-safe conversion makes values serialisable.\n"
        "  Sensitive-value protection is handled separately by\n"
        "  monitaudit's redaction rules.\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_json_safe_types.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_json_safe_types.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()