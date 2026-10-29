# src/monitaudit/utilities/load_config.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.models.sinks import monitauditConfig


DEFAULT_CONFIG_PATH = Path(
    "config/monitaudit/monitaudit.yaml"
)


def load_config(
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> monitauditConfig:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"monitaudit configuration file not found: "
            f"{config_path}"
        )

    if not config_path.is_file():
        raise ValueError(
            f"monitaudit configuration path is not a file: "
            f"{config_path}"
        )

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data: Any = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "monitaudit configuration must be a YAML mapping."
        )

    return monitauditConfig.model_validate(
        data
    )