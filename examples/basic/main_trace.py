"""
monitaudit tracing example.

Purpose
-------
Demonstrates how @mta.trace automatically records function execution and
builds a hierarchy using call_id and parent_call_id.

The example processes the workspace/element dataset from:

    examples/data/example_dataset.yaml

The monitaudit configuration is loaded from:

    examples/config/main_trace.yaml

Each workspace is processed by a traced parent function. Each element in the
workspace is processed by a traced child function.

Unlike the error examples, every operation in this example completes
successfully.

Demonstrates
------------
- example-specific monitaudit configuration
- loading the example dataset from YAML
- @mta.trace
- automatic parameter capture
- default parameter capture
- function_start events
- function_end events
- call_id
- parent_call_id
- nested traces
- duration_ms
- normal var/log inside traced functions
- ConsoleSink indentation

Use this example when
---------------------
- validating tracing
- checking nested trace depth
- checking call_id relationships
- testing ConsoleSink indentation
- verifying captured parameters in JsonSink output
- checking trace duration values

Do not use this example when
----------------------------
- specifically testing sensitive-data redaction
- testing exception and traceback behaviour
- testing child failures
- benchmarking monitaudit performance

Dedicated examples exist for those behaviours.
"""

from __future__ import annotations

from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"

from typing import Any

import yaml

from monitaudit.models.monitaudit import Monitaudit
from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


DATASET_PATH = (
    DATA_DIR
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    CONFIG_DIR
    / "main_trace.yaml"
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
            "Dataset does not contain a valid "
            f"'workspaces' list: {DATASET_PATH}"
        )

    return data


def run_trace_example(
    mta: Monitaudit,
    dataset: dict[str, Any],
) -> None:
    @mta.trace
    def process_element(
        ws_nummer: int,
        element_code: str,
        element_name: str,
        validate: bool = True,
    ) -> None:
        # Simulate element processing.
        _ = ws_nummer
        _ = element_code
        _ = element_name
        _ = validate

    @mta.trace
    def process_workspace(
        ws_nummer: int,
        ws_naam: str,
        elements: list[dict[str, Any]],
    ) -> None:
        mta.info(
            "Processing workspace",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_count=len(elements),
        )

        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(
                    f"Workspace {ws_nummer!r} "
                    "contains an invalid element."
                )

            process_element(
                ws_nummer=ws_nummer,
                element_code=element["element_code"],
                element_name=element["element_name"],
            )

        mta.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=len(elements),
        )

    workspaces = dataset["workspaces"]

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            raise ValueError(
                "Each workspace must be a mapping."
            )

        elements = workspace["elements"]

        if not isinstance(elements, list):
            raise ValueError(
                f"Workspace {workspace['ws_nummer']!r} "
                "'elements' must be a list."
            )

        process_workspace(
            ws_nummer=workspace["ws_nummer"],
            ws_naam=workspace["ws_naam"],
            elements=elements,
        )


def main() -> None:
    mta = build_monitaudit()

    mta.info(
        "Tracing example started",
        example="main_trace",
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    mta.info(
        "Dataset loaded",
        dataset_path=str(DATASET_PATH),
        workspace_count=len(workspaces),
    )

    run_trace_example(
        mta=mta,
        dataset=dataset,
    )

    mta.info(
        "Tracing example completed",
        workspace_count=len(workspaces),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: tracing ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - example dataset loaded from YAML\n"
        "  - @mta.trace\n"
        "  - workspace parent traces\n"
        "  - element child traces\n"
        "  - function_start and function_end events\n"
        "  - call_id and parent_call_id\n"
        "  - automatic parameter capture\n"
        "  - default parameter capture\n"
        "  - execution duration\n"
        "  - normal var/log inside a traced function\n"
        "\n"
        "Expected trace hierarchy:\n"
        "\n"
        "  process_workspace 301\n"
        "      process_element E001\n"
        "      process_element E002\n"
        "      process_element E003\n"
        "      process_element E004\n"
        "\n"
        "  process_workspace 302\n"
        "      process_element E001\n"
        "      process_element E002\n"
        "      process_element E005\n"
        "      process_element E006\n"
        "\n"
        "  process_workspace 303\n"
        "      process_element E003\n"
        "      process_element E004\n"
        "      process_element E005\n"
        "      process_element E006\n"
        "      process_element E007\n"
        "      process_element E008\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect nested indentation above\n"
        "  - JSON: examples/output/main_trace.jsonl\n"
        "  - File: examples/output/main_trace.log\n"
        "\n"
        "For each element trace inspect:\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters\n"
        "  - duration_ms\n"
        "  - attributes.event\n"
        "\n"
        "Expected captured element parameters:\n"
        "  - ws_nummer\n"
        "  - element_code\n"
        "  - element_name\n"
        "  - validate = true\n"
        "\n"
        "Expected relationship:\n"
        "  process_workspace.call_id\n"
        "      == process_element.parent_call_id\n"
        "\n"
        "All traced calls should end with function_end.\n"
        "There should be no function_error events in this example.\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_trace.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()