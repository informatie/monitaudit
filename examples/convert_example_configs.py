# examples/convert_example_configs.py

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import yaml


EXAMPLES_DIR = Path(__file__).resolve().parent
CONFIG_DIR = EXAMPLES_DIR / "config"
BACKUP_DIR = EXAMPLES_DIR / "config_backup"

ENVIRONMENTS = (
    "dev",
    "acc",
    "prod",
)


def load_yaml(
    path: Path,
) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data: Any = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: YAML root must be a mapping."
        )

    return cast(
        dict[str, Any],
        data,
    )


def remove_is_databricks(
    value: object,
) -> int:
    if not isinstance(value, dict):
        return 0

    removed = 0

    if "is_databricks" in value:
        value.pop("is_databricks")
        removed += 1

    for item in value.values():
        removed += remove_is_databricks(
            item
        )

    return removed


def convert_config(
    path: Path,
) -> tuple[bool, list[str]]:
    data = load_yaml(
        path
    )

    changes: list[str] = []

    monitaudit = data.get(
        "monitaudit"
    )

    if not isinstance(monitaudit, dict):
        raise ValueError(
            f"{path}: missing 'monitaudit' mapping."
        )

    application = monitaudit.get(
        "application"
    )

    if not isinstance(application, str) or not application.strip():
        raise ValueError(
            f"{path}: missing valid "
            "'monitaudit.application'."
        )

    global_config = monitaudit.get(
        "global"
    )

    if global_config is None:
        global_config = {}
        monitaudit["global"] = global_config

        changes.append(
            "added global section"
        )

    if not isinstance(global_config, dict):
        raise ValueError(
            f"{path}: 'monitaudit.global' "
            "must be a mapping."
        )

    existing_environments = monitaudit.get(
        "environments"
    )

    if existing_environments is None:
        environments: dict[str, Any] = {}
        monitaudit["environments"] = environments

        changes.append(
            "added environments section"
        )

    elif isinstance(existing_environments, dict):
        environments = existing_environments

    else:
        raise ValueError(
            f"{path}: 'monitaudit.environments' "
            "must be a mapping."
        )

    # Move legacy top-level environment sections:
    #
    # monitaudit:
    #   dev:
    #   acc:
    #   prod:
    #
    # into:
    #
    # monitaudit:
    #   environments:
    #     dev:
    #     acc:
    #     prod:

    for environment in ENVIRONMENTS:
        legacy = monitaudit.pop(
            environment,
            None,
        )

        if legacy is None:
            continue

        if not isinstance(legacy, dict):
            raise ValueError(
                f"{path}: legacy environment "
                f"{environment!r} must be a mapping."
            )

        existing = environments.get(
            environment
        )

        if existing is not None:
            if existing != legacy:
                raise ValueError(
                    f"{path}: both legacy and new "
                    f"{environment!r} configuration exist "
                    "with different values."
                )

            changes.append(
                f"removed duplicate legacy {environment}"
            )

            continue

        environments[environment] = legacy

        changes.append(
            f"moved {environment} under environments"
        )

    # Guarantee all supported environments exist.

    for environment in ENVIRONMENTS:
        if environment not in environments:
            environments[environment] = {}

            changes.append(
                f"added empty {environment} environment"
            )

        elif not isinstance(
            environments[environment],
            dict,
        ):
            raise ValueError(
                f"{path}: environment {environment!r} "
                "must be a mapping."
            )

    removed = remove_is_databricks(
        monitaudit
    )

    if removed:
        changes.append(
            f"removed {removed} is_databricks setting(s)"
        )

    if not changes:
        return False, []

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        yaml.safe_dump(
            data,
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

    return True, changes


def create_backup() -> None:
    if BACKUP_DIR.exists():
        raise FileExistsError(
            f"Backup directory already exists: "
            f"{BACKUP_DIR}"
        )

    shutil.copytree(
        CONFIG_DIR,
        BACKUP_DIR,
    )

    print(
        f"BACKUP   {CONFIG_DIR} -> {BACKUP_DIR}"
    )


def main() -> None:
    if not CONFIG_DIR.is_dir():
        raise FileNotFoundError(
            f"Example config directory not found: "
            f"{CONFIG_DIR}"
        )

    files = sorted(
        [
            *CONFIG_DIR.glob("*.yaml"),
            *CONFIG_DIR.glob("*.yml"),
        ]
    )

    if not files:
        raise FileNotFoundError(
            f"No YAML configuration files found in "
            f"{CONFIG_DIR}"
        )

    create_backup()

    print()
    print("Converting MonitAudit example configurations")
    print("=" * 72)

    changed_files = 0
    failed_files = 0

    for path in files:
        try:
            changed, changes = convert_config(
                path
            )

        except (
            OSError,
            ValueError,
            yaml.YAMLError,
        ) as exc:
            failed_files += 1

            print(
                f"ERROR    {path.name}"
            )
            print(
                f"         {exc}"
            )

            continue

        if not changed:
            print(
                f"OK       {path.name}"
            )
            continue

        changed_files += 1

        print(
            f"UPDATED  {path.name}"
        )

        for change in changes:
            print(
                f"         - {change}"
            )

    print()
    print("=" * 72)
    print(f"Files checked : {len(files)}")
    print(f"Files changed : {changed_files}")
    print(f"Files failed  : {failed_files}")
    print(f"Backup        : {BACKUP_DIR}")


if __name__ == "__main__":
    main()