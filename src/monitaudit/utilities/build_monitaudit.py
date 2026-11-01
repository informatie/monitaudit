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
    # ConsoleSink
    # -----------------------------------------------------------------------

    if config.sinks.console_sink.enabled:
        sinks.append(
            ConsoleSink(
                parameters=config.sinks.console_sink.parameters,
            )
        )

    # -----------------------------------------------------------------------
    # FileSink
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
    # JsonSink
    # -----------------------------------------------------------------------

    if config.sinks.json_sink.enabled:
        sinks.append(
            JsonSink(
                path=config.sinks.json_sink.path,
            )
        )

    # -----------------------------------------------------------------------
    # DeltaSink
    # -----------------------------------------------------------------------

    if config.sinks.delta_sink.enabled:
        delta_settings = config.sinks.delta_sink

        table = delta_settings.table
        path = delta_settings.path

        if table is None:
            raise ValueError(
                "Delta sink is enabled but no table is configured."
            )

        if path is None:
            raise ValueError(
                "Delta sink is enabled but no path is configured."
            )

        # Local Delta tables use the *.local convention.
        is_databricks = not table.endswith(
            ".local"
        )

        if is_databricks:
            spark = run_dbx()
        else:
            spark = get_spark_session()

        sinks.append(
            DeltaSink(
                table=table,
                path=path,
                spark=spark,
                is_databricks=is_databricks,
            )
        )

    # -----------------------------------------------------------------------
    # MonitAudit
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