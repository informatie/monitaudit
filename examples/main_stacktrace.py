"""
monitaudit CRITICAL stack-trace example.

Purpose
-------
Demonstrates how monitaudit records one severe application failure as a
CRITICAL log including the Python traceback.

The example uses the workspace/element dataset from:

    examples/data/example_dataset.yaml

The monitaudit configuration is loaded from:

    examples/config/main_stacktrace.yaml

The application processes workspaces and their elements. A specific element
deliberately raises an exception. The exception propagates to the application
boundary, where exactly one CRITICAL log is created.

This example deliberately does NOT use @obs.trace for the failing operation.

Why?
----
@obs.trace automatically creates an ERROR log when a traced function raises
an exception. If the application then also writes a CRITICAL log, the same
failure could be represented by both the trace error and the application
boundary CRITICAL log.

This example demonstrates the alternative pattern:

    workspace processing
        -> element processing
        -> exception
        -> application boundary catches exception
        -> one CRITICAL log
        -> traceback stored by monitaudit

Demonstrates
------------
- example-specific monitaudit configuration
- loading the example dataset from YAML
- workspace and element processing
- explicit CRITICAL logging
- exception propagation to the application boundary
- exception capture
- error_type
- error_message
- traceback
- structured attributes
- severe application failure handling

Use this example when
---------------------
- testing CRITICAL logging
- validating stack-trace capture
- checking FileSink traceback output
- checking JsonSink exception fields
- checking DeltaSink error columns
- demonstrating application-boundary error handling

Do not use this pattern when
----------------------------
- you want automatic tracing of the failing function
- you need call_id / parent_call_id for the failed operation
- you want function_start / function_error trace events

In those cases use @obs.trace instead.

Security
--------
Never place passwords, tokens, API keys or other secrets in exception
messages.

Trace parameter redaction does not protect secrets that have already been
embedded into an exception message or traceback.

Running the example
-------------------
From the project root:

    monitaudit_ENV=dev uv run python examples/main_stacktrace.py
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
    / "main_stacktrace.yaml"
)

FAILING_WORKSPACE = 303
FAILING_ELEMENT = "E007"


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


def process_element(
    ws_nummer: int,
    element_code: str,
    element_name: str,
) -> None:
    if (
        ws_nummer == FAILING_WORKSPACE
        and element_code == FAILING_ELEMENT
    ):
        raise RuntimeError(
            f"Element {element_code} in workspace "
            f"{ws_nummer} could not be processed"
        )

    # Simulate normal element processing.
    _ = element_name


def process_workspace(
    workspace: dict[str, Any],
) -> None:
    ws_nummer = workspace["ws_nummer"]
    elements = workspace["elements"]

    if not isinstance(elements, list):
        raise ValueError(
            f"Workspace {ws_nummer!r} "
            "'elements' must be a list."
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


def main() -> None:
    obs = build_observability(
        CONFIG_PATH
    )

    obs.info(
        "Stack-trace example started",
        example="main_stacktrace",
    )

    try:
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

            ws_nummer = workspace["ws_nummer"]
            ws_naam = workspace["ws_naam"]

            obs.info(
                "Processing workspace",
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
            )

            process_workspace(
                workspace
            )

            obs.info(
                "Workspace completed",
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
            )

    except RuntimeError as exception:
        obs.critical(
            "Application cannot continue",
            exception=exception,
            component="element_processing",
            ws_nummer=FAILING_WORKSPACE,
            element_code=FAILING_ELEMENT,
        )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit CRITICAL stack-trace example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] example-specific monitaudit configuration\n"
        "  [x] example dataset loaded from YAML\n"
        "  [x] workspaces processed sequentially\n"
        "  [x] elements processed without @obs.trace\n"
        "  [x] E007 in workspace 303 raised RuntimeError\n"
        "  [x] exception propagated to application boundary\n"
        "  [x] exactly one CRITICAL log created for the failure\n"
        "  [x] error_type captured\n"
        "  [x] error_message captured\n"
        "  [x] traceback captured\n"
        "\n"
        "Expected error information:\n"
        "  level         = CRITICAL\n"
        "  error_type    = RuntimeError\n"
        "  error_message = Element E007 in workspace 303 "
        "could not be processed\n"
        "  traceback     = populated\n"
        "\n"
        "Expected processing:\n"
        "  Workspace 301 -> completed\n"
        "  Workspace 302 -> completed\n"
        "  Workspace 303 -> E007 fails\n"
        "                   application stops\n"
        "                   CRITICAL is written\n"
        "\n"
        "Where to inspect the results:\n"
        "  - Console: CRITICAL output\n"
        "  - File: logs/examples/main_stacktrace.log\n"
        "  - JSON: logs/examples/main_stacktrace.jsonl\n"
        "\n"
        "Inspect the CRITICAL record for:\n"
        "  - level\n"
        "  - message\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "  - attributes\n"
        "\n"
        "Important:\n"
        "  There should be one exception log for this failure:\n"
        "  CRITICAL\n"
        "\n"
        "  There should not also be an automatic function_error,\n"
        "  because process_workspace() and process_element() are\n"
        "  intentionally not decorated with @obs.trace.\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_stacktrace.yaml\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()