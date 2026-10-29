from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from monitaudit.sinks.console import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
    ConsoleSink,
)


def make_log(
    *,
    message: str = "Test message",
    level: str = "INFO",
    module: str | None = "__main__",
    function: str | None = "test_function",
    call_id: str | None = None,
    parent_call_id: str | None = None,
    event: str | None = None,
    parameters: dict[str, object] | None = None,
) -> MagicMock:
    log = MagicMock()

    log.timestamp = datetime(
        2026,
        10,
        24,
        7,
        30,
        0,
        tzinfo=timezone.utc,
    )

    log.level = level
    log.message = message
    log.module = module
    log.function = function
    log.call_id = call_id
    log.parent_call_id = parent_call_id
    log.parameters = parameters or {}

    log.attributes = {}

    if event is not None:
        log.attributes["event"] = event

    return log


def test_default_configuration() -> None:
    sink = ConsoleSink()

    assert sink.indent_size == 4
    assert sink.location_width == 30
    assert sink.parameters == ()
    assert sink._depths == {}


def test_custom_configuration() -> None:
    sink = ConsoleSink(
        indent_size=2,
        location_width=40,
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    assert sink.indent_size == 2
    assert sink.location_width == 40

    assert sink.parameters == (
        "ws_nummer",
        "element_shortname",
    )


def test_negative_indent_size_raises() -> None:
    with pytest.raises(
        ValueError,
        match="indent_size must be 0 or greater",
    ):
        ConsoleSink(
            indent_size=-1,
        )


def test_negative_location_width_raises() -> None:
    with pytest.raises(
        ValueError,
        match="location_width must be 0 or greater",
    ):
        ConsoleSink(
            location_width=-1,
        )


def test_format_parameters_returns_empty_when_not_configured() -> None:
    sink = ConsoleSink()

    log = make_log(
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
        },
    )

    result = sink._format_parameters(log)

    assert result == ""


def test_format_parameters_returns_empty_when_no_matching_parameters() -> None:
    sink = ConsoleSink(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    log = make_log(
        parameters={
            "other_value": 123,
        },
    )

    result = sink._format_parameters(log)

    assert result == ""


def test_format_parameters_selects_configured_parameters() -> None:
    sink = ConsoleSink(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    log = make_log(
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
            "internal_value": "hidden",
        },
    )

    result = sink._format_parameters(log)

    assert result == (
        ' parameters={"ws_nummer": 302, '
        '"element_shortname": "E001"}'
    )


def test_format_parameters_preserves_configuration_order() -> None:
    sink = ConsoleSink(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    log = make_log(
        parameters={
            "element_shortname": "E001",
            "ws_nummer": 302,
        },
    )

    result = sink._format_parameters(log)

    assert result == (
        ' parameters={"ws_nummer": 302, '
        '"element_shortname": "E001"}'
    )


def test_format_parameters_preserves_reversed_configuration_order() -> None:
    sink = ConsoleSink(
        parameters=[
            "element_shortname",
            "ws_nummer",
        ],
    )

    log = make_log(
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
        },
    )

    result = sink._format_parameters(log)

    assert result == (
        ' parameters={"element_shortname": "E001", '
        '"ws_nummer": 302}'
    )


def test_format_parameters_ignores_missing_configured_parameter() -> None:
    sink = ConsoleSink(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    log = make_log(
        parameters={
            "ws_nummer": 302,
        },
    )

    result = sink._format_parameters(log)

    assert result == (
        ' parameters={"ws_nummer": 302}'
    )


def test_format_parameters_handles_non_json_value() -> None:
    sink = ConsoleSink(
        parameters=[
            "value",
        ],
    )

    custom_value = object()

    log = make_log(
        parameters={
            "value": custom_value,
        },
    )

    result = sink._format_parameters(log)

    assert "parameters=" in result
    assert "value" in result


def test_format_location_with_module_and_function() -> None:
    log = make_log(
        module="example.module",
        function="process_element",
    )

    result = ConsoleSink._format_location(
        log
    )

    assert result == (
        "example.module.process_element"
    )


def test_format_location_with_module_only() -> None:
    log = make_log(
        module="example.module",
        function=None,
    )

    result = ConsoleSink._format_location(
        log
    )

    assert result == "example.module"


def test_format_location_with_function_only() -> None:
    log = make_log(
        module=None,
        function="process_element",
    )

    result = ConsoleSink._format_location(
        log
    )

    assert result == "process_element"


def test_format_location_empty() -> None:
    log = make_log(
        module=None,
        function=None,
    )

    result = ConsoleSink._format_location(
        log
    )

    assert result == ""


def test_log_without_call_id_has_depth_zero() -> None:
    sink = ConsoleSink()

    log = make_log(
        call_id=None,
    )

    assert sink._get_depth(log) == 0


def test_root_function_start_has_depth_zero() -> None:
    sink = ConsoleSink()

    log = make_log(
        call_id="root",
        parent_call_id=None,
        event=FUNCTION_START,
    )

    assert sink._get_depth(log) == 0


def test_child_function_start_has_parent_depth_plus_one() -> None:
    sink = ConsoleSink()

    sink._depths["parent"] = 2

    log = make_log(
        call_id="child",
        parent_call_id="parent",
        event=FUNCTION_START,
    )

    assert sink._get_depth(log) == 3


def test_child_start_with_unknown_parent_uses_depth_one() -> None:
    sink = ConsoleSink()

    log = make_log(
        call_id="child",
        parent_call_id="unknown",
        event=FUNCTION_START,
    )

    assert sink._get_depth(log) == 1


def test_regular_log_inside_trace_uses_call_depth_plus_one() -> None:
    sink = ConsoleSink()

    sink._depths["call-1"] = 2

    log = make_log(
        call_id="call-1",
        event=None,
    )

    assert sink._get_depth(log) == 3


def test_function_end_uses_current_call_depth() -> None:
    sink = ConsoleSink()

    sink._depths["call-1"] = 2

    log = make_log(
        call_id="call-1",
        event=FUNCTION_END,
    )

    assert sink._get_depth(log) == 2


def test_function_error_uses_current_call_depth() -> None:
    sink = ConsoleSink()

    sink._depths["call-1"] = 2

    log = make_log(
        call_id="call-1",
        event=FUNCTION_ERROR,
    )

    assert sink._get_depth(log) == 2


def test_update_depth_stores_function_start() -> None:
    sink = ConsoleSink()

    log = make_log(
        call_id="call-1",
        event=FUNCTION_START,
    )

    sink._update_depth(
        log,
        2,
    )

    assert sink._depths == {
        "call-1": 2,
    }


def test_update_depth_removes_function_end() -> None:
    sink = ConsoleSink()

    sink._depths["call-1"] = 2

    log = make_log(
        call_id="call-1",
        event=FUNCTION_END,
    )

    sink._update_depth(
        log,
        2,
    )

    assert "call-1" not in sink._depths


def test_update_depth_removes_function_error() -> None:
    sink = ConsoleSink()

    sink._depths["call-1"] = 2

    log = make_log(
        call_id="call-1",
        event=FUNCTION_ERROR,
    )

    sink._update_depth(
        log,
        2,
    )

    assert "call-1" not in sink._depths


def test_update_depth_ignores_log_without_call_id() -> None:
    sink = ConsoleSink()

    log = make_log(
        call_id=None,
        event=FUNCTION_START,
    )

    sink._update_depth(
        log,
        3,
    )

    assert sink._depths == {}


def test_write_outputs_basic_log(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink(
        location_width=30,
    )

    log = make_log(
        message="Application started",
        module="__main__",
        function="main",
    )

    sink.write(log)

    output = capsys.readouterr().out

    assert (
        "2026-10-24T07:30:00+00:00"
        in output
    )

    assert "INFO" in output
    assert "__main__.main" in output
    assert "Application started" in output


def test_write_outputs_configured_parameters_in_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink(
        parameters=[
            "ws_nummer",
            "element_shortname",
        ],
    )

    log = make_log(
        message="process_element started",
        module="__main__",
        function="process_element",
        call_id="element-1",
        parent_call_id="workspace-1",
        event=FUNCTION_START,
        parameters={
            "element_shortname": "E001",
            "ws_nummer": 302,
        },
    )

    sink._depths["workspace-1"] = 0

    sink.write(log)

    output = capsys.readouterr().out

    expected_parameters = (
        'parameters={"ws_nummer": 302, '
        '"element_shortname": "E001"}'
    )

    assert expected_parameters in output

    assert output.index(
        '"ws_nummer"'
    ) < output.index(
        '"element_shortname"'
    )


def test_write_indents_nested_function_start(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink(
        indent_size=4,
        location_width=30,
    )

    sink._depths["parent"] = 0

    log = make_log(
        message="process_element started",
        call_id="child",
        parent_call_id="parent",
        event=FUNCTION_START,
    )

    sink.write(log)

    output = capsys.readouterr().out

    assert "    process_element started" in output

    assert sink._depths["child"] == 1


def test_write_registers_function_start_depth(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink()

    log = make_log(
        message="process_workspace started",
        call_id="workspace-1",
        event=FUNCTION_START,
    )

    sink.write(log)

    capsys.readouterr()

    assert sink._depths == {
        "workspace-1": 0,
    }


def test_write_removes_depth_after_function_end(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink()

    sink._depths["workspace-1"] = 1

    log = make_log(
        message="process_workspace completed",
        call_id="workspace-1",
        event=FUNCTION_END,
    )

    sink.write(log)

    capsys.readouterr()

    assert "workspace-1" not in sink._depths


def test_write_removes_depth_after_function_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sink = ConsoleSink()

    sink._depths["workspace-1"] = 1

    log = make_log(
        message="process_workspace failed",
        call_id="workspace-1",
        event=FUNCTION_ERROR,
    )

    sink.write(log)

    capsys.readouterr()

    assert "workspace-1" not in sink._depths


def test_nested_trace_depth_sequence() -> None:
    sink = ConsoleSink(
        indent_size=4,
    )

    pipeline_start = make_log(
        call_id="pipeline",
        parent_call_id=None,
        event=FUNCTION_START,
    )

    pipeline_depth = sink._get_depth(
        pipeline_start
    )

    assert pipeline_depth == 0

    sink._update_depth(
        pipeline_start,
        pipeline_depth,
    )

    workspace_start = make_log(
        call_id="workspace",
        parent_call_id="pipeline",
        event=FUNCTION_START,
    )

    workspace_depth = sink._get_depth(
        workspace_start
    )

    assert workspace_depth == 1

    sink._update_depth(
        workspace_start,
        workspace_depth,
    )

    element_start = make_log(
        call_id="element",
        parent_call_id="workspace",
        event=FUNCTION_START,
    )

    element_depth = sink._get_depth(
        element_start
    )

    assert element_depth == 2

    sink._update_depth(
        element_start,
        element_depth,
    )

    element_log = make_log(
        call_id="element",
    )

    assert (
        sink._get_depth(element_log)
        == 3
    )

    element_end = make_log(
        call_id="element",
        parent_call_id="workspace",
        event=FUNCTION_END,
    )

    assert (
        sink._get_depth(element_end)
        == 2
    )

    sink._update_depth(
        element_end,
        2,
    )

    assert "element" not in sink._depths

    workspace_end = make_log(
        call_id="workspace",
        parent_call_id="pipeline",
        event=FUNCTION_END,
    )

    assert (
        sink._get_depth(workspace_end)
        == 1
    )

    sink._update_depth(
        workspace_end,
        1,
    )

    assert "workspace" not in sink._depths

    pipeline_end = make_log(
        call_id="pipeline",
        parent_call_id=None,
        event=FUNCTION_END,
    )

    assert (
        sink._get_depth(pipeline_end)
        == 0
    )

    sink._update_depth(
        pipeline_end,
        0,
    )

    assert sink._depths == {}