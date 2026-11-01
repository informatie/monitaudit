"""
monitaudit nested-error example with JSON-safe warning attributes.

Purpose
-------
Demonstrates nested workspace and element tracing.

When an element fails:
- the element produces a function_error through @mta.trace
- trace parameters identify the workspace and element
- the workspace catches the element exception
- the caught exception is converted to JSON-safe string fields
- workspace and element information is stored as structured attributes
- remaining elements continue processing
- the workspace fails after all elements have been attempted
- the outer loop catches the workspace failure
- processing continues with the next workspace

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_error_json_safe.yaml

Important
---------
Raw exception objects are not passed as warning attributes.

The @mta.trace decorator handles the real exception for function_error
records. Caught exceptions used in additional warning records are represented
using error_type and error_message strings.

Demonstrates
------------
- nested @mta.trace calls
- workspace as parent trace
- element as child trace
- automatic trace parameter capture
- element-level function_error
- JSON-safe warning attributes
- structured workspace fields
- structured element fields
- continued element processing after failure
- workspace-level function_error
- call_id and parent_call_id handling
- trace-depth cleanup

This example is intentionally synchronous.
"""

from __future__ import annotations

from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"

from typing import Any

import yaml

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


DATASET_PATH = (
    DATA_DIR
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    CONFIG_DIR
    / "main_nested_error_json_safe.yaml"
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
    mta = build_monitaudit()

    @mta.trace
    def process_element(
        ws_nummer: int,
        ws_naam: str,
        element_code: str,
        element_name: str,
    ) -> None:
        """
        Process one element.

        Workspace and element values are separate arguments so monitaudit
        captures them as individual trace parameters.
        """

        if element_code == FAILING_ELEMENT:
            raise ValueError(
                f"Element {element_code} ({element_name}) "
                f"could not be processed in workspace "
                f"{ws_nummer} ({ws_naam})"
            )

        # Simulate successful processing.
        _ = element_name

    @mta.trace
    def process_workspace(
        ws_nummer: int,
        ws_naam: str,
        elements: list[dict[str, Any]],
    ) -> None:
        """
        Process every element in a workspace.

        Element failures are collected. Processing continues until every
        element has been attempted. The workspace then fails if one or more
        element failures occurred.
        """

        mta.info(
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
                error_type = type(exception).__name__
                error_message = str(exception)

                failed_elements.append(
                    {
                        "element_code": element_code,
                        "element_name": element_name,
                        "error_type": error_type,
                        "error_message": error_message,
                    }
                )

                mta.warning(
                    "Element processing failed; "
                    "continuing workspace",
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    element_name=element_name,
                    error_type=error_type,
                    error_message=error_message,
                )

        mta.info(
            "All workspace elements attempted",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            total_elements=len(elements),
            processed_elements=processed_elements,
            failed_element_count=len(failed_elements),
        )

        if failed_elements:
            failed_element_codes = [
                element["element_code"]
                for element in failed_elements
            ]

            failed_element_names = [
                element["element_name"]
                for element in failed_elements
            ]

            mta.warning(
                "Workspace contains failed elements",
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                failed_element_count=len(failed_elements),
                failed_element_codes=failed_element_codes,
                failed_element_names=failed_element_names,
                failed_elements=failed_elements,
            )

            failed_element_details = ", ".join(
                (
                    f"{element['element_code']} "
                    f"({element['element_name']})"
                )
                for element in failed_elements
            )

            raise RuntimeError(
                f"Workspace {ws_nummer} ({ws_naam}) failed because "
                f"{len(failed_elements)} element(s) "
                f"could not be processed: "
                f"{failed_element_details}"
            )

        mta.info(
            "Workspace completed successfully",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
        )

    mta.info(
        "Nested error JSON-safe example started",
        example="main_nested_error_json_safe",
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    mta.info(
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

        ws_nummer = workspace["ws_nummer"]
        ws_naam = workspace["ws_naam"]
        elements = workspace["elements"]

        if not isinstance(elements, list):
            raise ValueError(
                f"Workspace {ws_nummer!r} "
                "'elements' must be a list."
            )

        try:
            process_workspace(
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                elements=elements,
            )

            successful_workspaces += 1

        except RuntimeError as exception:
            failed_workspaces += 1

            mta.warning(
                "Workspace processing failed; "
                "continuing with next workspace",
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                error_type=type(exception).__name__,
                error_message=str(exception),
            )

    mta.info(
        "Nested error JSON-safe example completed",
        workspace_count=len(workspaces),
        successful_workspaces=successful_workspaces,
        failed_workspaces=failed_workspaces,
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested error JSON-safe logging ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - dataset loaded from YAML\n"
        "  - workspace as parent traced function\n"
        "  - element as child traced function\n"
        "  - deliberate child failure for E005\n"
        "  - workspace and element stored as structured fields\n"
        "  - caught exceptions converted to string attributes\n"
        "  - remaining elements continue processing\n"
        "  - workspace fails after all elements are attempted\n"
        "  - next workspace is still processed\n"
        "\n"
        "Structured element warning fields:\n"
        "  - ws_nummer\n"
        "  - ws_naam\n"
        "  - element_code\n"
        "  - element_name\n"
        "  - error_type\n"
        "  - error_message\n"
        "\n"
        "Structured workspace warning fields:\n"
        "  - ws_nummer\n"
        "  - ws_naam\n"
        "  - failed_element_count\n"
        "  - failed_element_codes\n"
        "  - failed_element_names\n"
        "  - failed_elements\n"
        "\n"
        "Expected workspace results:\n"
        "\n"
        "  Workspace 301\n"
        "    - all elements succeed\n"
        "    - workspace succeeds\n"
        "\n"
        "  Workspace 302\n"
        "    - E005 fails\n"
        "    - remaining elements are attempted\n"
        "    - workspace fails afterwards\n"
        "\n"
        "  Workspace 303\n"
        "    - E005 fails\n"
        "    - remaining elements are attempted\n"
        "    - workspace fails afterwards\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect indentation and trace hierarchy\n"
        "  - JSON: examples/output/main_nested_error_json_safe.jsonl\n"
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
        "      process_element E005 failed\n"
        "      JSON-safe warning written\n"
        "      remaining process_element calls complete\n"
        "      warning with failed-element details\n"
        "  process_workspace failed\n"
        "\n"
        "  next process_workspace starts\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_nested_error_json_safe.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()