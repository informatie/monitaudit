"""
monitaudit many-thread-tasks example.

Purpose
-------
Demonstrates how a ThreadPoolExecutor with three worker threads processes
more tasks than there are workers.

The monitaudit configuration is loaded from:

    examples/config/main_many_thread_tasks.yaml

The example creates:

    workers = 3
    tasks   = 20

Because there are substantially more tasks than worker threads, each worker
must be reused to process multiple tasks.

Every task is decorated with @obs.trace.

Execution model
---------------
The executor is configured with:

    ThreadPoolExecutor(
        max_workers=3,
        thread_name_prefix="many-task-worker",
    )

Twenty tasks are submitted:

    task(0)
    task(1)
    task(2)
    ...
    task(19)

At most three worker threads execute tasks concurrently.

As workers complete tasks, they are reused for later tasks.

Demonstrates
------------
- ThreadPoolExecutor
- max_workers = 3
- 20 submitted tasks
- worker-thread reuse
- concurrent traced functions
- independent call_id values
- function_start
- function_end
- duration_ms
- automatic parameter capture
- thread_name
- thread_id
- task completion tracking
- worker utilisation summary

Use this example when
---------------------
- validating traced functions in a worker pool
- demonstrating worker reuse
- checking thread names in monitaudit var/log
- checking thread IDs in monitaudit var/log
- validating many independent root traces
- checking trace counts
- checking parameter capture for task numbers

Expected behaviour
------------------
Twenty tasks should execute successfully.

Each task should generate:

    function_start
    function_end

Therefore the expected trace totals are:

    function_start = 20
    function_end   = 20
    function_error = 0

Each task should have:
- its own call_id
- parent_call_id = None
- parameters.number containing the task number

The executor can use up to three threads.

A task may execute on any of those workers. Worker assignment is controlled
by Python and the operating system and should not be hard-coded in tests.

Important
---------
The sleep is deliberate.

Without a small simulated workload, tasks may complete so quickly that the
runtime has little opportunity to make worker reuse and concurrency visible.

This is an monitaudit concurrency demonstration, not a performance benchmark.
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

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_many_thread_tasks.yaml"
)

WORKERS = 3
TASKS = 20


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def task(
        number: int,
    ) -> dict[str, Any]:
        """
        Process one numbered task.

        Every invocation is an independent root trace.
        """

        thread = threading.current_thread()

        obs.info(
            "Task running",
            task_number=number,
            worker_count=WORKERS,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        # Simulate real processing.
        #
        # This also makes concurrent execution and worker reuse easier
        # to observe in ConsoleSink and persisted logs
        time.sleep(0.05)

        obs.info(
            "Task completed",
            task_number=number,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        return {
            "task_number": number,
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    obs.info(
        "Many-thread-tasks example started",
        example="main_many_thread_tasks",
        worker_count=WORKERS,
        task_count=TASKS,
    )

    futures: list[
        Future[dict[str, Any]]
    ] = []

    with ThreadPoolExecutor(
        max_workers=WORKERS,
        thread_name_prefix="many-task-worker",
    ) as executor:
        for number in range(TASKS):
            future = executor.submit(
                task,
                number,
            )

            futures.append(
                future
            )

        obs.info(
            "All tasks submitted",
            worker_count=WORKERS,
            submitted_tasks=len(futures),
        )

        completed_tasks = 0
        completed_numbers: list[int] = []
        used_threads: set[str] = set()
        thread_task_counts: dict[str, int] = {}

        for future in as_completed(
            futures
        ):
            result = future.result()

            completed_tasks += 1

            task_number = result[
                "task_number"
            ]

            thread_name = result[
                "thread_name"
            ]

            completed_numbers.append(
                task_number
            )

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

            obs.info(
                "Task result received",
                task_number=task_number,
                completed_tasks=completed_tasks,
                thread_name=thread_name,
                thread_id=result["thread_id"],
            )

    obs.info(
        "Many-thread-tasks example completed",
        worker_count=WORKERS,
        submitted_tasks=len(futures),
        completed_tasks=completed_tasks,
        used_thread_count=len(used_threads),
        used_threads=sorted(
            used_threads
        ),
        thread_task_counts=thread_task_counts,
    )

    # Verify the functional outcome of the example.
    assert completed_tasks == TASKS

    assert sorted(
        completed_numbers
    ) == list(
        range(TASKS)
    )

    assert len(used_threads) <= WORKERS


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit many-thread-tasks example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ThreadPoolExecutor\n"
        "  [x] max_workers = 3\n"
        "  [x] 20 submitted tasks\n"
        "  [x] worker reuse\n"
        "  [x] concurrent traced functions\n"
        "  [x] independent root traces\n"
        "  [x] automatic parameter capture\n"
        "  [x] thread names\n"
        "  [x] thread IDs\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] duration_ms\n"
        "\n"
        "Executor configuration:\n"
        "\n"
        "  workers = 3\n"
        "  tasks   = 20\n"
        "\n"
        "Expected worker names may include:\n"
        "\n"
        "  many-task-worker_0\n"
        "  many-task-worker_1\n"
        "  many-task-worker_2\n"
        "\n"
        "The exact scheduling may vary between runs.\n"
        "\n"
        "Expected trace counts:\n"
        "\n"
        "  task function_start = 20\n"
        "  task function_end   = 20\n"
        "  task function_error = 0\n"
        "\n"
        "Expected trace relationship:\n"
        "\n"
        "  Every task is an independent root trace.\n"
        "\n"
        "  Therefore:\n"
        "\n"
        "    task.call_id\n"
        "        = unique per task\n"
        "\n"
        "    task.parent_call_id\n"
        "        = null\n"
        "\n"
        "Expected task parameters:\n"
        "\n"
        "  task(0)  -> parameters.number = 0\n"
        "  task(1)  -> parameters.number = 1\n"
        "  ...\n"
        "  task(19) -> parameters.number = 19\n"
        "\n"
        "Worker reuse:\n"
        "\n"
        "  20 tasks cannot execute simultaneously on a pool with\n"
        "  max_workers=3.\n"
        "\n"
        "  Workers therefore process multiple tasks over the life\n"
        "  of the executor.\n"
        "\n"
        "  Inspect thread_task_counts in the final monitaudit record\n"
        "  to see the actual distribution for this run.\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect interleaved task execution\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_many_thread_tasks.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_many_thread_tasks.jsonl\n"
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
        "Useful verification:\n"
        "\n"
        "  Count distinct task call_id values:\n"
        "      expected = 20\n"
        "\n"
        "  Count task function_start:\n"
        "      expected = 20\n"
        "\n"
        "  Count task function_end:\n"
        "      expected = 20\n"
        "\n"
        "  Count task function_error:\n"
        "      expected = 0\n"
        "\n"
        "  Count distinct thread names:\n"
        "      expected <= 3\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_many_thread_tasks.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_many_thread_tasks.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()