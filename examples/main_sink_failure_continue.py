"""
monitaudit sink-failure isolation example using continue mode.

Purpose
-------
Demonstrates how monitaudit behaves when one configured sink fails while
sink_failure_mode is set to:

    continue

A deliberately broken sink is inserted before the normally configured
monitaudit sinks.

When monitaudit writes a log record:

- BrokenSink is called
- BrokenSink deliberately raises RuntimeError
- monitaudit reports the sink failure to stderr
- monitaudit continues writing to the remaining sinks
- ConsoleSink still receives the log
- JsonSink still receives the log
- FileSink still receives the log
- the application continues normally

The monitaudit configuration is loaded from:

    examples/config/main_sink_failure_continue.yaml

Demonstrates
------------
- sink failure isolation
- sink_failure_mode = continue
- deliberately failing sink
- remaining sinks still being attempted
- application continuation after sink failure
- multiple writes after a sink failure
- normal logging after infrastructure failure

Use this example when
---------------------
- validating monitaudit sink isolation
- testing changes to monitauditLogger._write()
- testing sink_failure_mode
- checking that one broken sink does not block other sinks
- validating ConsoleSink after another sink fails
- validating FileSink after another sink fails
- validating JsonSink after another sink fails

Expected behaviour
------------------
Every monitaudit write reaches BrokenSink first.

BrokenSink raises:

    RuntimeError("Deliberate BrokenSink failure")

monitaudit should report something similar to:

    monitaudit sink failure:
    BrokenSink:
    RuntimeError:
    Deliberate BrokenSink failure

The exact stderr formatting is defined by monitauditLogger.

Because the failure mode is "continue", monitaudit must then continue with
the remaining sinks.

The application itself must not receive the BrokenSink exception.

Expected output files
---------------------
The successfully configured sinks should still contain records:

    logs/examples/main_sink_failure_continue.log

    logs/examples/main_sink_failure_continue.jsonl

Important
---------
Multiple monitaudit log calls are deliberately made after BrokenSink has been
installed.

This proves that continuing does not only work for the first failed write.
Subsequent application logging also continues.

Do not use this example when
----------------------------
- testing sink_failure_mode = raise
- testing a real filesystem failure
- testing a real Delta infrastructure failure
- benchmarking sink performance

A separate raise-mode example should be used for sink_failure_mode = raise.
"""

from __future__ import annotations

from pathlib import Path

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.utilities.build_observability import (
    build_observability,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_sink_failure_continue.yaml"
)


class BrokenSink(Sink):
    """
    Sink that deliberately fails on every write.

    This sink exists only for demonstrating monitaudit's sink-failure
    isolation behaviour.
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
    obs = build_observability(
        CONFIG_PATH
    )

    broken_sink = BrokenSink()

    # Add the deliberately broken sink before the sinks created from
    # configuration.
    configured_sinks = obs.logger.sinks

    obs.logger.sinks = (
        broken_sink,
        *configured_sinks,
    )

    print(
        "\n"
        "Starting sink-failure continue-mode example.\n"
        "\n"
        "BrokenSink will deliberately fail for every log record.\n"
        "monitaudit should report those failures to stderr while the\n"
        "remaining sinks continue writing.\n"
    )

    obs.info(
        "Sink failure example started",
        example="main_sink_failure_continue",
        sink_failure_mode="continue",
        broken_sink="BrokenSink",
    )

    obs.debug(
        "Debug message after BrokenSink installation",
        sequence=1,
    )

    obs.info(
        "Information message after BrokenSink failure",
        sequence=2,
    )

    obs.warning(
        "Warning message after BrokenSink failure",
        sequence=3,
    )

    # The application has reached this point despite several BrokenSink
    # failures. That itself demonstrates continue-mode behaviour.
    obs.info(
        "Application still running after sink failures",
        sequence=4,
        broken_sink_write_count=(
            broken_sink.write_count
        ),
    )

    # Do not log the final count through monitaudit because doing so would
    # itself increment BrokenSink.write_count again.
    final_write_count = (
        broken_sink.write_count
    )

    print(
        "\n"
        "Application reached the end of the example.\n"
        f"BrokenSink write attempts: {final_write_count}\n"
    )

    if final_write_count < 1:
        raise AssertionError(
            "BrokenSink was never called."
        )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit sink-failure CONTINUE example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] deliberately failing Sink implementation\n"
        "  [x] BrokenSink inserted before configured sinks\n"
        "  [x] BrokenSink raises RuntimeError\n"
        "  [x] monitaudit catches the sink exception\n"
        "  [x] sink failure is reported to stderr\n"
        "  [x] remaining sinks are still attempted\n"
        "  [x] application continues executing\n"
        "  [x] subsequent log calls still work\n"
        "\n"
        "Expected execution model:\n"
        "\n"
        "  monitauditLogger._write(log)\n"
        "      |\n"
        "      +-- BrokenSink\n"
        "      |      -> RuntimeError\n"
        "      |      -> failure reported\n"
        "      |\n"
        "      +-- ConsoleSink\n"
        "      |      -> log written\n"
        "      |\n"
        "      +-- JsonSink\n"
        "      |      -> log written\n"
        "      |\n"
        "      +-- FileSink\n"
        "             -> log written\n"
        "\n"
        "  application continues\n"
        "\n"
        "Expected stderr behaviour:\n"
        "\n"
        "  monitaudit sink failure: BrokenSink: RuntimeError:\n"
        "  Deliberate BrokenSink failure\n"
        "\n"
        "You should see one sink-failure report for every monitaudit\n"
        "write attempted while BrokenSink is installed.\n"
        "\n"
        "Where to inspect successful sink output:\n"
        "\n"
        "  ConsoleSink\n"
        "    -> normal application log messages should still appear\n"
        "\n"
        "  FileSink\n"
        "    -> logs/examples/main_sink_failure_continue.log\n"
        "\n"
        "  JsonSink\n"
        "    -> logs/examples/main_sink_failure_continue.jsonl\n"
        "\n"
        "Important verification:\n"
        "\n"
        "  The application reached this summary.\n"
        "\n"
        "  Therefore BrokenSink failures did not propagate back to\n"
        "  the application while sink_failure_mode=continue.\n"
        "\n"
        "JSON verification:\n"
        "  Look for messages such as:\n"
        "\n"
        "    Sink failure example started\n"
        "    Debug message after BrokenSink installation\n"
        "    Information message after BrokenSink failure\n"
        "    Warning message after BrokenSink failure\n"
        "    Application still running after sink failures\n"
        "\n"
        "All should still be present in JsonSink output even though\n"
        "BrokenSink failed for every one of those writes.\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_sink_failure_continue.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_sink_failure_continue.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()