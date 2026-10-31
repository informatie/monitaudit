"""
monitaudit nested-error parameter example using the workspace dataset.

Purpose
-------
Demonstrates nested workspace and element tracing with explicit parameters.

When an element fails:
- the element produces a function_error
- the error identifies both the workspace and element
- the workspace catches the element error
- the remaining elements in that workspace are still processed
- after all elements have been attempted, the workspace produces its own
  function_error
- the outer loop catches the workspace error
- processing continues with the next workspace

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_error_parameter.yaml

Demonstrates
------------
- example-specific monitaudit configuration
- nested @obs.trace calls
- automatic parameter capture
- workspace as parent trace
- element as child trace
- element-level function_error
- workspace and element identification in parameters and errors
- continued element processing after a failure
- workspace-level function_error
- correct trace-depth cleanup
- call_id and parent_call_id handling
- continuing with the next workspace after workspace failure

Use this example when
---------------------
- validating captured trace parameters
- validating ConsoleSink depth cleanup
- checking parent_call_id behaviour
- testing nested exception handling
- verifying that remaining elements continue after an element failure
- verifying that a workspace fails when one or more elements fail
- checking element and workspace function_error records

Do not use this example when
----------------------------
- testing immediate abortion of element processing
- testing multiprocessing behaviour
- testing async @obs.trace support

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
    / "main_nested_error_parameter.yaml"
)

# This element deliberately fails in every workspace containing it.
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
        ws_naam: str,
        element_code: str,
        element_name: str,
    ) -> None:
        if element_code == FAILING_ELEMENT:
            raise ValueError(
                f"Workspace {ws_nummer} ({ws_naam}) - "
                f"element {element_code} ({element_name}) "
                "could not be processed"
            )

        # Simulate successful element processing.
        _ = element_name

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
        failed_elements: list[dict[str, str]] = []

        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(
                    f"Workspace {ws_nummer!r} "
                    "contains an invalid element."
                )

            element_code = element["element_code"]
            element_name = element["element_name"]

            try:
                process_element(
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    element_name=element_name,
                )

                processed_elements += 1

            except ValueError as exception:
                failed_elements.append(
                    {
                        "element_code": element_code,
                        "element_name": element_name,
                    }
                )

                obs.warning(
                    "Element processing failed; "
                    "continuing workspace",
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    element_name=element_name,
                    error_type=type(exception).__name__,
                    error_message=str(exception),
                )

        obs.info(
            "All workspace elements attempted",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            total_elements=len(elements),
            processed_elements=processed_elements,
            failed_elements=len(failed_elements),
        )

        if failed_elements:
            failed_element_details = ", ".join(
                (
                    f"{element['element_code']} "
                    f"({element['element_name']})"
                )
                for element in failed_elements
            )

            raise RuntimeError(
                f"Workspace {ws_nummer} ({ws_naam}) failed because "
                f"{len(failed_elements)} element(s) failed: "
                f"{failed_element_details}"
            )

        obs.info(
            "Workspace completed successfully",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
        )

    obs.info(
        "Nested error parameter example started",
        example="main_nested_error_parameter",
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
        "Nested error parameter example completed",
        workspace_count=len(workspaces),
        successful_workspaces=successful_workspaces,
        failed_workspaces=failed_workspaces,
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested error parameter tracing ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - dataset loaded from YAML\n"
        "  - workspace as parent traced function\n"
        "  - element as child traced function\n"
        "  - automatic trace parameter capture\n"
        "  - deliberate child failure for E005\n"
        "  - element error contains workspace and element details\n"
        "  - remaining elements continue processing\n"
        "  - failed workspace contains failed element details\n"
        "  - next workspace is still processed\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect trace hierarchy\n"
        "  - JSON: var/log/examples/"
        "main_nested_error_parameter.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "  - duration_ms\n"
        "\n"
        "Expected trace flow:\n"
        "  process_workspace started\n"
        "      process_element completed\n"
        "      process_element E005 failed\n"
        "      workspace catches the element failure\n"
        "      remaining process_element calls complete\n"
        "  process_workspace failed\n"
        "\n"
        "  next process_workspace starts\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_nested_error_parameter.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()