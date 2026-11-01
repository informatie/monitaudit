# src/monitaudit/utilities/build_monitaudit.py

from __future__ import annotations

from pathlib import Path

from monitaudit.models.monitaudit import Monitaudit
from monitaudit.sinks import (
    ConsoleSink,
    DeltaSink,
    FileSink,
    JsonSink,
)
from monitaudit.sinks.base import Sink
from monitaudit.utilities.get_spark import (
    get_spark_session,
    run_dbx,
)
from monitaudit.utilities.load_config import load_config


def build_monitaudit(
    config_path: str | Path | None = None,
) -> Monitaudit:
    config = load_config(
        config_path
    )

    sinks: list[Sink] = []

    # -----------------------------------------------------------------------
    # FILE SINK
    # -----------------------------------------------------------------------

    if config.sinks.file_sink.enabled:
        sinks.append(
            FileSink(
                path=config.sinks.file_sink.path,
                format=config.sinks.file_sink.format,
                delimiter=config.sinks.file_sink.delimiter,
            )
        )

    # -----------------------------------------------------------------------
    # CONSOLE SINK
    # -----------------------------------------------------------------------

    if config.sinks.console_sink.enabled:
        sinks.append(
            ConsoleSink(
                parameters=config.sinks.console_sink.parameters,
            )
        )

    # -----------------------------------------------------------------------
    # JSON SINK
    # -----------------------------------------------------------------------

    if config.sinks.json_sink.enabled:
        sinks.append(
            JsonSink(
                path=config.sinks.json_sink.path,
            )
        )

    # -----------------------------------------------------------------------
    # DELTA SINK
    # -----------------------------------------------------------------------

    if config.sinks.delta_sink.enabled:
        table = config.sinks.delta_sink.table

        if table is None:
            raise ValueError(
                "Delta sink is enabled but no table is configured."
            )

        try:
            spark = run_dbx()
            is_databricks = True
        except Exception: # noqa: BLE001
            spark = get_spark_session()
            is_databricks = False

        sinks.append(
            DeltaSink(
                table=table,
                spark=spark,
                is_databricks=is_databricks,
            )
        )

    # -----------------------------------------------------------------------
    # MONITAUDIT
    # -----------------------------------------------------------------------

    return Monitaudit(
        config.application,
        config.environment,
        *sinks,
        timer=config.logging.timer,
        parameters=config.logging.parameters,
        max_parameter_length=(
            config.logging.max_parameter_length
        ),
        sink_failure_mode=(
            config.logging.sink_failure_mode
        ),
    )