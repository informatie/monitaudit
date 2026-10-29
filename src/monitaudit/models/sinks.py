from __future__ import annotations

from copy import deepcopy
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

class ConfigModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


class LoggingSettings(ConfigModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

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

    parameters: list[str] = Field(
        default_factory=list
    )

class JsonSinkSettings(ConfigModel):
    enabled: bool = False
    path: str = Field(
        default="logs/monitaudit.jsonl",
        min_length=1,
    )


class DeltaSinkSettings(ConfigModel):
    enabled: bool = False
    table: str = Field(
        default="main.logging.monitaudit",
        min_length=1,
    )


class FileSinkSettings(ConfigModel):
    enabled: bool = False
    path: str = Field(
        default="volume/metadata/state/logs/monitaudit.log",
        min_length=1,
    )


class SinkSettings(ConfigModel):
    console_sink: ConsoleSinkSettings = Field(
        default_factory=ConsoleSinkSettings
    )

    json_sink: JsonSinkSettings = Field(
        default_factory=JsonSinkSettings
    )

    delta_sink: DeltaSinkSettings = Field(
        default_factory=DeltaSinkSettings
    )

    file_sink: FileSinkSettings = Field(
        default_factory=FileSinkSettings
    )


class EnvironmentSettings(ConfigModel):
    is_databricks: bool = False

    logging: LoggingSettings = Field(
        default_factory=LoggingSettings
    )

    sinks: SinkSettings = Field(
        default_factory=SinkSettings
    )


class EnvironmentOverride(ConfigModel):
    is_databricks: bool | None = None

    logging: dict[str, object] | None = None

    sinks: dict[str, object] | None = None


class monitauditSettings(ConfigModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    application: str = Field(
        min_length=1,
    )

    global_settings: EnvironmentSettings = Field(
        alias="global"
    )

    dev: EnvironmentOverride = Field(
        default_factory=EnvironmentOverride
    )

    acc: EnvironmentOverride = Field(
        default_factory=EnvironmentOverride
    )

    prod: EnvironmentOverride = Field(
        default_factory=EnvironmentOverride
    )

    def for_environment(
        self,
        environment: Environment,
    ) -> EnvironmentSettings:
        merged_data = deepcopy(
            self.global_settings.model_dump()
        )

        override = getattr(
            self,
            environment,
        )

        override_data = override.model_dump(
            exclude_none=True,
            exclude_unset=True,
        )

        _deep_merge(
            merged_data,
            override_data,
        )

        return EnvironmentSettings.model_validate(
            merged_data
        )


class monitauditConfig(ConfigModel):
    monitaudit: monitauditSettings


def _deep_merge(
    target: dict[str, object],
    override: dict[str, object],
) -> None:
    for key, value in override.items():
        current_value = target.get(key)

        if (
            isinstance(current_value, dict)
            and isinstance(value, dict)
        ):
            _deep_merge(
                current_value,
                value,
            )
        else:
            target[key] = value