from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call

import pytest

from monitaudit.models.context import LogContext
from monitaudit.models.log import ErrorLog, InfoLog
from monitaudit.sinks.delta import (
    monitaudit_SCHEMA,
    STRING_MAP,
    DeltaSink,
    _serialize_traceback,
    _stringify_mapping,
    _stringify_value,
    _to_json,
)


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
        attributes={
            "team": "platform",
            "attempt": 2,
        },
    )


@pytest.fixture
def timestamp() -> datetime:
    return datetime(
        2026,
        10,
        23,
        12,
        30,
        15,
        tzinfo=timezone.utc,
    )


def configure_dataframe_writer(
    dataframe: MagicMock,
) -> MagicMock:
    writer = MagicMock()

    dataframe.write = writer

    writer.format.return_value = writer
    writer.mode.return_value = writer
    writer.save.return_value = None
    writer.saveAsTable.return_value = None

    return writer


def make_local_sink(
    spark: MagicMock,
    dataframe: MagicMock,
) -> DeltaSink:
    spark.createDataFrame.return_value = dataframe

    configure_dataframe_writer(dataframe)

    return DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=False,
    )


def make_databricks_sink(
    spark: MagicMock,
    dataframe: MagicMock,
) -> DeltaSink:
    spark.createDataFrame.return_value = dataframe

    configure_dataframe_writer(dataframe)

    return DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=True,
    )


@pytest.mark.parametrize(
    "table",
    [
        "main.logging.monitaudit",
        "catalog_1.schema_2.table_3",
        "_catalog._schema._table",
        "A.B.C",
        "catalog.schema.table123",
    ],
)
def test_valid_table_names(
    table: str,
) -> None:
    assert (
        DeltaSink._validate_table_name(table)
        == table
    )


def test_table_name_is_stripped() -> None:
    result = DeltaSink._validate_table_name(
        "  main.logging.monitaudit  "
    )

    assert result == "main.logging.monitaudit"


def test_non_string_table_name_raises_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="Delta table name must be a string.",
    ):
        DeltaSink._validate_table_name(123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "table",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_empty_table_name_raises_value_error(
    table: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Delta table name cannot be empty.",
    ):
        DeltaSink._validate_table_name(table)


@pytest.mark.parametrize(
    "table",
    [
        "monitaudit",
        "logging.monitaudit",
        "a.b.c.d",
        "1main.logging.monitaudit",
        "main.2logging.monitaudit",
        "main.logging.3monitaudit",
        "main.logging.monitaudit-name",
        "main.logging.monitaudit name",
        "main/logging/monitaudit",
        "main..monitaudit",
        ".logging.monitaudit",
        "main.logging.",
        "`main`.`logging`.`monitaudit`",
        "main.logging.monitaudit;",
    ],
)
def test_invalid_table_names_raise_value_error(
    table: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid Delta table name",
    ):
        DeltaSink._validate_table_name(table)


def test_constructor_stores_values_and_ensures_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spark = MagicMock()

    ensure_table = MagicMock()

    monkeypatch.setattr(
        DeltaSink,
        "_ensure_table",
        ensure_table,
    )

    sink = DeltaSink(
        table=" main.logging.monitaudit ",
        spark=spark,
        is_databricks=True,
    )

    assert sink.table == "main.logging.monitaudit"
    assert sink.spark is spark
    assert sink.is_databricks is True

    ensure_table.assert_called_once_with()


def test_table_parts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DeltaSink,
        "_ensure_table",
        MagicMock(),
    )

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=MagicMock(),
    )

    assert sink._table_parts() == (
        "main",
        "logging",
        "monitaudit",
    )


def test_quoted_table_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DeltaSink,
        "_ensure_table",
        MagicMock(),
    )

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=MagicMock(),
    )

    assert sink._quoted_table_name() == (
        "`main`.`logging`.`monitaudit`"
    )


def test_local_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DeltaSink,
        "_ensure_table",
        MagicMock(),
    )

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=MagicMock(),
    )

    assert sink._local_path() == (
        "main/logging/monitaudit"
    )


def test_ensure_table_creates_empty_dataframe_with_schema() -> None:
    spark = MagicMock()
    dataframe = MagicMock()

    spark.createDataFrame.return_value = dataframe

    configure_dataframe_writer(dataframe)

    DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=False,
    )

    spark.createDataFrame.assert_called_once_with(
        [],
        schema=monitaudit_SCHEMA,
    )


def test_local_initialisation_creates_delta_path() -> None:
    spark = MagicMock()
    dataframe = MagicMock()

    writer = configure_dataframe_writer(
        dataframe
    )

    spark.createDataFrame.return_value = dataframe

    DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=False,
    )

    writer.format.assert_called_once_with(
        "delta"
    )

    writer.mode.assert_called_once_with(
        "ignore"
    )

    writer.save.assert_called_once_with(
        "main/logging/monitaudit"
    )

    writer.saveAsTable.assert_not_called()
    spark.sql.assert_not_called()


def test_databricks_initialisation_creates_catalog_and_schema() -> None:
    spark = MagicMock()
    dataframe = MagicMock()

    configure_dataframe_writer(dataframe)

    spark.createDataFrame.return_value = dataframe

    DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=True,
    )

    assert spark.sql.call_args_list == [
        call(
            "CREATE CATALOG IF NOT EXISTS `main`"
        ),
        call(
            "CREATE SCHEMA IF NOT EXISTS "
            "`main`.`logging`"
        ),
    ]


def test_databricks_initialisation_creates_table() -> None:
    spark = MagicMock()
    dataframe = MagicMock()

    writer = configure_dataframe_writer(
        dataframe
    )

    spark.createDataFrame.return_value = dataframe

    DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=True,
    )

    writer.format.assert_called_once_with(
        "delta"
    )

    writer.mode.assert_called_once_with(
        "ignore"
    )

    writer.saveAsTable.assert_called_once_with(
        "`main`.`logging`.`monitaudit`"
    )

    writer.save.assert_not_called()


def test_write_creates_dataframe_from_log_row(
    context: LogContext,
    timestamp: datetime,
) -> None:
    spark = MagicMock()

    initial_dataframe = MagicMock()
    write_dataframe = MagicMock()

    configure_dataframe_writer(
        initial_dataframe
    )

    write_writer = configure_dataframe_writer(
        write_dataframe
    )

    spark.createDataFrame.side_effect = [
        initial_dataframe,
        write_dataframe,
    ]

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=False,
    )

    log = InfoLog(
        timestamp=timestamp,
        message="hello",
        context=context,
    )

    sink.write(log)

    expected_row = DeltaSink._to_row(log)

    assert spark.createDataFrame.call_args_list == [
        call(
            [],
            schema=monitaudit_SCHEMA,
        ),
        call(
            [expected_row],
            schema=monitaudit_SCHEMA,
        ),
    ]

    write_writer.mode.assert_called_once_with(
        "append"
    )


def test_local_write_appends_to_delta_path(
    context: LogContext,
) -> None:
    spark = MagicMock()

    initial_dataframe = MagicMock()
    write_dataframe = MagicMock()

    configure_dataframe_writer(
        initial_dataframe
    )

    writer = configure_dataframe_writer(
        write_dataframe
    )

    spark.createDataFrame.side_effect = [
        initial_dataframe,
        write_dataframe,
    ]

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=False,
    )

    sink.write(
        InfoLog(
            message="local write",
            context=context,
        )
    )

    writer.format.assert_called_once_with(
        "delta"
    )

    writer.mode.assert_called_once_with(
        "append"
    )

    writer.save.assert_called_once_with(
        "main/logging/monitaudit"
    )

    writer.saveAsTable.assert_not_called()


def test_databricks_write_appends_to_table(
    context: LogContext,
) -> None:
    spark = MagicMock()

    initial_dataframe = MagicMock()
    write_dataframe = MagicMock()

    configure_dataframe_writer(
        initial_dataframe
    )

    writer = configure_dataframe_writer(
        write_dataframe
    )

    spark.createDataFrame.side_effect = [
        initial_dataframe,
        write_dataframe,
    ]

    sink = DeltaSink(
        table="main.logging.monitaudit",
        spark=spark,
        is_databricks=True,
    )

    sink.write(
        InfoLog(
            message="Databricks write",
            context=context,
        )
    )

    writer.format.assert_called_once_with(
        "delta"
    )

    writer.mode.assert_called_once_with(
        "append"
    )

    writer.saveAsTable.assert_called_once_with(
        "`main`.`logging`.`monitaudit`"
    )

    writer.save.assert_not_called()


def test_to_row_maps_info_log(
    context: LogContext,
    timestamp: datetime,
) -> None:
    log = InfoLog(
        timestamp=timestamp,
        message="completed",
        context=context,
        call_id="call-123",
        parent_call_id="parent-456",
        duration_ms=12.5,
        module="example.module",
        function="example_function",
        parameters={
            "z": 1,
            "a": "value",
        },
        attributes={
            "event": "function_end",
            "count": 4,
        },
    )

    row = DeltaSink._to_row(log)

    assert row == {
        "timestamp": timestamp,
        "level": "INFO",
        "message": "completed",
        "application": "monitaudit-test",
        "environment": "dev",
        "correlation_id": "correlation-123",
        "run_id": "run-456",
        "context_attributes": {
            "team": "platform",
            "attempt": "2",
        },
        "call_id": "call-123",
        "parent_call_id": "parent-456",
        "duration_ms": 12.5,
        "module": "example.module",
        "function": "example_function",
        "parameters": (
            '{"a": "value", "z": 1}'
        ),
        "attributes": {
            "event": "function_end",
            "count": "4",
        },
        "error_type": None,
        "error_message": None,
        "traceback": None,
    }


def test_to_row_maps_error_fields(
    context: LogContext,
    timestamp: datetime,
) -> None:
    log = ErrorLog(
        timestamp=timestamp,
        message="operation failed",
        context=context,
        error_type="ValueError",
        error_message="invalid value",
        traceback=[
            "Traceback:\n",
            "ValueError: invalid value\n",
        ],
    )

    row = DeltaSink._to_row(log)

    assert row["level"] == "ERROR"
    assert row["error_type"] == "ValueError"

    assert (
        row["error_message"]
        == "invalid value"
    )

    assert row["traceback"] == (
        "Traceback:\n"
        "ValueError: invalid value\n"
    )


def test_to_row_empty_parameters_become_none(
    context: LogContext,
) -> None:
    log = InfoLog(
        message="empty parameters",
        context=context,
        parameters={},
    )

    row = DeltaSink._to_row(log)

    assert row["parameters"] is None


def test_to_row_empty_attributes_become_empty_map(
    context: LogContext,
) -> None:
    log = InfoLog(
        message="empty attributes",
        context=context,
        attributes={},
    )

    row = DeltaSink._to_row(log)

    assert row["attributes"] == {}


def test_serialize_traceback_without_traceback(
    context: LogContext,
) -> None:
    log = InfoLog(
        message="normal",
        context=context,
    )

    assert _serialize_traceback(log) is None


def test_serialize_empty_traceback(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="error",
        context=context,
        traceback=[],
    )

    assert _serialize_traceback(log) is None


def test_serialize_traceback_joins_lines(
    context: LogContext,
) -> None:
    log = ErrorLog(
        message="error",
        context=context,
        traceback=[
            "Traceback:\n",
            "ValueError: invalid\n",
        ],
    )

    assert _serialize_traceback(log) == (
        "Traceback:\n"
        "ValueError: invalid\n"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hello", "hello"),
        (42, "42"),
        (1.5, "1.5"),
        (True, "True"),
        (None, "None"),
    ],
)
def test_stringify_scalar_values(
    value: Any,
    expected: str,
) -> None:
    assert _stringify_value(value) == expected


def test_stringify_dictionary() -> None:
    result = _stringify_value(
        {
            "z": 1,
            "a": 2,
        }
    )

    assert result == '{"a": 2, "z": 1}'


def test_stringify_list() -> None:
    result = _stringify_value(
        [
            "one",
            "two",
        ]
    )

    assert json.loads(result) == [
        "one",
        "two",
    ]


def test_stringify_tuple() -> None:
    result = _stringify_value(
        (
            "one",
            "two",
        )
    )

    assert json.loads(result) == [
        "one",
        "two",
    ]


def test_stringify_set_is_deterministic() -> None:
    result = _stringify_value(
        {
            "three",
            "one",
            "two",
        }
    )

    assert result == (
        '["one", "three", "two"]'
    )


def test_stringify_frozenset_is_deterministic() -> None:
    result = _stringify_value(
        frozenset(
            {
                "three",
                "one",
                "two",
            }
        )
    )

    assert result == (
        '["one", "three", "two"]'
    )


def test_stringify_mapping() -> None:
    result = _stringify_mapping(
        {
            "string": "hello",
            "number": 42,
            "nested": {
                "name": "monitaudit",
            },
        }
    )

    assert result == {
        "string": "hello",
        "number": "42",
        "nested": '{"name": "monitaudit"}',
    }


def test_stringify_mapping_empty() -> None:
    assert _stringify_mapping({}) == {}


def test_stringify_mapping_converts_keys_to_strings() -> None:
    values: dict[Any, Any] = {
        1: "one",
        2: "two",
    }

    assert _stringify_mapping(values) == {
        "1": "one",
        "2": "two",
    }


def test_to_json_empty_mapping_returns_none() -> None:
    assert _to_json({}) is None


def test_to_json_sorts_keys() -> None:
    result = _to_json(
        {
            "z": 1,
            "a": 2,
        }
    )

    assert result == '{"a": 2, "z": 1}'


def test_to_json_uses_default_str() -> None:
    result = _to_json(
        {
            "path": Path("/tmp/example"),
        }
    )

    assert result is not None

    assert json.loads(result) == {
        "path": "/tmp/example",
    }


def test_string_map_allows_null_values() -> None:
    assert STRING_MAP.valueContainsNull is True


def test_schema_contains_expected_fields() -> None:
    assert monitaudit_SCHEMA.fieldNames() == [
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


def test_required_schema_fields_are_not_nullable() -> None:
    required_fields = {
        "timestamp",
        "level",
        "message",
        "application",
        "environment",
        "correlation_id",
    }

    fields = {
        field.name: field
        for field in monitaudit_SCHEMA.fields
    }

    for field_name in required_fields:
        assert fields[field_name].nullable is False


def test_optional_schema_fields_are_nullable() -> None:
    optional_fields = {
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
    }

    fields = {
        field.name: field
        for field in monitaudit_SCHEMA.fields
    }

    for field_name in optional_fields:
        assert fields[field_name].nullable is True