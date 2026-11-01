# examples/main_read_setting.py

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"

from typing import Any

import yaml

from monitaudit.utilities.load_config import (
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_PROPERTIES_PATH,
    ENVIRONMENT_VARIABLES,
    RUNTIME_CONFIG_FILENAMES,
    load_config,
)


MISSING = "-"


def find_environment() -> tuple[str | None, str | None]:
    """
    Find the environment variable used by MonitAudit.

    Priority:
    1. MONITAUDIT_ENVIRONMENT
    2. MONITAUDIT_ENV
    3. ENV
    """

    for variable in ENVIRONMENT_VARIABLES:
        value = os.getenv(variable)

        if value is not None and value.strip():
            return variable, value.strip().lower()

    return None, None


def find_runtime_file() -> Path:
    runtime_files = [
        DEFAULT_CONFIG_DIRECTORY / filename
        for filename in RUNTIME_CONFIG_FILENAMES
        if (DEFAULT_CONFIG_DIRECTORY / filename).is_file()
    ]

    if not runtime_files:
        raise FileNotFoundError(
            "No MonitAudit runtime configuration found."
        )

    if len(runtime_files) > 1:
        files = ", ".join(
            str(path)
            for path in runtime_files
        )

        raise RuntimeError(
            "Multiple MonitAudit runtime configuration files "
            f"found: {files}"
        )

    return runtime_files[0]


def parse_property_value(
    value: str,
) -> object:
    value = value.strip()

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    if value.lower() in {"null", "none"}:
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def load_properties_for_report(
    path: Path,
) -> dict[str, object]:
    properties: dict[str, object] = {}

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith(("#", "!")):
            continue

        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            maxsplit=1,
        )

        properties[key.strip()] = parse_property_value(
            value
        )

    return properties


def flatten(
    data: Mapping[str, Any],
    *,
    prefix: str = "",
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in data.items():
        full_key = (
            f"{prefix}.{key}"
            if prefix
            else str(key)
        )

        if isinstance(value, Mapping):
            result.update(
                flatten(
                    value,
                    prefix=full_key,
                )
            )
        else:
            result[full_key] = value

    return result


def load_runtime_for_report(
    path: Path,
    environment: str,
) -> dict[str, object]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data: Any = yaml.safe_load(
            file
        )

    if not isinstance(data, dict):
        raise ValueError(
            "Runtime configuration must be a YAML mapping."
        )

    monitaudit = data.get(
        "monitaudit"
    )

    if not isinstance(monitaudit, dict):
        raise ValueError(
            "Missing 'monitaudit' section."
        )

    result: dict[str, object] = {}

    application = monitaudit.get(
        "application"
    )

    if application is not None:
        result["application"] = application

    global_config = monitaudit.get(
        "global",
        {}
    )

    if isinstance(global_config, dict):
        for key, value in flatten(
            global_config
        ).items():
            result[key] = value

    environments = monitaudit.get(
        "environments",
        {}
    )

    if isinstance(environments, dict):
        selected = environments.get(
            environment,
            {}
        )

        if isinstance(selected, dict):
            for key, value in flatten(
                selected
            ).items():
                result[key] = value

    return result


def format_value(
    value: object,
) -> str:
    if value is None:
        return "null"

    if isinstance(value, bool):
        return str(value).lower()

    if isinstance(value, (list, tuple)):
        return ", ".join(
            str(item)
            for item in value
        )

    return str(value)


def print_matrix(
    properties: dict[str, object],
    runtime: dict[str, object],
    result: dict[str, object],
) -> None:
    keys = sorted(
        set(properties)
        | set(runtime)
        | set(result)
    )

    rows: list[
        tuple[str, str, str, str]
    ] = []

    for key in keys:
        rows.append(
            (
                key,
                format_value(
                    properties.get(
                        key,
                        MISSING,
                    )
                ),
                format_value(
                    runtime.get(
                        key,
                        MISSING,
                    )
                ),
                format_value(
                    result.get(
                        key,
                        MISSING,
                    )
                ),
            )
        )

    headers = (
        "KEY",
        "PROPERTIES",
        "RUNTIME YAML",
        "RESULT",
    )

    widths = [
        max(
            len(headers[index]),
            max(
                (
                    len(row[index])
                    for row in rows
                ),
                default=0,
            ),
        )
        for index in range(4)
    ]

    separator = (
        "+"
        + "+".join(
            "-" * (width + 2)
            for width in widths
        )
        + "+"
    )

    print(separator)

    print(
        "| "
        + " | ".join(
            headers[index].ljust(
                widths[index]
            )
            for index in range(4)
        )
        + " |"
    )

    print(separator)

    for row in rows:
        print(
            "| "
            + " | ".join(
                row[index].ljust(
                    widths[index]
                )
                for index in range(4)
            )
            + " |"
        )

    print(separator)


def main() -> None:
    environment_variable, environment = find_environment()

    if environment_variable is None or environment is None:
        variables = ", ".join(
            ENVIRONMENT_VARIABLES
        )

        raise RuntimeError(
            "No MonitAudit environment variable found. "
            f"Checked: {variables}"
        )

    runtime_path = find_runtime_file()

    properties = load_properties_for_report(
        DEFAULT_PROPERTIES_PATH
    )

    runtime = load_runtime_for_report(
        runtime_path,
        environment,
    )

    config = load_config()

    result = flatten(
        config.model_dump(
            mode="python",
            exclude_none=False,
        )
    )

    print()
    print("MONITAUDIT CONFIGURATION REPORT")
    print("=" * 80)

    print(
        f"Environment : {environment}"
    )

    print(
        f"Variable    : {environment_variable}"
    )

    print(
        f"Properties  : {DEFAULT_PROPERTIES_PATH}"
    )

    print(
        f"Runtime     : {runtime_path}"
    )

    print()

    print_matrix(
        properties,
        runtime,
        result,
    )


if __name__ == "__main__":
    main()