"""
monitaudit sink-failure isolation example using raise mode.

Purpose
-------
Demonstrates how monitaudit behaves when one configured sink fails while
sink_failure_mode is set to:

    raise

A deliberately broken sink is inserted before the normally configured
monitaudit sinks.

When monitaudit writes a log record:

- BrokenSink is called first
- BrokenSink deliberately raises RuntimeError
- monitaudit records the sink failure internally
- monitaudit continues attempting the remaining sinks
- ConsoleSink can still receive the record
- JsonSink can still receive the record
- FileSink can still receive the record
- after all sinks have been attempted, monitaudit raises RuntimeError
- the application can catch that final monitaudit exception

The monitaudit configuration is loaded from:

    examples/config/main_sink_failure_raise.yaml

Demonstrates
------------
- sink failure isolation
- sink_failure_mode = raise
- deliberately failing sink
- remaining sinks still being attempted
- RuntimeError after sink processing
- original sink exception preserved as __cause__
- application handling of the monitaudit failure
- successful sinks writing before the final exception is raised

Use this example when
---------------------
- validating monitauditLogger._write()
- testing sink_failure_mode = raise
- confirming all sinks are attempted before failure is propagated
- checking exception chaining
- comparing raise behaviour with the continue-mode example

Expected behaviour
------------------
BrokenSink raises:

    RuntimeError("Deliberate BrokenSink failure")

monitaudit should report the individual sink failure to stderr.

monitaudit should still attempt the other configured sinks.

After all sinks have been attempted, monitaudit should raise:

    RuntimeError(
        "monitaudit sink failure(s): BrokenSink"
    )

The raised monitaudit RuntimeError should have the original BrokenSink
RuntimeError as its __cause__.

Important
---------
This behaviour is different from sink_failure_mode = continue.

continue:

    BrokenSink fails
        -> remaining sinks run
        -> application continues normally

raise:

    BrokenSink fails
        -> remaining sinks run
        -> monitaudit raises after sink processing
        -> application receives RuntimeError

Expected output files
---------------------
Even though the application receives RuntimeError afterwards, the configured
working sinks should already have received the record.

Check:

    var/log/examples/main_sink_failure_raise.log

    var/log/examples/main_sink_failure_raise.jsonl

Do not use this example when
----------------------------
- validating continue mode
- testing a real filesystem failure
- testing Delta infrastructure failures
- benchmarking sink performance

Use main_sink_failure_continue.py for continue-mode behaviour.
"""

from __future__ import annotations

from pathlib import Path

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_sink_failure_raise.yaml"
)


class BrokenSink(Sink):
    """
    Sink that deliberately fails on every write.

    The counter allows the example to verify that the sink was actually
    invoked before monitaudit raised the combined sink-failure exception.
    """

    def __init__(self) -> None:
        self.write_count = 0

    def write(
        self,
        log: BaseLog,
    ) -> None:
        self.write_count += 1

        raise RuntimeError(
            "Deliberate BrokenSink failure"
        )


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    broken_sink = BrokenSink()

    configured_sinks = (
        obs.logger.sinks
    )

    # BrokenSink is deliberately placed first.
    #
    # This is important because the example must demonstrate that monitaudit
    # does not immediately stop processing sinks after the first failure.
    obs.logger.sinks = (
        broken_sink,
        *configured_sinks,
    )

    print(
        "\n"
        "Starting sink-failure RAISE-mode example.\n"
        "\n"
        "BrokenSink will fail first.\n"
        "The remaining configured sinks should still be attempted.\n"
        "monitaudit should then raise RuntimeError.\n"
    )

    monitaudit_exception: RuntimeError | None = None

    try:
        obs.info(
            "Every sink is attempted before raise mode reports failure",
            example="main_sink_failure_raise",
            sink_failure_mode="raise",
            broken_sink="BrokenSink",
        )

    except RuntimeError as exception:
        monitaudit_exception = exception

        print(
            "\n"
            "Expected monitaudit failure received:\n"
            f"  {type(exception).__name__}: "
            f"{exception}\n"
        )

        if exception.__cause__ is not None:
            print(
                "Original sink failure:\n"
                f"  {type(exception.__cause__).__name__}: "
                f"{exception.__cause__}\n"
            )

    else:
        raise AssertionError(
            "sink_failure_mode='raise' did not raise"
        )

    if broken_sink.write_count != 1:
        raise AssertionError(
            "BrokenSink should have been called exactly once "
            f"but was called {broken_sink.write_count} times."
        )

    if monitaudit_exception is None:
        raise AssertionError(
            "Expected monitaudit RuntimeError was not captured."
        )

    expected_message = (
        "monitaudit sink failure(s): BrokenSink"
    )

    if str(monitaudit_exception) != expected_message:
        raise AssertionError(
            "Unexpected monitaudit exception message: "
            f"{monitaudit_exception}"
        )

    cause = monitaudit_exception.__cause__

    if not isinstance(
        cause,
        RuntimeError,
    ):
        raise AssertionError(
            "monitaudit RuntimeError should preserve the "
            "original RuntimeError as __cause__."
        )

    if str(cause) != (
        "Deliberate BrokenSink failure"
    ):
        raise AssertionError(
            "Unexpected original sink exception: "
            f"{cause}"
        )

    print(
        "Verification successful:\n"
        f"  BrokenSink writes = {broken_sink.write_count}\n"
        "  monitaudit raised   = RuntimeError\n"
        "  original cause    = RuntimeError\n"
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit sink-failure RAISE example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] deliberately failing Sink implementation\n"
        "  [x] BrokenSink inserted before configured sinks\n"
        "  [x] BrokenSink raises RuntimeError\n"
        "  [x] monitaudit catches the individual sink exception\n"
        "  [x] sink failure is reported to stderr\n"
        "  [x] remaining configured sinks are still attempted\n"
        "  [x] monitaudit raises after sink processing\n"
        "  [x] application catches the monitaudit RuntimeError\n"
        "  [x] original sink failure is preserved as __cause__\n"
        "\n"
        "Expected execution model:\n"
        "\n"
        "  monitauditLogger._write(log)\n"
        "      |\n"
        "      +-- BrokenSink\n"
        "      |      -> RuntimeError\n"
        "      |      -> failure collected\n"
        "      |      -> failure reported to stderr\n"
        "      |\n"
        "      +-- ConsoleSink\n"
        "      |      -> log written\n"
        "      |\n"
        "      +-- JsonSink\n"
        "      |      -> log written\n"
        "      |\n"
        "      +-- FileSink\n"
        "      |      -> log written\n"
        "      |\n"
        "      +-- all sinks attempted\n"
        "      |\n"
        "      +-- RuntimeError raised\n"
        "\n"
        "Expected monitaudit exception:\n"
        "\n"
        "  RuntimeError:\n"
        "    monitaudit sink failure(s): BrokenSink\n"
        "\n"
        "Expected original cause:\n"
        "\n"
        "  RuntimeError:\n"
        "    Deliberate BrokenSink failure\n"
        "\n"
        "Important difference from continue mode:\n"
        "\n"
        "  CONTINUE\n"
        "    BrokenSink fails\n"
        "    remaining sinks run\n"
        "    application continues\n"
        "\n"
        "  RAISE\n"
        "    BrokenSink fails\n"
        "    remaining sinks run\n"
        "    monitaudit raises afterwards\n"
        "\n"
        "Where to inspect successful sink output:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> the log record should appear before the final exception\n"
        "\n"
        "  FileSink\n"
        "    -> var/log/examples/main_sink_failure_raise.log\n"
        "\n"
        "  JsonSink\n"
        "    -> var/log/examples/main_sink_failure_raise.jsonl\n"
        "\n"
        "Important verification:\n"
        "\n"
        "  Even though monitaudit eventually raised RuntimeError,\n"
        "  the working sinks should already contain the INFO record.\n"
        "\n"
        "  This proves raise mode means:\n"
        "\n"
        "      attempt all sinks first\n"
        "      raise afterwards\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_sink_failure_raise.yaml\n"
        "\n"
        "Required configuration:\n"
        "  sink_failure_mode: raise\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_sink_failure_raise.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()