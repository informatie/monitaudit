"""
monitaudit ThreadPoolExecutor example.

Purpose
-------
Demonstrates concurrent element processing using exactly three worker
threads.

The workspace/element dataset is loaded from:

    examples/data/example_dataset.yaml

monitaudit configuration is loaded from:

    examples/config/main_thread_executor.yaml

Three worker threads are created through ThreadPoolExecutor(max_workers=3).

Each element-processing log explicitly contains:

- executor_name
- executor_count
- thread_name
- thread_id
- workspace number
- element code
- element name

This makes it possible to inspect the monitaudit var/log and see which worker
processed each element.

Demonstrates
------------
- ThreadPoolExecutor
- exactly three worker threads
- concurrent element processing
- thread identification in monitaudit logging
- structured thread attributes
- @obs.trace on worker functions
- automatic parameter capture
- call_id
- duration_ms
- waiting for all futures to complete

Important
---------
Thread scheduling is controlled by Python and the operating system.

Using max_workers=3 permits three worker threads, but a very short workload
does not guarantee that all three will visibly receive work. A short sleep
is therefore used here to simulate real processing and make concurrent use
of the worker pool visible.
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
    / "main_thread_executor.yaml"
)

EXECUTOR_NAME = "element-worker"
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
        thread = threading.current_thread()

        obs.info(
            "Element processing started on worker",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            thread_name=thread.name,
            thread_id=thread.ident,
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_code=element_code,
            element_name=element_name,
        )

        # Simulate work long enough for the worker pool to operate
        # concurrently.
        time.sleep(0.20)

        obs.info(
            "Element processing completed on worker",
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
            "ws_nummer": ws_nummer,
            "element_code": element_code,
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Thread executor example started",
        example="main_thread_executor",
        executor_name=EXECUTOR_NAME,
        executor_count=EXECUTOR_COUNT,
        workspace_count=len(workspaces),
    )

    futures: list[Future[dict[str, Any]]] = []

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
                "Submitting workspace elements",
                executor_name=EXECUTOR_NAME,
                executor_count=EXECUTOR_COUNT,
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

                future = executor.submit(
                    process_element,
                    ws_nummer,
                    ws_naam,
                    element["element_code"],
                    element["element_name"],
                )

                futures.append(future)

        obs.info(
            "All elements submitted",
            executor_name=EXECUTOR_NAME,
            executor_count=EXECUTOR_COUNT,
            submitted_tasks=len(futures),
        )

        completed_tasks = 0

        for future in as_completed(futures):
            result = future.result()
            completed_tasks += 1

            obs.info(
                "Worker result received",
                executor_name=EXECUTOR_NAME,
                executor_count=EXECUTOR_COUNT,
                completed_tasks=completed_tasks,
                ws_nummer=result["ws_nummer"],
                element_code=result["element_code"],
                worker_thread=result["thread_name"],
                worker_thread_id=result["thread_id"],
            )

    obs.info(
        "Thread executor example completed",
        executor_name=EXECUTOR_NAME,
        executor_count=EXECUTOR_COUNT,
        submitted_tasks=len(futures),
        completed_tasks=completed_tasks,
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: ThreadPoolExecutor ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - ThreadPoolExecutor\n"
        "  - max_workers = 3\n"
        "  - concurrent element processing\n"
        "  - traced worker functions\n"
        "  - worker thread names in structured logging\n"
        "  - worker thread IDs in structured logging\n"
        "  - futures collected with as_completed()\n"
        "\n"
        "Executor configuration:\n"
        "  executor_name  = element-worker\n"
        "  executor_count = 3\n"
        "\n"
        "Look for worker names similar to:\n"
        "  element-worker_0\n"
        "  element-worker_1\n"
        "  element-worker_2\n"
        "\n"
        "In JSON inspect:\n"
        "  - attributes.executor_name\n"
        "  - attributes.executor_count\n"
        "  - attributes.thread_name\n"
        "  - attributes.thread_id\n"
        "  - attributes.ws_nummer\n"
        "  - attributes.element_code\n"
        "  - call_id\n"
        "  - duration_ms\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_thread_executor.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()