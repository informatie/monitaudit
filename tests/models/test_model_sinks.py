# tests/models/test_sinks.py

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from monitaudit.models.sinks import (
    ConfigModel,
    ConsoleSinkSettings,
    DeltaSinkSettings,
    Environment,
    FileFormat,
    FileSinkSettings,
    JsonSinkSettings,
    LoggingSettings,
    LogLevel,
    SinkFailureMode,
    SinkSettings,
    monitauditConfig,
)


def make_sink_settings() -> SinkSettings:
    return SinkSettings(
        console_sink=ConsoleSinkSettings(),
        json_sink=JsonSinkSettings(
            path="output/log.jsonl",
        ),
        delta_sink=DeltaSinkSettings(),
        file_sink=FileSinkSettings(
            path="output/log",
        ),
    )


def make_config(
    **overrides: object,
) -> monitauditConfig:
    values: dict[str, object] = {
        "application": "test-application",
        "environment": "dev",
        "logging": LoggingSettings(),
        "sinks": make_sink_settings(),
    }

    values.update(overrides)

    return monitauditConfig(
        **values,
    )


class TestLiteralDefinitions:
    def test_environment_values(
        self,
    ) -> None:
        assert get_args(
            Environment
        ) == (
            "dev",
            "acc",
            "prod",
        )

    def test_log_level_values(
        self,
    ) -> None:
        assert get_args(
            LogLevel
        ) == (
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        )

    def test_sink_failure_mode_values(
        self,
    ) -> None:
        assert get_args(
            SinkFailureMode
        ) == (
            "continue",
            "raise",
        )

    def test_file_format_values(
        self,
    ) -> None:
        assert get_args(
            FileFormat
        ) == (
            "text",
            "csv",
        )


class TestConfigModel:
    def test_extra_fields_are_forbidden(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                unexpected="value",
            )

    def test_model_is_frozen(
        self,
    ) -> None:
        settings = LoggingSettings()

        with pytest.raises(
            ValidationError,
        ):
            settings.level = "DEBUG"

    def test_model_config_extra(
        self,
    ) -> None:
        assert (
            ConfigModel.model_config[
                "extra"
            ]
            == "forbid"
        )

    def test_model_config_frozen(
        self,
    ) -> None:
        assert (
            ConfigModel.model_config[
                "frozen"
            ]
            is True
        )


class TestLoggingSettingsDefaults:
    def test_defaults(
        self,
    ) -> None:
        settings = LoggingSettings()

        assert settings.level == "INFO"
        assert settings.timer is True
        assert (
            settings.parameters
            is True
        )
        assert (
            settings.max_parameter_length
            == 1000
        )
        assert (
            settings.sink_failure_mode
            == "continue"
        )

    def test_expected_fields(
        self,
    ) -> None:
        assert set(
            LoggingSettings.model_fields
        ) == {
            "level",
            "timer",
            "parameters",
            "max_parameter_length",
            "sink_failure_mode",
        }


class TestLoggingLevel:
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
    def test_accepts_supported_levels(
        self,
        level: str,
    ) -> None:
        settings = LoggingSettings(
            level=level,  # type: ignore[arg-type]
        )

        assert settings.level == level

    @pytest.mark.parametrize(
        "level",
        [
            "",
            "debug",
            "info",
            "WARN",
            "TRACE",
            "FATAL",
        ],
    )
    def test_rejects_unsupported_levels(
        self,
        level: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                level=level,  # type: ignore[arg-type]
            )

    def test_level_is_case_sensitive(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                level="info",  # type: ignore[arg-type]
            )


class TestLoggingBooleans:
    @pytest.mark.parametrize(
        "timer",
        [
            True,
            False,
        ],
    )
    def test_timer(
        self,
        timer: bool,
    ) -> None:
        settings = LoggingSettings(
            timer=timer,
        )

        assert (
            settings.timer
            is timer
        )

    @pytest.mark.parametrize(
        "parameters",
        [
            True,
            False,
        ],
    )
    def test_parameters(
        self,
        parameters: bool,
    ) -> None:
        settings = LoggingSettings(
            parameters=parameters,
        )

        assert (
            settings.parameters
            is parameters
        )


class TestMaximumParameterLength:
    @pytest.mark.parametrize(
        "value",
        [
            50,
            51,
            1000,
            10_000,
            100_000,
        ],
    )
    def test_accepts_valid_values(
        self,
        value: int,
    ) -> None:
        settings = LoggingSettings(
            max_parameter_length=value,
        )

        assert (
            settings.max_parameter_length
            == value
        )

    @pytest.mark.parametrize(
        "value",
        [
            -1,
            0,
            1,
            49,
        ],
    )
    def test_rejects_values_below_minimum(
        self,
        value: int,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                max_parameter_length=value,
            )

    @pytest.mark.parametrize(
        "value",
        [
            100_001,
            1_000_000,
        ],
    )
    def test_rejects_values_above_maximum(
        self,
        value: int,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                max_parameter_length=value,
            )

    def test_minimum_boundary(
        self,
    ) -> None:
        settings = LoggingSettings(
            max_parameter_length=50,
        )

        assert (
            settings.max_parameter_length
            == 50
        )

    def test_maximum_boundary(
        self,
    ) -> None:
        settings = LoggingSettings(
            max_parameter_length=100_000,
        )

        assert (
            settings.max_parameter_length
            == 100_000
        )


class TestSinkFailureMode:
    @pytest.mark.parametrize(
        "mode",
        [
            "continue",
            "raise",
        ],
    )
    def test_accepts_supported_modes(
        self,
        mode: str,
    ) -> None:
        settings = LoggingSettings(
            sink_failure_mode=mode,  # type: ignore[arg-type]
        )

        assert (
            settings.sink_failure_mode
            == mode
        )

    @pytest.mark.parametrize(
        "mode",
        [
            "",
            "CONTINUE",
            "RAISE",
            "ignore",
            "fail",
        ],
    )
    def test_rejects_unsupported_modes(
        self,
        mode: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            LoggingSettings(
                sink_failure_mode=mode,  # type: ignore[arg-type]
            )


class TestConsoleSinkSettings:
    def test_defaults(
        self,
    ) -> None:
        settings = (
            ConsoleSinkSettings()
        )

        assert (
            settings.enabled
            is True
        )
        assert (
            settings.parameters
            == ()
        )

    def test_can_be_disabled(
        self,
    ) -> None:
        settings = (
            ConsoleSinkSettings(
                enabled=False,
            )
        )

        assert (
            settings.enabled
            is False
        )

    def test_parameters_can_be_configured(
        self,
    ) -> None:
        settings = ConsoleSinkSettings(
            parameters=(
                "customer_id",
                "region",
            ),
        )

        assert settings.parameters == (
            "customer_id",
            "region",
        )

    def test_parameter_tuple_is_preserved(
        self,
    ) -> None:
        parameters = (
            "customer_id",
            "region",
        )

        settings = ConsoleSinkSettings(
            parameters=parameters,
        )

        assert (
            settings.parameters
            == parameters
        )

    def test_extra_field_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            ConsoleSinkSettings(
                unknown=True,
            )


class TestJsonSinkSettings:
    def test_default_enabled_is_false(
        self,
    ) -> None:
        settings = JsonSinkSettings(
            path="output/log.jsonl",
        )

        assert (
            settings.enabled
            is False
        )

    def test_path_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            JsonSinkSettings()

    def test_non_empty_path_is_allowed(
        self,
    ) -> None:
        settings = JsonSinkSettings(
            path="output/log.jsonl",
        )

        assert (
            settings.path
            == "output/log.jsonl"
        )

    def test_empty_path_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            JsonSinkSettings(
                path="",
            )

    def test_whitespace_path_is_currently_allowed(
        self,
    ) -> None:
        settings = JsonSinkSettings(
            path="   ",
        )

        assert settings.path == "   "

    def test_can_be_enabled(
        self,
    ) -> None:
        settings = JsonSinkSettings(
            enabled=True,
            path="output/log.jsonl",
        )

        assert settings.enabled is True


class TestDeltaSinkSettings:
    def test_defaults(
        self,
    ) -> None:
        settings = (
            DeltaSinkSettings()
        )

        assert (
            settings.enabled
            is False
        )
        assert settings.table is None
        assert settings.path is None

    def test_can_be_enabled(
        self,
    ) -> None:
        settings = DeltaSinkSettings(
            enabled=True,
            table="main.logging.events",
            path="output/delta",
        )

        assert (
            settings.enabled
            is True
        )
        assert (
            settings.table
            == "main.logging.events"
        )
        assert (
            settings.path
            == "output/delta"
        )

    def test_non_empty_table_is_allowed(
        self,
    ) -> None:
        settings = DeltaSinkSettings(
            table="main.logging.events",
        )

        assert (
            settings.table
            == "main.logging.events"
        )

    def test_empty_table_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            DeltaSinkSettings(
                table="",
            )

    def test_none_table_is_allowed(
        self,
    ) -> None:
        settings = DeltaSinkSettings(
            table=None,
        )

        assert settings.table is None

    def test_empty_path_is_currently_allowed(
        self,
    ) -> None:
        settings = DeltaSinkSettings(
            path="",
        )

        assert settings.path == ""

    def test_path_can_be_none(
        self,
    ) -> None:
        settings = DeltaSinkSettings(
            path=None,
        )

        assert settings.path is None


class TestFileSinkSettings:
    def test_path_is_required(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            FileSinkSettings()

    def test_defaults(
        self,
    ) -> None:
        settings = FileSinkSettings(
            path="output/application",
        )

        assert (
            settings.enabled
            is False
        )
        assert (
            settings.format
            == "text"
        )
        assert settings.delimiter == ";"

    def test_can_be_enabled(
        self,
    ) -> None:
        settings = FileSinkSettings(
            enabled=True,
            path="output/application",
        )

        assert settings.enabled is True

    @pytest.mark.parametrize(
        "format_value",
        [
            "text",
            "csv",
        ],
    )
    def test_accepts_supported_formats(
        self,
        format_value: str,
    ) -> None:
        settings = FileSinkSettings(
            path="output/application",
            format=format_value,  # type: ignore[arg-type]
        )

        assert (
            settings.format
            == format_value
        )

    @pytest.mark.parametrize(
        "format_value",
        [
            "",
            "TEXT",
            "CSV",
            "json",
        ],
    )
    def test_rejects_unsupported_formats(
        self,
        format_value: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            FileSinkSettings(
                path="output/application",
                format=format_value,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "delimiter",
        [
            ";",
            ",",
            "|",
            "\t",
            "\n",
        ],
    )
    def test_single_character_delimiters_are_allowed_by_model(
        self,
        delimiter: str,
    ) -> None:
        settings = FileSinkSettings(
            path="output/application",
            delimiter=delimiter,
        )

        assert (
            settings.delimiter
            == delimiter
        )

    @pytest.mark.parametrize(
        "delimiter",
        [
            "",
            ";;",
            "ab",
        ],
    )
    def test_invalid_delimiter_length_is_rejected(
        self,
        delimiter: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            FileSinkSettings(
                path="output/application",
                delimiter=delimiter,
            )

    def test_empty_path_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            FileSinkSettings(
                path="",
            )

    def test_whitespace_path_is_currently_allowed(
        self,
    ) -> None:
        settings = FileSinkSettings(
            path=" ",
        )

        assert settings.path == " "


class TestSinkSettings:
    def test_complete_sink_settings(
        self,
    ) -> None:
        console = (
            ConsoleSinkSettings()
        )
        json_sink = JsonSinkSettings(
            path="output/log.jsonl",
        )
        delta = DeltaSinkSettings()
        file_sink = FileSinkSettings(
            path="output/log",
        )

        settings = SinkSettings(
            console_sink=console,
            json_sink=json_sink,
            delta_sink=delta,
            file_sink=file_sink,
        )

        assert (
            settings.console_sink
            is console
        )
        assert (
            settings.json_sink
            is json_sink
        )
        assert (
            settings.delta_sink
            is delta
        )
        assert (
            settings.file_sink
            is file_sink
        )

    @pytest.mark.parametrize(
        "missing_field",
        [
            "console_sink",
            "json_sink",
            "delta_sink",
            "file_sink",
        ],
    )
    def test_all_sink_sections_are_required(
        self,
        missing_field: str,
    ) -> None:
        values = {
            "console_sink": (
                ConsoleSinkSettings()
            ),
            "json_sink": (
                JsonSinkSettings(
                    path="output/log.jsonl",
                )
            ),
            "delta_sink": (
                DeltaSinkSettings()
            ),
            "file_sink": (
                FileSinkSettings(
                    path="output/log",
                )
            ),
        }

        del values[
            missing_field
        ]

        with pytest.raises(
            ValidationError,
        ):
            SinkSettings(
                **values,
            )

    def test_expected_fields(
        self,
    ) -> None:
        assert set(
            SinkSettings.model_fields
        ) == {
            "console_sink",
            "json_sink",
            "delta_sink",
            "file_sink",
        }


class TestMonitauditConfig:
    def test_complete_config(
        self,
    ) -> None:
        logging = LoggingSettings()
        sinks = make_sink_settings()

        config = monitauditConfig(
            application="monitaudit-example",
            environment="dev",
            logging=logging,
            sinks=sinks,
        )

        assert (
            config.application
            == "monitaudit-example"
        )
        assert (
            config.environment
            == "dev"
        )
        assert config.logging is logging
        assert config.sinks is sinks

    @pytest.mark.parametrize(
        "environment",
        [
            "dev",
            "acc",
            "prod",
        ],
    )
    def test_accepts_supported_environments(
        self,
        environment: str,
    ) -> None:
        config = make_config(
            environment=environment,
        )

        assert (
            config.environment
            == environment
        )

    @pytest.mark.parametrize(
        "environment",
        [
            "",
            "DEV",
            "ACC",
            "PROD",
            "test",
            "local",
            "qa",
        ],
    )
    def test_rejects_unsupported_environments(
        self,
        environment: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_config(
                environment=environment,
            )

    def test_empty_application_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            make_config(
                application="",
            )

    def test_single_character_application_is_allowed(
        self,
    ) -> None:
        config = make_config(
            application="a",
        )

        assert config.application == "a"

    def test_whitespace_application_is_currently_allowed(
        self,
    ) -> None:
        config = make_config(
            application="   ",
        )

        assert config.application == "   "

    @pytest.mark.parametrize(
        "missing_field",
        [
            "application",
            "environment",
            "logging",
            "sinks",
        ],
    )
    def test_required_fields(
        self,
        missing_field: str,
    ) -> None:
        values: dict[
            str,
            object,
        ] = {
            "application": (
                "test-application"
            ),
            "environment": "dev",
            "logging": (
                LoggingSettings()
            ),
            "sinks": (
                make_sink_settings()
            ),
        }

        del values[
            missing_field
        ]

        with pytest.raises(
            ValidationError,
        ):
            monitauditConfig(
                **values,
            )

    def test_extra_fields_are_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            monitauditConfig(
                application=(
                    "test-application"
                ),
                environment="dev",
                logging=LoggingSettings(),
                sinks=make_sink_settings(),
                unexpected="value",
            )

    def test_config_is_frozen(
        self,
    ) -> None:
        config = make_config()

        with pytest.raises(
            ValidationError,
        ):
            config.application = "changed"

    def test_expected_fields(
        self,
    ) -> None:
        assert set(
            monitauditConfig.model_fields
        ) == {
            "application",
            "environment",
            "logging",
            "sinks",
        }


class TestNestedValidation:
    def test_constructs_nested_models_from_dictionaries(
        self,
    ) -> None:
        config = (
            monitauditConfig.model_validate(
                {
                    "application": (
                        "test-application"
                    ),
                    "environment": "dev",
                    "logging": {
                        "level": "DEBUG",
                        "timer": False,
                        "parameters": True,
                        "max_parameter_length": 500,
                        "sink_failure_mode": "raise",
                    },
                    "sinks": {
                        "console_sink": {
                            "enabled": True,
                            "parameters": [
                                "customer_id",
                            ],
                        },
                        "json_sink": {
                            "enabled": True,
                            "path": (
                                "output/log.jsonl"
                            ),
                        },
                        "delta_sink": {
                            "enabled": False,
                            "table": None,
                            "path": None,
                        },
                        "file_sink": {
                            "enabled": True,
                            "format": "csv",
                            "delimiter": ";",
                            "path": "output/log",
                        },
                    },
                }
            )
        )

        assert isinstance(
            config.logging,
            LoggingSettings,
        )
        assert isinstance(
            config.sinks,
            SinkSettings,
        )
        assert isinstance(
            config.sinks.console_sink,
            ConsoleSinkSettings,
        )
        assert isinstance(
            config.sinks.json_sink,
            JsonSinkSettings,
        )
        assert isinstance(
            config.sinks.delta_sink,
            DeltaSinkSettings,
        )
        assert isinstance(
            config.sinks.file_sink,
            FileSinkSettings,
        )

        assert (
            config.logging.level
            == "DEBUG"
        )
        assert (
            config.logging.timer
            is False
        )
        assert (
            config.logging.max_parameter_length
            == 500
        )
        assert (
            config.logging.sink_failure_mode
            == "raise"
        )
        assert (
            config.sinks.console_sink.parameters
            == (
                "customer_id",
            )
        )

    def test_nested_extra_field_is_rejected(
        self,
    ) -> None:
        values = {
            "application": "test",
            "environment": "dev",
            "logging": {
                "unexpected": True,
            },
            "sinks": {
                "console_sink": {},
                "json_sink": {
                    "path": "output/log.jsonl",
                },
                "delta_sink": {},
                "file_sink": {
                    "path": "output/log",
                },
            },
        }

        with pytest.raises(
            ValidationError,
        ) as exception_info:
            monitauditConfig.model_validate(
                values
            )

        assert any(
            error["loc"]
            == (
                "logging",
                "unexpected",
            )
            for error
            in exception_info.value.errors()
        )


class TestSerialisation:
    def test_logging_settings_model_dump(
        self,
    ) -> None:
        settings = LoggingSettings()

        assert (
            settings.model_dump()
            == {
                "level": "INFO",
                "timer": True,
                "parameters": True,
                "max_parameter_length": 1000,
                "sink_failure_mode": "continue",
            }
        )

    def test_complete_config_model_dump(
        self,
    ) -> None:
        config = make_config(
            application="app",
            environment="prod",
        )

        result = config.model_dump()

        assert (
            result["application"]
            == "app"
        )
        assert (
            result["environment"]
            == "prod"
        )
        assert (
            result["logging"]["level"]
            == "INFO"
        )
        assert (
            result["sinks"][
                "console_sink"
            ]["enabled"]
            is True
        )

    def test_complete_config_json_serialisation(
        self,
    ) -> None:
        config = make_config()

        result = (
            config.model_dump_json()
        )

        assert isinstance(
            result,
            str,
        )
        assert (
            '"application":"test-application"'
            in result
        )
        assert (
            '"environment":"dev"'
            in result
        )


class TestCurrentModelBoundaries:
    def test_file_model_allows_newline_delimiter(
        self,
    ) -> None:
        """
        FileSink itself rejects newline delimiters, but FileSinkSettings only
        constrains delimiter length. This test records the current model
        contract.
        """

        settings = FileSinkSettings(
            path="output/log",
            format="csv",
            delimiter="\n",
        )

        assert (
            settings.delimiter
            == "\n"
        )

    def test_enabled_delta_sink_does_not_require_table_at_model_level(
        self,
    ) -> None:
        """
        The model allows enabled=True with table=None. Validation of that
        combination currently occurs in build_monitaudit().
        """

        settings = DeltaSinkSettings(
            enabled=True,
            table=None,
            path=None,
        )

        assert (
            settings.enabled
            is True
        )
        assert settings.table is None
        assert settings.path is None

    def test_json_sink_path_required_even_when_disabled(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            JsonSinkSettings(
                enabled=False,
            )

    def test_file_sink_path_required_even_when_disabled(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
        ):
            FileSinkSettings(
                enabled=False,
            )