from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from monitaudit.sinks.file import FileSink


def make_log(
    *,
    message: str = "Test message",
    level: str = "INFO",
    module: str | None = "__main__",
    function: str | None = "test_function",
    application: str = "test-app",
    environment: str = "dev",
    correlation_id: str = "correlation-123",
    run_id: str | None = "run-456",
    parameters: dict[str, object] | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    traceback_lines: list[str] | None = None,
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

    log.context = SimpleNamespace(
        application=application,
        environment=environment,
        correlation_id=correlation_id,
        run_id=run_id,
    )

    log.parameters = (
        parameters
        if parameters is not None
        else {}
    )

    log.error_type = error_type
    log.error_message = error_message
    log.traceback = traceback_lines

    return log


def test_empty_path_raises_value_error() -> None:
    with pytest.raises(
        ValueError,
        match="File sink path cannot be empty",
    ):
        FileSink("")


def test_path_is_converted_to_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    assert sink.path == path
    assert isinstance(sink.path, Path)


def test_parent_directories_are_created(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "nested"
        / "logs"
        / "monitaudit.log"
    )

    assert not path.parent.exists()

    FileSink(
        str(path)
    )

    assert path.parent.exists()
    assert path.parent.is_dir()


def test_format_basic_log() -> None:
    log = make_log(
        message="Application started",
    )

    result = FileSink._format(log)

    assert "2026-10-24T07:30:00+00:00" in result
    assert "INFO" in result
    assert "application=test-app" in result
    assert "environment=dev" in result
    assert "correlation_id=correlation-123" in result
    assert "run_id=run-456" in result
    assert "__main__.test_function" in result
    assert "Application started" in result
    assert "parameters={}" in result


def test_format_without_run_id_uses_dash() -> None:
    log = make_log(
        run_id=None,
    )

    result = FileSink._format(log)

    assert "run_id=-" in result


def test_format_location_with_module_and_function() -> None:
    log = make_log(
        module="example.module",
        function="process_element",
    )

    result = FileSink._format(log)

    assert "example.module.process_element" in result


def test_format_location_with_module_only() -> None:
    log = make_log(
        module="example.module",
        function=None,
    )

    result = FileSink._format(log)

    assert "example.module" in result


def test_format_location_with_function_only() -> None:
    log = make_log(
        module=None,
        function="process_element",
    )

    result = FileSink._format(log)

    assert "process_element" in result


def test_format_location_empty() -> None:
    log = make_log(
        module=None,
        function=None,
    )

    result = FileSink._format(log)

    assert "Test message" in result


def test_format_empty_parameters() -> None:
    log = make_log(
        parameters={},
    )

    result = FileSink._format(log)

    assert "parameters={}" in result


def test_format_parameters() -> None:
    log = make_log(
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
        },
    )

    result = FileSink._format(log)

    assert (
        'parameters={"ws_nummer": 302, '
        '"element_shortname": "E001"}'
        in result
    )


def test_parameter_order_is_preserved() -> None:
    log = make_log(
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
        },
    )

    result = FileSink._format(log)

    assert (
        result.index('"ws_nummer"')
        < result.index('"element_shortname"')
    )


def test_reversed_parameter_order_is_preserved() -> None:
    log = make_log(
        parameters={
            "element_shortname": "E001",
            "ws_nummer": 302,
        },
    )

    result = FileSink._format(log)

    assert (
        result.index('"element_shortname"')
        < result.index('"ws_nummer"')
    )


def test_format_integer_parameter() -> None:
    log = make_log(
        parameters={
            "ws_nummer": 302,
        },
    )

    result = FileSink._format(log)

    assert '"ws_nummer": 302' in result


def test_format_string_parameter() -> None:
    log = make_log(
        parameters={
            "element_shortname": "E001",
        },
    )

    result = FileSink._format(log)

    assert '"element_shortname": "E001"' in result


def test_non_json_parameter_uses_string_representation() -> None:
    class CustomValue:
        def __str__(self) -> str:
            return "custom-value"

    log = make_log(
        parameters={
            "value": CustomValue(),
        },
    )

    result = FileSink._format(log)

    assert '"value": "custom-value"' in result


def test_format_error_returns_empty_for_normal_log() -> None:
    log = make_log()

    result = FileSink._format_error(log)

    assert result == ""


def test_format_error_type_only() -> None:
    log = make_log(
        error_type="ValueError",
    )

    result = FileSink._format_error(log)

    assert result == "error_type=ValueError"


def test_format_error_message_only() -> None:
    log = make_log(
        error_message="Invalid value",
    )

    result = FileSink._format_error(log)

    assert result == "error_message=Invalid value"


def test_format_error_type_and_message() -> None:
    log = make_log(
        error_type="ValueError",
        error_message="Invalid value",
    )

    result = FileSink._format_error(log)

    assert result == (
        "error_type=ValueError\n"
        "error_message=Invalid value"
    )


def test_format_traceback_only() -> None:
    log = make_log(
        traceback_lines=[
            "Traceback (most recent call last):\n",
            '  File "example.py", line 10\n',
            "ValueError: Invalid value\n",
        ],
    )

    result = FileSink._format_error(log)

    assert result == (
        "traceback:\n"
        "Traceback (most recent call last):\n"
        '  File "example.py", line 10\n'
        "ValueError: Invalid value"
    )


def test_format_complete_error() -> None:
    log = make_log(
        error_type="ValueError",
        error_message="Invalid value",
        traceback_lines=[
            "Traceback:\n",
            "ValueError: Invalid value\n",
        ],
    )

    result = FileSink._format_error(log)

    assert result == (
        "error_type=ValueError\n"
        "error_message=Invalid value\n"
        "traceback:\n"
        "Traceback:\n"
        "ValueError: Invalid value"
    )


def test_format_error_details_follow_log_line() -> None:
    log = make_log(
        message="process_element failed",
        level="ERROR",
        error_type="ValueError",
        error_message="Invalid element",
    )

    result = FileSink._format(log)
    lines = result.splitlines()

    assert "process_element failed" in lines[0]
    assert lines[1] == "error_type=ValueError"
    assert lines[2] == "error_message=Invalid element"


def test_traceback_trailing_newline_is_removed() -> None:
    log = make_log(
        traceback_lines=[
            "Traceback:\n",
            "ValueError: failure\n",
        ],
    )

    result = FileSink._format_error(log)

    assert not result.endswith("\n")
    assert result.endswith(
        "ValueError: failure"
    )


def test_write_creates_log_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            message="Application started",
        )
    )

    assert path.exists()
    assert path.is_file()


def test_write_writes_formatted_log(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            message="Application started",
            parameters={
                "ws_nummer": 301,
            },
        )
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert "Application started" in content
    assert '"ws_nummer": 301' in content


def test_write_ends_with_newline(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log()
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert content.endswith("\n")


def test_write_appends_logs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            message="First log",
        )
    )

    sink.write(
        make_log(
            message="Second log",
        )
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert "First log" in content
    assert "Second log" in content

    assert (
        content.index("First log")
        < content.index("Second log")
    )


def test_write_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    path.write_text(
        "existing-line\n",
        encoding="utf-8",
    )

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            message="New log",
        )
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert content.startswith(
        "existing-line\n"
    )

    assert "New log" in content


def test_write_multiple_log_records_on_separate_lines(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            message="First log",
        )
    )

    sink.write(
        make_log(
            message="Second log",
        )
    )

    content = path.read_text(
        encoding="utf-8"
    )

    lines = content.splitlines()

    assert len(lines) == 2
    assert "First log" in lines[0]
    assert "Second log" in lines[1]


def test_write_error_log(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    sink.write(
        make_log(
            level="ERROR",
            message="Processing failed",
            error_type="ValueError",
            error_message="Invalid value",
        )
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert "Processing failed" in content
    assert "error_type=ValueError" in content
    assert "error_message=Invalid value" in content


def test_write_error_log_with_traceback(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.log"

    sink = FileSink(
        str(path)
    )

    log = make_log(
        level="ERROR",
        message="process_element failed",
        parameters={
            "ws_nummer": 302,
            "element_shortname": "E001",
        },
        error_type="ValueError",
        error_message="Invalid element",
        traceback_lines=[
            "Traceback (most recent call last):\n",
            '  File "example.py", line 10\n',
            "ValueError: Invalid element\n",
        ],
    )

    sink.write(log)

    content = path.read_text(
        encoding="utf-8"
    )

    assert "process_element failed" in content

    assert (
        'parameters={"ws_nummer": 302, '
        '"element_shortname": "E001"}'
        in content
    )

    assert "error_type=ValueError" in content
    assert "error_message=Invalid element" in content
    assert "traceback:" in content

    assert (
        "Traceback (most recent call last):"
        in content
    )

    assert (
        'File "example.py", line 10'
        in content
    )

    assert (
        "ValueError: Invalid element"
        in content
    )