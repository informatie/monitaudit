from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from monitaudit.models.sinks import monitauditConfig
from monitaudit.utilities.load_config import (
    DEFAULT_CONFIG_PATH,
    load_config,
)


VALID_CONFIG = """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      level: INFO
      timer: true
      parameters: true
      max_parameter_length: 1000
      sink_failure_mode: continue

    sinks:
      console_sink:
        enabled: true

      json_sink:
        enabled: false
        path: logs/monitaudit.jsonl

      delta_sink:
        enabled: false
        table: main.logging.monitaudit

      file_sink:
        enabled: false
        path: logs/monitaudit.log
"""


def test_default_config_path() -> None:
    assert DEFAULT_CONFIG_PATH == Path(
        "config/monitaudit/monitaudit.yaml"
    )


def test_load_valid_config(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        VALID_CONFIG,
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert isinstance(
        config,
        monitauditConfig,
    )

    assert (
        config.monitaudit.application
        == "monitaudit-test"
    )


def test_load_config_accepts_path(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        VALID_CONFIG,
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert isinstance(
        config,
        monitauditConfig,
    )


def test_load_config_accepts_string_path(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        VALID_CONFIG,
        encoding="utf-8",
    )

    config = load_config(
        str(config_file)
    )

    assert isinstance(
        config,
        monitauditConfig,
    )


def test_load_config_missing_file_raises(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "does_not_exist.yaml"
    )

    with pytest.raises(
        FileNotFoundError,
    ):
        load_config(config_file)


def test_missing_file_error_contains_path(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "missing.yaml"
    )

    with pytest.raises(
        FileNotFoundError,
    ) as error_info:
        load_config(config_file)

    assert str(config_file) in str(
        error_info.value
    )


def test_directory_path_raises_value_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        load_config(tmp_path)


def test_directory_error_contains_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
    ) as error_info:
        load_config(tmp_path)

    assert str(tmp_path) in str(
        error_info.value
    )


@pytest.mark.parametrize(
    "content",
    [
        "",
        "null",
        "hello",
        "123",
        "true",
        "- first\n- second\n",
    ],
)
def test_non_mapping_yaml_raises_value_error(
    tmp_path: Path,
    content: str,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        content,
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        load_config(config_file)


def test_empty_yaml_raises_value_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        load_config(config_file)


def test_empty_mapping_reaches_pydantic_validation(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_missing_monitaudit_section_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
something_else:
  value: test
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_invalid_application_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: ""

  global:
    is_databricks: false
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_unknown_top_level_field_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

unknown_field: value
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_unknown_monitaudit_field_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

  unknown_field: value
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_invalid_logging_level_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      level: INVALID
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_invalid_sink_failure_mode_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      sink_failure_mode: invalid
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_max_parameter_length_below_minimum_raises_validation_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      max_parameter_length: 49
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
    ):
        load_config(config_file)


def test_max_parameter_length_minimum_is_valid(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      max_parameter_length: 50
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    settings = (
        config.monitaudit.global_settings
    )

    assert (
        settings.logging.max_parameter_length
        == 50
    )


def test_default_logging_settings_are_applied(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    logging = (
        config
        .monitaudit
        .global_settings
        .logging
    )

    assert logging.level == "INFO"
    assert logging.timer is True
    assert logging.parameters is True
    assert logging.max_parameter_length == 1000
    assert logging.sink_failure_mode == "continue"


def test_environment_override_is_loaded(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      level: INFO

  prod:
    logging:
      level: ERROR
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    prod_settings = (
        config.monitaudit.for_environment(
            "prod"
        )
    )

    assert (
        prod_settings.logging.level
        == "ERROR"
    )


def test_global_settings_survive_environment_override(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "monitaudit.yaml"

    config_file.write_text(
        """
monitaudit:
  application: monitaudit-test

  global:
    is_databricks: false

    logging:
      level: INFO
      timer: true
      parameters: true

  prod:
    logging:
      level: ERROR
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    settings = (
        config.monitaudit.for_environment(
            "prod"
        )
    )

    assert settings.logging.level == "ERROR"
    assert settings.logging.timer is True
    assert settings.logging.parameters is True