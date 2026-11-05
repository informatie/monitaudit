# tests/utilities/test_load_config.py

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

load_config_module = importlib.import_module(
    "monitaudit.utilities.load_config"
)

from monitaudit.utilities.load_config import (  # noqa: E402
    ENVIRONMENT_VARIABLES,
    ConfigurationError,
    _deep_merge,
    _find_runtime_config,
    _get_environment,
    _load_properties,
    _load_runtime,
    _parse_property_value,
    load_config,
)


@pytest.fixture(autouse=True)
def clean_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    for variable in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(
            variable,
            raising=False,
        )

    yield


def write_text(
    path: Path,
    content: str,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        content,
        encoding="utf-8",
    )
    return path


def write_runtime(
    path: Path,
    *,
    application: str = "example",
    environments: dict[str, Any] | None = None,
    global_config: dict[str, Any] | None = None,
) -> Path:
    root: dict[str, Any] = {
        "application": application,
        "environments": (
            environments
            if environments is not None
            else {"dev": {}}
        ),
    }

    if global_config is not None:
        root["global"] = global_config

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        yaml.safe_dump(
            {
                "monitaudit": root,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def valid_properties() -> str:
    return (
        "logging.level=INFO\n"
        "logging.timer=true\n"
        "logging.show_parameters=true\n"
        "logging.file_cycle=10\n"
        "logging.max_parameter_length=1000\n"
        "logging.sink_failure_mode=continue\n"
        "sinks.console_sink.enabled=true\n"
        "sinks.file_sink.enabled=false\n"
        "sinks.file_sink.format=text\n"
        "sinks.file_sink.delimiter=;\n"
        "sinks.file_sink.path=output/monitaudit.txt\n"
        "sinks.json_sink.enabled=false\n"
        "sinks.json_sink.path=output/monitaudit.jsonl\n"
        "sinks.delta_sink.enabled=false\n"
    )


class TestEnvironment:
    @pytest.mark.parametrize(
        ("variable", "value", "expected"),
        [
            (
                "MONITAUDIT_ENVIRONMENT",
                "dev",
                "dev",
            ),
            (
                "MONITAUDIT_ENV",
                "ACC",
                "acc",
            ),
            (
                "ENV",
                " Prod ",
                "prod",
            ),
            (
                "RUN_ENVIRONMENT",
                "local-test",
                "local-test",
            ),
        ],
    )
    def test_environment_selection(
        self,
        monkeypatch: pytest.MonkeyPatch,
        variable: str,
        value: str,
        expected: str,
    ) -> None:
        monkeypatch.setenv(
            variable,
            value,
        )

        assert _get_environment() == expected

    def test_environment_precedence(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "acc",
        )
        monkeypatch.setenv(
            "ENV",
            "prod",
        )

        assert _get_environment() == "dev"

    def test_missing_environment_fails(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ):
            _get_environment()

    def test_invalid_environment_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "invalid environment",
        )

        with pytest.raises(
            ConfigurationError,
        ):
            _get_environment()


class TestPropertyValues:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("true", True),
            ("false", False),
            ("null", None),
            ("42", 42),
            ("-42", -42),
            ("1.5", 1.5),
            ("1.5e2", 150.0),
            ("hello", "hello"),
            (" hello ", "hello"),
        ],
    )
    def test_parse_property_value(
        self,
        value: str,
        expected: object,
    ) -> None:
        result = _parse_property_value(
            value
        )

        assert result == expected
        assert type(result) is type(expected)


class TestProperties:
    def test_load_properties(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            "logging.level=INFO\n"
            "logging.timer=true\n"
            "logging.show_parameters=false\n",
        )

        assert _load_properties(path) == {
            "logging": {
                "level": "INFO",
                "timer": True,
                "show_parameters": False,
            }
        }

    @pytest.mark.parametrize(
        "content",
        [
            "logging.level\n",
            "=INFO\n",
            (
                "logging.level=INFO\n"
                "logging.level=DEBUG\n"
            ),
        ],
    )
    def test_invalid_properties_fail(
        self,
        tmp_path: Path,
        content: str,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            content,
        )

        with pytest.raises(
            ConfigurationError,
        ):
            _load_properties(path)

    def test_missing_properties_file_fails(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            FileNotFoundError,
        ):
            _load_properties(
                tmp_path / "missing.properties"
            )


class TestRuntime:
    def test_load_runtime_yaml(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_runtime(
            tmp_path / "monitaudit.runtime",
        )

        result = _load_runtime(path)

        assert result["monitaudit"][
            "application"
        ] == "example"

    @pytest.mark.parametrize(
        "content",
        [
            "",
            "- one\n- two\n",
            "42\n",
            "true\n",
        ],
    )
    def test_invalid_root_fails(
        self,
        tmp_path: Path,
        content: str,
    ) -> None:
        path = write_text(
            tmp_path / "runtime",
            content,
        )

        with pytest.raises(
            ConfigurationError,
        ):
            _load_runtime(path)

    def test_invalid_yaml_fails(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_text(
            tmp_path / "runtime",
            "monitaudit:\n  application: [\n",
        )

        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _load_runtime(path)

        assert isinstance(
            exc.value.__cause__,
            yaml.YAMLError,
        )


class TestRuntimeDiscovery:
    def test_explicit_runtime_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_runtime(
            tmp_path / "custom.runtime",
        )

        assert _find_runtime_config(
            path,
            directory=tmp_path,
        ) == path

    def test_missing_runtime_file_fails(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            FileNotFoundError,
        ):
            _find_runtime_config(
                None,
                directory=tmp_path,
            )

    def test_multiple_runtime_files_fail(
        self,
        tmp_path: Path,
    ) -> None:
        write_runtime(
            tmp_path / "monitaudit.runtime",
        )
        write_runtime(
            tmp_path / "monitaudit.runtime.yaml",
        )

        with pytest.raises(
            ConfigurationError,
            match="Multiple MonitAudit runtime",
        ):
            _find_runtime_config(
                None,
                directory=tmp_path,
            )


class TestDeepMerge:
    def test_recursive_override(
        self,
    ) -> None:
        base = {
            "logging": {
                "level": "INFO",
                "timer": True,
            }
        }

        override = {
            "logging": {
                "level": "DEBUG",
            }
        }

        result = _deep_merge(
            base,
            override,
        )

        assert result == {
            "logging": {
                "level": "DEBUG",
                "timer": True,
            }
        }

    def test_inputs_are_not_modified(
        self,
    ) -> None:
        base = {
            "nested": {
                "values": [1, 2],
            }
        }

        override = {
            "nested": {
                "value": True,
            }
        }

        original_base = {
            "nested": {
                "values": [1, 2],
            }
        }

        original_override = {
            "nested": {
                "value": True,
            }
        }

        result = _deep_merge(
            base,
            override,
        )

        assert base == original_base
        assert override == original_override

        assert result == {
            "nested": {
                "values": [1, 2],
                "value": True,
            }
        }

        assert result is not base
        assert result is not override


class TestLoadConfig:
    def test_real_configuration(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            valid_properties(),
        )

        runtime = write_runtime(
            tmp_path / "monitaudit.runtime",
            application="example",
            environments={
                "dev": {},
            },
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )

        config = load_config(
            runtime,
            properties_path=properties,
        )

        assert config.application == "example"
        assert config.environment == "dev"
        assert config.logging.level == "INFO"
        assert config.logging.timer is True
        assert (
            config.logging.show_parameters
            is True
        )
        assert (
            config.logging.max_parameter_length
            == 1000
        )
        assert (
            config.logging.sink_failure_mode
            == "continue"
        )

        assert (
            config.sinks.file_sink.enabled
            is False
        )
        assert (
            config.sinks.json_sink.enabled
            is False
        )
        assert (
            config.sinks.delta_sink.enabled
            is False
        )

    def test_merge_precedence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            valid_properties(),
        )

        runtime = write_runtime(
            tmp_path / "monitaudit.runtime",
            global_config={
                "logging": {
                    "level": "WARNING",
                    "show_parameters": False,
                }
            },
            environments={
                "dev": {
                    "logging": {
                        "level": "DEBUG",
                    }
                }
            },
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )

        config = load_config(
            runtime,
            properties_path=properties,
        )

        assert config.logging.level == "DEBUG"
        assert (
            config.logging.show_parameters
            is False
        )

        # Not overridden by runtime configuration.
        assert config.logging.timer is True
        assert (
            config.logging.max_parameter_length
            == 1000
        )

    def test_runtime_application_and_environment_win(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            (
                valid_properties()
                + "application=wrong\n"
                + "environment=wrong\n"
            ),
        )

        runtime = write_runtime(
            tmp_path / "monitaudit.runtime",
            application="correct",
            environments={
                "prod": {},
            },
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "prod",
        )

        config = load_config(
            runtime,
            properties_path=properties,
        )

        assert config.application == "correct"
        assert config.environment == "prod"

    def test_validation_error_is_wrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )

        runtime = write_runtime(
            tmp_path / "monitaudit.runtime",
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )

        class InvalidModel(BaseModel):
            required_value: int

        with pytest.raises(
            ValidationError,
        ) as original:
            InvalidModel.model_validate({})

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                _value: dict[str, Any],
            ) -> object:
                raise original.value

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        with pytest.raises(
            ConfigurationError,
            match=(
                "Effective MonitAudit "
                "configuration is invalid"
            ),
        ) as exc:
            load_config(
                runtime,
                properties_path=properties,
            )

        assert (
            exc.value.__cause__
            is original.value
        )

    def test_unexpected_validation_error_propagates(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )

        runtime = write_runtime(
            tmp_path / "monitaudit.runtime",
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )

        expected = RuntimeError(
            "unexpected failure"
        )

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                _value: dict[str, Any],
            ) -> object:
                raise expected

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        with pytest.raises(
            RuntimeError,
        ) as exc:
            load_config(
                runtime,
                properties_path=properties,
            )

        assert exc.value is expected