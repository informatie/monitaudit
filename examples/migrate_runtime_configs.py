# examples/migrate_runtime_configs.py

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


EXAMPLES_DIR = Path(__file__).resolve().parent
CONFIG_DIR = EXAMPLES_DIR / "config"

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
            f"{path}: root must be a YAML mapping."
        )

    return cast(
        dict[str, Any],
        data,
    )


def migrate_config(
    path: Path,
) -> bool:
    data = load_yaml(
        path
    )

    monitaudit = data.get(
        "monitaudit"
    )

    if not isinstance(monitaudit, dict):
        print(
            f"SKIP     {path.name}: "
            "no monitaudit section"
        )
        return False

    # Already migrated.
    if "environments" in monitaudit:
        print(
            f"OK       {path.name}"
        )
        return False

    environments: dict[str, Any] = {}

    for environment in ENVIRONMENTS:
        if environment in monitaudit:
            environments[environment] = (
                monitaudit.pop(environment)
            )

    if not environments:
        print(
            f"SKIP     {path.name}: "
            "no dev/acc/prod sections"
        )
        return False

    monitaudit["environments"] = environments

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        yaml.safe_dump(
            data,
            file,
            sort_keys=False,
            allow_unicode=True,
        )

    print(
        f"UPDATED  {path.name}"
    )

    return True


def main() -> None:
    if not CONFIG_DIR.is_dir():
        raise FileNotFoundError(
            f"Config directory not found: {CONFIG_DIR}"
        )

    config_files = sorted(
        (
            *CONFIG_DIR.glob("*.yaml"),
            *CONFIG_DIR.glob("*.yml"),
        )
    )

    print()
    print("MonitAudit example configuration migration")
    print("=" * 72)
    print(f"Directory: {CONFIG_DIR}")
    print()

    changed = 0

    for path in config_files:
        if migrate_config(path):
            changed += 1

    print()
    print("=" * 72)
    print(f"Files checked : {len(config_files)}")
    print(f"Files changed : {changed}")


if __name__ == "__main__":
    main()
