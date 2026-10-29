from __future__ import annotations

import pytest
from pydantic import ValidationError

from monitaudit.models.sinks import (
    ConfigModel,
    ConsoleSinkSettings,
    DeltaSinkSettings,
    EnvironmentOverride,
    EnvironmentSettings,
    FileSinkSettings,
    JsonSinkSettings,
    LoggingSettings,
    monitauditConfig,
    monitauditSettings,
    SinkSettings,
    _deep_merge,
)


def make_monitaudit_settings(
    **kwargs: object,
) -> monitauditSettings:
    data: dict[str, object] = {
        "application": "monitaudit-test",
        "global": {},
    }

    data.update(kwargs)

    return monitauditSettings.model_validate(data)


def test_config_model_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ConfigModel(
            unknown="value",
        )


def test_logging_settings_defaults() -> None:
    settings = LoggingSettings()

    assert settings.level == "INFO"
    assert settings.timer is True
    assert settings.parameters is True
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
def test_valid_log_levels(
    level: str,
) -> None:
    settings = LoggingSettings(
        level=level,  # type: ignore[arg-type]
    )

    assert settings.level == level


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            level="INVALID",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "mode",
    [
        "continue",
        "raise",
    ],
)
def test_valid_sink_failure_modes(
    mode: str,
) -> None:
    settings = LoggingSettings(
        sink_failure_mode=mode,  # type: ignore[arg-type]
    )

    assert settings.sink_failure_mode == mode


def test_invalid_sink_failure_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            sink_failure_mode="invalid",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "max_length",
    [
        50,
        1000,
        100_000,
    ],
)
def test_valid_max_parameter_length(
    max_length: int,
) -> None:
    settings = LoggingSettings(
        max_parameter_length=max_length,
    )

    assert settings.max_parameter_length == max_length


@pytest.mark.parametrize(
    "max_length",
    [
        0,
        49,
        100_001,
    ],
)
def test_invalid_max_parameter_length(
    max_length: int,
) -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            max_parameter_length=max_length,
        )


def test_logging_settings_are_frozen() -> None:
    settings = LoggingSettings()

    with pytest.raises(ValidationError):
        settings.level = "ERROR"  # type: ignore[misc]


def test_logging_settings_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(
            unknown="value",
        )


def test_console_sink_defaults() -> None:
    settings = ConsoleSinkSettings()

    assert settings.enabled is True


def test_json_sink_defaults() -> None:
    settings = JsonSinkSettings()

    assert settings.enabled is False
    assert settings.path == "logs/monitaudit.jsonl"


def test_json_sink_rejects_empty_path() -> None:
    with pytest.raises(ValidationError):
        JsonSinkSettings(
            path="",
        )


def test_delta_sink_defaults() -> None:
    settings = DeltaSinkSettings()

    assert settings.enabled is False

    assert (
        settings.table
        == "main.logging.monitaudit"
    )


def test_delta_sink_rejects_empty_table() -> None:
    with pytest.raises(ValidationError):
        DeltaSinkSettings(
            table="",
        )


def test_file_sink_defaults() -> None:
    settings = FileSinkSettings()

    assert settings.enabled is False

    assert settings.path == (
        "volume/metadata/state/logs/"
        "monitaudit.log"
    )


def test_file_sink_rejects_empty_path() -> None:
    with pytest.raises(ValidationError):
        FileSinkSettings(
            path="",
        )


def test_sink_settings_defaults() -> None:
    settings = SinkSettings()

    assert settings.console_sink.enabled is True

    assert (
        settings.json_sink.enabled
        is False
    )

    assert (
        settings.delta_sink.enabled
        is False
    )

    assert (
        settings.file_sink.enabled
        is False
    )


def test_sink_default_instances_are_independent() -> None:
    first = SinkSettings()
    second = SinkSettings()

    assert (
        first.console_sink
        is not second.console_sink
    )

    assert (
        first.json_sink
        is not second.json_sink
    )

    assert (
        first.delta_sink
        is not second.delta_sink
    )

    assert (
        first.file_sink
        is not second.file_sink
    )


def test_environment_settings_defaults() -> None:
    settings = EnvironmentSettings()

    assert settings.is_databricks is False

    assert isinstance(
        settings.logging,
        LoggingSettings,
    )

    assert isinstance(
        settings.sinks,
        SinkSettings,
    )


def test_environment_default_instances_are_independent() -> None:
    first = EnvironmentSettings()
    second = EnvironmentSettings()

    assert first.logging is not second.logging
    assert first.sinks is not second.sinks


def test_environment_override_defaults() -> None:
    override = EnvironmentOverride()

    assert override.is_databricks is None
    assert override.logging is None
    assert override.sinks is None


def test_monitaudit_application_is_required() -> None:
    with pytest.raises(ValidationError):
        monitauditSettings.model_validate(
            {
                "global": {},
            }
        )


def test_monitaudit_application_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        monitauditSettings.model_validate(
            {
                "application": "",
                "global": {},
            }
        )


def test_global_settings_are_required() -> None:
    with pytest.raises(ValidationError):
        monitauditSettings(
            application="monitaudit-test",
        )


def test_global_alias_is_accepted() -> None:
    settings = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "is_databricks": True,
            },
        }
    )

    assert (
        settings.global_settings.is_databricks
        is True
    )


def test_global_settings_field_name_is_accepted() -> None:
    settings = monitauditSettings(
        application="monitaudit-test",
        global_settings=EnvironmentSettings(
            is_databricks=True,
        ),
    )

    assert (
        settings.global_settings.is_databricks
        is True
    )


def test_environment_overrides_default_empty() -> None:
    settings = make_monitaudit_settings()

    assert settings.dev == EnvironmentOverride()
    assert settings.acc == EnvironmentOverride()
    assert settings.prod == EnvironmentOverride()


def test_monitaudit_settings_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        monitauditSettings.model_validate(
            {
                "application": "monitaudit-test",
                "global": {},
                "unknown": True,
            }
        )


def test_for_environment_returns_global_settings_without_override() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "is_databricks": False,
                "logging": {
                    "level": "WARNING",
                    "timer": False,
                    "parameters": False,
                    "max_parameter_length": 500,
                    "sink_failure_mode": "raise",
                },
                "sinks": {
                    "console_sink": {
                        "enabled": False,
                    },
                    "json_sink": {
                        "enabled": True,
                        "path": "logs/custom.jsonl",
                    },
                },
            },
        }
    )

    settings = monitaudit.for_environment(
        "dev"
    )

    assert settings.is_databricks is False
    assert settings.logging.level == "WARNING"
    assert settings.logging.timer is False
    assert settings.logging.parameters is False

    assert (
        settings.logging.max_parameter_length
        == 500
    )

    assert (
        settings.logging.sink_failure_mode
        == "raise"
    )

    assert (
        settings.sinks.console_sink.enabled
        is False
    )

    assert (
        settings.sinks.json_sink.enabled
        is True
    )

    assert (
        settings.sinks.json_sink.path
        == "logs/custom.jsonl"
    )


def test_environment_override_replaces_scalar() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "is_databricks": False,
            },
            "prod": {
                "is_databricks": True,
            },
        }
    )

    settings = monitaudit.for_environment(
        "prod"
    )

    assert settings.is_databricks is True


def test_logging_override_is_deep_merged() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "logging": {
                    "level": "INFO",
                    "timer": True,
                    "parameters": True,
                    "max_parameter_length": 1000,
                    "sink_failure_mode": "continue",
                },
            },
            "prod": {
                "logging": {
                    "level": "ERROR",
                },
            },
        }
    )

    settings = monitaudit.for_environment(
        "prod"
    )

    assert settings.logging.level == "ERROR"
    assert settings.logging.timer is True
    assert settings.logging.parameters is True

    assert (
        settings.logging.max_parameter_length
        == 1000
    )

    assert (
        settings.logging.sink_failure_mode
        == "continue"
    )


def test_sink_override_is_deep_merged() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "sinks": {
                    "console_sink": {
                        "enabled": True,
                    },
                    "json_sink": {
                        "enabled": False,
                        "path": "logs/monitaudit.jsonl",
                    },
                },
            },
            "prod": {
                "sinks": {
                    "json_sink": {
                        "enabled": True,
                    },
                },
            },
        }
    )

    settings = monitaudit.for_environment(
        "prod"
    )

    assert (
        settings.sinks.console_sink.enabled
        is True
    )

    assert (
        settings.sinks.json_sink.enabled
        is True
    )

    assert (
        settings.sinks.json_sink.path
        == "logs/monitaudit.jsonl"
    )


def test_override_does_not_mutate_global_settings() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "logging": {
                    "level": "INFO",
                },
            },
            "prod": {
                "logging": {
                    "level": "ERROR",
                },
            },
        }
    )

    prod = monitaudit.for_environment(
        "prod"
    )

    dev = monitaudit.for_environment(
        "dev"
    )

    assert prod.logging.level == "ERROR"
    assert dev.logging.level == "INFO"

    assert (
        monitaudit.global_settings.logging.level
        == "INFO"
    )


def test_environment_results_are_independent() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {
                "logging": {
                    "level": "INFO",
                },
            },
            "acc": {
                "logging": {
                    "level": "WARNING",
                },
            },
            "prod": {
                "logging": {
                    "level": "ERROR",
                },
            },
        }
    )

    dev = monitaudit.for_environment(
        "dev"
    )

    acc = monitaudit.for_environment(
        "acc"
    )

    prod = monitaudit.for_environment(
        "prod"
    )

    assert dev.logging.level == "INFO"
    assert acc.logging.level == "WARNING"
    assert prod.logging.level == "ERROR"


def test_invalid_override_is_validated_after_merge() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {},
            "prod": {
                "logging": {
                    "level": "INVALID",
                },
            },
        }
    )

    with pytest.raises(ValidationError):
        monitaudit.for_environment(
            "prod"
        )


def test_invalid_nested_override_field_is_rejected_after_merge() -> None:
    monitaudit = monitauditSettings.model_validate(
        {
            "application": "monitaudit-test",
            "global": {},
            "prod": {
                "logging": {
                    "unknown": True,
                },
            },
        }
    )

    with pytest.raises(ValidationError):
        monitaudit.for_environment(
            "prod"
        )


def test_monitaudit_config() -> None:
    config = monitauditConfig.model_validate(
        {
            "monitaudit": {
                "application": "monitaudit-test",
                "global": {},
            },
        }
    )

    assert (
        config.monitaudit.application
        == "monitaudit-test"
    )


def test_monitaudit_config_requires_monitaudit() -> None:
    with pytest.raises(ValidationError):
        monitauditConfig.model_validate(
            {}
        )


def test_monitaudit_config_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        monitauditConfig.model_validate(
            {
                "monitaudit": {
                    "application": "monitaudit-test",
                    "global": {},
                },
                "unknown": True,
            }
        )


def test_deep_merge_replaces_scalar() -> None:
    target: dict[str, object] = {
        "level": "INFO",
    }

    override: dict[str, object] = {
        "level": "ERROR",
    }

    _deep_merge(
        target,
        override,
    )

    assert target == {
        "level": "ERROR",
    }


def test_deep_merge_merges_nested_dictionary() -> None:
    target: dict[str, object] = {
        "logging": {
            "level": "INFO",
            "timer": True,
        },
    }

    override: dict[str, object] = {
        "logging": {
            "level": "ERROR",
        },
    }

    _deep_merge(
        target,
        override,
    )

    assert target == {
        "logging": {
            "level": "ERROR",
            "timer": True,
        },
    }


def test_deep_merge_adds_new_value() -> None:
    target: dict[str, object] = {
        "existing": True,
    }

    override: dict[str, object] = {
        "new": "value",
    }

    _deep_merge(
        target,
        override,
    )

    assert target == {
        "existing": True,
        "new": "value",
    }


def test_deep_merge_replaces_dictionary_with_scalar() -> None:
    target: dict[str, object] = {
        "value": {
            "nested": True,
        },
    }

    override: dict[str, object] = {
        "value": "replacement",
    }

    _deep_merge(
        target,
        override,
    )

    assert target == {
        "value": "replacement",
    }


def test_deep_merge_replaces_scalar_with_dictionary() -> None:
    target: dict[str, object] = {
        "value": "original",
    }

    override: dict[str, object] = {
        "value": {
            "nested": True,
        },
    }

    _deep_merge(
        target,
        override,
    )

    assert target == {
        "value": {
            "nested": True,
        },
    }