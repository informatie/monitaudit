# src/monitaudit/models/sinks.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, ValidationError
from pathlib import Path
from typing import Self
from pydantic_core import PydanticCustomError

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

    file_cycle: int = Field(
        default=10,
        ge=1,
        le=100,
    )

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


class SinkSettings(BaseModel):
    console_sink: ConsoleSinkSettings
    file_sink: FileSinkSettings
    json_sink: JsonSinkSettings
    delta_sink: DeltaSinkSettings

    @model_validator(mode="after")
    def validate_sink_paths(self) -> Self:
        if not (
            self.file_sink.enabled
            and self.json_sink.enabled
        ):
            return self

        file_path = Path(
            self.file_sink.path
        ).expanduser().resolve(strict=False)

        json_path = Path(
            self.json_sink.path
        ).expanduser().resolve(strict=False)

        if file_path != json_path:
            return self

        error = PydanticCustomError(
            "sink_path_conflict",
            "path must be different from the other enabled file sink",
        )

        raise ValidationError.from_exception_data(
            self.__class__.__name__,
            [
                {
                    "type": error,
                    "loc": ("file_sink", "path"),
                    "input": self.file_sink.path,
                },
                {
                    "type": error,
                    "loc": ("json_sink", "path"),
                    "input": self.json_sink.path,
                },
            ],
        )
    
class monitauditConfig(ConfigModel):
    application: str = Field(
        min_length=1,
    )

    environment: Environment

    logging: LoggingSettings

    sinks: SinkSettings