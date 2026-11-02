# tests/sinks/test_delta.py

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pyspark.sql.types import (
    DoubleType,
    MapType,
    StringType,
    TimestampType,
)

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.sinks.delta import (
    MONITAUDIT_SCHEMA,
    STRING_MAP,
    DeltaSink,
    _serialize_traceback,
    _stringify_mapping,
    _stringify_value,
    _to_json,
)


class FakeWriter:
    """Fluent DataFrame writer test double."""

    def __init__(self) -> None:
        self.operations: list[
            tuple[str, Any]
        ] = []

    def format(
        self,
        value: str,
    ) -> FakeWriter:
        self.operations.append(
            (
                "format",
                value,
            )
        )
        return self

    def mode(
        self,
        value: str,
    ) -> FakeWriter:
        self.operations.append(
            (
                "mode",
                value,
            )
        )
        return self

    def save(
        self,
        path: str,
    ) -> None:
        self.operations.append(
            (
                "save",
                path,
            )
        )

    def saveAsTable(
        self,
        table: str,
    ) -> None:
        self.operations.append(
            (
                "saveAsTable",
                table,
            )
        )


class FakeDataFrame:
    def __init__(self) -> None:
        self.write = FakeWriter()


class FakeSpark:
    def __init__(self) -> None:
        self.create_calls: list[
            tuple[list[Any], Any]
        ] = []
        self.dataframes: list[
            FakeDataFrame
        ] = []
        self.sql_calls: list[str] = []

    def createDataFrame(
        self,
        data: list[Any],
        *,
        schema: Any,
    ) -> FakeDataFrame:
        dataframe = FakeDataFrame()

        self.create_calls.append(
            (
                data,
                schema,
            )
        )
        self.dataframes.append(
            dataframe
        )

        return dataframe

    def sql(
        self,
        statement: str,
    ) -> None:
        self.sql_calls.append(
            statement
        )


class CustomValue:
    def __str__(self) -> str:
        return "custom-value"


def make_sink_without_initialisation(
    *,
    table: str = "main.logging.events",
    path: Path | None = None,
    is_databricks: bool = False,
    spark: Any | None = None,
) -> DeltaSink:
    """
    Construct a DeltaSink without invoking __init__.

    This is useful when testing individual helper methods without triggering
    Spark table creation.
    """

    sink = object.__new__(
        DeltaSink
    )

    sink.table = table
    sink.path = path
    sink.is_databricks = (
        is_databricks
    )
    sink.spark = (
        spark
        if spark is not None
        else FakeSpark()
    )

    return sink


def make_log(
    *,
    traceback_value: list[str] | None = None,
) -> BaseLog:
    """
    Create a lightweight log-shaped object.

    DeltaSink._to_row() uses attributes only, so this test double avoids
    coupling these tests to BaseLog model validation.
    """

    context = SimpleNamespace(
        application="test-application",
        environment="dev",
        correlation_id="correlation-1",
        run_id="run-1",
        attributes={
            "region": "eu",
            "attempt": 2,
        },
    )

    value = SimpleNamespace(
        timestamp=datetime(
            2026,
            11,
            2,
            19,
            30,
            tzinfo=UTC,
        ),
        level="INFO",
        message="Processing completed",
        context=context,
        call_id="call-1",
        parent_call_id="parent-1",
        duration_ms=125.5,
        module="example.module",
        function="process",
        parameters={
            "customer_id": 42,
        },
        attributes={
            "batch": "nightly",
            "successful": True,
        },
        traceback=traceback_value,
    )

    return cast(
        BaseLog,
        value,
    )


class TestSchema:
    def test_string_map_structure(
        self,
    ) -> None:
        assert isinstance(
            STRING_MAP,
            MapType,
        )
        assert isinstance(
            STRING_MAP.keyType,
            StringType,
        )
        assert isinstance(
            STRING_MAP.valueType,
            StringType,
        )
        assert (
            STRING_MAP.valueContainsNull
            is True
        )

    def test_schema_field_names(
        self,
    ) -> None:
        assert MONITAUDIT_SCHEMA.fieldNames() == [
            "timestamp",
            "level",
            "message",
            "application",
            "environment",
            "correlation_id",
            "run_id",
            "context_attributes",
            "call_id",
            "parent_call_id",
            "duration_ms",
            "module",
            "function",
            "parameters",
            "attributes",
            "error_type",
            "error_message",
            "traceback",
        ]

    def test_required_schema_fields(
        self,
    ) -> None:
        required = {
            field.name
            for field in MONITAUDIT_SCHEMA.fields
            if not field.nullable
        }

        assert required == {
            "timestamp",
            "level",
            "message",
            "application",
            "environment",
            "correlation_id",
        }

    def test_timestamp_field_type(
        self,
    ) -> None:
        assert isinstance(
            MONITAUDIT_SCHEMA[
                "timestamp"
            ].dataType,
            TimestampType,
        )

    def test_duration_field_type(
        self,
    ) -> None:
        assert isinstance(
            MONITAUDIT_SCHEMA[
                "duration_ms"
            ].dataType,
            DoubleType,
        )

    @pytest.mark.parametrize(
        "field_name",
        [
            "level",
            "message",
            "application",
            "environment",
            "correlation_id",
            "run_id",
            "call_id",
            "parent_call_id",
            "module",
            "function",
            "parameters",
            "error_type",
            "error_message",
            "traceback",
        ],
    )
    def test_string_field_types(
        self,
        field_name: str,
    ) -> None:
        assert isinstance(
            MONITAUDIT_SCHEMA[
                field_name
            ].dataType,
            StringType,
        )

    @pytest.mark.parametrize(
        "field_name",
        [
            "context_attributes",
            "attributes",
        ],
    )
    def test_mapping_field_types(
        self,
        field_name: str,
    ) -> None:
        assert isinstance(
            MONITAUDIT_SCHEMA[
                field_name
            ].dataType,
            MapType,
        )


class TestTableValidation:
    @pytest.mark.parametrize(
        "table",
        [
            "main.logging.events",
            "catalog.schema.table",
            "_catalog._schema._table",
            "catalog1.schema2.table3",
            "A_B.C_D.E_F",
        ],
    )
    def test_accepts_valid_table_names(
        self,
        table: str,
    ) -> None:
        assert (
            DeltaSink._validate_table_name(
                table
            )
            == table
        )

    def test_strips_table_name(
        self,
    ) -> None:
        assert (
            DeltaSink._validate_table_name(
                "  main.logging.events  "
            )
            == "main.logging.events"
        )

    @pytest.mark.parametrize(
        "table",
        [
            None,
            1,
            Path("main.logging.events"),
            object(),
        ],
    )
    def test_rejects_non_string_table(
        self,
        table: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "Delta table name must "
                "be a string"
            ),
        ):
            DeltaSink._validate_table_name(
                table  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "table",
        [
            "",
            " ",
            "\t",
            "\n",
        ],
    )
    def test_rejects_empty_table(
        self,
        table: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "Delta table name "
                "cannot be empty"
            ),
        ):
            DeltaSink._validate_table_name(
                table
            )

    @pytest.mark.parametrize(
        "table",
        [
            "table",
            "schema.table",
            "catalog.schema.table.extra",
            "1catalog.schema.table",
            "catalog.1schema.table",
            "catalog.schema.1table",
            "catalog..table",
            ".schema.table",
            "catalog.schema.",
            "catalog-schema.table.name",
            "catalog.schema.table-name",
            "catalog schema.table.name",
            "catalog.schema.table name",
            "catalog/schema/table",
            "catalog.schema.*",
            "`catalog`.`schema`.`table`",
        ],
    )
    def test_rejects_invalid_table_names(
        self,
        table: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "Invalid Delta table name"
            ),
        ):
            DeltaSink._validate_table_name(
                table
            )


class TestTableNameHelpers:
    def test_returns_table_parts(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.logging.events",
        )

        assert sink._table_parts() == (
            "main",
            "logging",
            "events",
        )

    def test_returns_quoted_table_name(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.logging.events",
        )

        assert (
            sink._quoted_table_name()
            == "`main`.`logging`.`events`"
        )


class TestPathResolution:
    def test_databricks_mode_ignores_path(
        self,
        tmp_path: Path,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.logging.events",
            is_databricks=True,
        )

        result = sink._resolve_path(
            tmp_path
        )

        assert result is None

    def test_databricks_mode_does_not_require_path(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.logging.events",
            is_databricks=True,
        )

        assert sink._resolve_path(None) is None

    def test_local_mode_requires_path(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.delta.local",
            is_databricks=False,
        )

        with pytest.raises(
            ValueError,
            match=(
                "local mode requires "
                "a configured path"
            ),
        ):
            sink._resolve_path(None)

    def test_local_path_appends_table_directory(
        self,
        tmp_path: Path,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.delta.local",
        )

        result = sink._resolve_path(
            tmp_path / "delta_sink"
        )

        assert result == (
            tmp_path
            / "delta_sink"
            / "main_delta_local"
        ).resolve()

    def test_local_path_accepts_string(
        self,
        tmp_path: Path,
    ) -> None:
        sink = make_sink_without_initialisation(
            table="main.delta.local",
        )

        result = sink._resolve_path(
            str(tmp_path)
        )

        assert result == (
            tmp_path
            / "main_delta_local"
        ).resolve()

    def test_local_path_property_returns_path(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "main_delta_local"
        )

        sink = make_sink_without_initialisation(
            path=path,
        )

        assert sink.local_path is path

    def test_local_path_property_returns_none_in_databricks(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            path=None,
            is_databricks=True,
        )

        assert sink.local_path is None

    def test_require_local_path_returns_path(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "delta"

        sink = make_sink_without_initialisation(
            path=path,
        )

        assert (
            sink._require_local_path()
            is path
        )

    def test_require_local_path_rejects_none(
        self,
    ) -> None:
        sink = make_sink_without_initialisation(
            path=None,
        )

        with pytest.raises(
            RuntimeError,
            match=(
                "Local Delta path "
                "is unavailable"
            ),
        ):
            sink._require_local_path()


class TestConstruction:
    def test_delta_sink_inherits_from_sink(
        self,
    ) -> None:
        assert issubclass(
            DeltaSink,
            Sink,
        )

    def test_local_initialisation_creates_empty_dataframe(
        self,
        tmp_path: Path,
    ) -> None:
        spark = FakeSpark()

        DeltaSink(
            table="main.delta.local",
            spark=cast(Any, spark),
            path=tmp_path,
            is_databricks=False,
        )

        assert spark.create_calls == [
            (
                [],
                MONITAUDIT_SCHEMA,
            )
        ]

    def test_local_initialisation_writes_ignored_delta_table(
        self,
        tmp_path: Path,
    ) -> None:
        spark = FakeSpark()

        sink = DeltaSink(
            table="main.delta.local",
            spark=cast(Any, spark),
            path=tmp_path,
            is_databricks=False,
        )

        assert (
            spark.dataframes[0]
            .write.operations
            == [
                (
                    "format",
                    "delta",
                ),
                (
                    "mode",
                    "ignore",
                ),
                (
                    "save",
                    str(
                        sink.local_path
                    ),
                ),
            ]
        )

    def test_local_initialisation_creates_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        base = (
            tmp_path
            / "one"
            / "two"
        )

        spark = FakeSpark()

        sink = DeltaSink(
            table="main.delta.local",
            spark=cast(Any, spark),
            path=base,
            is_databricks=False,
        )

        assert (
            sink.local_path is not None
        )
        assert (
            sink.local_path.parent.is_dir()
        )

    def test_databricks_initialisation_creates_catalog_and_schema(
        self,
    ) -> None:
        spark = FakeSpark()

        DeltaSink(
            table="main.logging.events",
            spark=cast(Any, spark),
            path=None,
            is_databricks=True,
        )

        assert spark.sql_calls == [
            (
                "CREATE CATALOG IF NOT "
                "EXISTS `main`"
            ),
            (
                "CREATE SCHEMA IF NOT EXISTS "
                "`main`.`logging`"
            ),
        ]

    def test_databricks_initialisation_creates_table(
        self,
    ) -> None:
        spark = FakeSpark()

        DeltaSink(
            table="main.logging.events",
            spark=cast(Any, spark),
            is_databricks=True,
        )

        assert (
            spark.dataframes[0]
            .write.operations
            == [
                (
                    "format",
                    "delta",
                ),
                (
                    "mode",
                    "ignore",
                ),
                (
                    "saveAsTable",
                    (
                        "`main`."
                        "`logging`."
                        "`events`"
                    ),
                ),
            ]
        )


class TestWrites:
    def test_local_write_creates_dataframe_with_row(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSpark()

        sink = DeltaSink(
            table="main.delta.local",
            spark=cast(Any, spark),
            path=tmp_path,
        )

        row = {
            "message": "test",
        }

        monkeypatch.setattr(
            sink,
            "_to_row",
            lambda _log: row,
        )

        log = make_log()

        sink.write(log)

        assert spark.create_calls[-1] == (
            [
                row,
            ],
            MONITAUDIT_SCHEMA,
        )

    def test_local_write_appends_to_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSpark()

        sink = DeltaSink(
            table="main.delta.local",
            spark=cast(Any, spark),
            path=tmp_path,
        )

        monkeypatch.setattr(
            sink,
            "_to_row",
            lambda _log: {
                "message": "test",
            },
        )

        sink.write(
            make_log()
        )

        write_operations = (
            spark.dataframes[-1]
            .write.operations
        )

        assert write_operations == [
            (
                "format",
                "delta",
            ),
            (
                "mode",
                "append",
            ),
            (
                "save",
                str(
                    sink.local_path
                ),
            ),
        ]

    def test_databricks_write_appends_to_table(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSpark()

        sink = DeltaSink(
            table="main.logging.events",
            spark=cast(Any, spark),
            is_databricks=True,
        )

        monkeypatch.setattr(
            sink,
            "_to_row",
            lambda _log: {
                "message": "test",
            },
        )

        sink.write(
            make_log()
        )

        write_operations = (
            spark.dataframes[-1]
            .write.operations
        )

        assert write_operations == [
            (
                "format",
                "delta",
            ),
            (
                "mode",
                "append",
            ),
            (
                "saveAsTable",
                (
                    "`main`."
                    "`logging`."
                    "`events`"
                ),
            ),
        ]


class TestRowConversion:
    def test_converts_standard_log(
        self,
    ) -> None:
        log = make_log()

        result = DeltaSink._to_row(
            log
        )

        assert result == {
            "timestamp": datetime(
                2026,
                11,
                2,
                19,
                30,
                tzinfo=UTC,
            ),
            "level": "INFO",
            "message": "Processing completed",
            "application": "test-application",
            "environment": "dev",
            "correlation_id": "correlation-1",
            "run_id": "run-1",
            "context_attributes": {
                "region": "eu",
                "attempt": "2",
            },
            "call_id": "call-1",
            "parent_call_id": "parent-1",
            "duration_ms": 125.5,
            "module": "example.module",
            "function": "process",
            "parameters": (
                '{"customer_id": 42}'
            ),
            "attributes": {
                "batch": "nightly",
                "successful": "True",
            },
            "error_type": None,
            "error_message": None,
            "traceback": None,
        }

    def test_converts_exception_fields(
        self,
    ) -> None:
        log = make_log(
            traceback_value=[
                "Traceback:\n",
                "ValueError: failed\n",
            ]
        )

        log.error_type = "ValueError"
        log.error_message = "failed"

        result = DeltaSink._to_row(
            log
        )

        assert (
            result["error_type"]
            == "ValueError"
        )
        assert (
            result["error_message"]
            == "failed"
        )
        assert result["traceback"] == (
            "Traceback:\n"
            "ValueError: failed\n"
        )

    def test_missing_exception_fields_become_none(
        self,
    ) -> None:
        result = DeltaSink._to_row(
            make_log()
        )

        assert result["error_type"] is None
        assert result["error_message"] is None

    def test_empty_parameters_become_none(
        self,
    ) -> None:
        log = make_log()
        log.parameters = {}

        result = DeltaSink._to_row(
            log
        )

        assert result["parameters"] is None


class TestTracebackSerialisation:
    def test_missing_traceback_returns_none(
        self,
    ) -> None:
        log = cast(
            BaseLog,
            SimpleNamespace(),
        )

        assert (
            _serialize_traceback(log)
            is None
        )

    @pytest.mark.parametrize(
        "traceback_value",
        [
            None,
            [],
            (),
        ],
    )
    def test_empty_traceback_returns_none(
        self,
        traceback_value: object,
    ) -> None:
        log = cast(
            BaseLog,
            SimpleNamespace(
                traceback=traceback_value
            ),
        )

        assert (
            _serialize_traceback(log)
            is None
        )

    def test_joins_traceback_lines(
        self,
    ) -> None:
        log = cast(
            BaseLog,
            SimpleNamespace(
                traceback=[
                    "Traceback:\n",
                    "ValueError: failed\n",
                ]
            ),
        )

        assert _serialize_traceback(
            log
        ) == (
            "Traceback:\n"
            "ValueError: failed\n"
        )

    def test_does_not_insert_additional_newlines(
        self,
    ) -> None:
        log = cast(
            BaseLog,
            SimpleNamespace(
                traceback=[
                    "first",
                    "second",
                ]
            ),
        )

        assert (
            _serialize_traceback(log)
            == "firstsecond"
        )


class TestStringifyValue:
    @pytest.mark.parametrize(
        (
            "value",
            "expected",
        ),
        [
            (
                None,
                "None",
            ),
            (
                True,
                "True",
            ),
            (
                42,
                "42",
            ),
            (
                1.5,
                "1.5",
            ),
            (
                "text",
                "text",
            ),
        ],
    )
    def test_scalar_values_use_str(
        self,
        value: Any,
        expected: str,
    ) -> None:
        assert (
            _stringify_value(value)
            == expected
        )

    def test_dictionary_becomes_sorted_json(
        self,
    ) -> None:
        result = _stringify_value(
            {
                "z": 1,
                "a": 2,
            }
        )

        assert result == (
            '{"a": 2, "z": 1}'
        )

    def test_list_becomes_json(
        self,
    ) -> None:
        assert _stringify_value(
            [
                1,
                2,
                3,
            ]
        ) == "[1, 2, 3]"

    def test_tuple_becomes_json_array(
        self,
    ) -> None:
        assert _stringify_value(
            (
                "a",
                "b",
            )
        ) == '["a", "b"]'

    def test_set_is_sorted_before_json_encoding(
        self,
    ) -> None:
        result = _stringify_value(
            {
                "z",
                "a",
                "m",
            }
        )

        assert result == (
            '["a", "m", "z"]'
        )

    def test_frozenset_is_sorted_before_json_encoding(
        self,
    ) -> None:
        result = _stringify_value(
            frozenset(
                {
                    3,
                    1,
                    2,
                }
            )
        )

        assert result == "[1, 2, 3]"

    def test_custom_value_uses_str(
        self,
    ) -> None:
        assert _stringify_value(
            CustomValue()
        ) == "custom-value"


class TestStringifyMapping:
    def test_empty_mapping_returns_empty_mapping(
        self,
    ) -> None:
        assert _stringify_mapping(
            {}
        ) == {}

    def test_stringifies_all_values(
        self,
    ) -> None:
        result = _stringify_mapping(
            {
                "string": "value",
                "integer": 42,
                "boolean": True,
                "mapping": {
                    "b": 2,
                    "a": 1,
                },
                "set": {
                    "b",
                    "a",
                },
            }
        )

        assert result == {
            "string": "value",
            "integer": "42",
            "boolean": "True",
            "mapping": (
                '{"a": 1, "b": 2}'
            ),
            "set": '["a", "b"]',
        }

    def test_keys_are_converted_to_strings(
        self,
    ) -> None:
        values: dict[Any, Any] = {
            42: "value",
            None: "none",
        }

        assert _stringify_mapping(
            values
        ) == {
            "42": "value",
            "None": "none",
        }

    def test_returns_new_mapping(
        self,
    ) -> None:
        values = {
            "value": "test",
        }

        result = _stringify_mapping(
            values
        )

        assert result == values
        assert result is not values


class TestToJson:
    def test_empty_mapping_returns_none(
        self,
    ) -> None:
        assert _to_json({}) is None

    def test_serialises_mapping_with_sorted_keys(
        self,
    ) -> None:
        result = _to_json(
            {
                "z": 1,
                "a": 2,
            }
        )

        assert result == (
            '{"a": 2, "z": 1}'
        )

    def test_serialises_nested_values(
        self,
    ) -> None:
        result = _to_json(
            {
                "parameters": {
                    "customer_id": 42,
                    "active": True,
                }
            }
        )

        assert result is not None

        assert json.loads(
            result
        ) == {
            "parameters": {
                "customer_id": 42,
                "active": True,
            }
        }

    def test_unsupported_value_uses_str(
        self,
    ) -> None:
        result = _to_json(
            {
                "value": CustomValue(),
            }
        )

        assert result == (
            '{"value": "custom-value"}'
        )

    def test_does_not_modify_input(
        self,
    ) -> None:
        values = {
            "z": 1,
            "a": {
                "value": 2,
            },
        }

        original = {
            "z": 1,
            "a": {
                "value": 2,
            },
        }

        _to_json(values)

        assert values == original