# tests/sinks/test_console.py

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)
from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.sinks.console import (
    TRACE_END_EVENTS,
    ConsoleSink,
)

TIMESTAMP = datetime(
    2026,
    11,
    2,
    19,
    30,
    tzinfo=UTC,
)


def make_log(
    *,
    level: str = "INFO",
    message: str = "test message",
    module: str | None = "example.module",
    function: str | None = "example_function",
    call_id: str | None = None,
    parent_call_id: str | None = None,
    event: str | None = None,
    parameters: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> BaseLog:
    """
    Create the minimal log-shaped object required by ConsoleSink.
    """

    log_attributes = dict(
        attributes or {}
    )

    if event is not None:
        log_attributes["event"] = event

    value = SimpleNamespace(
        timestamp=TIMESTAMP,
        level=level,
        message=message,
        module=module,
        function=function,
        call_id=call_id,
        parent_call_id=parent_call_id,
        parameters=(
            dict(parameters)
            if parameters is not None
            else {}
        ),
        attributes=log_attributes,
    )

    return cast(
        BaseLog,
        value,
    )


class CustomValue:
    def __str__(self) -> str:
        return "custom-value"


class TestConstants:
    def test_trace_end_events(
        self,
    ) -> None:
        assert TRACE_END_EVENTS == frozenset(
            {
                FUNCTION_END,
                FUNCTION_ERROR,
            }
        )

    def test_trace_end_events_is_frozenset(
        self,
    ) -> None:
        assert isinstance(
            TRACE_END_EVENTS,
            frozenset,
        )

    def test_function_start_is_not_end_event(
        self,
    ) -> None:
        assert (
            FUNCTION_START
            not in TRACE_END_EVENTS
        )


class TestConstruction:
    def test_console_sink_is_sink_subclass(
        self,
    ) -> None:
        assert issubclass(
            ConsoleSink,
            Sink,
        )

    def test_default_settings(
        self,
    ) -> None:
        sink = ConsoleSink()

        assert sink.indent_size == 4
        assert sink.location_width == 30
        assert sink.parameters == ()
        assert sink._depths == {}

    def test_custom_settings(
        self,
    ) -> None:
        sink = ConsoleSink(
            indent_size=2,
            location_width=50,
            parameters=[
                "customer_id",
                "region",
            ],
        )

        assert sink.indent_size == 2
        assert sink.location_width == 50
        assert sink.parameters == (
            "customer_id",
            "region",
        )

    def test_parameters_are_copied_to_tuple(
        self,
    ) -> None:
        parameters = [
            "customer_id",
        ]

        sink = ConsoleSink(
            parameters=parameters,
        )

        parameters.append(
            "region"
        )

        assert sink.parameters == (
            "customer_id",
        )

    def test_none_parameters_become_empty_tuple(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=None,
        )

        assert sink.parameters == ()

    def test_empty_parameters_become_empty_tuple(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[],
        )

        assert sink.parameters == ()

    @pytest.mark.parametrize(
        "indent_size",
        [
            0,
            1,
            4,
            100,
        ],
    )
    def test_accepts_non_negative_indent_size(
        self,
        indent_size: int,
    ) -> None:
        sink = ConsoleSink(
            indent_size=indent_size,
        )

        assert (
            sink.indent_size
            == indent_size
        )

    @pytest.mark.parametrize(
        "indent_size",
        [
            -1,
            -10,
        ],
    )
    def test_rejects_negative_indent_size(
        self,
        indent_size: int,
    ) -> None:
        with pytest.raises(
            ValueError
        ) as exception_info:
            ConsoleSink(
                indent_size=indent_size,
            )

        assert (
            str(exception_info.value)
            == (
                "indent_size must be "
                "0 or greater."
            )
        )

    @pytest.mark.parametrize(
        "location_width",
        [
            0,
            1,
            30,
            100,
        ],
    )
    def test_accepts_non_negative_location_width(
        self,
        location_width: int,
    ) -> None:
        sink = ConsoleSink(
            location_width=location_width,
        )

        assert (
            sink.location_width
            == location_width
        )

    @pytest.mark.parametrize(
        "location_width",
        [
            -1,
            -10,
        ],
    )
    def test_rejects_negative_location_width(
        self,
        location_width: int,
    ) -> None:
        with pytest.raises(
            ValueError
        ) as exception_info:
            ConsoleSink(
                location_width=location_width,
            )

        assert (
            str(exception_info.value)
            == (
                "location_width must be "
                "0 or greater."
            )
        )


class TestFormatLocation:
    def test_module_and_function(
        self,
    ) -> None:
        log = make_log(
            module="example.module",
            function="process",
        )

        assert (
            ConsoleSink._format_location(
                log
            )
            == "example.module.process"
        )

    def test_only_module(
        self,
    ) -> None:
        log = make_log(
            module="example.module",
            function=None,
        )

        assert (
            ConsoleSink._format_location(
                log
            )
            == "example.module"
        )

    def test_only_function(
        self,
    ) -> None:
        log = make_log(
            module=None,
            function="process",
        )

        assert (
            ConsoleSink._format_location(
                log
            )
            == "process"
        )

    def test_no_location(
        self,
    ) -> None:
        log = make_log(
            module=None,
            function=None,
        )

        assert (
            ConsoleSink._format_location(
                log
            )
            == ""
        )

    def test_empty_values_are_ignored(
        self,
    ) -> None:
        log = make_log(
            module="",
            function="",
        )

        assert (
            ConsoleSink._format_location(
                log
            )
            == ""
        )


class TestFormatParameters:
    def test_returns_empty_when_no_parameters_configured(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            parameters={
                "customer_id": 42,
            }
        )

        assert (
            sink._format_parameters(
                log
            )
            == ""
        )

    def test_returns_empty_when_selected_parameter_missing(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "customer_id",
            ]
        )

        log = make_log(
            parameters={
                "region": "eu",
            }
        )

        assert (
            sink._format_parameters(
                log
            )
            == ""
        )

    def test_formats_selected_parameter(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "customer_id",
            ]
        )

        log = make_log(
            parameters={
                "customer_id": 42,
                "region": "eu",
            }
        )

        assert (
            sink._format_parameters(
                log
            )
            == ' parameters={"customer_id": 42}'
        )

    def test_formats_multiple_selected_parameters(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "customer_id",
                "region",
            ]
        )

        log = make_log(
            parameters={
                "customer_id": 42,
                "region": "eu",
                "ignored": True,
            }
        )

        result = sink._format_parameters(
            log
        )

        assert result == (
            ' parameters={"customer_id": 42, '
            '"region": "eu"}'
        )

    def test_parameter_order_follows_configured_order(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "region",
                "customer_id",
            ]
        )

        log = make_log(
            parameters={
                "customer_id": 42,
                "region": "eu",
            }
        )

        assert (
            sink._format_parameters(
                log
            )
            == (
                ' parameters={"region": "eu", '
                '"customer_id": 42}'
            )
        )

    def test_missing_selected_parameters_are_skipped(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "missing",
                "customer_id",
            ]
        )

        log = make_log(
            parameters={
                "customer_id": 42,
            }
        )

        assert (
            sink._format_parameters(
                log
            )
            == ' parameters={"customer_id": 42}'
        )

    def test_custom_value_uses_string_fallback(
        self,
    ) -> None:
        sink = ConsoleSink(
            parameters=[
                "value",
            ]
        )

        log = make_log(
            parameters={
                "value": CustomValue(),
            }
        )

        result = sink._format_parameters(
            log
        )

        assert result == (
            ' parameters={"value": "custom-value"}'
        )


class TestGetDepth:
    def test_log_without_call_id_has_zero_depth(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id=None,
        )

        assert sink._get_depth(
            log
        ) == 0

    def test_root_function_start_has_zero_depth(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="root",
            parent_call_id=None,
            event=FUNCTION_START,
        )

        assert sink._get_depth(
            log
        ) == 0

    def test_child_function_start_is_parent_depth_plus_one(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths[
            "parent"
        ] = 2

        log = make_log(
            call_id="child",
            parent_call_id="parent",
            event=FUNCTION_START,
        )

        assert sink._get_depth(
            log
        ) == 3

    def test_child_start_with_unknown_parent_uses_depth_one(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="child",
            parent_call_id="unknown",
            event=FUNCTION_START,
        )

        assert sink._get_depth(
            log
        ) == 1

    @pytest.mark.parametrize(
        "event",
        [
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_trace_end_returns_existing_call_depth(
        self,
        event: str,
    ) -> None:
        sink = ConsoleSink()

        sink._depths[
            "call-1"
        ] = 3

        log = make_log(
            call_id="call-1",
            event=event,
        )

        assert sink._get_depth(
            log
        ) == 3

    @pytest.mark.parametrize(
        "event",
        [
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_unknown_trace_end_has_zero_depth(
        self,
        event: str,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="unknown",
            event=event,
        )

        assert sink._get_depth(
            log
        ) == 0

    def test_normal_log_uses_call_depth_plus_one(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths[
            "call-1"
        ] = 2

        log = make_log(
            call_id="call-1",
            event=None,
        )

        assert sink._get_depth(
            log
        ) == 3

    def test_normal_log_with_unknown_call_has_depth_one(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="unknown",
        )

        assert sink._get_depth(
            log
        ) == 1


class TestUpdateDepth:
    def test_log_without_call_id_does_nothing(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id=None,
            event=FUNCTION_START,
        )

        sink._update_depth(
            log,
            5,
        )

        assert sink._depths == {}

    def test_function_start_registers_depth(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="call-1",
            event=FUNCTION_START,
        )

        sink._update_depth(
            log,
            3,
        )

        assert sink._depths == {
            "call-1": 3,
        }

    @pytest.mark.parametrize(
        "event",
        [
            FUNCTION_END,
            FUNCTION_ERROR,
        ],
    )
    def test_trace_end_removes_depth(
        self,
        event: str,
    ) -> None:
        sink = ConsoleSink()

        sink._depths[
            "call-1"
        ] = 2

        log = make_log(
            call_id="call-1",
            event=event,
        )

        sink._update_depth(
            log,
            2,
        )

        assert (
            "call-1"
            not in sink._depths
        )

    def test_unknown_end_call_is_safe(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="unknown",
            event=FUNCTION_END,
        )

        sink._update_depth(
            log,
            0,
        )

        assert sink._depths == {}

    def test_normal_event_does_not_change_depths(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths[
            "call-1"
        ] = 2

        log = make_log(
            call_id="call-1",
            event="custom_event",
        )

        sink._update_depth(
            log,
            5,
        )

        assert sink._depths == {
            "call-1": 2,
        }


class TestTraceLifecycle:
    def test_root_start_is_registered_at_zero(
        self,
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="root",
            event=FUNCTION_START,
        )

        depth = sink._get_depth(
            log
        )

        sink._update_depth(
            log,
            depth,
        )

        assert depth == 0
        assert sink._depths == {
            "root": 0,
        }

    def test_child_start_is_registered_below_parent(
        self,
    ) -> None:
        sink = ConsoleSink()

        root = make_log(
            call_id="root",
            event=FUNCTION_START,
        )

        root_depth = (
            sink._get_depth(root)
        )
        sink._update_depth(
            root,
            root_depth,
        )

        child = make_log(
            call_id="child",
            parent_call_id="root",
            event=FUNCTION_START,
        )

        child_depth = (
            sink._get_depth(child)
        )

        sink._update_depth(
            child,
            child_depth,
        )

        assert root_depth == 0
        assert child_depth == 1
        assert sink._depths == {
            "root": 0,
            "child": 1,
        }

    def test_three_level_trace_depth(
        self,
    ) -> None:
        sink = ConsoleSink()

        root = make_log(
            call_id="root",
            event=FUNCTION_START,
        )
        root_depth = sink._get_depth(
            root
        )
        sink._update_depth(
            root,
            root_depth,
        )

        child = make_log(
            call_id="child",
            parent_call_id="root",
            event=FUNCTION_START,
        )
        child_depth = sink._get_depth(
            child
        )
        sink._update_depth(
            child,
            child_depth,
        )

        grandchild = make_log(
            call_id="grandchild",
            parent_call_id="child",
            event=FUNCTION_START,
        )
        grandchild_depth = (
            sink._get_depth(
                grandchild
            )
        )
        sink._update_depth(
            grandchild,
            grandchild_depth,
        )

        assert root_depth == 0
        assert child_depth == 1
        assert grandchild_depth == 2

    def test_function_end_removes_only_finished_call(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths.update(
            {
                "root": 0,
                "child": 1,
            }
        )

        child_end = make_log(
            call_id="child",
            parent_call_id="root",
            event=FUNCTION_END,
        )

        depth = sink._get_depth(
            child_end
        )

        sink._update_depth(
            child_end,
            depth,
        )

        assert depth == 1
        assert sink._depths == {
            "root": 0,
        }

    def test_function_error_removes_failed_call(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths.update(
            {
                "root": 0,
                "child": 1,
            }
        )

        error_log = make_log(
            call_id="child",
            parent_call_id="root",
            event=FUNCTION_ERROR,
        )

        depth = sink._get_depth(
            error_log
        )

        sink._update_depth(
            error_log,
            depth,
        )

        assert depth == 1
        assert sink._depths == {
            "root": 0,
        }


class TestWrite:
    def test_write_outputs_log(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            location_width=0,
        )

        log = make_log(
            message="Hello MonitAudit",
        )

        result = sink.write(
            log
        )

        assert result is None

        output = (
            capsys.readouterr().out
        )

        assert TIMESTAMP.isoformat() in output
        assert "INFO" in output
        assert (
            "example.module.example_function"
            in output
        )
        assert (
            "Hello MonitAudit"
            in output
        )

    def test_write_updates_trace_depth_after_print(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink()

        log = make_log(
            call_id="call-1",
            event=FUNCTION_START,
        )

        assert sink._depths == {}

        sink.write(
            log
        )

        capsys.readouterr()

        assert sink._depths == {
            "call-1": 0,
        }

    def test_write_removes_depth_on_function_end(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink()

        start = make_log(
            call_id="call-1",
            event=FUNCTION_START,
        )

        sink.write(start)

        assert "call-1" in sink._depths

        end = make_log(
            call_id="call-1",
            event=FUNCTION_END,
        )

        sink.write(end)

        capsys.readouterr()

        assert (
            "call-1"
            not in sink._depths
        )

    def test_write_removes_depth_on_function_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink()

        start = make_log(
            call_id="call-1",
            event=FUNCTION_START,
        )

        sink.write(start)

        error = make_log(
            call_id="call-1",
            event=FUNCTION_ERROR,
        )

        sink.write(error)

        capsys.readouterr()

        assert (
            "call-1"
            not in sink._depths
        )

    def test_write_with_selected_parameters(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            location_width=0,
            parameters=[
                "customer_id",
            ],
        )

        log = make_log(
            parameters={
                "customer_id": 42,
                "ignored": "value",
            }
        )

        sink.write(log)

        output = (
            capsys.readouterr().out
        )

        assert (
            'parameters={"customer_id": 42}'
            in output
        )
        assert "ignored" not in output

    def test_write_without_parameter_selection_does_not_output_parameters(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            location_width=0,
        )

        log = make_log(
            parameters={
                "customer_id": 42,
            }
        )

        sink.write(log)

        output = (
            capsys.readouterr().out
        )

        assert (
            "customer_id"
            not in output
        )
        assert (
            "parameters="
            not in output
        )


class TestIndentation:
    def test_root_start_has_no_trace_indent(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            indent_size=4,
            location_width=0,
        )

        log = make_log(
            call_id="root",
            event=FUNCTION_START,
            module=None,
            function=None,
            message="ROOT",
        )

        sink.write(log)

        output = (
            capsys.readouterr()
            .out
        )

        assert "ROOT" in output

    def test_nested_function_is_indented(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            indent_size=4,
            location_width=0,
        )

        root = make_log(
            call_id="root",
            event=FUNCTION_START,
            module=None,
            function=None,
            message="ROOT",
        )

        sink.write(root)

        child = make_log(
            call_id="child",
            parent_call_id="root",
            event=FUNCTION_START,
            module=None,
            function=None,
            message="CHILD",
        )

        sink.write(child)

        output = (
            capsys.readouterr()
            .out
        )

        lines = output.splitlines()

        assert len(lines) == 2
        assert "ROOT" in lines[0]
        assert "    CHILD" in lines[1]

    def test_message_inside_root_call_is_indented_one_level(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            indent_size=2,
            location_width=0,
        )

        sink.write(
            make_log(
                call_id="root",
                event=FUNCTION_START,
                module=None,
                function=None,
                message="START",
            )
        )

        sink.write(
            make_log(
                call_id="root",
                event=None,
                module=None,
                function=None,
                message="INSIDE",
            )
        )

        lines = (
            capsys.readouterr()
            .out
            .splitlines()
        )

        assert len(lines) == 2
        assert "  INSIDE" in lines[1]

    def test_zero_indent_size_produces_no_trace_indentation(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sink = ConsoleSink(
            indent_size=0,
            location_width=0,
        )

        sink._depths[
            "call-1"
        ] = 10

        sink.write(
            make_log(
                call_id="call-1",
                module=None,
                function=None,
                message="MESSAGE",
            )
        )

        output = (
            capsys.readouterr().out
        )

        assert "MESSAGE" in output


class TestDepthIsolation:
    def test_independent_root_calls_keep_independent_depths(
        self,
    ) -> None:
        sink = ConsoleSink()

        first = make_log(
            call_id="first",
            event=FUNCTION_START,
        )
        second = make_log(
            call_id="second",
            event=FUNCTION_START,
        )

        first_depth = (
            sink._get_depth(first)
        )
        sink._update_depth(
            first,
            first_depth,
        )

        second_depth = (
            sink._get_depth(second)
        )
        sink._update_depth(
            second,
            second_depth,
        )

        assert sink._depths == {
            "first": 0,
            "second": 0,
        }

    def test_completing_one_root_does_not_remove_another(
        self,
    ) -> None:
        sink = ConsoleSink()

        sink._depths.update(
            {
                "first": 0,
                "second": 0,
            }
        )

        first_end = make_log(
            call_id="first",
            event=FUNCTION_END,
        )

        depth = sink._get_depth(
            first_end
        )

        sink._update_depth(
            first_end,
            depth,
        )

        assert sink._depths == {
            "second": 0,
        }