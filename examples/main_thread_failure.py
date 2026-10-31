"""
monitaudit ThreadPoolExecutor failure-handling example.

Purpose
-------
Demonstrates what happens when one traced worker task fails while other
worker tasks complete successfully.

The example creates exactly three tasks using:

    ThreadPoolExecutor(max_workers=3)

Task 2 deliberately raises RuntimeError.

Tasks 1 and 3 complete successfully.

The monitaudit configuration is loaded from:

    examples/config/main_thread_failure.yaml

Execution model
---------------
Three tasks are submitted:

    task(1) -> success
    task(2) -> RuntimeError
    task(3) -> success

Because task() is decorated with @obs.trace, monitaudit automatically creates:

Successful task:

    function_start
        ->
    function_end

Failed task:

    function_start
        ->
    function_error

The exception raised by task(2) is stored in the Future.

The main thread later receives that exception when:

    future.result()

is called.

The outer application catches the RuntimeError, writes a structured warning,
and continues collecting the remaining futures.

Demonstrates
------------
- ThreadPoolExecutor
- max_workers = 3
- concurrent traced tasks
- successful worker execution
- worker failure
- Future exception propagation
- function_start
- function_end
- function_error
- error_type
- error_message
- traceback
- handling worker exceptions in the main thread
- continuing after one worker task fails
- collecting futures with as_completed()

Use this example when
---------------------
- validating @obs.trace inside ThreadPoolExecutor
- testing worker exceptions
- verifying function_error records
- checking Future exception propagation
- validating that successful workers are unaffected
- testing thread trace isolation after failures
- checking JsonSink error information
- checking FileSink traceback output

Expected result
---------------
Exactly three task executions occur.

Expected task results:

    task(1) -> success
    task(2) -> failure
    task(3) -> success

Expected trace lifecycle:

    task(1)
        function_start = 1
        function_end   = 1
        function_error = 0

    task(2)
        function_start = 1
        function_end   = 0
        function_error = 1

    task(3)
        function_start = 1
        function_end   = 1
        function_error = 0

Totals:

    function_start = 3
    function_end   = 2
    function_error = 1

The task(2) function_error should contain:

    error_type    = RuntimeError
    error_message = Deliberate worker failure
    traceback     = populated

Important
---------
The worker exception does not disappear.

@obs.trace var/log the function_error and then re-raises the original exception.

ThreadPoolExecutor stores that exception in the Future.

Calling:

    future.result()

re-raises it in the main thread.

The example deliberately handles that exception so processing of the other
Future results can continue.
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
    / "main_thread_failure.yaml"
)

WORKERS = 3
TASK_COUNT = 3
FAILING_TASK = 2


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def task(
        number: int,
    ) -> dict[str, Any]:
        """
        Execute one worker task.

        Task 2 deliberately fails. Tasks 1 and 3 complete successfully.
        """

        thread = threading.current_thread()

        obs.info(
            "Worker task started",
            task_number=number,
            worker_count=WORKERS,
            thread_name=thread.name,
            thread_id=thread.ident,
        )

        # Simulate work so concurrent worker activity is visible.
        time.sleep(0.10)

        if number == FAILING_TASK:
            raise RuntimeError(
                "Deliberate worker failure"
            )

        obs.info(
            "Worker task completed",
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
        "Thread failure example started",
        example="main_thread_failure",
        worker_count=WORKERS,
        task_count=TASK_COUNT,
        failing_task=FAILING_TASK,
    )

    futures: dict[
        Future[dict[str, Any]],
        int,
    ] = {}

    successful_tasks = 0
    failed_tasks = 0
    completed_task_numbers: list[int] = []
    failed_task_numbers: list[int] = []
    used_threads: set[str] = set()

    with ThreadPoolExecutor(
        max_workers=WORKERS,
        thread_name_prefix="failure-worker",
    ) as executor:
        for number in range(
            1,
            TASK_COUNT + 1,
        ):
            future = executor.submit(
                task,
                number,
            )

            futures[future] = number

        obs.info(
            "All worker tasks submitted",
            submitted_tasks=len(futures),
            worker_count=WORKERS,
        )

        for future in as_completed(
            futures
        ):
            task_number = futures[future]

            try:
                result = future.result()

            except RuntimeError as exception:
                failed_tasks += 1

                failed_task_numbers.append(
                    task_number
                )

                obs.warning(
                    "Worker failure handled",
                    task_number=task_number,
                    error_type=type(exception).__name__,
                    error_message=str(exception),
                )

            else:
                successful_tasks += 1

                completed_task_numbers.append(
                    task_number
                )

                used_threads.add(
                    result["thread_name"]
                )

                obs.info(
                    "Worker result received",
                    task_number=result["task_number"],
                    thread_name=result["thread_name"],
                    thread_id=result["thread_id"],
                )

    obs.info(
        "Thread failure example completed",
        submitted_tasks=len(futures),
        successful_tasks=successful_tasks,
        failed_tasks=failed_tasks,
        completed_task_numbers=sorted(
            completed_task_numbers
        ),
        failed_task_numbers=sorted(
            failed_task_numbers
        ),
        used_threads=sorted(
            used_threads
        ),
    )

    # Runtime verification of the expected example behaviour.
    assert successful_tasks == 2
    assert failed_tasks == 1

    assert sorted(
        completed_task_numbers
    ) == [
        1,
        3,
    ]

    assert failed_task_numbers == [
        2,
    ]


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit ThreadPoolExecutor failure example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ThreadPoolExecutor\n"
        "  [x] max_workers = 3\n"
        "  [x] three traced worker tasks\n"
        "  [x] task 1 completes successfully\n"
        "  [x] task 2 deliberately fails\n"
        "  [x] task 3 completes successfully\n"
        "  [x] failed task produces function_error\n"
        "  [x] successful tasks produce function_end\n"
        "  [x] worker exception is stored in Future\n"
        "  [x] future.result() re-raises worker exception\n"
        "  [x] main thread catches expected RuntimeError\n"
        "  [x] remaining futures continue to be processed\n"
        "\n"
        "Expected task results:\n"
        "\n"
        "  task(1) -> SUCCESS\n"
        "  task(2) -> FAILURE\n"
        "  task(3) -> SUCCESS\n"
        "\n"
        "Expected total trace events:\n"
        "\n"
        "  function_start = 3\n"
        "  function_end   = 2\n"
        "  function_error = 1\n"
        "\n"
        "Expected failed trace:\n"
        "\n"
        "  function      = task\n"
        "  task number   = 2\n"
        "  error_type    = RuntimeError\n"
        "  error_message = Deliberate worker failure\n"
        "  traceback     = populated\n"
        "\n"
        "Expected worker names:\n"
        "\n"
        "  failure-worker_0\n"
        "  failure-worker_1\n"
        "  failure-worker_2\n"
        "\n"
        "The exact task-to-worker assignment may vary.\n"
        "\n"
        "Expected execution flow:\n"
        "\n"
        "  executor submits task(1)\n"
        "  executor submits task(2)\n"
        "  executor submits task(3)\n"
        "\n"
        "      task(1) start\n"
        "      task(2) start\n"
        "      task(3) start\n"
        "\n"
        "      task(1) end\n"
        "      task(2) error\n"
        "      task(3) end\n"
        "\n"
        "  main thread collects future results\n"
        "  RuntimeError from task(2) is handled\n"
        "  application completes normally\n"
        "\n"
        "Where to inspect the results:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> inspect concurrent worker output\n"
        "    -> inspect task(2) function_error\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_thread_failure.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_thread_failure.jsonl\n"
        "\n"
        "In JSON inspect:\n"
        "  - function\n"
        "  - call_id\n"
        "  - parent_call_id\n"
        "  - parameters.number\n"
        "  - attributes.event\n"
        "  - attributes.thread_name\n"
        "  - attributes.thread_id\n"
        "  - error_type\n"
        "  - error_message\n"
        "  - traceback\n"
        "  - duration_ms\n"
        "\n"
        "Important verification:\n"
        "\n"
        "  Task 2 should contain:\n"
        "\n"
        "      function_start\n"
        "      function_error\n"
        "\n"
        "  but NOT:\n"
        "\n"
        "      function_end\n"
        "\n"
        "  Tasks 1 and 3 should contain:\n"
        "\n"
        "      function_start\n"
        "      function_end\n"
        "\n"
        "  but NOT:\n"
        "\n"
        "      function_error\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_thread_failure.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_thread_failure.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()