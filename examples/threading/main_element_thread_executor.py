"""
monitaudit element-level ThreadPoolExecutor example.

Purpose
-------
Demonstrates concurrent element processing using exactly three worker
threads.

Unlike the workspace-level executor example, the individual elements are
submitted directly to the ThreadPoolExecutor.

The monitaudit configuration is loaded from:

    examples/config/main_element_thread_executor.yaml

Execution model
---------------
The executor is configured with:

    max_workers = 3

Nine independent element tasks are submitted:

    task(0)
    task(1)
    task(2)
    ...
    task(8)

At most three worker threads execute concurrently.

Every invocation of task() is decorated with @mta.trace, so every element
processing operation becomes its own independent root trace.

Demonstrates
------------
- ThreadPoolExecutor
- exactly three worker threads
- nine submitted element tasks
- worker reuse
- concurrent traced functions
- independent call_id values
- parent_call_id for root traces
- automatic parameter capture
- function_start
- function_end
- duration_ms
- thread_name
- thread_id
- collecting results with as_completed()

Use this example when
---------------------
- validating element-level parallel processing
- checking thread reuse
- checking independent trace contexts
- checking call_id uniqueness
- checking parent_call_id on root traces
- checking thread names in JsonSink
- checking thread IDs in JsonSink
- testing ContextVar isolation between workers

Expected behaviour
------------------
All nine tasks should complete successfully.

Every task should produce:

    function_start = 1
    function_end   = 1
    function_error = 0

Totals:

    function_start = 9
    function_end   = 9
    function_error = 0

Because task() is submitted directly to the executor, every invocation is
an independent root trace.

Therefore:

    task.call_id
        = unique

    task.parent_call_id
        = None

The executor can use at most three worker threads.

Important
---------
Thread scheduling is controlled by Python and the operating system.

max_workers=3 means that no more than three executor workers execute
simultaneously. It does not guarantee a particular task-to-thread mapping.

The short sleep is deliberate so concurrency and worker reuse are easier to
observe. This example is not intended as a performance benchmark.
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


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"

from typing import Any

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


CONFIG_PATH = (
    CONFIG_DIR
    / "main_element_thread_executor.yaml"
)

WORKERS = 3
TASKS = 9


def main() -> None:
    mta = build_monitaudit()

    @mta.trace
    def task(
        number: int,
    ) -> dict[str, Any]:
        """
        Process one element task as an independent root trace.
        """

        thread = threading.current_thread()

        mta.info(
            "Element processing started",
            task_number=number,
            worker_count=WORKERS,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        # Simulate element processing so concurrency and worker reuse
        # become visible in the logs
        time.sleep(0.10)

        mta.info(
            "Element processing completed",
            task_number=number,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        return {
            "task_number": number,
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    mta.info(
        "Element thread executor example started",
        example="main_element_thread_executor",
        worker_count=WORKERS,
        task_count=TASKS,
    )

    futures: list[
        Future[dict[str, Any]]
    ] = []

    results: list[
        dict[str, Any]
    ] = []

    with ThreadPoolExecutor(
        max_workers=WORKERS,
        thread_name_prefix="element-worker",
    ) as executor:
        for number in range(TASKS):
            future = executor.submit(
                task,
                number,
            )

            futures.append(
                future
            )

        mta.info(
            "All element tasks submitted",
            worker_count=WORKERS,
            submitted_tasks=len(futures),
        )

        completed_tasks = 0
        used_threads: set[str] = set()
        thread_task_counts: dict[str, int] = {}

        for future in as_completed(
            futures
        ):
            result = future.result()

            results.append(
                result
            )

            completed_tasks += 1

            thread_name = result[
                "thread_name"
            ]

            used_threads.add(
                thread_name
            )

            thread_task_counts[
                thread_name
            ] = (
                thread_task_counts.get(
                    thread_name,
                    0,
                )
                + 1
            )

            mta.info(
                "Element result received",
                task_number=result["task_number"],
                completed_tasks=completed_tasks,
                thread_name=thread_name,
                thread_id=result["thread_id"],
            )

    task_numbers = sorted(
        result["task_number"]
        for result in results
    )

    mta.info(
        "Element thread executor example completed",
        worker_count=WORKERS,
        submitted_tasks=len(futures),
        completed_tasks=completed_tasks,
        used_thread_count=len(used_threads),
        used_threads=sorted(
            used_threads
        ),
        thread_task_counts=thread_task_counts,
    )

    # Verify the functional result of the example.
    assert completed_tasks == TASKS

    assert task_numbers == list(
        range(TASKS)
    )

    assert len(used_threads) <= WORKERS


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit element ThreadPoolExecutor example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ThreadPoolExecutor\n"
        "  [x] max_workers = 3\n"
        "  [x] 9 element tasks submitted\n"
        "  [x] concurrent element processing\n"
        "  [x] worker reuse\n"
        "  [x] @mta.trace inside executor workers\n"
        "  [x] independent root traces\n"
        "  [x] unique call_id values\n"
        "  [x] automatic parameter capture\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] duration_ms\n"
        "  [x] thread_name\n"
        "  [x] thread_id\n"
        "\n"
        "Executor configuration:\n"
        "\n"
        "  workers = 3\n"
        "  tasks   = 9\n"
        "\n"
        "Expected worker names may include:\n"
        "\n"
        "  element-worker_0\n"
        "  element-worker_1\n"
        "  element-worker_2\n"
        "\n"
        "Expected trace counts:\n"
        "\n"
        "  task function_start = 9\n"
        "  task function_end   = 9\n"
        "  task function_error = 0\n"
        "\n"
        "Expected trace relationship:\n"
        "\n"
        "  Each task is submitted directly to the executor.\n"
        "\n"
        "  Therefore each task is a root trace:\n"
        "\n"
        "      task.call_id\n"
        "          = unique per task\n"
        "\n"
        "      task.parent_call_id\n"
        "          = null\n"
        "\n"
        "Expected captured parameters:\n"
        "\n"
        "  task(0) -> parameters.number = 0\n"
        "  task(1) -> parameters.number = 1\n"
        "  task(2) -> parameters.number = 2\n"
        "  ...\n"
        "  task(8) -> parameters.number = 8\n"
        "\n"
        "Expected worker reuse:\n"
        "\n"
        "  There are 9 tasks but only 3 workers.\n"
        "\n"
        "  Workers therefore process multiple element tasks.\n"
        "\n"
        "  The final monitaudit record contains:\n"
        "\n"
        "      thread_task_counts\n"
        "\n"
        "  showing the actual task distribution for the run.\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect interleaved element processing\n"
        "\n"
        "  FileSink\n"
        "    -> examples/output/main_element_thread_executor.log\n"
        "\n"
        "  JsonSink\n"
        "    -> examples/output/main_element_thread_executor.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters.number\n"
        "  - attributes.event\n"
        "  - attributes.task_number\n"
        "  - attributes.thread_name\n"
        "  - attributes.thread_id\n"
        "  - duration_ms\n"
        "\n"
        "Important verification:\n"
        "\n"
        "  Distinct task call_id values:\n"
        "      expected = 9\n"
        "\n"
        "  Distinct worker names:\n"
        "      expected <= 3\n"
        "\n"
        "  function_start:\n"
        "      expected = 9\n"
        "\n"
        "  function_end:\n"
        "      expected = 9\n"
        "\n"
        "  function_error:\n"
        "      expected = 0\n"
        "\n"
        "Difference from workspace-thread example:\n"
        "\n"
        "  main_element_thread_executor.py\n"
        "      -> individual elements/tasks are submitted to executor\n"
        "      -> every element is an independent root trace\n"
        "\n"
        "  main_workspace_thread_executor.py\n"
        "      -> complete workspace is submitted to executor\n"
        "      -> workspace is the root trace\n"
        "      -> element traces are children of workspace trace\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_element_thread_executor.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_element_thread_executor.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()