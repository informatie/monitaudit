"""
monitaudit nested-error example with safe exception serialization.

Purpose
-------
Demonstrates nested workspace and element tracing with explicit,
JSON-safe exception serialization.

When an element fails:
- the element produces a function_error through @obs.trace
- the workspace catches the element exception
- the caught exception is converted to JSON-safe fields
- workspace and element are included as structured fields
- the traceback is converted to a string
- remaining elements continue processing
- the workspace fails after all elements have been attempted
- the outer loop catches the workspace failure
- processing continues with the next workspace

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_error_serialization.yaml

Demonstrates
------------
- example-specific monitaudit configuration
- nested @obs.trace calls
- workspace as parent trace
- element as child trace
- safe exception serialization
- error_type
- error_message
- traceback
- structured workspace fields
- structured element fields
- continued processing after element failure
- workspace failure after element processing
- call_id and parent_call_id handling
- JSON-safe structured logging

This example is intentionally synchronous.
"""

from __future__ import annotations

import traceback
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
    / "main_nested_error_serialization.yaml"
)

# This element deliberately fails in every workspace containing it.
FAILING_ELEMENT = "E005"


def serialize_exception(
    exception: BaseException,
) -> dict[str, str]:
    """
    Convert a Python exception into JSON-safe structured values.

    The raw exception object is never returned. Only strings are returned.
    """

    return {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "traceback": "".join(
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            )
        ),
    }


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
    obs = build_observability(
        CONFIG_PATH
    )

    @obs.trace
    def process_element(
        ws_nummer: int,
        ws_naam: str,
        element_code: str,
        element_name: str,
    ) -> None:
        """
        Process one element.

        Workspace and element values are separate parameters so monitaudit
        captures them as structured trace parameters.
        """

        if element_code == FAILING_ELEMENT:
            raise ValueError(
                f"Element {element_code} ({element_name}) "
                f"could not be processed in workspace "
                f"{ws_nummer} ({ws_naam})"
            )

        # Simulate successful element processing.
        _ = element_name

    @obs.trace
    def process_workspace(
        ws_nummer: int,
        ws_naam: str,
        elements: list[dict[str, Any]],
    ) -> None:
        """
        Process all elements belonging to one workspace.

        Individual element failures are collected. All remaining elements
        are attempted before the workspace itself fails.
        """

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
                error = serialize_exception(
                    exception
                )

                failed_elements.append(
                    {
                        "element_code": element_code,
                        "element_name": element_name,
                        "error_type": error["error_type"],
                        "error_message": error[
                            "error_message"
                        ],
                    }
                )

                obs.warning(
                    "Element processing failed; "
                    "continuing workspace",
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    element_name=element_name,
                    error_type=error["error_type"],
                    error_message=error["error_message"],
                    traceback=error["traceback"],
                )

        obs.info(
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

            obs.warning(
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

        obs.info(
            "Workspace completed successfully",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
        )

    obs.info(
        "Nested error serialization example started",
        example="main_nested_error_serialization",
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

            error = serialize_exception(
                exception
            )

            obs.warning(
                "Workspace processing failed; "
                "continuing with next workspace",
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                error_type=error["error_type"],
                error_message=error["error_message"],
                traceback=error["traceback"],
            )

    obs.info(
        "Nested error serialization example completed",
        workspace_count=len(workspaces),
        successful_workspaces=successful_workspaces,
        failed_workspaces=failed_workspaces,
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested error serialization ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - dataset loaded from YAML\n"
        "  - workspace as parent traced function\n"
        "  - element as child traced function\n"
        "  - deliberate child failure for E005\n"
        "  - caught exceptions converted to strings\n"
        "  - error_type serialized as string\n"
        "  - error_message serialized as string\n"
        "  - traceback serialized as string\n"
        "  - workspace and element stored as structured fields\n"
        "  - remaining elements continue processing\n"
        "  - workspace fails after all elements are attempted\n"
        "  - next workspace is still processed\n"
        "\n"
        "Structured error attributes:\n"
        "  - ws_nummer\n"
        "  - ws_naam\n"
        "  - element_code\n"
        "  - element_name\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect indentation and trace hierarchy\n"
        "  - JSON: logs/examples/"
        "main_nested_error_serialization.jsonl\n"
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
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/"
        "main_nested_error_serialization.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()