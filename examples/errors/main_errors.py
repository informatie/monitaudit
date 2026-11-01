"""
monitaudit nested-error example using the example workspace dataset.

Purpose
-------
Demonstrates a nested traced element-processing call that fails while the
parent workspace catches the exception, continues processing the remaining
elements, and eventually completes successfully.

The dataset is read from:

    examples/data/example_dataset.yaml

This scenario is particularly useful for validating ConsoleSink depth state,
ContextVar restoration, call_id and parent_call_id handling.

Demonstrates
------------
- nested @mta.trace calls
- workspace as parent trace
- element as child trace
- child function_error
- parent remaining active after child failure
- continued element processing after a failure
- correct trace-depth cleanup
- successful parent function_end
- exception handling inside a traced parent

Use this example when
---------------------
- validating ConsoleSink depth cleanup
- checking parent_call_id behaviour
- testing nested exception handling
- ensuring a failed child is removed from trace-depth state
- verifying that the workspace can continue processing normally

Do not use this example when
----------------------------
- testing an exception that propagates through every parent
- testing multiprocessing behaviour
- testing async @mta.trace support

This example is intentionally synchronous and demonstrates a handled child
failure rather than a fully propagated failure.
"""

from __future__ import annotations

from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"

from typing import Any

import yaml

from monitaudit.utilities.build_monitaudit import build_monitaudit


DATASET_PATH = Path(__file__).parent / "data" / "example_dataset.yaml"

# This element deliberately fails to demonstrate nested error handling.
FAILING_ELEMENT = "E005"


def load_dataset() -> dict[str, Any]:
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid dataset format: {DATASET_PATH}"
        )

    if "workspaces" not in data:
        raise ValueError(
            f"Dataset does not contain 'workspaces': {DATASET_PATH}"
        )

    return data


def main() -> None:
    mta = build_monitaudit()

    @mta.trace
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

    @mta.trace
    def process_workspace(
        workspace: dict[str, Any],
    ) -> None:
        ws_nummer = workspace["ws_nummer"]
        ws_naam = workspace["ws_naam"]
        elements = workspace["elements"]

        mta.info(
            "Processing workspace",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_count=len(elements),
        )

        processed_elements = 0
        failed_elements = 0

        for element in elements:
            try:
                process_element(
                    ws_nummer,
                    element,
                )
                processed_elements += 1

            except ValueError:
                failed_elements += 1

                mta.warning(
                    "Element processing failed",
                    ws_nummer=ws_nummer,
                    element_code=element["element_code"],
                )

        mta.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            failed_elements=failed_elements,
        )

    mta.info("Nested error example started")

    dataset = load_dataset()

    mta.info(
        "Dataset loaded",
        workspace_count=len(dataset["workspaces"]),
    )

    for workspace in dataset["workspaces"]:
        process_workspace(workspace)

    mta.info("Nested error example completed")


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: nested error tracing ===\n"
        "\n"
        "What was demonstrated:\n"
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
        "  - JSON/Delta: inspect call_id and parent_call_id\n"
        "  - Delta: inspect function_error for E005\n"
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
        "  config/monitaudit/monitaudit.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()