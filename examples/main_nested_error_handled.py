"""
monitaudit nested-error example using the example workspace dataset.

Purpose
-------
Demonstrates nested element processing where a child element may fail while
the parent workspace catches the failure, continues processing all remaining
elements, and completes successfully.

The dataset is read from:

    examples/data/example_dataset.yaml

The monitaudit configuration is read from:

    examples/config/main_nested_error_handled.yaml

Processing behaviour
--------------------
- workspace trace starts
- every element is processed by a child trace
- E005 deliberately raises ValueError
- the child produces function_error
- the workspace catches the exception
- a structured warning records the handled failure
- remaining elements continue processing
- the workspace completes normally
- the workspace produces function_end

Demonstrates
------------
- example-specific monitaudit configuration
- nested @obs.trace calls
- workspace as parent trace
- element as child trace
- child function_error
- parent remaining active after child failure
- ContextVar restoration after child failure
- continued processing after a child failure
- correct ConsoleSink depth cleanup
- successful parent function_end
- call_id and parent_call_id relationships

This example intentionally handles the child error. The workspace itself
therefore does not fail.
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
    / "main_nested_error_handled.yaml"
)

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
    obs = build_observability(
        CONFIG_PATH
    )

    @obs.trace
    def process_element(
        ws_nummer: int,
        element_code: str,
        element_name: str,
    ) -> None:
        if element_code == FAILING_ELEMENT:
            raise ValueError(
                f"Element {element_code} is invalid"
            )

        # Simulate successful element processing.
        _ = ws_nummer
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
        failed_elements = 0

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
                    element_code=element_code,
                    element_name=element_name,
                )

                processed_elements += 1

            except ValueError as exception:
                failed_elements += 1

                obs.warning(
                    "Element processing failed; continuing workspace",
                    ws_nummer=ws_nummer,
                    ws_naam=ws_naam,
                    element_code=element_code,
                    element_name=element_name,
                    error_type=type(exception).__name__,
                    error_message=str(exception),
                )

        obs.info(
            "Continuing after element processing",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            failed_elements=failed_elements,
        )

        obs.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            failed_elements=failed_elements,
        )

    obs.info(
        "Nested handled-error example started",
        example="main_nested_error_handled",
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Dataset loaded",
        dataset_path=str(DATASET_PATH),
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
        "Nested handled-error example completed",
        workspace_count=len(workspaces),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: handled nested error ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - example dataset loaded from YAML\n"
        "  - workspaces processed sequentially\n"
        "  - workspace as parent traced function\n"
        "  - elements as child traced functions\n"
        "  - deliberate E005 child failure\n"
        "  - child function_error cleanup\n"
        "  - workspace remains active after child failure\n"
        "  - remaining elements continue processing\n"
        "  - workspace completes successfully\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect indentation and trace hierarchy\n"
        "  - JSON: logs/examples/main_nested_error_handled.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - event\n"
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
        "      process_element started\n"
        "      process_element completed\n"
        "      ...\n"
        "      process_element E005 started\n"
        "      process_element E005 failed\n"
        "      workspace catches the failure\n"
        "      warning is logged inside workspace trace\n"
        "      remaining process_element calls continue\n"
        "  process_workspace completed\n"
        "\n"
        "Important:\n"
        "  - E005 has function_error\n"
        "  - process_workspace has function_end\n"
        "  - process_workspace does NOT have function_error\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_nested_error_handled.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()