# src/monitaudit/utilities/load_config.py

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeAlias, cast

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from monitaudit.models.sinks import monitauditConfig

ConfigValue: TypeAlias = Any
ConfigDict: TypeAlias = dict[str, ConfigValue]


DEFAULT_CONFIG_DIRECTORY = Path("config/monitaudit")

DEFAULT_PROPERTIES_PATH = (
    DEFAULT_CONFIG_DIRECTORY / "monitaudit.properties"
)

RUNTIME_CONFIG_FILENAMES: tuple[str, ...] = (
    "monitaudit.runtime.yaml",
    "monitaudit.runtime.yml",
)

ENVIRONMENT_VARIABLES: tuple[str, ...] = (
    "MONITAUDIT_ENVIRONMENT",
    "MONITAUDIT_ENV",
    "ENV",
)

ENVIRONMENT_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]*$"
)

INTEGER_PATTERN = re.compile(
    r"^[+-]?\d+$"
)

FLOAT_PATTERN = re.compile(
    r"^[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$"
)


class ConfigurationError(ValueError):
    """Raised when the MonitAudit configuration is invalid."""


def _validate_file(
    path: Path,
    *,
    description: str,
) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    if not path.is_file():
        raise ConfigurationError(
            f"{description} path is not a file: {path}"
        )

    return path


def _find_runtime_config(
    path: str | Path | None,
    *,
    directory: str | Path,
) -> Path:
    """
    Resolve the MonitAudit runtime configuration file.

    Resolution order:
    1. Explicit path.
    2. monitaudit.runtime.yaml.
    3. monitaudit.runtime.yml.

    If both default runtime files exist, loading fails instead
    of silently choosing one.
    """

    if path is not None:
        return _validate_file(
            Path(path),
            description="MonitAudit runtime configuration file",
        )

    config_directory = Path(directory)

    candidates = tuple(
        config_directory / filename
        for filename in RUNTIME_CONFIG_FILENAMES
    )

    existing = tuple(
        candidate
        for candidate in candidates
        if candidate.is_file()
    )

    if len(existing) > 1:
        files = ", ".join(
            str(candidate)
            for candidate in existing
        )

        raise ConfigurationError(
            "Multiple MonitAudit runtime configuration files "
            f"found: {files}. Keep only one."
        )

    if existing:
        return existing[0]

    expected = ", ".join(
        str(candidate)
        for candidate in candidates
    )

    raise FileNotFoundError(
        "MonitAudit runtime configuration file not found. "
        f"Expected one of: {expected}"
    )


def _get_environment() -> str:
    """
    Read the active environment from the operating system.

    Resolution order:
    1. MONITAUDIT_ENVIRONMENT
    2. MONITAUDIT_ENV
    3. ENV

    The first non-empty variable wins.

    Environment values are normalised to lowercase.

    Examples:
        dev
        acc
        prod
    """

    for variable in ENVIRONMENT_VARIABLES:
        value = os.getenv(variable)

        if value is None:
            continue

        environment = value.strip().lower()

        if not environment:
            continue

        if ENVIRONMENT_PATTERN.fullmatch(environment) is None:
            raise ConfigurationError(
                f"OS environment variable {variable!r} "
                f"contains an invalid environment name: {value!r}. "
                "Use letters, numbers, underscores or hyphens, "
                "starting with a letter."
            )

        return environment

    variables = ", ".join(
        ENVIRONMENT_VARIABLES
    )

    raise ConfigurationError(
        "No MonitAudit environment variable is set. "
        f"Expected one of: {variables}"
    )


def _parse_property_value(
    value: str,
) -> ConfigValue:
    """
    Convert a properties value into a predictable Python value.

    Supported conversions:
        true, false     -> bool
        null, none      -> None
        integer         -> int
        decimal         -> float
        everything else -> str

    Values such as yes, no, on and off remain strings.
    """

    stripped_value = value.strip()
    lowercase_value = stripped_value.lower()

    if lowercase_value == "true":
        return True

    if lowercase_value == "false":
        return False

    if lowercase_value in {
        "null",
        "none",
    }:
        return None

    if INTEGER_PATTERN.fullmatch(stripped_value) is not None:
        try:
            return int(stripped_value)
        except ValueError:
            return stripped_value

    if FLOAT_PATTERN.fullmatch(stripped_value) is not None:
        try:
            return float(stripped_value)
        except ValueError:
            return stripped_value

    return stripped_value


def _set_nested_value(
    target: ConfigDict,
    dotted_key: str,
    value: ConfigValue,
) -> None:
    """
    Convert a dotted properties key into nested dictionaries.

    Example:

        logging.level=INFO

    becomes:

        {
            "logging": {
                "level": "INFO"
            }
        }
    """

    parts = tuple(
        part.strip()
        for part in dotted_key.split(".")
    )

    if not parts or any(
        not part
        for part in parts
    ):
        raise ConfigurationError(
            f"Invalid property name: {dotted_key!r}"
        )

    current = target

    for part in parts[:-1]:
        existing = current.get(part)

        if existing is None:
            nested: ConfigDict = {}

            current[part] = nested
            current = nested

            continue

        if not isinstance(existing, dict):
            raise ConfigurationError(
                "Property namespace conflicts with an existing "
                f"value: {dotted_key!r}"
            )

        current = cast(
            ConfigDict,
            existing,
        )

    final_key = parts[-1]

    if final_key in current:
        raise ConfigurationError(
            f"Duplicate property: {dotted_key!r}"
        )

    current[final_key] = value


def _load_properties(
    path: str | Path,
) -> ConfigDict:
    """
    Load MonitAudit defaults from monitaudit.properties.
    """

    properties_path = _validate_file(
        Path(path),
        description="MonitAudit properties file",
    )

    properties: ConfigDict = {}

    try:
        content = properties_path.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise ConfigurationError(
            "Could not read MonitAudit properties file: "
            f"{properties_path}"
        ) from exc

    for line_number, raw_line in enumerate(
        content.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith(
            (
                "#",
                "!",
            )
        ):
            continue

        if "=" not in line:
            raise ConfigurationError(
                "Invalid property at "
                f"{properties_path}:{line_number}. "
                "Expected 'key=value'."
            )

        raw_key, raw_value = line.split(
            "=",
            maxsplit=1,
        )

        key = raw_key.strip()

        if not key:
            raise ConfigurationError(
                "Empty property name at "
                f"{properties_path}:{line_number}."
            )

        try:
            value = _parse_property_value(
                raw_value
            )

            _set_nested_value(
                properties,
                key,
                value,
            )

        except ConfigurationError as exc:
            raise ConfigurationError(
                f"{properties_path}:{line_number}: {exc}"
            ) from exc

    return properties


def _validate_string_keys(
    value: dict[object, object],
    *,
    location: str,
) -> ConfigDict:
    """
    Recursively validate that all YAML mapping keys are strings.
    """

    validated: ConfigDict = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise ConfigurationError(
                f"Configuration key at {location} must be "
                f"a string, received {key!r}."
            )

        child_location = (
            f"{location}.{key}"
        )

        if isinstance(item, dict):
            validated[key] = _validate_string_keys(
                cast(
                    dict[object, object],
                    item,
                ),
                location=child_location,
            )
        else:
            validated[key] = item

    return validated


def _load_runtime_yaml(
    path: Path,
) -> ConfigDict:
    """
    Load and validate the application-specific runtime YAML.
    """

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data: Any = yaml.safe_load(
                file
            )

    except YAMLError as exc:
        raise ConfigurationError(
            "Invalid MonitAudit YAML configuration: "
            f"{path}: {exc}"
        ) from exc

    except OSError as exc:
        raise ConfigurationError(
            "Could not read MonitAudit runtime configuration: "
            f"{path}"
        ) from exc

    if data is None:
        raise ConfigurationError(
            "MonitAudit runtime configuration is empty: "
            f"{path}"
        )

    if not isinstance(data, dict):
        raise ConfigurationError(
            "MonitAudit runtime configuration must "
            "be a YAML mapping."
        )

    return _validate_string_keys(
        cast(
            dict[object, object],
            data,
        ),
        location="root",
    )


def _deep_merge(
    base: Mapping[str, ConfigValue],
    override: Mapping[str, ConfigValue],
) -> ConfigDict:
    """
    Recursively merge configuration mappings.

    Rules:
    - Nested mappings are recursively merged.
    - Scalars in override replace values from base.
    - Lists in override replace lists from base.
    - Explicit None replaces the base value.
    - Input mappings are never modified.
    """

    merged: ConfigDict = deepcopy(
        dict(base)
    )

    for key, override_value in override.items():
        base_value = merged.get(
            key
        )

        if (
            isinstance(base_value, Mapping)
            and isinstance(override_value, Mapping)
        ):
            merged[key] = _deep_merge(
                cast(
                    Mapping[str, ConfigValue],
                    base_value,
                ),
                cast(
                    Mapping[str, ConfigValue],
                    override_value,
                ),
            )
        else:
            merged[key] = deepcopy(
                override_value
            )

    return merged


def _get_mapping(
    source: ConfigDict,
    key: str,
    *,
    required: bool,
    location: str,
) -> ConfigDict:
    """
    Retrieve and validate a mapping from configuration.
    """

    value = source.get(
        key
    )

    if value is None:
        if required:
            raise ConfigurationError(
                f"{location}.{key} must be a mapping."
            )

        return {}

    if not isinstance(value, dict):
        raise ConfigurationError(
            f"{location}.{key} must be a mapping."
        )

    return cast(
        ConfigDict,
        value,
    )


def _get_monitaudit_root(
    runtime: ConfigDict,
) -> ConfigDict:
    """
    Return the top-level monitaudit configuration section.
    """

    return _get_mapping(
        runtime,
        "monitaudit",
        required=True,
        location="root",
    )


def _get_application(
    root: ConfigDict,
) -> str:
    """
    Return the configured application name.
    """

    application = root.get(
        "application"
    )

    if (
        not isinstance(application, str)
        or not application.strip()
    ):
        raise ConfigurationError(
            "'monitaudit.application' must be "
            "a non-empty string."
        )

    return application.strip()


def _get_global_config(
    root: ConfigDict,
) -> ConfigDict:
    """
    Return global application-specific overrides.
    """

    return _get_mapping(
        root,
        "global",
        required=False,
        location="monitaudit",
    )


def _get_environment_config(
    root: ConfigDict,
    environment: str,
) -> ConfigDict:
    """
    Return the configuration for the selected environment.
    """

    environments = _get_mapping(
        root,
        "environments",
        required=True,
        location="monitaudit",
    )

    invalid_names = tuple(
        name
        for name in environments
        if (
            name != name.strip().lower()
            or ENVIRONMENT_PATTERN.fullmatch(name) is None
        )
    )

    if invalid_names:
        formatted_names = ", ".join(
            repr(name)
            for name in invalid_names
        )

        raise ConfigurationError(
            "MonitAudit environment names must be lowercase "
            "and use only letters, numbers, underscores or "
            f"hyphens: {formatted_names}"
        )

    if environment not in environments:
        available = ", ".join(
            sorted(environments)
        )

        availability_message = (
            available
            if available
            else "<none>"
        )

        raise ConfigurationError(
            "No MonitAudit configuration exists for "
            f"environment {environment!r}. "
            f"Available environments: {availability_message}"
        )

    environment_config = environments[
        environment
    ]

    if not isinstance(environment_config, dict):
        raise ConfigurationError(
            "MonitAudit environment configuration "
            f"{environment!r} must be a mapping."
        )

    return cast(
        ConfigDict,
        environment_config,
    )


def load_config(
    path: str | Path | None = None,
    *,
    properties_path: str | Path = DEFAULT_PROPERTIES_PATH,
    config_directory: str | Path = DEFAULT_CONFIG_DIRECTORY,
) -> monitauditConfig:
    """
    Load and validate the effective MonitAudit configuration.

    Environment variable precedence:
    1. MONITAUDIT_ENVIRONMENT
    2. MONITAUDIT_ENV
    3. ENV

    Runtime file discovery:
    1. Explicit path.
    2. monitaudit.runtime.yaml.
    3. monitaudit.runtime.yml.

    Configuration precedence:
    1. monitaudit.properties.
    2. monitaudit.global.
    3. monitaudit.environments.<environment>.

    The resulting effective configuration is validated
    using monitauditConfig.
    """

    environment = _get_environment()

    properties = _load_properties(
        properties_path
    )

    runtime_path = _find_runtime_config(
        path,
        directory=config_directory,
    )

    runtime = _load_runtime_yaml(
        runtime_path
    )

    root = _get_monitaudit_root(
        runtime
    )

    application = _get_application(
        root
    )

    global_config = _get_global_config(
        root
    )

    environment_config = _get_environment_config(
        root,
        environment,
    )

    effective = _deep_merge(
        properties,
        global_config,
    )

    effective = _deep_merge(
        effective,
        environment_config,
    )

    effective["application"] = application
    effective["environment"] = environment

    try:
        return monitauditConfig.model_validate(
            effective
        )

    except ValidationError as exc:
        raise ConfigurationError(
            "Effective MonitAudit configuration is invalid "
            f"for application {application!r} and environment "
            f"{environment!r}: {exc}"
        ) from exc