# tests/utilities/test_load_config.py

from __future__ import annotations

import importlib
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

load_config_module = importlib.import_module(
    "monitaudit.utilities.load_config"
)

from monitaudit.utilities.load_config import (  # noqa: E402
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_PROPERTIES_PATH,
    ENVIRONMENT_PATTERN,
    ENVIRONMENT_VARIABLES,
    FLOAT_PATTERN,
    INTEGER_PATTERN,
    RUNTIME_CONFIG_FILENAMES,
    ConfigurationError,
    _deep_merge,
    _find_runtime_config,
    _get_application,
    _get_environment,
    _get_environment_config,
    _get_global_config,
    _get_mapping,
    _get_monitaudit_root,
    _load_properties,
    _load_runtime,
    _parse_property_value,
    _set_nested_value,
    _validate_file,
    _validate_string_keys,
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


def write_yaml(
    path: Path,
    value: Any,
) -> Path:
    return write_text(
        path,
        yaml.safe_dump(
            value,
            sort_keys=False,
        ),
    )


def runtime_file(
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

    return write_yaml(
        path,
        {
            "monitaudit": root,
        },
    )


class NeverMatchingPattern:
    @staticmethod
    def fullmatch(
        _value: str,
    ) -> None:
        return None


class AlwaysMatchingPattern:
    @staticmethod
    def fullmatch(
        _value: str,
    ) -> object:
        return object()


class TestConstants:
    def test_constants(
        self,
    ) -> None:
        assert DEFAULT_CONFIG_DIRECTORY == Path(
            "config/monitaudit"
        )
        assert DEFAULT_PROPERTIES_PATH == Path(
            "config/monitaudit/monitaudit.properties"
        )
        assert RUNTIME_CONFIG_FILENAMES == (
            "monitaudit.runtime.yaml",
            "monitaudit.runtime.yml",
            "monitaudit.runtime",
        )
        assert ENVIRONMENT_VARIABLES == (
            "MONITAUDIT_ENVIRONMENT",
            "MONITAUDIT_ENV",
            "ENV",
            "RUN_ENVIRONMENT",
        )

    @pytest.mark.parametrize(
        "values",
        [
            RUNTIME_CONFIG_FILENAMES,
            ENVIRONMENT_VARIABLES,
        ],
    )
    def test_constants_are_unique(
        self,
        values: tuple[str, ...],
    ) -> None:
        assert len(values) == len(
            set(values)
        )


class TestValidateFile:
    def test_existing_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_text(
            tmp_path / "config",
            "value",
        )

        assert _validate_file(
            path,
            description="Configuration",
        ) is path

    def test_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "missing"

        with pytest.raises(
            FileNotFoundError,
        ) as exc:
            _validate_file(
                path,
                description="Configuration",
            )

        assert str(exc.value) == (
            f"Configuration not found: {path}"
        )

    def test_directory_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "config"
        path.mkdir()

        with pytest.raises(
            ConfigurationError,
            match="path is not a file",
        ):
            _validate_file(
                path,
                description="Configuration",
            )


class TestFindRuntimeConfig:
    @pytest.mark.parametrize(
        "as_string",
        [False, True],
    )
    def test_explicit_path(
        self,
        tmp_path: Path,
        as_string: bool,
    ) -> None:
        path = write_text(
            tmp_path / "custom.runtime",
            "monitaudit: {}\n",
        )

        supplied: str | Path = (
            str(path)
            if as_string
            else path
        )

        result = _find_runtime_config(
            supplied,
            directory=tmp_path,
        )

        assert result == path
        assert isinstance(
            result,
            Path,
        )

    def test_missing_explicit_path(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            FileNotFoundError,
        ):
            _find_runtime_config(
                tmp_path / "missing",
                directory=tmp_path,
            )

    def test_explicit_directory_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "runtime"
        path.mkdir()

        with pytest.raises(
            ConfigurationError,
        ):
            _find_runtime_config(
                path,
                directory=tmp_path,
            )

    @pytest.mark.parametrize(
        "filename",
        RUNTIME_CONFIG_FILENAMES,
    )
    def test_discovers_supported_filename(
        self,
        tmp_path: Path,
        filename: str,
    ) -> None:
        path = write_text(
            tmp_path / filename,
            "monitaudit: {}\n",
        )

        assert _find_runtime_config(
            None,
            directory=tmp_path,
        ) == path

    @pytest.mark.parametrize(
        "filenames",
        [
            RUNTIME_CONFIG_FILENAMES[:2],
            RUNTIME_CONFIG_FILENAMES,
        ],
    )
    def test_multiple_runtime_files_rejected(
        self,
        tmp_path: Path,
        filenames: tuple[str, ...],
    ) -> None:
        paths = [
            write_text(
                tmp_path / filename,
                "monitaudit: {}\n",
            )
            for filename in filenames
        ]

        with pytest.raises(
            ConfigurationError,
            match="Multiple MonitAudit runtime",
        ) as exc:
            _find_runtime_config(
                None,
                directory=tmp_path,
            )

        message = str(
            exc.value
        )

        assert "Keep only one." in message

        for path in paths:
            assert str(path) in message

    def test_directories_are_ignored(
        self,
        tmp_path: Path,
    ) -> None:
        for filename in RUNTIME_CONFIG_FILENAMES:
            (
                tmp_path / filename
            ).mkdir()

        with pytest.raises(
            FileNotFoundError,
        ):
            _find_runtime_config(
                None,
                directory=tmp_path,
            )

    def test_missing_runtime_lists_candidates(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            FileNotFoundError,
        ) as exc:
            _find_runtime_config(
                None,
                directory=tmp_path,
            )

        message = str(
            exc.value
        )

        for filename in RUNTIME_CONFIG_FILENAMES:
            assert str(
                tmp_path / filename
            ) in message


class TestGetEnvironment:
    def test_missing_environment(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _get_environment()

        message = str(
            exc.value
        )

        for variable in ENVIRONMENT_VARIABLES:
            assert variable in message

    @pytest.mark.parametrize(
        (
            "variable",
            "value",
            "expected",
        ),
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
    def test_environment_variables(
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
            "",
        )
        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            " ",
        )
        monkeypatch.setenv(
            "ENV",
            "acc",
        )
        monkeypatch.setenv(
            "RUN_ENVIRONMENT",
            "prod",
        )

        assert _get_environment() == "acc"

    @pytest.mark.parametrize(
        "value",
        [
            "dev",
            "dev1",
            "dev_environment",
            "dev-environment",
            "a",
            "a1_b-2",
        ],
    )
    def test_valid_environment_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
    ) -> None:
        monkeypatch.setenv(
            ENVIRONMENT_VARIABLES[0],
            value,
        )

        assert _get_environment() == value

    @pytest.mark.parametrize(
        "value",
        [
            "1dev",
            "_dev",
            "-dev",
            "dev environment",
            "dev.environment",
            "dev/environment",
            "dev!",
            "édev",
        ],
    )
    def test_invalid_environment_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
    ) -> None:
        monkeypatch.setenv(
            ENVIRONMENT_VARIABLES[0],
            value,
        )
        monkeypatch.setenv(
            ENVIRONMENT_VARIABLES[1],
            "prod",
        )

        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _get_environment()

        message = str(
            exc.value
        )

        assert ENVIRONMENT_VARIABLES[0] in message
        assert repr(value) in message


class TestPatterns:
    @pytest.mark.parametrize(
        (
            "pattern",
            "accepted",
            "rejected",
        ),
        [
            pytest.param(
                ENVIRONMENT_PATTERN,
                (
                    "dev",
                    "dev1",
                    "dev_environment",
                    "dev-environment",
                ),
                (
                    "",
                    "1dev",
                    "_dev",
                    "-dev",
                    "dev environment",
                    "DEV",
                ),
                id="environment",
            ),
            pytest.param(
                INTEGER_PATTERN,
                (
                    "0",
                    "1",
                    "-1",
                    "+1",
                    "001",
                    "-0004",
                ),
                (
                    "",
                    "1.0",
                    "1e3",
                    "one",
                ),
                id="integer",
            ),
            pytest.param(
                FLOAT_PATTERN,
                (
                    "1.0",
                    "-1.0",
                    "+1.0",
                    ".5",
                    "-.5",
                    "1.",
                    "1.5e2",
                    "1.5E-2",
                ),
                (
                    "",
                    "1",
                    "1e3",
                    ".",
                    "value",
                ),
                id="float",
            ),
        ],
    )
    def test_pattern(
        self,
        pattern: Any,
        accepted: tuple[str, ...],
        rejected: tuple[str, ...],
    ) -> None:
        assert all(
            pattern.fullmatch(value)
            is not None
            for value in accepted
        )
        assert all(
            pattern.fullmatch(value)
            is None
            for value in rejected
        )


class TestParsePropertyValue:
    @pytest.mark.parametrize(
        (
            "value",
            "expected",
            "expected_type",
        ),
        [
            ("true", True, bool),
            ("TRUE", True, bool),
            (" false ", False, bool),
            ("null", None, type(None)),
            ("NONE", None, type(None)),
            ("0", 0, int),
            ("42", 42, int),
            ("-42", -42, int),
            ("+42", 42, int),
            ("001", 1, int),
            ("0.0", 0.0, float),
            ("1.5", 1.5, float),
            ("-.5", -0.5, float),
            ("1.", 1.0, float),
            ("1.5e2", 150.0, float),
            ("1.5E-2", 0.015, float),
            ("yes", "yes", str),
            ("no", "no", str),
            ("on", "on", str),
            ("off", "off", str),
            ("1e3", "1e3", str),
            ("NaN", "NaN", str),
            ("Infinity", "Infinity", str),
            (" hello ", "hello", str),
            ("   ", "", str),
        ],
    )
    def test_parse(
        self,
        value: str,
        expected: object,
        expected_type: type[object],
    ) -> None:
        result = _parse_property_value(
            value
        )

        assert result == expected
        assert isinstance(
            result,
            expected_type,
        )

    @pytest.mark.parametrize(
        (
            "integer_matches",
            "float_matches",
            "value",
        ),
        [
            (
                True,
                False,
                "not-an-int",
            ),
            (
                False,
                True,
                "not-a-float",
            ),
        ],
    )
    def test_conversion_failure_returns_string(
        self,
        monkeypatch: pytest.MonkeyPatch,
        integer_matches: bool,
        float_matches: bool,
        value: str,
    ) -> None:
        integer_pattern = (
            AlwaysMatchingPattern()
            if integer_matches
            else NeverMatchingPattern()
        )
        float_pattern = (
            AlwaysMatchingPattern()
            if float_matches
            else NeverMatchingPattern()
        )

        monkeypatch.setattr(
            load_config_module,
            "INTEGER_PATTERN",
            integer_pattern,
        )
        monkeypatch.setattr(
            load_config_module,
            "FLOAT_PATTERN",
            float_pattern,
        )

        assert (
            load_config_module
            ._parse_property_value(value)
            == value
        )


class TestSetNestedValue:
    @pytest.mark.parametrize(
        (
            "key",
            "value",
            "expected",
        ),
        [
            (
                "level",
                "INFO",
                {
                    "level": "INFO",
                },
            ),
            (
                "logging.level",
                "INFO",
                {
                    "logging": {
                        "level": "INFO",
                    }
                },
            ),
            (
                "sinks.file_sink.path",
                "output/log",
                {
                    "sinks": {
                        "file_sink": {
                            "path": "output/log",
                        }
                    }
                },
            ),
            (
                " logging . level ",
                "DEBUG",
                {
                    "logging": {
                        "level": "DEBUG",
                    }
                },
            ),
        ],
    )
    def test_set_value(
        self,
        key: str,
        value: object,
        expected: dict[str, Any],
    ) -> None:
        target: dict[str, Any] = {}

        _set_nested_value(
            target,
            key,
            value,
        )

        assert target == expected

    def test_reuses_existing_namespace(
        self,
    ) -> None:
        target: dict[str, Any] = {
            "logging": {
                "level": "INFO",
            }
        }

        _set_nested_value(
            target,
            "logging.timer",
            True,
        )

        assert target == {
            "logging": {
                "level": "INFO",
                "timer": True,
            }
        }

    @pytest.mark.parametrize(
        "key",
        [
            "",
            " ",
            ".",
            "logging.",
            ".logging",
            "logging..level",
            "logging. .level",
        ],
    )
    def test_invalid_name(
        self,
        key: str,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match="Invalid property name",
        ):
            _set_nested_value(
                {},
                key,
                "value",
            )

    @pytest.mark.parametrize(
        (
            "target",
            "message",
        ),
        [
            (
                {
                    "logging": "INFO",
                },
                "namespace conflicts",
            ),
            (
                {
                    "logging": {
                        "level": "INFO",
                    }
                },
                "Duplicate property",
            ),
        ],
    )
    def test_conflict(
        self,
        target: dict[str, Any],
        message: str,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match=message,
        ):
            _set_nested_value(
                target,
                "logging.level",
                "DEBUG",
            )


class TestLoadProperties:
    def test_loads_properties(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            "\n"
            "# comment\n"
            "! comment\n"
            "logging.level=INFO\n"
            "logging.timer=true\n"
            "logging.show_parameters=false\n"
            "logging.max_parameter_length=1000\n"
            "value=left=right\n"
            "sinks.file_sink.path=output/log\n",
        )

        assert _load_properties(path) == {
            "logging": {
                "level": "INFO",
                "timer": True,
                "parameters": False,
                "max_parameter_length": 1000,
            },
            "value": "left=right",
            "sinks": {
                "file_sink": {
                    "path": "output/log",
                }
            },
        }

    def test_empty_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )

        assert _load_properties(path) == {}

    @pytest.mark.parametrize(
        (
            "content",
            "line",
            "message",
        ),
        [
            (
                "logging.level\n",
                1,
                "Expected 'key=value'",
            ),
            (
                " =INFO\n",
                1,
                "Empty property name",
            ),
            (
                "logging.level=INFO\n"
                "logging.level=DEBUG\n",
                2,
                "Duplicate property",
            ),
            (
                "logging=INFO\n"
                "logging.level=DEBUG\n",
                2,
                "namespace conflicts",
            ),
        ],
    )
    def test_invalid_property(
        self,
        tmp_path: Path,
        content: str,
        line: int,
        message: str,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            content,
        )

        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _load_properties(path)

        text = str(
            exc.value
        )

        assert f"{path}:{line}" in text
        assert message in text

    def test_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            FileNotFoundError,
        ):
            _load_properties(
                tmp_path / "missing.properties"
            )

    def test_read_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = write_text(
            tmp_path / "monitaudit.properties",
            "value=true\n",
        )

        def fail_read(
            self: Path,
            *_args: Any,
            **_kwargs: Any,
        ) -> str:
            del self
            raise OSError(
                "read failed"
            )

        monkeypatch.setattr(
            Path,
            "read_text",
            fail_read,
        )

        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _load_properties(path)

        assert isinstance(
            exc.value.__cause__,
            OSError,
        )


class TestValidateStringKeys:
    def test_valid_mapping_is_copied(
        self,
    ) -> None:
        source: dict[object, object] = {
            "logging": {
                "level": "INFO",
            }
        }

        result = _validate_string_keys(
            source,
            location="root",
        )

        assert result == source
        assert result is not source
        assert (
            result["logging"]
            is not source["logging"]
        )

    @pytest.mark.parametrize(
        (
            "source",
            "location",
        ),
        [
            (
                {
                    1: "value",
                },
                "root",
            ),
            (
                {
                    "logging": {
                        1: "value",
                    }
                },
                "root.logging",
            ),
        ],
    )
    def test_non_string_key(
        self,
        source: dict[object, object],
        location: str,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match=location,
        ):
            _validate_string_keys(
                source,
                location="root",
            )


class TestLoadRuntime:
    def test_mapping(
        self,
        tmp_path: Path,
    ) -> None:
        path = runtime_file(
            tmp_path / "monitaudit.runtime",
        )

        result = _load_runtime(path)

        assert result["monitaudit"][
            "application"
        ] == "example"

    @pytest.mark.parametrize(
        (
            "content",
            "message",
        ),
        [
            (
                "",
                "is empty",
            ),
            (
                "- one\n- two\n",
                "must be a YAML mapping",
            ),
            (
                "value\n",
                "must be a YAML mapping",
            ),
            (
                "42\n",
                "must be a YAML mapping",
            ),
            (
                "true\n",
                "must be a YAML mapping",
            ),
            (
                "1: value\n",
                "key at root must be a string",
            ),
        ],
    )
    def test_invalid_runtime(
        self,
        tmp_path: Path,
        content: str,
        message: str,
    ) -> None:
        path = write_text(
            tmp_path / "runtime",
            content,
        )

        with pytest.raises(
            ConfigurationError,
            match=message,
        ):
            _load_runtime(path)

    def test_invalid_yaml(
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

    def test_open_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "runtime"

        def fail_open(
            self: Path,
            *_args: Any,
            **_kwargs: Any,
        ) -> Any:
            del self
            raise OSError(
                "open failed"
            )

        monkeypatch.setattr(
            Path,
            "open",
            fail_open,
        )

        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _load_runtime(path)

        assert isinstance(
            exc.value.__cause__,
            OSError,
        )

class TestDeepMerge:
    @pytest.mark.parametrize(
        ("base", "override", "expected"),
        [
            pytest.param(
                {"a": 1},
                {"b": 2},
                {"a": 1, "b": 2},
                id="disjoint",
            ),
            pytest.param(
                {
                    "logging": {
                        "level": "INFO",
                        "timer": True,
                    },
                },
                {
                    "logging": {
                        "level": "DEBUG",
                    },
                },
                {
                    "logging": {
                        "level": "DEBUG",
                        "timer": True,
                    },
                },
                id="recursive",
            ),
            pytest.param(
                {"value": "base"},
                {"value": "override"},
                {"value": "override"},
                id="scalar",
            ),
            pytest.param(
                {"values": [1, 2]},
                {"values": [3]},
                {"values": [3]},
                id="list",
            ),
            pytest.param(
                {"value": "base"},
                {"value": None},
                {"value": None},
                id="none",
            ),
            pytest.param(
                {"value": "base"},
                {
                    "value": {
                        "nested": True,
                    },
                },
                {
                    "value": {
                        "nested": True,
                    },
                },
                id="mapping-over-scalar",
            ),
            pytest.param(
                {
                    "value": {
                        "nested": True,
                    },
                },
                {"value": "override"},
                {"value": "override"},
                id="scalar-over-mapping",
            ),
        ],
    )
    def test_merge_rules(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        base_before = deepcopy(base)
        override_before = deepcopy(override)

        result = _deep_merge(
            base,
            override,
        )

        assert result == expected

        # _deep_merge must never modify its inputs.
        assert base == base_before
        assert override == override_before

        # The result must be a new mapping.
        assert result is not base
        assert result is not override

    def test_nested_values_are_copied(
        self,
    ) -> None:
        base = {
            "nested": {
                "base": [1],
            },
        }
        override = {
            "nested": {
                "override": [2],
            },
        }

        result = _deep_merge(
            base,
            override,
        )

        assert result == {
            "nested": {
                "base": [1],
                "override": [2],
            },
        }

        assert (
            result["nested"]
            is not base["nested"]
        )
        assert (
            result["nested"]
            is not override["nested"]
        )

        assert (
            result["nested"]["base"]
            is not base["nested"]["base"]
        )
        assert (
            result["nested"]["override"]
            is not override["nested"]["override"]
        )
class TestHelpers:
    def test_get_mapping_variants(
        self,
    ) -> None:
        mapping = {
            "value": True,
        }

        assert _get_mapping(
            {
                "section": mapping,
            },
            "section",
            required=True,
            location="root",
        ) is mapping

        assert _get_mapping(
            {},
            "section",
            required=False,
            location="root",
        ) == {}

        assert _get_mapping(
            {
                "section": None,
            },
            "section",
            required=False,
            location="root",
        ) == {}

    def test_required_mapping_missing(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match="root.section must be a mapping",
        ):
            _get_mapping(
                {},
                "section",
                required=True,
                location="root",
            )

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "value",
            0,
            1,
            False,
            [],
            (),
        ],
    )
    def test_non_mapping(
        self,
        value: Any,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match="root.section must be a mapping",
        ):
            _get_mapping(
                {
                    "section": value,
                },
                "section",
                required=False,
                location="root",
            )

    def test_root_and_global(
        self,
    ) -> None:
        root = {
            "application": "example",
        }
        global_config = {
            "logging": {},
        }

        assert _get_monitaudit_root(
            {
                "monitaudit": root,
            }
        ) is root

        assert _get_global_config(
            {
                "global": global_config,
            }
        ) is global_config

        assert _get_global_config({}) == {}

    def test_missing_root(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ):
            _get_monitaudit_root({})

    @pytest.mark.parametrize(
        (
            "value",
            "expected",
        ),
        [
            (
                "application",
                "application",
            ),
            (
                " application ",
                "application",
            ),
            (
                "My Application",
                "My Application",
            ),
        ],
    )
    def test_application(
        self,
        value: str,
        expected: str,
    ) -> None:
        assert _get_application(
            {
                "application": value,
            }
        ) == expected

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            " ",
            1,
            False,
            [],
            {},
        ],
    )
    def test_invalid_application(
        self,
        value: Any,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match="non-empty string",
        ):
            _get_application(
                {
                    "application": value,
                }
            )


class TestEnvironmentConfig:
    def test_selected_environment(
        self,
    ) -> None:
        dev = {
            "logging": {},
        }

        assert _get_environment_config(
            {
                "environments": {
                    "dev": dev,
                }
            },
            "dev",
        ) is dev

    def test_environments_required(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ):
            _get_environment_config(
                {},
                "dev",
            )

    @pytest.mark.parametrize(
        "name",
        [
            "DEV",
            " Dev ",
            "1dev",
            "_dev",
            "-dev",
            "dev.environment",
            "dev environment",
        ],
    )
    def test_invalid_environment_name(
        self,
        name: str,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _get_environment_config(
                {
                    "environments": {
                        name: {},
                    }
                },
                "dev",
            )

        assert repr(name) in str(
            exc.value
        )

    def test_all_invalid_names_reported(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _get_environment_config(
                {
                    "environments": {
                        "DEV": {},
                        " Prod ": {},
                        "dev": {},
                    }
                },
                "dev",
            )

        message = str(
            exc.value
        )

        assert "'DEV'" in message
        assert "' Prod '" in message

    @pytest.mark.parametrize(
        (
            "environments",
            "expected",
        ),
        [
            (
                {
                    "dev": {},
                    "prod": {},
                },
                "Available environments: dev, prod",
            ),
            (
                {},
                "Available environments: <none>",
            ),
        ],
    )
    def test_missing_environment(
        self,
        environments: dict[str, Any],
        expected: str,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ) as exc:
            _get_environment_config(
                {
                    "environments": environments,
                },
                "acc",
            )

        assert expected in str(
            exc.value
        )

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "value",
            1,
            False,
            [],
        ],
    )
    def test_environment_must_be_mapping(
        self,
        value: Any,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
        ):
            _get_environment_config(
                {
                    "environments": {
                        "dev": value,
                    }
                },
                "dev",
            )


class TestLoadConfig:
    def test_merge_precedence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "logging.level=INFO\n"
            "logging.timer=true\n"
            "logging.show_parameters=false\n"
            "logging.max_parameter_length=1000\n"
            "logging.sink_failure_mode=continue\n",
        )

        runtime = runtime_file(
            tmp_path / "monitaudit.runtime",
            global_config={
                "logging": {
                    "level": "WARNING",
                    "parameters": True,
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

        captured: list[
            dict[str, Any]
        ] = []
        sentinel = object()

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                value: dict[str, Any],
            ) -> object:
                captured.append(
                    value
                )
                return sentinel

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        result = load_config(
            runtime,
            properties_path=properties,
        )

        assert result is sentinel
        assert captured == [
            {
                "logging": {
                    "level": "DEBUG",
                    "timer": True,
                    "parameters": True,
                    "max_parameter_length": 1000,
                    "sink_failure_mode": "continue",
                },
                "application": "example",
                "environment": "dev",
            }
        ]

    def test_runtime_discovery(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )

        runtime_file(
            tmp_path / "monitaudit.runtime",
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENV",
            "dev",
        )

        sentinel = object()

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                _value: dict[str, Any],
            ) -> object:
                return sentinel

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        assert load_config(
            properties_path=properties,
            config_directory=tmp_path,
        ) is sentinel

    def test_application_and_environment_override_properties(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "application=wrong\n"
            "environment=wrong\n",
        )

        runtime = runtime_file(
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

        captured: list[
            dict[str, Any]
        ] = []

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                value: dict[str, Any],
            ) -> object:
                captured.append(
                    value
                )
                return object()

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        load_config(
            runtime,
            properties_path=properties,
        )

        assert captured[0][
            "application"
        ] == "correct"

        assert captured[0][
            "environment"
        ] == "prod"

    def test_model_validate_called_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[
            dict[str, Any]
        ] = []
        sentinel = object()

        monkeypatch.setattr(
            load_config_module,
            "_get_environment",
            lambda: "dev",
        )
        monkeypatch.setattr(
            load_config_module,
            "_load_properties",
            lambda _path: {
                "logging": {
                    "level": "INFO",
                }
            },
        )
        monkeypatch.setattr(
            load_config_module,
            "_find_runtime_config",
            lambda _path, directory: Path(
                "runtime"
            ),
        )
        monkeypatch.setattr(
            load_config_module,
            "_load_runtime",
            lambda _path: {
                "monitaudit": {
                    "application": "example",
                    "environments": {
                        "dev": {},
                    },
                }
            },
        )

        class FakeConfig:
            @classmethod
            def model_validate(
                cls,
                value: dict[str, Any],
            ) -> object:
                calls.append(
                    value
                )
                return sentinel

        monkeypatch.setattr(
            load_config_module,
            "monitauditConfig",
            FakeConfig,
        )

        assert load_config() is sentinel
        assert calls == [
            {
                "logging": {
                    "level": "INFO",
                },
                "application": "example",
                "environment": "dev",
            }
        ]

    def test_validation_error_is_wrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )
        runtime = runtime_file(
            tmp_path / "monitaudit.runtime",
        )

        monkeypatch.setenv(
            "MONITAUDIT_ENVIRONMENT",
            "dev",
        )

        class InvalidModel(
            BaseModel
        ):
            required_value: int

        with pytest.raises(
            ValidationError,
        ) as original:
            InvalidModel.model_validate(
                {}
            )

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
        ) as exc:
            load_config(
                runtime,
                properties_path=properties,
            )

        message = str(
            exc.value
        )

        assert (
            "Effective MonitAudit configuration "
            "is invalid"
            in message
        )
        assert "application 'example'" in message
        assert "environment 'dev'" in message
        assert (
            exc.value.__cause__
            is original.value
        )

    def test_non_validation_error_propagates(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        properties = write_text(
            tmp_path / "monitaudit.properties",
            "",
        )
        runtime = runtime_file(
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