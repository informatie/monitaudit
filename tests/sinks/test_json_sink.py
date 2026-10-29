from __future__ import annotations

import json
from pathlib import Path

import pytest

from monitaudit.models.context import LogContext
from monitaudit.models.log import (
    ErrorLog,
    InfoLog,
)
from monitaudit.sinks.json import JsonSink


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )


def test_empty_path_raises_value_error() -> None:
    with pytest.raises(
        ValueError,
        match="JSON sink path cannot be empty.",
    ):
        JsonSink("")


def test_sink_stores_path_as_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    assert isinstance(sink.path, Path)
    assert sink.path == path


def test_sink_creates_parent_directory(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "nested"
        / "logs"
        / "monitaudit.jsonl"
    )

    assert not path.parent.exists()

    JsonSink(str(path))

    assert path.parent.exists()
    assert path.parent.is_dir()


def test_sink_initialisation_does_not_create_log_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    JsonSink(str(path))

    assert not path.exists()


def test_write_creates_file(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="hello",
        context=context,
    )

    sink.write(log)

    assert path.exists()
    assert path.is_file()


def test_write_creates_valid_json(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="hello",
        context=context,
    )

    sink.write(log)

    content = path.read_text(
        encoding="utf-8",
    )

    data = json.loads(
        content.strip()
    )

    assert data["level"] == "INFO"
    assert data["message"] == "hello"


def test_write_adds_newline(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="hello",
        context=context,
    )

    sink.write(log)

    content = path.read_text(
        encoding="utf-8",
    )

    assert content.endswith("\n")


def test_write_preserves_context(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="context test",
        context=context,
    )

    sink.write(log)

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert data["context"] == {
        "application": "monitaudit-test",
        "environment": "dev",
        "correlation_id": "correlation-123",
        "run_id": "run-456",
        "attributes": {},
    }


def test_write_preserves_common_log_fields(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="complete test",
        context=context,
        call_id="call-123",
        parent_call_id="parent-456",
        parameters={
            "item": "value",
        },
        duration_ms=12.5,
        module="example.module",
        function="example_function",
        attributes={
            "event": "function_end",
        },
    )

    sink.write(log)

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert data["level"] == "INFO"
    assert data["message"] == "complete test"
    assert data["call_id"] == "call-123"
    assert data["parent_call_id"] == "parent-456"

    assert data["parameters"] == {
        "item": "value",
    }

    assert data["duration_ms"] == 12.5
    assert data["module"] == "example.module"
    assert data["function"] == "example_function"

    assert data["attributes"] == {
        "event": "function_end",
    }


def test_multiple_writes_append_lines(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    first = InfoLog(
        message="first",
        context=context,
    )

    second = InfoLog(
        message="second",
        context=context,
    )

    sink.write(first)
    sink.write(second)

    lines = path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 2

    first_data = json.loads(
        lines[0]
    )

    second_data = json.loads(
        lines[1]
    )

    assert first_data["message"] == "first"
    assert second_data["message"] == "second"


def test_new_sink_instance_appends_existing_file(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    first_sink = JsonSink(str(path))

    first_sink.write(
        InfoLog(
            message="first",
            context=context,
        )
    )

    second_sink = JsonSink(str(path))

    second_sink.write(
        InfoLog(
            message="second",
            context=context,
        )
    )

    lines = path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 2

    assert (
        json.loads(lines[0])["message"]
        == "first"
    )

    assert (
        json.loads(lines[1])["message"]
        == "second"
    )


def test_each_line_is_independently_valid_json(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    for number in range(3):
        sink.write(
            InfoLog(
                message=f"log-{number}",
                context=context,
            )
        )

    lines = path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 3

    entries = [
        json.loads(line)
        for line in lines
    ]

    assert [
        entry["message"]
        for entry in entries
    ] == [
        "log-0",
        "log-1",
        "log-2",
    ]


def test_error_log_is_serialised(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = ErrorLog(
        message="operation failed",
        context=context,
        error_type="ValueError",
        error_message="invalid value",
        traceback=[
            "Traceback:\n",
            "ValueError: invalid value\n",
        ],
    )

    sink.write(log)

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert data["level"] == "ERROR"
    assert data["message"] == "operation failed"

    assert (
        data["error_type"]
        == "ValueError"
    )

    assert (
        data["error_message"]
        == "invalid value"
    )

    assert data["traceback"] == [
        "Traceback:\n",
        "ValueError: invalid value\n",
    ]


def test_error_log_without_exception_details_is_serialised(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = ErrorLog(
        message="operation failed",
        context=context,
    )

    sink.write(log)

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert data["level"] == "ERROR"
    assert data["error_type"] is None
    assert data["error_message"] is None
    assert data["traceback"] == []


def test_unicode_message_is_preserved(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    message = "Héllo wereld 日本語"

    sink.write(
        InfoLog(
            message=message,
            context=context,
        )
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert data["message"] == message


def test_existing_content_is_not_overwritten(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    existing = json.dumps(
        {
            "message": "existing",
        }
    )

    path.write_text(
        existing + "\n",
        encoding="utf-8",
    )

    sink = JsonSink(str(path))

    sink.write(
        InfoLog(
            message="new",
            context=context,
        )
    )

    lines = path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 2

    assert (
        json.loads(lines[0])["message"]
        == "existing"
    )

    assert (
        json.loads(lines[1])["message"]
        == "new"
    )


def test_written_line_matches_model_dump_json(
    tmp_path: Path,
    context: LogContext,
) -> None:
    path = tmp_path / "monitaudit.jsonl"

    sink = JsonSink(str(path))

    log = InfoLog(
        message="exact serialisation",
        context=context,
        parameters={
            "value": 42,
        },
    )

    sink.write(log)

    content = path.read_text(
        encoding="utf-8",
    )

    assert content == (
        log.model_dump_json()
        + "\n"
    )