# src/monitaudit/utilities/build_monitaudit.py

from __future__ import annotations

from pathlib import Path

from monitaudit.models.monitaudit import Monitaudit
from monitaudit.sinks import ConsoleSink, DeltaSink, FileSink, JsonSink
from monitaudit.sinks.base import Sink
from monitaudit.utilities.get_spark import get_spark_session, run_dbx
from monitaudit.utilities.load_config import load_config


def build_monitaudit(
    config_path: str | Path | None = None,
    correlation_id: str | None = None,
) -> Monitaudit:
    config = load_config(config_path)
    sinks: list[Sink] = []

    if config.sinks.console_sink.enabled:
        sinks.append(
            ConsoleSink(
                parameters=config.sinks.console_sink.parameters,
            )
        )

    if config.sinks.file_sink.enabled:
        file_sink = config.sinks.file_sink
        sinks.append(
            FileSink(
                path=file_sink.path,
                format=file_sink.format,
                delimiter=file_sink.delimiter,
                file_cycle=config.logging.file_cycle,
            )
        )

    if config.sinks.json_sink.enabled:
        json_sink = config.sinks.json_sink
        sinks.append(
            JsonSink(
                path=json_sink.path,
                file_cycle=config.logging.file_cycle,
            )
        )

    if config.sinks.delta_sink.enabled:
        delta_sink = config.sinks.delta_sink

        if delta_sink.table is None:
            raise ValueError(
                "Delta sink is enabled but no table is configured."
            )

        if delta_sink.path is None:
            raise ValueError(
                "Delta sink is enabled but no path is configured."
            )

        is_databricks = not delta_sink.table.endswith(".local")
        spark = run_dbx() if is_databricks else get_spark_session()

        sinks.append(
            DeltaSink(
                table=delta_sink.table,
                path=delta_sink.path,
                spark=spark,
                is_databricks=is_databricks,
            )
        )

    return Monitaudit(
        config.application,
        config.environment,
        *sinks,
        timer=config.logging.timer,
        correlation_id = correlation_id,
        parameters=config.logging.parameters,
        max_parameter_length=config.logging.max_parameter_length,
        sink_failure_mode=config.logging.sink_failure_mode,
    )