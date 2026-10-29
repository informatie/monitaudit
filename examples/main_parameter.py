"""
monitaudit trace parameter example.

Purpose
-------
Demonstrates automatic function parameter capture with monitaudit tracing.

The example reads workspace and element data from:

    examples/data/example_dataset.yaml

Trace hierarchy
---------------
process_pipeline()
    process_workspace(ws_nummer)
        process_element(ws_nummer, element_name)

Expected ConsoleSink parameters
-------------------------------
process_workspace:
    ws_nummer

process_element:
    ws_nummer
    element_name

Configuration
-------------
    examples/config/main_parameter.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.utilities.build_observability import build_observability


EXAMPLE_DIR = Path(__file__).parent

DATASET_PATH = (
    EXAMPLE_DIR
    / "data"
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_parameter.yaml"
)


def load_dataset() -> dict[str, Any]:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(
            f"Example dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid dataset format: {DATASET_PATH}"
        )

    workspaces = data.get("workspaces")

    if not isinstance(workspaces, list):
        raise ValueError(
            "Dataset field 'workspaces' must be a list: "
            f"{DATASET_PATH}"
        )

    return data


obs = build_observability()


@obs.trace
def process_element(
    ws_nummer: int,
    element_name: str,
) -> None:
    obs.info(
        "Element running",
    )


@obs.trace
def process_workspace(
    ws_nummer: int,
    elements: list[dict[str, Any]],
) -> None:
    obs.info(
        "Workspace running",
    )

    for element in elements:
        if not isinstance(element, dict):
            raise ValueError(
                f"Workspace {ws_nummer!r} "
                "contains an invalid element."
            )

        element_name = element.get(
            "element_name"
        )

        if element_name is None:
            element_name = element.get(
                "element_code"
            )

        if element_name is None:
            raise ValueError(
                f"Workspace {ws_nummer!r} contains "
                "an element without 'element_name' "
                "or 'element_code'."
            )

        process_element(
            ws_nummer=ws_nummer,
            element_name=str(
                element_name
            ),
        )

    obs.info(
        "Workspace completed",
    )


@obs.trace
def process_pipeline(
    workspaces: list[dict[str, Any]],
) -> None:
    obs.info(
        "Pipeline running",
    )

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            raise ValueError(
                "Each workspace must be a mapping."
            )

        ws_nummer = workspace["ws_nummer"]
        elements = workspace["elements"]

        if not isinstance(elements, list):
            raise ValueError(
                f"Workspace {ws_nummer!r} "
                "'elements' must be a list."
            )

        process_workspace(
            ws_nummer=ws_nummer,
            elements=elements,
        )

    obs.info(
        "Pipeline completed",
    )


def main() -> None:
    obs.info(
        "Application started",
        example="main_parameter",
    )

    obs.debug(
        "Loading example dataset",
        dataset_path=str(DATASET_PATH),
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Dataset loaded",
        workspace_count=len(workspaces),
    )

    process_pipeline(
        workspaces=workspaces,
    )

    obs.info(
        "Application completed",
        workspace_count=len(workspaces),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: trace parameters ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - reading the example dataset from YAML\n"
        "  - nested monitaudit tracing\n"
        "  - automatic parameter capture\n"
        "  - ws_nummer on process_workspace\n"
        "  - ws_nummer and element_name on process_element\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_parameter.yaml\n"
        "\n"
        "Expected ConsoleSink parameters:\n"
        "  process_workspace:\n"
        "    ws_nummer\n"
        "\n"
        "  process_element:\n"
        "    ws_nummer\n"
        "    element_name\n"
    )


if __name__ == "__main__":
    main()
    print_summary()