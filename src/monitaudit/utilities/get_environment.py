# src/monitaudit/utilities/get_environment.py

import os
from typing import cast

from monitaudit.models.sinks import Environment


_ALLOWED_ENVIRONMENTS = {
    "dev",
    "acc",
    "prod",
}


def get_environment() -> Environment:
    environment = os.getenv(
        "monitaudit_ENV",
        "dev",
    ).lower()

    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(
            f"Unsupported monitaudit environment: "
            f"{environment!r}"
        )

    return cast(
        Environment,
        environment,
    )