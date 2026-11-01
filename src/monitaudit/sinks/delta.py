# src/monitaudit/sinks/delta.py

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    DoubleType,
    MapType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink


STRING_MAP = MapType(
    StringType(),
    StringType(),
    valueContainsNull=True,
)


MONITAUDIT_SCHEMA = StructType(
    [
        StructField("timestamp", TimestampType(), False),
        StructField("level", StringType(), False),
        StructField("message", StringType(), False),
        StructField("application", StringType(), False),
        StructField("environment", StringType(), False),
        StructField("correlation_id", StringType(), False),
        StructField("run_id", StringType(), True),
        StructField("context_attributes", STRING_MAP, True),
        StructField("call_id", StringType(), True),
        StructField("parent_call_id", StringType(), True),
        StructField("duration_ms", DoubleType(), True),
        StructField("module", StringType(), True),
        StructField("function", StringType(), True),
        StructField("parameters", StringType(), True),
        StructField("attributes", STRING_MAP, True),
        StructField("error_type", StringType(), True),
        StructField("error_message", StringType(), True),
        StructField("traceback", StringType(), True),
    ]
)


class DeltaSink(Sink):
    _TABLE_NAME_PATTERN = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*"
        r"(?:\.[A-Za-z_][A-Za-z0-9_]*){2}$"
    )

    def __init__(
        self,
        table: str,
        spark: SparkSession,
        path: str | Path | None = None,
        is_databricks: bool = False,
    ) -> None:
        self.table = self._validate_table_name(
            table
        )

        self.spark = spark
        self.is_databricks = is_databricks

        self.path = self._resolve_path(
            path
        )

        self._ensure_table()

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    @classmethod
    def _validate_table_name(
        cls,
        table: str,
    ) -> str:
        if not isinstance(table, str):
            raise TypeError(
                "Delta table name must be a string."
            )

        table = table.strip()

        if not table:
            raise ValueError(
                "Delta table name cannot be empty."
            )

        if not cls._TABLE_NAME_PATTERN.fullmatch(
            table
        ):
            raise ValueError(
                f"Invalid Delta table name: {table!r}. "
                "Expected 'catalog.schema.table'. Each part may "
                "contain only letters, numbers and underscores, "
                "and may not start with a number."
            )

        return table

    # -----------------------------------------------------------------------
    # Table
    # -----------------------------------------------------------------------

    def _table_parts(
        self,
    ) -> tuple[str, str, str]:
        catalog, schema, table = self.table.split(
            ".",
            maxsplit=2,
        )

        return (
            catalog,
            schema,
            table,
        )

    def _quoted_table_name(
        self,
    ) -> str:
        catalog, schema, table = self._table_parts()

        return (
            f"`{catalog}`."
            f"`{schema}`."
            f"`{table}`"
        )

    # -----------------------------------------------------------------------
    # Local path
    # -----------------------------------------------------------------------

    def _resolve_path(
        self,
        path: str | Path | None,
    ) -> Path | None:
        """
        Resolve the configured local Delta destination.

        The configured path is the base directory.

        Example:

            table = main.delta.local
            path  = output/delta_sink

        becomes:

            output/delta_sink/main_delta_local

        Databricks mode does not require a local path.
        """

        if self.is_databricks:
            return None

        if path is None:
            raise ValueError(
                "DeltaSink local mode requires a configured path."
            )

        base_path = Path(
            path
        ).expanduser()

        table_directory = self.table.replace(
            ".",
            "_",
        )

        return (
            base_path
            / table_directory
        ).resolve()

    @property
    def local_path(
        self,
    ) -> Path | None:
        """
        Return the physical local Delta path.

        Returns None when running in Databricks mode.
        """

        return self.path

    def _require_local_path(
        self,
    ) -> Path:
        if self.path is None:
            raise RuntimeError(
                "Local Delta path is unavailable."
            )

        return self.path

    # -----------------------------------------------------------------------
    # Initialisation
    # -----------------------------------------------------------------------

    def _ensure_table(
        self,
    ) -> None:
        dataframe = self.spark.createDataFrame(
            [],
            schema=MONITAUDIT_SCHEMA,
        )

        if self.is_databricks:
            self._ensure_databricks_table(
                dataframe
            )
        else:
            self._ensure_local_table(
                dataframe
            )

    def _ensure_local_table(
        self,
        dataframe: DataFrame,
    ) -> None:
        path = self._require_local_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            dataframe.write
            .format("delta")
            .mode("ignore")
            .save(str(path))
        )

    def _ensure_databricks_table(
        self,
        dataframe: DataFrame,
    ) -> None:
        catalog, schema, _ = self._table_parts()

        self.spark.sql(
            f"CREATE CATALOG IF NOT EXISTS `{catalog}`"
        )

        self.spark.sql(
            "CREATE SCHEMA IF NOT EXISTS "
            f"`{catalog}`.`{schema}`"
        )

        (
            dataframe.write
            .format("delta")
            .mode("ignore")
            .saveAsTable(
                self._quoted_table_name()
            )
        )

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    def write(
        self,
        log: BaseLog,
    ) -> None:
        row = self._to_row(
            log
        )

        dataframe = self.spark.createDataFrame(
            [row],
            schema=MONITAUDIT_SCHEMA,
        )

        if self.is_databricks:
            self._write_databricks(
                dataframe
            )
        else:
            self._write_local(
                dataframe
            )

    def _write_local(
        self,
        dataframe: DataFrame,
    ) -> None:
        path = self._require_local_path()

        (
            dataframe.write
            .format("delta")
            .mode("append")
            .save(str(path))
        )

    def _write_databricks(
        self,
        dataframe: DataFrame,
    ) -> None:
        (
            dataframe.write
            .format("delta")
            .mode("append")
            .saveAsTable(
                self._quoted_table_name()
            )
        )

    # -----------------------------------------------------------------------
    # Row conversion
    # -----------------------------------------------------------------------

    @staticmethod
    def _to_row(
        log: BaseLog,
    ) -> dict[str, Any]:
        return {
            "timestamp": log.timestamp,
            "level": str(log.level),
            "message": log.message,
            "application": log.context.application,
            "environment": log.context.environment,
            "correlation_id": log.context.correlation_id,
            "run_id": log.context.run_id,
            "context_attributes": _stringify_mapping(
                log.context.attributes
            ),
            "call_id": log.call_id,
            "parent_call_id": log.parent_call_id,
            "duration_ms": log.duration_ms,
            "module": log.module,
            "function": log.function,
            "parameters": _to_json(
                log.parameters
            ),
            "attributes": _stringify_mapping(
                log.attributes
            ),
            "error_type": getattr(
                log,
                "error_type",
                None,
            ),
            "error_message": getattr(
                log,
                "error_message",
                None,
            ),
            "traceback": _serialize_traceback(
                log
            ),
        }


def _serialize_traceback(
    log: BaseLog,
) -> str | None:
    traceback_lines = getattr(
        log,
        "traceback",
        None,
    )

    if not traceback_lines:
        return None

    return "".join(
        traceback_lines
    )


def _stringify_mapping(
    values: dict[str, Any],
) -> dict[str, str]:
    return {
        str(key): _stringify_value(
            value
        )
        for key, value in values.items()
    }


def _stringify_value(
    value: Any,
) -> str:
    if isinstance(
        value,
        (
            set,
            frozenset,
        ),
    ):
        value = sorted(
            value,
            key=str,
        )

    if isinstance(
        value,
        (
            dict,
            list,
            tuple,
        ),
    ):
        return json.dumps(
            value,
            default=str,
            sort_keys=True,
        )

    return str(
        value
    )


def _to_json(
    values: dict[str, Any],
) -> str | None:
    if not values:
        return None

    return json.dumps(
        values,
        default=str,
        sort_keys=True,
    )