# tests/utilities/test_build_monitaudit.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import monitaudit.utilities.build_monitaudit as build_module
from monitaudit.models.sinks import (
    ConsoleSinkSettings,
    DeltaSinkSettings,
    FileSinkSettings,
    JsonSinkSettings,
    LoggingSettings,
    SinkSettings,
    monitauditConfig,
)


def make_config(
    *,
    console_enabled: bool = True,
    file_enabled: bool = False,
    json_enabled: bool = False,
    delta_enabled: bool = False,
    delta_table: str | None = None,
    delta_path: str | None = None,
) -> monitauditConfig:
    return monitauditConfig(
        application="test-application",
        environment="dev",
        logging=LoggingSettings(),
        sinks=SinkSettings(
            console_sink=ConsoleSinkSettings(
                enabled=console_enabled,
            ),
            file_sink=FileSinkSettings(
                enabled=file_enabled,
                path="output/monitaudit.txt",
            ),
            json_sink=JsonSinkSettings(
                enabled=json_enabled,
                path="output/monitaudit.jsonl",
            ),
            delta_sink=DeltaSinkSettings(
                enabled=delta_enabled,
                table=delta_table,
                path=delta_path,
            ),
        ),
    )


def test_passes_none_correlation_id_to_monitaudit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    received: dict[str, Any] = {}

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            received["args"] = args
            received["kwargs"] = kwargs

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit()

    assert received["kwargs"]["correlation_id"] is None


def test_passes_explicit_correlation_id_to_monitaudit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    received: dict[str, Any] = {}

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            received["args"] = args
            received["kwargs"] = kwargs

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit(
        correlation_id="RELATICS-12345",
    )

    assert (
        received["kwargs"]["correlation_id"]
        == "RELATICS-12345"
    )


def test_correlation_id_is_preserved_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    received: dict[str, Any] = {}

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            received.update(kwargs)

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    correlation_id = "RELATICS-12345"

    build_module.build_monitaudit(
        correlation_id=correlation_id,
    )

    assert received["correlation_id"] is correlation_id


def test_passes_config_path_to_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    received: list[str | Path | None] = []

    def fake_load_config(
        path: str | Path | None,
    ) -> monitauditConfig:
        received.append(path)
        return config

    monkeypatch.setattr(
        build_module,
        "load_config",
        fake_load_config,
    )

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    path = Path("config/test.yaml")

    build_module.build_monitaudit(
        config_path=path,
    )

    assert received == [path]


def test_passes_logging_settings_to_monitaudit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    received: dict[str, Any] = {}

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            received["args"] = args
            received["kwargs"] = kwargs

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit(
        correlation_id="CID-001",
    )

    assert received["args"] == (
        "test-application",
        "dev",
    )

    assert received["kwargs"] == {
        "timer": True,
        "correlation_id": "CID-001",
        "show_parameters": True,
        "max_parameter_length": 1000,
        "sink_failure_mode": "continue",
    }


def test_creates_console_sink_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=True,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    console_sink = object()

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        lambda **kwargs: console_sink,
    )

    received: dict[str, Any] = {}

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            received["args"] = args

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit()

    assert received["args"] == (
        "test-application",
        "dev",
        console_sink,
    )


def test_does_not_create_console_sink_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    def unexpected_console_sink(
        **kwargs: Any,
    ) -> object:
        raise AssertionError(
            "ConsoleSink must not be created"
        )

    monkeypatch.setattr(
        build_module,
        "ConsoleSink",
        unexpected_console_sink,
    )

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit()


def test_enabled_delta_sink_requires_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
        delta_enabled=True,
        delta_table=None,
        delta_path="/tmp/delta",
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Delta sink is enabled but "
            "no table is configured"
        ),
    ):
        build_module.build_monitaudit()


def test_enabled_delta_sink_requires_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
        delta_enabled=True,
        delta_table="catalog.schema.audit",
        delta_path=None,
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Delta sink is enabled but "
            "no path is configured"
        ),
    ):
        build_module.build_monitaudit()


def test_local_delta_table_uses_local_spark_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
        delta_enabled=True,
        delta_table="audit.local",
        delta_path="/tmp/audit",
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    spark = object()

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        lambda: spark,
    )

    def unexpected_run_dbx() -> object:
        raise AssertionError(
            "run_dbx must not be called "
            "for a local Delta table"
        )

    monkeypatch.setattr(
        build_module,
        "run_dbx",
        unexpected_run_dbx,
    )

    delta_arguments: dict[str, Any] = {}

    class FakeDeltaSink:
        def __init__(
            self,
            **kwargs: Any,
        ) -> None:
            delta_arguments.update(kwargs)

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        FakeDeltaSink,
    )

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit()

    assert delta_arguments == {
        "table": "audit.local",
        "path": "/tmp/audit",
        "spark": spark,
        "is_databricks": False,
    }


def test_databricks_delta_table_uses_run_dbx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(
        console_enabled=False,
        delta_enabled=True,
        delta_table="catalog.schema.audit",
        delta_path="/Volumes/audit",
    )

    monkeypatch.setattr(
        build_module,
        "load_config",
        lambda path: config,
    )

    spark = object()

    monkeypatch.setattr(
        build_module,
        "run_dbx",
        lambda: spark,
    )

    def unexpected_local_spark() -> object:
        raise AssertionError(
            "get_spark_session must not "
            "be called for Databricks"
        )

    monkeypatch.setattr(
        build_module,
        "get_spark_session",
        unexpected_local_spark,
    )

    delta_arguments: dict[str, Any] = {}

    class FakeDeltaSink:
        def __init__(
            self,
            **kwargs: Any,
        ) -> None:
            delta_arguments.update(kwargs)

    monkeypatch.setattr(
        build_module,
        "DeltaSink",
        FakeDeltaSink,
    )

    class FakeMonitaudit:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

    monkeypatch.setattr(
        build_module,
        "Monitaudit",
        FakeMonitaudit,
    )

    build_module.build_monitaudit()

    assert delta_arguments["spark"] is spark
    assert delta_arguments["is_databricks"] is True