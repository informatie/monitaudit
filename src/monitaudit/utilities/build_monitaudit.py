# src/monitaudit/utilities/build_monitaudit.py

from __future__ import annotations
from monitaudit.utilities.get_spark import (
    get_spark_session,
    run_dbx,
)
from pathlib import Path

from monitaudit.models.monitaudit import Monitaudit
from monitaudit.sinks import (
    ConsoleSink,
    DeltaSink,
    FileSink,
    JsonSink,
)
from monitaudit.sinks.base import Sink

from monitaudit.utilities.get_environment import get_environment
from monitaudit.utilities.load_config import load_config


def build_monitaudit(
    config_path: str | Path | None = None,
) -> Monitaudit:
    if config_path is None:
        config = load_config()
    else:
        config = load_config(config_path)

    monitaudit = config.monitaudit

    environment = get_environment()

    settings = monitaudit.for_environment(
        environment,
    )

    sinks: list[Sink] = []

    if settings.sinks.file_sink.enabled:
        sinks.append(
            FileSink(
                path=settings.sinks.file_sink.path,
                format=settings.sinks.file_sink.format,
                delimiter=settings.sinks.file_sink.delimiter,                
            )
        )

    if settings.sinks.console_sink.enabled:
        sinks.append(
            ConsoleSink(
                parameters=(
                    settings
                    .sinks
                    .console_sink
                    .parameters
                ),
            )
        )

    if settings.sinks.json_sink.enabled:
        sinks.append(
            JsonSink(
                path=settings.sinks.json_sink.path,
            )
        )

    if settings.sinks.delta_sink.enabled:
        if settings.is_databricks:
            spark = run_dbx()
        else:
            spark = get_spark_session()

        if settings.sinks.delta_sink.table is None:
            raise ValueError(
                "Delta sink is enabled but no table is configured."
            )

        sinks.append(
            DeltaSink(
                table=settings.sinks.delta_sink.table,
                spark=spark,
                is_databricks=settings.is_databricks,
            )
        )

    return Monitaudit(
        monitaudit.application,
        environment,
        *sinks,
        timer=settings.logging.timer,
        parameters=settings.logging.parameters,
        max_parameter_length=settings.logging.max_parameter_length,
        sink_failure_mode=settings.logging.sink_failure_mode,
    )