# tests/models/test_sinks.py

from __future__ import annotations

import pytest
from pydantic import ValidationError

from monitaudit.models.sinks import (
    ConsoleSinkSettings,
    DeltaSinkSettings,
    FileSinkSettings,
    JsonSinkSettings,
    LoggingSettings,
    SinkSettings,
    monitauditConfig,
)


def test_logging_settings_defaults() -> None:
    settings = LoggingSettings()

    assert settings.level == "INFO"
    assert settings.timer is True
    assert settings.show_parameters is True
    assert settings.file_cycle == 10
    assert settings.max_parameter_length == 1000
    assert settings.sink_failure_mode == "continue"


@pytest.mark.parametrize(
    "level",
    [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ],
)
def test_logging_settings_accepts_valid_levels(
    level: str,
) -> None:
    settings = LoggingSettings(
        level=level,  # type: ignore[arg-type]
    )

    assert settings.level == level


def test_logging_settings_rejects_invalid_level() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            level="TRACE",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "file_cycle",
    [
        1,
        10,
        100,
    ],
)
def test_logging_settings_accepts_valid_file_cycle(
    file_cycle: int,
) -> None:
    settings = LoggingSettings(
        file_cycle=file_cycle,
    )

    assert settings.file_cycle == file_cycle


@pytest.mark.parametrize(
    "file_cycle",
    [
        0,
        101,
        -1,
    ],
)
def test_logging_settings_rejects_invalid_file_cycle(
    file_cycle: int,
) -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            file_cycle=file_cycle,
        )


@pytest.mark.parametrize(
    "max_parameter_length",
    [
        50,
        1000,
        100_000,
    ],
)
def test_logging_settings_accepts_valid_max_parameter_length(
    max_parameter_length: int,
) -> None:
    settings = LoggingSettings(
        max_parameter_length=max_parameter_length,
    )

    assert (
        settings.max_parameter_length
        == max_parameter_length
    )


@pytest.mark.parametrize(
    "max_parameter_length",
    [
        0,
        49,
        100_001,
    ],
)
def test_logging_settings_rejects_invalid_max_parameter_length(
    max_parameter_length: int,
) -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            max_parameter_length=max_parameter_length,
        )


@pytest.mark.parametrize(
    "sink_failure_mode",
    [
        "continue",
        "raise",
    ],
)
def test_logging_settings_accepts_sink_failure_modes(
    sink_failure_mode: str,
) -> None:
    settings = LoggingSettings(
        sink_failure_mode=sink_failure_mode,  # type: ignore[arg-type]
    )

    assert settings.sink_failure_mode == sink_failure_mode


def test_logging_settings_rejects_invalid_sink_failure_mode() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            sink_failure_mode="ignore",  # type: ignore[arg-type]
        )


def test_configuration_models_are_frozen() -> None:
    settings = LoggingSettings()

    with pytest.raises(ValidationError):
        settings.level = "DEBUG"  # type: ignore[misc]


def test_configuration_models_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError) as caught:
        LoggingSettings(
            unexpected=True,  # type: ignore[call-arg]
        )

    assert caught.value.errors()[0]["type"] == "extra_forbidden"


def test_console_sink_defaults() -> None:
    settings = ConsoleSinkSettings()

    assert settings.enabled is True
    assert settings.parameters == ()


def test_console_sink_accepts_parameters() -> None:
    settings = ConsoleSinkSettings(
        parameters=(
            "timestamp",
            "level",
            "message",
        ),
    )

    assert settings.parameters == (
        "timestamp",
        "level",
        "message",
    )


def test_json_sink_requires_path() -> None:
    with pytest.raises(ValidationError):
        JsonSinkSettings()  # type: ignore[call-arg]


def test_json_sink_rejects_empty_path() -> None:
    with pytest.raises(ValidationError):
        JsonSinkSettings(
            path="",
        )


def test_json_sink_defaults_to_disabled() -> None:
    settings = JsonSinkSettings(
        path="output/monitaudit.jsonl",
    )

    assert settings.enabled is False
    assert settings.path == "output/monitaudit.jsonl"


def test_file_sink_requires_path() -> None:
    with pytest.raises(ValidationError):
        FileSinkSettings()  # type: ignore[call-arg]


def test_file_sink_defaults() -> None:
    settings = FileSinkSettings(
        path="output/monitaudit.txt",
    )

    assert settings.enabled is False
    assert settings.format == "text"
    assert settings.delimiter == ";"
    assert settings.path == "output/monitaudit.txt"


@pytest.mark.parametrize(
    "file_format",
    [
        "text",
        "csv",
    ],
)
def test_file_sink_accepts_valid_formats(
    file_format: str,
) -> None:
    settings = FileSinkSettings(
        path="output/monitaudit.txt",
        format=file_format,  # type: ignore[arg-type]
    )

    assert settings.format == file_format


def test_file_sink_rejects_invalid_format() -> None:
    with pytest.raises(ValidationError):
        FileSinkSettings(
            path="output/monitaudit.txt",
            format="json",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "delimiter",
    [
        ";",
        ":",
        ",",
        "|",
        "\t",
    ],
)
def test_file_sink_accepts_single_character_delimiter(
    delimiter: str,
) -> None:
    settings = FileSinkSettings(
        path="output/monitaudit.csv",
        format="csv",
        delimiter=delimiter,
    )

    assert settings.delimiter == delimiter


@pytest.mark.parametrize(
    "delimiter",
    [
        "",
        "::",
        ";;",
    ],
)
def test_file_sink_rejects_invalid_delimiter(
    delimiter: str,
) -> None:
    with pytest.raises(ValidationError):
        FileSinkSettings(
            path="output/monitaudit.csv",
            delimiter=delimiter,
        )


def test_delta_sink_defaults() -> None:
    settings = DeltaSinkSettings()

    assert settings.enabled is False
    assert settings.table is None
    assert settings.path is None


def test_delta_sink_accepts_table() -> None:
    settings = DeltaSinkSettings(
        enabled=True,
        table="catalog.schema.monitaudit",
    )

    assert settings.enabled is True
    assert settings.table == "catalog.schema.monitaudit"


def test_delta_sink_rejects_empty_table() -> None:
    with pytest.raises(ValidationError):
        DeltaSinkSettings(
            enabled=True,
            table="",
        )


def make_sink_settings(
    *,
    file_enabled: bool = False,
    file_path: str = "output/monitaudit.txt",
    json_enabled: bool = False,
    json_path: str = "output/monitaudit.jsonl",
) -> SinkSettings:
    return SinkSettings(
        console_sink=ConsoleSinkSettings(),
        file_sink=FileSinkSettings(
            enabled=file_enabled,
            path=file_path,
        ),
        json_sink=JsonSinkSettings(
            enabled=json_enabled,
            path=json_path,
        ),
        delta_sink=DeltaSinkSettings(),
    )


def test_sink_settings_accepts_different_enabled_paths() -> None:
    settings = make_sink_settings(
        file_enabled=True,
        file_path="output/monitaudit.txt",
        json_enabled=True,
        json_path="output/monitaudit.jsonl",
    )

    assert settings.file_sink.enabled is True
    assert settings.json_sink.enabled is True


def test_sink_settings_allows_same_path_when_file_sink_disabled() -> None:
    settings = make_sink_settings(
        file_enabled=False,
        file_path="output/shared.log",
        json_enabled=True,
        json_path="output/shared.log",
    )

    assert settings.file_sink.path == settings.json_sink.path


def test_sink_settings_allows_same_path_when_json_sink_disabled() -> None:
    settings = make_sink_settings(
        file_enabled=True,
        file_path="output/shared.log",
        json_enabled=False,
        json_path="output/shared.log",
    )

    assert settings.file_sink.path == settings.json_sink.path


def test_sink_settings_rejects_same_enabled_path() -> None:
    with pytest.raises(ValidationError) as caught:
        make_sink_settings(
            file_enabled=True,
            file_path="output/shared.log",
            json_enabled=True,
            json_path="output/shared.log",
        )

    errors = caught.value.errors()

    assert len(errors) == 2

    locations = {
        error["loc"]
        for error in errors
    }

    assert locations == {
        ("file_sink", "path"),
        ("json_sink", "path"),
    }

    assert all(
        error["type"] == "sink_path_conflict"
        for error in errors
    )


def test_sink_settings_rejects_equivalent_normalized_paths() -> None:
    with pytest.raises(ValidationError) as caught:
        make_sink_settings(
            file_enabled=True,
            file_path="output/./shared.log",
            json_enabled=True,
            json_path="output/shared.log",
        )

    locations = {
        error["loc"]
        for error in caught.value.errors()
    }

    assert locations == {
        ("file_sink", "path"),
        ("json_sink", "path"),
    }


def test_sink_path_conflict_message() -> None:
    with pytest.raises(ValidationError) as caught:
        make_sink_settings(
            file_enabled=True,
            file_path="output/shared.log",
            json_enabled=True,
            json_path="output/shared.log",
        )

    errors = caught.value.errors()

    assert all(
        error["msg"]
        == "path must be different from the other enabled file sink"
        for error in errors
    )


def test_complete_monitaudit_configuration() -> None:
    config = monitauditConfig(
        application="relatics",
        environment="dev",
        logging=LoggingSettings(
            level="INFO",
            timer=True,
            show_parameters=True,
            file_cycle=10,
            max_parameter_length=1000,
            sink_failure_mode="continue",
        ),
        sinks=make_sink_settings(),
    )

    assert config.application == "relatics"
    assert config.environment == "dev"
    assert config.logging.level == "INFO"
    assert config.sinks.console_sink.enabled is True


@pytest.mark.parametrize(
    "environment",
    [
        "dev",
        "acc",
        "prod",
    ],
)
def test_configuration_accepts_valid_environments(
    environment: str,
) -> None:
    config = monitauditConfig(
        application="test",
        environment=environment,  # type: ignore[arg-type]
        logging=LoggingSettings(),
        sinks=make_sink_settings(),
    )

    assert config.environment == environment


def test_configuration_rejects_invalid_environment() -> None:
    with pytest.raises(ValidationError):
        monitauditConfig(
            application="test",
            environment="production",  # type: ignore[arg-type]
            logging=LoggingSettings(),
            sinks=make_sink_settings(),
        )


def test_configuration_rejects_empty_application() -> None:
    with pytest.raises(ValidationError):
        monitauditConfig(
            application="",
            environment="dev",
            logging=LoggingSettings(),
            sinks=make_sink_settings(),
        )


def test_complete_configuration_is_frozen() -> None:
    config = monitauditConfig(
        application="test",
        environment="dev",
        logging=LoggingSettings(),
        sinks=make_sink_settings(),
    )

    with pytest.raises(ValidationError):
        config.application = "changed"  # type: ignore[misc]