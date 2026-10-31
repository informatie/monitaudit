"""
monitaudit thread trace-isolation example.

Purpose
-------
Demonstrates that multiple traced root functions can execute concurrently
on separate ThreadPoolExecutor workers while maintaining independent trace
contexts.

The example starts exactly three root tasks using:

    ThreadPoolExecutor(max_workers=3)

Each root task calls one nested traced child function.

The monitaudit configuration is loaded from:

    examples/config/main_thread_trace_isolation.yaml

Execution model
---------------
Three root operations run concurrently:

    trace-worker_0
        root(1)
            child(1)

    trace-worker_1
        root(2)
            child(2)

    trace-worker_2
        root(3)
            child(3)

The exact task-to-thread assignment is controlled by Python and the
operating system and may differ between runs.

Trace relationship
------------------
Every root() invocation is an independent root trace:

    root.call_id = unique UUID
    root.parent_call_id = None

The nested child() call receives the active root call as its parent:

    child.call_id = unique UUID
    child.parent_call_id = root.call_id

The important relationship is therefore:

    child.parent_call_id
        ==
    root.call_id

for the same task_id.

Demonstrates
------------
- ThreadPoolExecutor
- three concurrent worker threads
- independent root traces
- nested child traces
- ContextVar isolation between workers
- call_id
- parent_call_id
- automatic parameter capture
- function_start
- function_end
- duration_ms
- structured thread information
- thread_name
- thread_id

Use this example when
---------------------
- validating tracing with threads
- validating ContextVar isolation
- checking that concurrent traces do not share call_id
- checking parent_call_id relationships
- checking nested traces inside worker threads
- testing ConsoleSink with concurrent traces
- inspecting thread relationships in JsonSink
- checking tracing after ContextVar changes

Expected result
---------------
There should be three independent root traces.

Each root should:
- have a unique call_id
- have parent_call_id = None
- execute exactly one child trace

Each child should:
- have its own unique call_id
- have parent_call_id equal to its root call_id
- use the same task_id as its root
- execute on the same worker thread as its root

There should normally be:
- 3 root function_start records
- 3 root function_end records
- 3 child function_start records
- 3 child function_end records
- 0 function_error records

Do not use this example when
----------------------------
- testing multiprocessing
- testing async tracing
- testing worker failures
- testing large task queues
- benchmarking monitaudit performance

Dedicated examples should be used for those scenarios.
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
    / "main_thread_trace_isolation.yaml"
)

WORKERS = 3
TASK_COUNT = 3


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def child(
        task_id: int,
    ) -> dict[str, Any]:
        """
        Execute one nested child operation.

        The active root trace should automatically become this child's
        parent trace.
        """

        thread = threading.current_thread()

        obs.info(
            "Child running",
            task_id=task_id,
            worker_count=WORKERS,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        # Keep the worker busy briefly so concurrent execution is easier
        # to observe in ConsoleSink and persisted logs
        time.sleep(0.40)

        obs.info(
            "Child completed",
            task_id=task_id,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        return {
            "task_id": task_id,
            "thread_name": thread.name,
            "thread_id": thread.ident,
        }

    @obs.trace
    def root(
        task_id: int,
    ) -> dict[str, Any]:
        """
        Execute one independent root trace on an executor worker.
        """

        thread = threading.current_thread()

        obs.info(
            "Root running",
            task_id=task_id,
            worker_count=WORKERS,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        result = child(
            task_id
        )

        obs.info(
            "Root completed",
            task_id=task_id,
            child_task_id=result["task_id"],
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        return {
            "task_id": task_id,
            "thread_name": thread.name,
            "thread_id": thread.ident,
            "child_thread_name": result[
                "thread_name"
            ],
            "child_thread_id": result[
                "thread_id"
            ],
        }

    obs.info(
        "Thread trace isolation example started",
        example="main_thread_trace_isolation",
        worker_count=WORKERS,
        task_count=TASK_COUNT,
    )

    futures: list[
        Future[dict[str, Any]]
    ] = []

    with ThreadPoolExecutor(
        max_workers=WORKERS,
        thread_name_prefix="trace-worker",
    ) as executor:
        for task_id in range(
            1,
            TASK_COUNT + 1,
        ):
            future = executor.submit(
                root,
                task_id,
            )

            futures.append(
                future
            )

        obs.info(
            "All root tasks submitted",
            worker_count=WORKERS,
            submitted_tasks=len(futures),
        )

        completed_tasks = 0
        used_threads: set[str] = set()

        for future in as_completed(
            futures
        ):
            result = future.result()

            completed_tasks += 1

            used_threads.add(
                result["thread_name"]
            )

            # root() and child() execute synchronously on the same
            # executor worker.
            assert (
                result["thread_name"]
                == result["child_thread_name"]
            )

            assert (
                result["thread_id"]
                == result["child_thread_id"]
            )

            obs.info(
                "Root task result received",
                task_id=result["task_id"],
                completed_tasks=completed_tasks,
                thread_name=result["thread_name"],
                thread_id=result["thread_id"],
            )

    obs.info(
        "Thread trace isolation example completed",
        workers=WORKERS,
        submitted_tasks=len(futures),
        completed_tasks=completed_tasks,
        used_thread_count=len(used_threads),
        used_threads=sorted(
            used_threads
        ),
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit thread trace-isolation example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ThreadPoolExecutor\n"
        "  [x] max_workers = 3\n"
        "  [x] three concurrent root tasks\n"
        "  [x] one nested child trace per root\n"
        "  [x] independent root trace contexts\n"
        "  [x] unique root call_id values\n"
        "  [x] child parent_call_id relationships\n"
        "  [x] ContextVar isolation between workers\n"
        "  [x] thread_name logging\n"
        "  [x] thread_id logging\n"
        "  [x] automatic parameter capture\n"
        "  [x] trace timing\n"
        "\n"
        "Expected worker names:\n"
        "  trace-worker_0\n"
        "  trace-worker_1\n"
        "  trace-worker_2\n"
        "\n"
        "The exact task-to-worker assignment may vary.\n"
        "\n"
        "Expected trace structure:\n"
        "\n"
        "  root(1)\n"
        "      child(1)\n"
        "\n"
        "  root(2)\n"
        "      child(2)\n"
        "\n"
        "  root(3)\n"
        "      child(3)\n"
        "\n"
        "Expected root relationship:\n"
        "\n"
        "  root.call_id\n"
        "      = unique\n"
        "\n"
        "  root.parent_call_id\n"
        "      = null\n"
        "\n"
        "Expected child relationship:\n"
        "\n"
        "  child.call_id\n"
        "      = unique\n"
        "\n"
        "  child.parent_call_id\n"
        "      == root.call_id\n"
        "\n"
        "  child.parameters.task_id\n"
        "      == root.parameters.task_id\n"
        "\n"
        "Expected trace counts:\n"
        "  root function_start   = 3\n"
        "  root function_end     = 3\n"
        "  child function_start  = 3\n"
        "  child function_end    = 3\n"
        "  function_error        = 0\n"
        "\n"
        "Expected thread relationship:\n"
        "  root and its child execute on the same worker thread\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect concurrent/interleaved trace output\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_thread_trace_isolation.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_thread_trace_isolation.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters.task_id\n"
        "  - attributes.event\n"
        "  - attributes.thread_name\n"
        "  - attributes.thread_id\n"
        "  - duration_ms\n"
        "\n"
        "Most important verification:\n"
        "\n"
        "  For every child function_start:\n"
        "\n"
        "      child.parent_call_id\n"
        "          ==\n"
        "      matching root.call_id\n"
        "\n"
        "  The match should be made using task_id.\n"
        "\n"
        "Isolation verification:\n"
        "  - root(1), root(2), root(3) have different call_id values\n"
        "  - a child never points to another task's root call_id\n"
        "  - no root has another root as its parent\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_thread_trace_isolation.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_thread_trace_isolation.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()
