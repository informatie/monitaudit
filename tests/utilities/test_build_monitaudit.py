# tests/utilities/test_build_monitaudit.py

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

build_module = importlib.import_module(
    "monitaudit.utilities.build_monitaudit"
)

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


@dataclass
class ConstructedSink:
    """Representation of a sink created by a mocked constructor."""

    sink_type: str
    arguments: dict[str, Any]


class SinkFactory:
    """Callable test double that records sink construction."""

    def __init__(
        self,
        sink_type: str,
    ) -> None:
        self.sink_type = sink_type
        self.calls: list[dict[str, Any]] = []
        self.instances: list[ConstructedSink] = []

    def __call__(
        self,
        **kwargs: Any,
    ) -> ConstructedSink:
        arguments = dict(kwargs)

        self.calls.append(
            arguments
        )

        instance = ConstructedSink(
            sink_type=self.sink_type,
            arguments=arguments,
        )

        self.instances.append(
            instance
        )

        return instance


class MonitauditFactory:
    """Callable test double that records Monitaudit construction."""

    def __init__(
        self,
    ) -> None:
        self.calls: list[
            tuple[
                tuple[Any, ...],
                dict[str, Any],
            ]
        ] = []

        self.instance = object()

    def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> object:
        self.calls.append(
            (
                args,
                dict(kwargs),
            )
        )

        return self.instance


@dataclass
class Factories:
    console: SinkFactory
    file: SinkFactory
    json: SinkFactory
    delta: SinkFactory
    monitaudit: MonitauditFactory


def make_config(
    *,
    console_enabled: bool = False,
    file_enabled: bool = False,
    json_enabled: bool = False,
    delta_enabled: bool = False,
    delta_table: str | None = None,
    delta_path: str | Path | None = None,
    application: str = "test-application",
    environment: str = "test",
    timer: bool = True,
    parameters: bool = True,
    max_parameter_length: int = 1000,
    sink_failure_mode: str = "continue",
    file_cycle: int = 10,
) -> SimpleNamespace:
    """Build a configuration consumed by build_monitaudit()."""

    return SimpleNamespace(
        application=application,
        environment=environment,
        logging=SimpleNamespace(
            timer=timer,
            parameters=parameters,
            max_parameter_length=max_parameter_length,
            sink_failure_mode=sink_failure_mode,
            file_cycle=file_cycle,
        ),
        sinks=SimpleNamespace(
            console_sink=SimpleNamespace(
                enabled=console_enabled,
                parameters=True,
            ),
            file_sink=SimpleNamespace(
                enabled=file_enabled,
                path=Path(
                    "output/file_sink/application.log"
                ),
                format="text",
                delimiter=" | ",
            ),
            json_sink=SimpleNamespace(
                enabled=json_enabled,
                path=Path(
                    "output/json_sink/application.jsonl"
                ),
            ),
            delta_sink=SimpleNamespace(
                enabled=delta_enabled,
                table=delta_table,
                path=delta_path,
            ),
        ),
    )


@pytest.fixture
def factories(
    monkeypatch: pytest.MonkeyPatch,
) -> Factories:
    console_factory = SinkFactory(
        "ConsoleSink"
    )
    file_factory = SinkFactory(
        "FileSink"
    )
    json_factory = SinkFactory(
        "JsonSink"
    )
    delta_factory = SinkFactory(
        "DeltaSink"
    )
    monitaudit_factory = (
        MonitauditFactory()
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        console_factory,
    )
    monkeypatch.setattr(
        build_module,
        "FileSink",
        file_factory,
    )
    monkeypatch.setattr(
        build_module,
        "JsonSink",
        json_factory,
    )
    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        delta_factory,
    )
    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        monitaudit_factory,
    )

    return Factories(
        console=console_factory,
        file=file_factory,
        json=json_factory,
        delta=delta_factory,
        monitaudit=monitaudit_factory,
    )


def configure_loaded_config(
    monkeypatch: pytest.MonkeyPatch,
    config: SimpleNamespace,
) -> list[str | Path | None]:
    """Install a load_config test double and return its call list."""

    calls: list[
        str | Path | None
    ] = []

    def fake_load_config(
        config_path: str | Path | None = None,
    ) -> SimpleNamespace:
        calls.append(
            config_path
        )

        return config

    monkeypatch.setattr(
        build_module,
        "load_config",
        fake_load_config,
    )

    return calls


class TestConfigurationLoading:
    @pytest.mark.parametrize(
        "config_path",
        [
            None,
            "config/application.yaml",
            Path(
                "config/application.yaml"
            ),
        ],
    )
    def test_passes_config_path_to_load_config(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
        config_path: str | Path | None,
    ) -> None:
        config = make_config()

        load_calls = configure_loaded_config(
            monkeypatch,
            config,
        )

        result = build_monitaudit(
            config_path
        )

        assert load_calls == [
            config_path,
        ]

        assert (
            result
            is factories.monitaudit.instance
        )

    def test_does_not_transform_path_before_loading(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config()

        config_path = Path(
            "../configuration/runtime"
        )

        load_calls = configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit(
            config_path
        )

        assert (
            load_calls[0]
            is config_path
        )

    def test_propagates_configuration_loading_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected_exception = RuntimeError(
            "configuration could not be loaded"
        )

        def failing_load_config(
            _config_path: str | Path | None = None,
        ) -> SimpleNamespace:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "load_config",
            failing_load_config,
        )

        with pytest.raises(
            RuntimeError,
        ) as exception_info:
            build_monitaudit(
                "config/missing.yaml"
            )

        assert (
            exception_info.value
            is expected_exception
        )


class TestMonitauditConstruction:
    def test_builds_monitaudit_without_sinks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config()

        configure_loaded_config(
            monkeypatch,
            config,
        )

        result = build_monitaudit()

        assert (
            result
            is factories.monitaudit.instance
        )

        assert factories.monitaudit.calls == [
            (
                (
                    "test-application",
                    "test",
                ),
                {
                    "timer": True,
                    "parameters": True,
                    "max_parameter_length": 1000,
                    "sink_failure_mode": "continue",
                },
            )
        ]

    def test_passes_logging_configuration(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            application="orders-application",
            environment="production",
            timer=False,
            parameters=False,
            max_parameter_length=250,
            sink_failure_mode="raise",
            file_cycle=45,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.monitaudit.calls == [
            (
                (
                    "orders-application",
                    "production",
                ),
                {
                    "timer": False,
                    "parameters": False,
                    "max_parameter_length": 250,
                    "sink_failure_mode": "raise",
                },
            )
        ]

    def test_file_cycle_is_not_passed_to_monitaudit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_cycle=30,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        _, kwargs = (
            factories.monitaudit.calls[0]
        )

        assert (
            "file_cycle"
            not in kwargs
        )

    def test_returns_value_created_by_monitaudit_constructor(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config()

        configure_loaded_config(
            monkeypatch,
            config,
        )

        result = build_monitaudit()

        assert (
            result
            is factories.monitaudit.instance
        )

    def test_propagates_monitaudit_construction_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config()

        expected_exception = ValueError(
            "invalid Monitaudit configuration"
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        def failing_monitaudit(
            *_args: Any,
            **_kwargs: Any,
        ) -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "Monitaudit",
            failing_monitaudit,
        )

        with pytest.raises(
            ValueError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )


class TestConsoleSink:
    def test_creates_enabled_console_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=True,
        )

        config.sinks.console_sink.parameters = False

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.console.calls == [
            {
                "parameters": False,
            }
        ]

        monitaudit_args, _ = (
            factories.monitaudit.calls[0]
        )

        assert monitaudit_args == (
            "test-application",
            "test",
            factories.console.instances[0],
        )

    def test_file_cycle_is_not_passed_to_console_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=True,
            file_cycle=25,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.console.calls == [
            {
                "parameters": True,
            }
        ]

    def test_does_not_create_disabled_console_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=False,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.console.calls == []


class TestFileSink:
    def test_creates_enabled_file_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=True,
            file_cycle=30,
        )

        config.sinks.file_sink.path = Path(
            "logs/monitaudit.log"
        )
        config.sinks.file_sink.format = "text"
        config.sinks.file_sink.delimiter = ";"

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.file.calls == [
            {
                "path": Path(
                    "logs/monitaudit.log"
                ),
                "format": "text",
                "delimiter": ";",
                "file_cycle": 30,
            }
        ]

        monitaudit_args, _ = (
            factories.monitaudit.calls[0]
        )

        assert monitaudit_args == (
            "test-application",
            "test",
            factories.file.instances[0],
        )

    def test_passes_default_file_cycle_to_file_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=True,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert (
            factories.file.calls[0][
                "file_cycle"
            ]
            == 10
        )

    def test_passes_custom_file_cycle_to_file_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=True,
            file_cycle=45,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert (
            factories.file.calls[0][
                "file_cycle"
            ]
            == 45
        )

    def test_does_not_create_disabled_file_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=False,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.file.calls == []

    def test_propagates_file_sink_construction_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=True,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        expected_exception = OSError(
            "cannot create log file"
        )

        def failing_file_sink(
            **_kwargs: Any,
        ) -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "FileSink",
            failing_file_sink,
        )

        with pytest.raises(
            OSError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )
        assert factories.monitaudit.calls == []


class TestJsonSink:
    def test_creates_enabled_json_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            json_enabled=True,
            file_cycle=30,
        )

        config.sinks.json_sink.path = Path(
            "logs/monitaudit.jsonl"
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.json.calls == [
            {
                "path": Path(
                    "logs/monitaudit.jsonl"
                ),
                "file_cycle": 30,
            }
        ]

        monitaudit_args, _ = (
            factories.monitaudit.calls[0]
        )

        assert monitaudit_args == (
            "test-application",
            "test",
            factories.json.instances[0],
        )

    def test_passes_default_file_cycle_to_json_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            json_enabled=True,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert (
            factories.json.calls[0][
                "file_cycle"
            ]
            == 10
        )

    def test_passes_custom_file_cycle_to_json_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            json_enabled=True,
            file_cycle=45,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert (
            factories.json.calls[0][
                "file_cycle"
            ]
            == 45
        )

    def test_does_not_create_disabled_json_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            json_enabled=False,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.json.calls == []

    def test_propagates_json_sink_construction_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            json_enabled=True,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        expected_exception = OSError(
            "cannot create JSON log file"
        )

        def failing_json_sink(
            **_kwargs: Any,
        ) -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "JsonSink",
            failing_json_sink,
        )

        with pytest.raises(
            OSError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )
        assert factories.monitaudit.calls == []


class TestFileCyclePropagation:
    def test_same_file_cycle_is_passed_to_file_and_json_sinks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            file_enabled=True,
            json_enabled=True,
            file_cycle=25,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert (
            factories.file.calls[0][
                "file_cycle"
            ]
            == 25
        )

        assert (
            factories.json.calls[0][
                "file_cycle"
            ]
            == 25
        )

    def test_file_cycle_is_not_passed_to_non_file_sinks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=True,
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path="output/delta",
            file_cycle=25,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        spark = object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            lambda: spark,
        )

        build_monitaudit()

        assert factories.console.calls == [
            {
                "parameters": True,
            }
        ]

        assert factories.delta.calls == [
            {
                "table": "main.delta.local",
                "path": "output/delta",
                "spark": spark,
                "is_databricks": False,
            }
        ]


class TestDeltaSinkValidation:
    def test_requires_table_when_delta_sink_is_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table=None,
            delta_path=Path(
                "output/delta/application"
            ),
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        with pytest.raises(
            ValueError,
            match=(
                "^Delta sink is enabled but "
                "no table is configured\\.$"
            ),
        ):
            build_monitaudit()

        assert factories.delta.calls == []
        assert factories.monitaudit.calls == []

    def test_requires_path_when_delta_sink_is_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table=(
                "main.logging.application"
            ),
            delta_path=None,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        with pytest.raises(
            ValueError,
            match=(
                "^Delta sink is enabled but "
                "no path is configured\\.$"
            ),
        ):
            build_monitaudit()

        assert factories.delta.calls == []
        assert factories.monitaudit.calls == []

    def test_table_validation_occurs_before_path_validation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table=None,
            delta_path=None,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        with pytest.raises(
            ValueError,
        ) as exception_info:
            build_monitaudit()

        assert (
            str(exception_info.value)
            == (
                "Delta sink is enabled but no table "
                "is configured."
            )
        )

    def test_delta_settings_are_not_validated_when_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=False,
            delta_table=None,
            delta_path=None,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        result = build_monitaudit()

        assert (
            result
            is factories.monitaudit.instance
        )
        assert factories.delta.calls == []


class TestLocalDeltaSink:
    def test_local_table_uses_local_spark_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path=Path(
                "output/delta_sink/application"
            ),
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        local_spark = object()
        local_calls: list[None] = []
        dbx_calls: list[None] = []

        def fake_get_spark_session() -> object:
            local_calls.append(
                None
            )
            return local_spark

        def fake_run_dbx() -> object:
            dbx_calls.append(
                None
            )
            return object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            fake_get_spark_session,
        )
        monkeypatch.setattr(
            build_module,
            "run_dbx",
            fake_run_dbx,
        )

        build_monitaudit()

        assert local_calls == [
            None,
        ]
        assert dbx_calls == []

        assert factories.delta.calls == [
            {
                "table": "main.delta.local",
                "path": Path(
                    "output/delta_sink/application"
                ),
                "spark": local_spark,
                "is_databricks": False,
            }
        ]

    @pytest.mark.parametrize(
        "table",
        [
            "main.local",
            "catalog.schema.local",
            "main.logging.local",
            "main.delta.local",
        ],
    )
    def test_tables_ending_in_dot_local_use_local_spark(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
        table: str,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table=table,
            delta_path="output/delta",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        local_spark = object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            lambda: local_spark,
        )

        def unexpected_run_dbx() -> object:
            raise AssertionError(
                "run_dbx must not be called for "
                "a table ending in '.local'"
            )

        monkeypatch.setattr(
            build_module,
            "run_dbx",
            unexpected_run_dbx,
        )

        build_monitaudit()

        assert (
            factories.delta.calls[0][
                "is_databricks"
            ]
            is False
        )

        assert (
            factories.delta.calls[0][
                "spark"
            ]
            is local_spark
        )


class TestDatabricksDeltaSink:
    @pytest.mark.parametrize(
        "table",
        [
            "main.logging.application",
            "catalog.schema.table",
            "main.delta.LOCAL",
            "main.delta.local.backup",
            "local_table",
        ],
    )
    def test_non_local_table_uses_run_dbx(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
        table: str,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table=table,
            delta_path="dbfs:/delta/application",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        dbx_spark = object()

        monkeypatch.setattr(
            build_module,
            "run_dbx",
            lambda: dbx_spark,
        )

        def unexpected_local_spark() -> object:
            raise AssertionError(
                "get_spark_session must not be called "
                "for a Databricks Delta table"
            )

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            unexpected_local_spark,
        )

        build_monitaudit()

        assert factories.delta.calls == [
            {
                "table": table,
                "path": "dbfs:/delta/application",
                "spark": dbx_spark,
                "is_databricks": True,
            }
        ]

    def test_databricks_table_passes_run_dbx_result_to_sink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.logging.events",
            delta_path="abfss://logs/events",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        spark = object()
        run_dbx_calls: list[None] = []

        def fake_run_dbx() -> object:
            run_dbx_calls.append(
                None
            )
            return spark

        monkeypatch.setattr(
            build_module,
            "run_dbx",
            fake_run_dbx,
        )

        build_monitaudit()

        assert run_dbx_calls == [
            None,
        ]

        assert (
            factories.delta.calls[0][
                "spark"
            ]
            is spark
        )

        assert (
            factories.delta.calls[0][
                "is_databricks"
            ]
            is True
        )


class TestDeltaSparkFailures:
    def test_propagates_local_spark_creation_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path="output/delta",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        expected_exception = RuntimeError(
            "local Spark unavailable"
        )

        def failing_get_spark_session() -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            failing_get_spark_session,
        )

        with pytest.raises(
            RuntimeError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )
        assert factories.delta.calls == []
        assert factories.monitaudit.calls == []

    def test_propagates_databricks_creation_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.logging.events",
            delta_path="dbfs:/delta/events",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        expected_exception = RuntimeError(
            "Databricks connection failed"
        )

        def failing_run_dbx() -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "run_dbx",
            failing_run_dbx,
        )

        with pytest.raises(
            RuntimeError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )
        assert factories.delta.calls == []
        assert factories.monitaudit.calls == []

    def test_propagates_delta_sink_construction_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path="output/delta",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            lambda: object(),
        )

        expected_exception = ValueError(
            "invalid Delta sink configuration"
        )

        def failing_delta_sink(
            **_kwargs: Any,
        ) -> object:
            raise expected_exception

        monkeypatch.setattr(
            build_module,
            "DeltaSink",
            failing_delta_sink,
        )

        with pytest.raises(
            ValueError,
        ) as exception_info:
            build_monitaudit()

        assert (
            exception_info.value
            is expected_exception
        )
        assert factories.monitaudit.calls == []


class TestSinkSelection:
    def test_builds_all_enabled_sinks_in_defined_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=True,
            file_enabled=True,
            json_enabled=True,
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path="output/delta",
            file_cycle=20,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        spark = object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            lambda: spark,
        )

        build_monitaudit()

        monitaudit_args, monitaudit_kwargs = (
            factories.monitaudit.calls[0]
        )

        assert monitaudit_args == (
            "test-application",
            "test",
            factories.console.instances[0],
            factories.file.instances[0],
            factories.json.instances[0],
            factories.delta.instances[0],
        )

        assert monitaudit_kwargs == {
            "timer": True,
            "parameters": True,
            "max_parameter_length": 1000,
            "sink_failure_mode": "continue",
        }

        assert (
            factories.file.calls[0][
                "file_cycle"
            ]
            == 20
        )
        assert (
            factories.json.calls[0][
                "file_cycle"
            ]
            == 20
        )

    @pytest.mark.parametrize(
        (
            "console_enabled",
            "file_enabled",
            "json_enabled",
            "expected_sink_types",
        ),
        [
            (
                False,
                False,
                False,
                [],
            ),
            (
                True,
                False,
                False,
                [
                    "ConsoleSink",
                ],
            ),
            (
                False,
                True,
                False,
                [
                    "FileSink",
                ],
            ),
            (
                False,
                False,
                True,
                [
                    "JsonSink",
                ],
            ),
            (
                True,
                True,
                False,
                [
                    "ConsoleSink",
                    "FileSink",
                ],
            ),
            (
                True,
                False,
                True,
                [
                    "ConsoleSink",
                    "JsonSink",
                ],
            ),
            (
                False,
                True,
                True,
                [
                    "FileSink",
                    "JsonSink",
                ],
            ),
            (
                True,
                True,
                True,
                [
                    "ConsoleSink",
                    "FileSink",
                    "JsonSink",
                ],
            ),
        ],
    )
    def test_selects_configured_non_delta_sinks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
        console_enabled: bool,
        file_enabled: bool,
        json_enabled: bool,
        expected_sink_types: list[str],
    ) -> None:
        config = make_config(
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            json_enabled=json_enabled,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        monitaudit_args, _ = (
            factories.monitaudit.calls[0]
        )

        constructed_sinks = (
            monitaudit_args[2:]
        )

        assert [
            sink.sink_type
            for sink in constructed_sinks
        ] == expected_sink_types

    def test_disabled_sinks_are_not_constructed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config()

        configure_loaded_config(
            monkeypatch,
            config,
        )

        build_monitaudit()

        assert factories.console.calls == []
        assert factories.file.calls == []
        assert factories.json.calls == []
        assert factories.delta.calls == []


class TestSparkCallIsolation:
    def test_spark_helpers_are_not_called_when_delta_is_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            console_enabled=True,
            file_enabled=True,
            json_enabled=True,
            delta_enabled=False,
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        def unexpected_call() -> object:
            raise AssertionError(
                "Spark helper must not be called "
                "when DeltaSink is disabled"
            )

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            unexpected_call,
        )
        monkeypatch.setattr(
            build_module,
            "run_dbx",
            unexpected_call,
        )

        result = build_monitaudit()

        assert (
            result
            is factories.monitaudit.instance
        )

    def test_only_one_spark_helper_is_called_for_local_delta(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.delta.local",
            delta_path="output/delta",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        local_calls = 0
        dbx_calls = 0

        def fake_local() -> object:
            nonlocal local_calls
            local_calls += 1
            return object()

        def fake_dbx() -> object:
            nonlocal dbx_calls
            dbx_calls += 1
            return object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            fake_local,
        )
        monkeypatch.setattr(
            build_module,
            "run_dbx",
            fake_dbx,
        )

        build_monitaudit()

        assert local_calls == 1
        assert dbx_calls == 0

    def test_only_one_spark_helper_is_called_for_databricks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factories: Factories,
    ) -> None:
        config = make_config(
            delta_enabled=True,
            delta_table="main.logging.events",
            delta_path="dbfs:/delta/events",
        )

        configure_loaded_config(
            monkeypatch,
            config,
        )

        local_calls = 0
        dbx_calls = 0

        def fake_local() -> object:
            nonlocal local_calls
            local_calls += 1
            return object()

        def fake_dbx() -> object:
            nonlocal dbx_calls
            dbx_calls += 1
            return object()

        monkeypatch.setattr(
            build_module,
            "get_spark_session",
            fake_local,
        )
        monkeypatch.setattr(
            build_module,
            "run_dbx",
            fake_dbx,
        )

        build_monitaudit()

        assert local_calls == 0
        assert dbx_calls == 1