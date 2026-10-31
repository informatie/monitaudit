"""
monitaudit ConsoleSink example.

Purpose
-------
Demonstrates monitaudit's human-readable console output and, in particular,
the indentation produced by ConsoleSink for nested traced functions.

The monitaudit configuration is loaded from:

    examples/config/main_console_sink.yaml

The example creates a three-level trace hierarchy:

    process_pipeline
        process_workspace
            process_element

Normal obs.info() messages are also written inside each traced function.

This makes it possible to visually inspect how ConsoleSink represents:

- root traces
- nested traces
- var/log inside traced functions
- function_start
- function_end
- call depth
- module/function locations

Demonstrates
------------
- ConsoleSink
- @obs.trace
- three-level nested tracing
- function_start
- function_end
- nested indentation
- call_id
- parent_call_id
- normal logging inside traces
- automatic parameter capture
- default parameter capture
- duration_ms
- trace-depth cleanup

Use this example when
---------------------
- validating ConsoleSink
- checking indentation
- testing nested trace depth
- checking ContextVar nesting
- checking parent_call_id relationships
- testing ConsoleSink after internal changes
- demonstrating trace hierarchy visually

Expected behaviour
------------------
The console should show a hierarchy similar to:

    process_pipeline started
        Pipeline running
        process_workspace started
            Workspace running
            process_element started
                Element running
            process_element completed
            process_element started
                Element running
            process_element completed
            Workspace completed
        process_workspace completed
        Pipeline completed
    process_pipeline completed

The actual lines additionally contain timestamp, level and function location.

Important
---------
ConsoleSink indentation is based on the trace depth stored using call_id and
parent_call_id relationships.

The start and end records for one traced function should appear at the same
indentation depth.

Ordinary var/log generated inside the traced function are displayed one level
deeper.

This example is intentionally successful. No function_error events should
be produced.
"""

from __future__ import annotations

from pathlib import Path

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_console_sink.yaml"
)


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def process_element(
        workspace: int,
        element_code: str,
        validate: bool = True,
    ) -> None:
        """
        Third trace level.

        Normal logging inside this function should appear one level below
        the process_element START/END trace records.
        """

        obs.info(
            "Element running",
            workspace=workspace,
            element_code=element_code,
            validate=validate,
        )

    @obs.trace
    def process_workspace(
        workspace: int,
    ) -> None:
        """
        Second trace level.
        """

        obs.info(
            "Workspace running",
            workspace=workspace,
        )

        process_element(
            workspace=workspace,
            element_code="E001",
        )

        process_element(
            workspace=workspace,
            element_code="E002",
        )

        obs.info(
            "Workspace completed",
            workspace=workspace,
        )

    @obs.trace
    def process_pipeline() -> None:
        """
        Root trace.
        """

        obs.info(
            "Pipeline running"
        )

        process_workspace(
            workspace=301,
        )

        obs.info(
            "Pipeline completed"
        )

    obs.info(
        "ConsoleSink example started",
        example="main_console_sink",
    )

    process_pipeline()

    obs.info(
        "ConsoleSink example completed",
        example="main_console_sink",
    )


def print_summary() -> None:
    print(
        "\n"
        "============================================================\n"
        " monitaudit ConsoleSink example completed\n"
        "============================================================\n"
        "\n"
        "What was demonstrated:\n"
        "  [x] ConsoleSink output\n"
        "  [x] @obs.trace\n"
        "  [x] three-level nested tracing\n"
        "  [x] function_start\n"
        "  [x] function_end\n"
        "  [x] trace indentation\n"
        "  [x] ordinary var/log inside traces\n"
        "  [x] automatic parameter capture\n"
        "  [x] default parameter capture\n"
        "  [x] call_id\n"
        "  [x] parent_call_id\n"
        "  [x] duration_ms\n"
        "\n"
        "Expected trace hierarchy:\n"
        "\n"
        "  process_pipeline\n"
        "      process_workspace\n"
        "          process_element E001\n"
        "          process_element E002\n"
        "\n"
        "Expected indentation conceptually:\n"
        "\n"
        "  process_pipeline started\n"
        "      Pipeline running\n"
        "\n"
        "      process_workspace started\n"
        "          Workspace running\n"
        "\n"
        "          process_element started\n"
        "              Element running\n"
        "          process_element completed\n"
        "\n"
        "          process_element started\n"
        "              Element running\n"
        "          process_element completed\n"
        "\n"
        "          Workspace completed\n"
        "      process_workspace completed\n"
        "\n"
        "      Pipeline completed\n"
        "  process_pipeline completed\n"
        "\n"
        "Expected call relationships:\n"
        "\n"
        "  process_pipeline\n"
        "      parent_call_id = null\n"
        "\n"
        "  process_workspace\n"
        "      parent_call_id = process_pipeline.call_id\n"
        "\n"
        "  process_element\n"
        "      parent_call_id = process_workspace.call_id\n"
        "\n"
        "Expected trace counts:\n"
        "\n"
        "  process_pipeline:\n"
        "      function_start = 1\n"
        "      function_end   = 1\n"
        "\n"
        "  process_workspace:\n"
        "      function_start = 1\n"
        "      function_end   = 1\n"
        "\n"
        "  process_element:\n"
        "      function_start = 2\n"
        "      function_end   = 2\n"
        "\n"
        "  function_error:\n"
        "      expected = 0\n"
        "\n"
        "Expected process_element parameters:\n"
        "\n"
        "  workspace\n"
        "      301\n"
        "\n"
        "  element_code\n"
        "      E001 / E002\n"
        "\n"
        "  validate\n"
        "      true\n"
        "\n"
        "The validate parameter is not explicitly supplied by the\n"
        "caller, but should still appear because monitaudit calls\n"
        "bound.apply_defaults() during parameter capture.\n"
        "\n"
        "Most important visual check:\n"
        "\n"
        "  START and END for the same function should have the\n"
        "  same indentation.\n"
        "\n"
        "  Normal var/log inside that function should appear one\n"
        "  indentation level deeper.\n"
        "\n"
        "Configuration:\n"
        "  examples/config/main_console_sink.yaml\n"
        "\n"
        "Run:\n"
        "  monitaudit_ENV=dev uv run python "
        "examples/main_console_sink.py\n"
        "\n"
        "============================================================\n"
    )


if __name__ == "__main__":
    main()
    print_summary()