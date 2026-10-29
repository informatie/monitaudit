from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import monitaudit.utilities.build_observability as build_module


def make_settings(
    *,
    file_enabled: bool = False,
    file_path: str = "logs/monitaudit.log",
    console_enabled: bool = False,
    console_parameters: list[str] | None = None,
    json_enabled: bool = False,
    json_path: str = "logs/monitaudit.jsonl",
    delta_enabled: bool = False,
    delta_table: str | None = "catalog.schema.monitaudit",
    is_databricks: bool = False,
    timer: bool = True,
    parameters: bool = True,
    max_parameter_length: int = 1000,
    sink_failure_mode: str = "continue",
) -> SimpleNamespace:
    return SimpleNamespace(
        is_databricks=is_databricks,
        logging=SimpleNamespace(
            timer=timer,
            parameters=parameters,
            max_parameter_length=max_parameter_length,
            sink_failure_mode=sink_failure_mode,
        ),
        sinks=SimpleNamespace(
            file_sink=SimpleNamespace(
                enabled=file_enabled,
                path=file_path,
            ),
            console_sink=SimpleNamespace(
                enabled=console_enabled,
                parameters=console_parameters or [],
            ),
            json_sink=SimpleNamespace(
                enabled=json_enabled,
                path=json_path,
            ),
            delta_sink=SimpleNamespace(
                enabled=delta_enabled,
                table=delta_table,
            ),
        ),
    )


def make_config(
    settings: SimpleNamespace,
    *,
    application: str = "test-application",
) -> tuple[SimpleNamespace, MagicMock]:
    for_environment = MagicMock(
        return_value=settings
    )

    monitaudit = SimpleNamespace(
        application=application,
        for_environment=for_environment,
    )

    config = SimpleNamespace(
        monitaudit=monitaudit,
    )

    return config, for_environment


def patch_common(
    monkeypatch: pytest.MonkeyPatch,
    *,
    settings: SimpleNamespace,
    environment: str = "dev",
    application: str = "test-application",
) -> tuple[
    MagicMock,
    MagicMock,
    MagicMock,
]:
    config, for_environment = make_config(
        settings,
        application=application,
    )

    load_config_mock = MagicMock(
        return_value=config
    )

    get_environment_mock = MagicMock(
        return_value=environment
    )

    observability_instance = MagicMock()

    observability_mock = MagicMock(
        return_value=observability_instance
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        load_config_mock,
    )

    monkeypatch.setattr(
        build_module,
        "get_environment",
        get_environment_mock,
    )

    monkeypatch.setattr(
        build_module,
        "Observability",
        observability_mock,
    )

    return (
        load_config_mock,
        for_environment,
        observability_mock,
    )


def test_build_observability_loads_default_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings()

    (
        load_config_mock,
        for_environment,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    result = build_module.build_observability()

    load_config_mock.assert_called_once_with()

    for_environment.assert_called_once_with(
        "dev"
    )

    observability_mock.assert_called_once_with(
        "test-application",
        "dev",
        timer=True,
        parameters=True,
        max_parameter_length=1000,
        sink_failure_mode="continue",
    )

    assert result is observability_mock.return_value


def test_build_observability_loads_custom_config_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings()

    (
        load_config_mock,
        _,
        _,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    config_path = Path(
        "examples/config/main_parameter.yaml"
    )

    build_module.build_observability(
        config_path
    )

    load_config_mock.assert_called_once_with(
        config_path
    )


def test_build_observability_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings()

    (
        _,
        for_environment,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
        environment="acc",
    )

    build_module.build_observability()

    for_environment.assert_called_once_with(
        "acc"
    )

    args = observability_mock.call_args.args

    assert args[0] == "test-application"
    assert args[1] == "acc"


def test_build_observability_passes_logging_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        timer=False,
        parameters=False,
        max_parameter_length=5000,
        sink_failure_mode="raise",
    )

    (
        _,
        _,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    build_module.build_observability()

    kwargs = observability_mock.call_args.kwargs

    assert kwargs == {
        "timer": False,
        "parameters": False,
        "max_parameter_length": 5000,
        "sink_failure_mode": "raise",
    }


def test_build_observability_with_no_enabled_sinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings()

    (
        _,
        _,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    build_module.build_observability()

    args = observability_mock.call_args.args

    assert args == (
        "test-application",
        "dev",
    )


def test_build_observability_creates_file_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        file_enabled=True,
        file_path="logs/test.log",
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    file_sink_instance = MagicMock()

    file_sink_mock = MagicMock(
        return_value=file_sink_instance
    )

    monkeypatch.setattr(
        build_module,
        "FileSink",
        file_sink_mock,
    )

    observability_instance = (
        build_module.build_observability()
    )

    file_sink_mock.assert_called_once_with(
        path="logs/test.log"
    )

    assert observability_instance is not None


def test_build_observability_creates_json_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        json_enabled=True,
        json_path="logs/test.jsonl",
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    json_sink_instance = MagicMock()

    json_sink_mock = MagicMock(
        return_value=json_sink_instance
    )

    monkeypatch.setattr(
        build_module,
        "JsonSink",
        json_sink_mock,
    )

    build_module.build_observability()

    json_sink_mock.assert_called_once_with(
        path="logs/test.jsonl"
    )


def test_build_observability_creates_console_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        console_enabled=True,
        console_parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    console_sink_instance = MagicMock()

    console_sink_mock = MagicMock(
        return_value=console_sink_instance
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        console_sink_mock,
    )

    build_module.build_observability()

    console_sink_mock.assert_called_once_with(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ]
    )


def test_console_parameter_order_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_parameters = [
        "ws_nummer",
        "element_shortname",
    ]

    settings = make_settings(
        console_enabled=True,
        console_parameters=configured_parameters,
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    console_sink_mock = MagicMock(
        return_value=MagicMock()
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        console_sink_mock,
    )

    build_module.build_observability()

    actual_parameters = (
        console_sink_mock
        .call_args
        .kwargs["parameters"]
    )

    assert actual_parameters == [
        "ws_nummer",
        "element_shortname",
    ]


def test_disabled_sinks_are_not_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        file_enabled=False,
        console_enabled=False,
        json_enabled=False,
        delta_enabled=False,
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    file_sink_mock = MagicMock()
    console_sink_mock = MagicMock()
    json_sink_mock = MagicMock()
    delta_sink_mock = MagicMock()

    monkeypatch.setattr(
        build_module,
        "FileSink",
        file_sink_mock,
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        console_sink_mock,
    )

    monkeypatch.setattr(
        build_module,
        "JsonSink",
        json_sink_mock,
    )

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        delta_sink_mock,
    )

    build_module.build_observability()

    file_sink_mock.assert_not_called()
    console_sink_mock.assert_not_called()
    json_sink_mock.assert_not_called()
    delta_sink_mock.assert_not_called()


def test_delta_sink_uses_local_spark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        delta_enabled=True,
        delta_table="catalog.schema.monitaudit",
        is_databricks=False,
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    spark = MagicMock(
        name="local_spark"
    )

    get_spark_mock = MagicMock(
        return_value=spark
    )

    run_dbx_mock = MagicMock()

    delta_sink_instance = MagicMock()

    delta_sink_mock = MagicMock(
        return_value=delta_sink_instance
    )

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        get_spark_mock,
    )

    monkeypatch.setattr(
        build_module,
        "run_dbx",
        run_dbx_mock,
    )

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        delta_sink_mock,
    )

    build_module.build_observability()

    get_spark_mock.assert_called_once_with()
    run_dbx_mock.assert_not_called()

    delta_sink_mock.assert_called_once_with(
        table="catalog.schema.monitaudit",
        spark=spark,
        is_databricks=False,
    )


def test_delta_sink_uses_databricks_spark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        delta_enabled=True,
        delta_table="catalog.schema.monitaudit",
        is_databricks=True,
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    spark = MagicMock(
        name="databricks_spark"
    )

    run_dbx_mock = MagicMock(
        return_value=spark
    )

    get_spark_mock = MagicMock()

    delta_sink_mock = MagicMock(
        return_value=MagicMock()
    )

    monkeypatch.setattr(
        build_module,
        "run_dbx",
        run_dbx_mock,
    )

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        get_spark_mock,
    )

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        delta_sink_mock,
    )

    build_module.build_observability()

    run_dbx_mock.assert_called_once_with()
    get_spark_mock.assert_not_called()

    delta_sink_mock.assert_called_once_with(
        table="catalog.schema.monitaudit",
        spark=spark,
        is_databricks=True,
    )


def test_delta_sink_requires_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        delta_enabled=True,
        delta_table=None,
        is_databricks=False,
    )

    patch_common(
        monkeypatch,
        settings=settings,
    )

    spark = MagicMock()

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        MagicMock(
            return_value=spark
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Delta sink is enabled but "
            "no table is configured"
        ),
    ):
        build_module.build_observability()


def test_all_enabled_sinks_are_passed_to_observability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        file_enabled=True,
        console_enabled=True,
        console_parameters=[
            "ws_nummer",
            "element_shortname",
        ],
        json_enabled=True,
        delta_enabled=True,
        delta_table="catalog.schema.monitaudit",
        is_databricks=False,
    )

    (
        _,
        _,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    file_sink = MagicMock(
        name="file_sink"
    )

    console_sink = MagicMock(
        name="console_sink"
    )

    json_sink = MagicMock(
        name="json_sink"
    )

    delta_sink = MagicMock(
        name="delta_sink"
    )

    spark = MagicMock(
        name="spark"
    )

    monkeypatch.setattr(
        build_module,
        "FileSink",
        MagicMock(
            return_value=file_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        MagicMock(
            return_value=console_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "JsonSink",
        MagicMock(
            return_value=json_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        MagicMock(
            return_value=delta_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        MagicMock(
            return_value=spark
        ),
    )

    build_module.build_observability()

    args = observability_mock.call_args.args

    assert args == (
        "test-application",
        "dev",
        file_sink,
        console_sink,
        json_sink,
        delta_sink,
    )


def test_sink_order_is_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        file_enabled=True,
        console_enabled=True,
        json_enabled=True,
        delta_enabled=False,
    )

    (
        _,
        _,
        observability_mock,
    ) = patch_common(
        monkeypatch,
        settings=settings,
    )

    file_sink = MagicMock(
        name="file_sink"
    )

    console_sink = MagicMock(
        name="console_sink"
    )

    json_sink = MagicMock(
        name="json_sink"
    )

    monkeypatch.setattr(
        build_module,
        "FileSink",
        MagicMock(
            return_value=file_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        MagicMock(
            return_value=console_sink
        ),
    )

    monkeypatch.setattr(
        build_module,
        "JsonSink",
        MagicMock(
            return_value=json_sink
        ),
    )

    build_module.build_observability()

    args = observability_mock.call_args.args

    assert args[2:] == (
        file_sink,
        console_sink,
        json_sink,
    )