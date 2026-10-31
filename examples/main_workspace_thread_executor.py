"""
monitaudit workspace-level ThreadPoolExecutor example.

Purpose
-------
Demonstrates parallel workspace processing with exactly three worker threads,
with nested element traces under every workspace trace.

The example dataset is loaded from:

    examples/data/example_dataset.yaml

The monitaudit configuration is loaded from:

    examples/config/main_workspace_thread_executor.yaml

Each workspace is submitted as one task to a ThreadPoolExecutor configured
with max_workers=3.

Within each workspace worker:
- process_workspace creates the parent trace
- process_element creates a child trace for every element
- elements are processed sequentially inside their workspace
- three workspaces may run concurrently

Every workspace and element log includes thread information so the executor
activity is visible in ConsoleSink, FileSink and JsonSink output.

Demonstrates
------------
- ThreadPoolExecutor with exactly three workers
- workspace-level parallel processing
- workspace parent traces
- nested element child traces
- call_id and parent_call_id relationships
- thread names and IDs in structured logging
- automatic parameter capture
- function_start and function_end events
- duration_ms
- collecting workspace results with as_completed()

Important
---------
Each process_workspace invocation starts in a worker thread and is therefore
an independent root trace.

Each process_element invocation runs inside process_workspace and therefore
receives the workspace call_id as its parent_call_id.

Thread scheduling is controlled by Python and the operating system. The
exact workspace-to-thread assignment may vary between runs.

YIU WANT TO Prove

process_workspace
    call_id = W

    process_element
        call_id = E1
        parent_call_id = W

    process_element
        call_id = E2
        parent_call_id = W
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
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
    / "main_workspace_thread_executor.yaml"
)

EXECUTOR_NAME = "workspace-worker"
EXECUTOR_COUNT = 3


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
    ) -> dict[str, Any]:
        """
        Process one element as a child trace of process_workspace.
        """

        thread = threading.current_thread()

        obs.info(
            "Element processing started",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            thread_name=thread.name,
            thread_id=thread.ident,
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_code=element_code,
            element_name=element_name,
        )

        # Simulate element processing.
        time.sleep(0.15)

        obs.info(
            "Element processing completed",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            thread_name=thread.name,
            thread_id=thread.ident,
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_code=element_code,
            element_name=element_name,
        )

        return {
            "element_code": element_code,
            "element_name": element_name,
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    @obs.trace
    def process_workspace(
        ws_nummer: int,
        ws_naam: str,
        elements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Process one workspace as a root trace in a worker thread.

        Every element is processed through the nested process_element trace.
        """

        thread = threading.current_thread()

        obs.info(
            "Workspace processing started on worker",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            thread_name=thread.name,
            thread_id=thread.ident,
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_count=len(elements),
        )

        processed_elements = 0
        processed_element_codes: list[str] = []

        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(
                    f"Workspace {ws_nummer!r} "
                    "contains an invalid element."
                )

            result = process_element(
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                element_code=element["element_code"],
                element_name=element["element_name"],
            )

            processed_elements += 1

            processed_element_codes.append(
                result["element_code"]
            )

        obs.info(
            "Workspace processing completed on worker",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            thread_name=thread.name,
            thread_id=thread.ident,
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=processed_elements,
            processed_element_codes=processed_element_codes,
        )

        return {
            "ws_nummer": ws_nummer,
            "ws_naam": ws_naam,
            "processed_elements": processed_elements,
            "processed_element_codes": (
                processed_element_codes
            ),
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Workspace thread executor example started",
        example="main_workspace_thread_executor",
        executor_name=EXECUTOR_NAME,
        executor_count=EXECUTOR_COUNT,
        workspace_count=len(workspaces),
    )

    futures: dict[
        Future[dict[str, Any]],
        dict[str, Any],
    ] = {}

    with ThreadPoolExecutor(
        max_workers=EXECUTOR_COUNT,
        thread_name_prefix=EXECUTOR_NAME,
    ) as executor:
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
                "Submitting workspace to executor",
                executor_name=EXECUTOR_NAME,
                executor_count=EXECUTOR_COUNT,
                ws_nummer=ws_nummer,
                ws_naam=ws_naam,
                element_count=len(elements),
            )

            future = executor.submit(
                process_workspace,
                ws_nummer,
                ws_naam,
                elements,
            )

            futures[future] = {
                "ws_nummer": ws_nummer,
                "ws_naam": ws_naam,
            }

        obs.info(
            "All workspaces submitted",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            submitted_workspaces=len(futures),
        )

        completed_workspaces = 0
        failed_workspaces = 0
        processed_elements = 0
        used_threads: set[str] = set()

        for future in as_completed(futures):
            workspace = futures[future]

            try:
                result = future.result()

            except Exception as exception:
                failed_workspaces += 1

                obs.error(
                    "Workspace worker failed",
                    exception=exception,
                    executor_name=EXECUTOR_NAME,
                    executor_count=EXECUTOR_COUNT,
                    ws_nummer=workspace["ws_nummer"],
                    ws_naam=workspace["ws_naam"],
                )

            else:
                completed_workspaces += 1

                processed_elements += result[
                    "processed_elements"
                ]

                used_threads.add(
                    result["thread_name"]
                )

                obs.info(
                    "Workspace result received",
                    executor_name=EXECUTOR_NAME,
                    executor_count=EXECUTOR_COUNT,
                    completed_workspaces=(
                        completed_workspaces
                    ),
                    ws_nummer=result["ws_nummer"],
                    ws_naam=result["ws_naam"],
                    processed_elements=result[
                        "processed_elements"
                    ],
                    processed_element_codes=result[
                        "processed_element_codes"
                    ],
                    worker_thread=result["thread_name"],
                    worker_thread_id=result["thread_id"],
                )

    obs.info(
        "Workspace thread executor example completed",
        executor_name=EXECUTOR_NAME,
        executor_count=EXECUTOR_COUNT,
        submitted_workspaces=len(futures),
        completed_workspaces=completed_workspaces,
        failed_workspaces=failed_workspaces,
        processed_elements=processed_elements,
        used_thread_count=len(used_threads),
        used_threads=sorted(used_threads),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: workspace ThreadPoolExecutor ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - workspace-level parallel processing\n"
        "  - ThreadPoolExecutor with max_workers=3\n"
        "  - one root trace per workspace\n"
        "  - nested element traces under each workspace\n"
        "  - sequential element processing per workspace\n"
        "  - three workspaces running concurrently\n"
        "  - thread names and IDs in structured logging\n"
        "  - workspace results collected with as_completed()\n"
        "\n"
        "Executor configuration:\n"
        "  executor_name  = workspace-worker\n"
        "  executor_count = 3\n"
        "\n"
        "Expected worker names:\n"
        "  workspace-worker_0\n"
        "  workspace-worker_1\n"
        "  workspace-worker_2\n"
        "\n"
        "Expected trace hierarchy per workspace:\n"
        "\n"
        "  process_workspace started\n"
        "      Workspace processing started on worker\n"
        "      process_element started\n"
        "          Element processing started\n"
        "          Element processing completed\n"
        "      process_element completed\n"
        "      ...\n"
        "      Workspace processing completed on worker\n"
        "  process_workspace completed\n"
        "\n"
        "Expected call relationships:\n"
        "  - process_workspace has a unique call_id\n"
        "  - process_workspace.parent_call_id is empty\n"
        "  - process_element has a unique call_id\n"
        "  - process_element.parent_call_id equals the\n"
        "    process_workspace.call_id\n"
        "  - var/log inside process_element use its call_id\n"
        "\n"
        "Expected thread behaviour:\n"
        "  - workspace and its elements use the same worker\n"
        "  - different workspaces can use different workers\n"
        "  - console output may be interleaved\n"
        "  - JSON records preserve the exact relationships\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters\n"
        "  - duration_ms\n"
        "  - attributes.executor_name\n"
        "  - attributes.executor_count\n"
        "  - attributes.thread_name\n"
        "  - attributes.thread_id\n"
        "  - attributes.ws_nummer\n"
        "  - attributes.element_code\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: interleaved nested workspace traces\n"
        "  - JSON: var/log/examples/"
        "main_workspace_thread_executor.jsonl\n"
        "  - File: var/log/examples/"
        "main_workspace_thread_executor.log\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/"
        "main_workspace_thread_executor.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()