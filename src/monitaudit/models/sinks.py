# src/monitaudit/models/sinks.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Environment = Literal[
    "dev",
    "acc",
    "prod",
]

LogLevel = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]

SinkFailureMode = Literal[
    "continue",
    "raise",
]

FileFormat = Literal[
    "text",
    "csv",
]


class ConfigModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class LoggingSettings(ConfigModel):
    level: LogLevel = "INFO"
    timer: bool = True
    parameters: bool = True

    max_parameter_length: int = Field(
        default=1000,
        ge=50,
        le=100_000,
    )

    sink_failure_mode: SinkFailureMode = "continue"


class ConsoleSinkSettings(ConfigModel):
    enabled: bool = True

    parameters: tuple[str, ...] = ()


class JsonSinkSettings(ConfigModel):
    enabled: bool = False

    path: str = Field(
        min_length=1,
    )


class DeltaSinkSettings(ConfigModel):
    enabled: bool = False

    table: str | None = Field(
        default=None,
        min_length=1,
    )
    path: str | None = None


class FileSinkSettings(ConfigModel):
    enabled: bool = False

    format: FileFormat = "text"

    delimiter: str = Field(
        default=";",
        min_length=1,
        max_length=1,
    )

    path: str = Field(
        min_length=1,
    )


class SinkSettings(ConfigModel):
    console_sink: ConsoleSinkSettings
    json_sink: JsonSinkSettings
    delta_sink: DeltaSinkSettings
    file_sink: FileSinkSettings

class monitauditConfig(ConfigModel):
    application: str = Field(
        min_length=1,
    )

    environment: Environment

    logging: LoggingSettings

    sinks: SinkSettings