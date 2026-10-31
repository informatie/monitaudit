"""
monitaudit nested-error example using the example workspace dataset.

Purpose
-------
Demonstrates nested element processing where an element may fail, while the
workspace continues processing all remaining elements.

If one or more elements fail, the workspace itself is marked as failed after
all its elements have been processed.

Processing behaviour
--------------------
- workspace processing starts
- every element is attempted
- a failed element produces function_error
- the workspace catches the element error
- remaining elements continue processing
- after all elements have been attempted, the workspace fails if one or more
  elements failed
- the workspace produces function_error
- the application catches the workspace error
- processing continues with the next workspace

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_workspace_failure.yaml

Demonstrates
------------
- example-specific monitaudit configuration
- nested @obs.trace calls
- workspace as parent trace
- element as child trace
- child function_error
- continued element processing after failure
- workspace function_error after element processing
- correct trace-depth cleanup
- call_id and parent_call_id handling
- continuing with the next workspace after workspace failure

This example is intentionally synchronous.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
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
    / "main_nested_workspace_failure.yaml"
)

# This element deliberately fails.
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
            "Dataset does not contain a valid "
            f"'workspaces' list: {DATASET_PATH}"
        )

    return data


def main() -> None:
    obs = build_monitaudit(
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
                f"Element {element_code} in workspace "
                f"{ws_nummer} could not be processed"
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
        failed_elements: list[str] = []

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

            except ValueError as exception:
                element_code = element["element_code"]

                failed_elements.append(
                    element_code
                )

                obs.warning(
                    "Element processing failed",
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    error_type=type(exception).__name__,
                    error_message=str(exception),
                )

        obs.info(
            "Workspace elements processed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            failed_elements=len(failed_elements),
        )

        # Every element has now been attempted.
        #
        # If one or more elements failed, fail the workspace itself.
        # Because process_workspace is traced, monitaudit generates a
        # function_error for this workspace.
        if failed_elements:
            raise RuntimeError(
                f"Workspace {ws_nummer} failed because "
                f"{len(failed_elements)} element(s) failed: "
                f"{', '.join(failed_elements)}"
            )

        obs.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
        )

    obs.info(
        "Nested workspace failure example started",
        example="main_nested_workspace_failure",
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Dataset loaded",
        dataset_path=str(DATASET_PATH),
        workspace_count=len(workspaces),
    )

    successful_workspaces = 0
    failed_workspaces = 0

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            raise ValueError(
                "Each workspace must be a mapping."
            )

        try:
            process_workspace(
                workspace
            )

            successful_workspaces += 1

        except RuntimeError as exception:
            failed_workspaces += 1

            obs.warning(
                "Workspace processing failed; "
                "continuing with next workspace",
                ws_nummer=workspace["ws_nummer"],
                ws_naam=workspace["ws_naam"],
                error_type=type(exception).__name__,
                error_message=str(exception),
            )

    obs.info(
        "Nested workspace failure example completed",
        workspace_count=len(workspaces),
        successful_workspaces=successful_workspaces,
        failed_workspaces=failed_workspaces,
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested workspace failure ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - dataset loaded from YAML\n"
        "  - workspace as parent traced function\n"
        "  - element as child traced function\n"
        "  - deliberate child failure for E005\n"
        "  - failed element produces function_error\n"
        "  - remaining elements continue processing\n"
        "  - workspace remembers element failures\n"
        "  - workspace produces function_error afterwards\n"
        "  - next workspace is still processed\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect indentation and trace hierarchy\n"
        "  - JSON: var/log/examples/"
        "main_nested_workspace_failure.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters\n"
        "  - attributes\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "  - duration_ms\n"
        "\n"
        "Expected trace flow:\n"
        "\n"
        "  process_workspace started\n"
        "      process_element completed\n"
        "      process_element completed\n"
        "      process_element E005 failed\n"
        "      element failure is caught\n"
        "      remaining process_element calls continue\n"
        "  process_workspace failed\n"
        "\n"
        "  next process_workspace starts\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_nested_workspace_failure.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()