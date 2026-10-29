"""
monitaudit nested-error example using the example workspace dataset.

Purpose
-------
Demonstrates a nested traced element-processing call that fails while the
parent workspace catches the exception, continues processing the remaining
elements, and eventually completes successfully.

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_error.yaml

This scenario is particularly useful for validating ConsoleSink depth state,
ContextVar restoration, call_id and parent_call_id handling.

Demonstrates
------------
- example-specific monitaudit configuration
- nested @obs.trace calls
- workspace as parent trace
- element as child trace
- child function_error
- parent remaining active after child failure
- continued element processing after a failure
- correct trace-depth cleanup
- successful parent function_end
- exception handling inside a traced parent
- JSON trace inspection

Use this example when
---------------------
- validating ConsoleSink depth cleanup
- checking parent_call_id behaviour
- testing nested exception handling
- ensuring a failed child is removed from trace-depth state
- verifying that the workspace can continue processing normally
- inspecting trace relationships in JsonSink output

Do not use this example when
----------------------------
- testing an exception that propagates through every parent
- testing multiprocessing behaviour
- testing async @obs.trace support

This example is intentionally synchronous and demonstrates a handled child
failure rather than a fully propagated failure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.utilities.build_observability import (
    build_observability,
)


EXAMPLE_DIR = Path(__file__).parent

DATASET_PATH = (
    EXAMPLE_DIR
    / "data"
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_nested_error.yaml"
)

# This element deliberately fails to demonstrate nested error handling.
FAILING_ELEMENT = "E005"


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
    obs = build_observability(
        CONFIG_PATH
    )

    @obs.trace
    def process_element(
        ws_nummer: int,
        element: dict[str, Any],
    ) -> None:
        element_code = element["element_code"]

        if element_code == FAILING_ELEMENT:
            raise ValueError(
                f"Element {element_code} could not be processed"
            )

        # Simulate successful element processing.
        _ = element["element_name"]

    @obs.trace
    def process_workspace(
        workspace: dict[str, Any],
    ) -> None:
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
            element_count=len(elements),
        )

        processed_elements = 0
        failed_elements = 0

        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(
                    f"Workspace {ws_nummer!r} "
                    "contains an invalid element."
                )

            try:
                process_element(
                    ws_nummer,
                    element,
                )

                processed_elements += 1

            except ValueError:
                failed_elements += 1

                obs.warning(
                    "Element processing failed",
                    ws_nummer=ws_nummer,
                    element_code=element["element_code"],
                )

        obs.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            failed_elements=failed_elements,
        )

    obs.info(
        "Nested error example started",
        example="main_nested_error",
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

        process_workspace(
            workspace
        )

    obs.info(
        "Nested error example completed"
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested error tracing ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - dataset loaded from YAML\n"
        "  - workspace as parent traced function\n"
        "  - element as child traced function\n"
        "  - deliberate child failure for E005\n"
        "  - child function_error cleanup\n"
        "  - workspace remains active after child failure\n"
        "  - remaining elements continue processing\n"
        "  - workspace completes successfully\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect indentation and trace hierarchy above\n"
        "  - JSON: logs/examples/main_nested_error.jsonl\n"
        "\n"
        "Inspect in JSON:\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - event\n"
        "  - parameters\n"
        "  - duration_ms\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "\n"
        "Expected trace flow:\n"
        "  process_workspace started\n"
        "      process_element started\n"
        "      process_element completed\n"
        "      ...\n"
        "      process_element started for E005\n"
        "      process_element failed\n"
        "      workspace catches failure\n"
        "      process_element continues with next element\n"
        "  process_workspace completed\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_nested_error.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()