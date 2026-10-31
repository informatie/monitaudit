"""
Basic monitaudit logging example.

Purpose
-------
Demonstrates the normal monitaudit logging API without function tracing.

The example reads a small workspace/element dataset from:

    examples/data/basic_dataset.yaml

The script processes each workspace and then processes all elements belonging
to that workspace. Individual elements are intentionally not logged.

Demonstrates
------------
- loading example data from YAML
- debug logging
- info logging
- warning logging
- structured attributes
- workspace processing
- configured monitaudit sinks

Use this example when
---------------------
- verifying monitaudit.yaml
- testing ConsoleSink
- testing FileSink
- testing JsonSink
- testing DeltaSink
- checking that build_monitaudit() works
- troubleshooting logging without involving tracing

Do not use this example when
----------------------------
- testing call_id or parent_call_id
- testing nested traces
- testing automatic parameter capture
- testing sensitive parameters redaction
- testing trace exception handling

Those behaviours are demonstrated by the other examples.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.utilities.build_monitaudit import build_monitaudit

EXAMPLE_DIR = Path(__file__).parent

DATASET_PATH = (
    EXAMPLE_DIR
    / "data"
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_basic.yaml"
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


def main() -> None:
    obs = build_monitaudit()

    obs.info(
        "Application started",
        example="main_basic",
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

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            raise ValueError(
                "Each workspace must be a mapping."
            )

        ws_nummer = workspace["ws_nummer"]
        ws_naam = workspace["ws_naam"]
        elements = workspace["elements"]

        if not isinstance(elements, list):
            raise ValueError(
                f"Workspace {ws_nummer!r} "
                "'elements' must be a list."
            )

        obs.info(
            "Processing workspace",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
        )

        processed_elements = 0

        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(
                    f"Workspace {ws_nummer!r} contains "
                    "an invalid element."
                )

            element_code = element["element_code"]
            element_name = element["element_name"]

            # Simulate actual element processing.
            #
            # Individual elements are deliberately not logged so
            # console output remains focused on workspace processing.
            _ = element_code
            _ = element_name

            processed_elements += 1

        obs.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
        )

    obs.warning(
        "Example warning",
        reason="This warning is generated intentionally",
    )

    obs.info(
        "Application completed",
        workspace_count=len(workspaces),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: basic logging ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - reading the example dataset from YAML\n"
        "  - DEBUG, INFO and WARNING logging\n"
        "  - structured log attributes\n"
        "  - workspace-level processing\n"
        "  - element processing without element-level logging\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: output above\n"
        "  - FileSink: configured file_sink.path\n"
        "  - JsonSink: configured json_sink.path\n"
        "  - DeltaSink: configured delta_sink.table\n"
        "\n"
        "monitaudit configuration:\n"
        "  config/monitaudit/monitaudit.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()