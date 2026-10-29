# tests/stability/test_traceback_sink_persistence.py

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from monitaudit import Observability
from monitaudit.sinks.delta import DeltaSink
from monitaudit.sinks.file import FileSink
from monitaudit.sinks.json import JsonSink
from monitaudit.utilities import get_spark_session


TRACEBACK_MESSAGE = "traceback sink persistence failure"
TRACEBACK_FUNCTION = "raise_sink_persistence_error"


# ---------------------------------------------------------------------------
# Test application functions
# ---------------------------------------------------------------------------


def raise_sink_persistence_error() -> None:
    nested_failure()


def nested_failure() -> None:
    raise RuntimeError(TRACEBACK_MESSAGE)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def execute_failing_trace(
    observability: Observability,
) -> None:
    @observability.trace
    def traced_application_function() -> None:
        raise_sink_persistence_error()

    with pytest.raises(
        RuntimeError,
        match=TRACEBACK_MESSAGE,
    ) as exc_info:
        traced_application_function()

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == TRACEBACK_MESSAGE


def assert_traceback_integrity(
    traceback_text: str,
) -> None:
    assert traceback_text.strip()
    assert "Traceback" in traceback_text
    assert f"RuntimeError: {TRACEBACK_MESSAGE}" in traceback_text
    assert "traced_application_function" in traceback_text
    assert TRACEBACK_FUNCTION in traceback_text
    assert "nested_failure" in traceback_text
    assert "\n" in traceback_text
    assert len(traceback_text.splitlines()) >= 4


def recursively_find_tracebacks(
    value: Any,
) -> list[str]:
    traceback_keys = {
        "traceback",
        "traceback_text",
        "stack_trace",
        "stacktrace",
    }

    found: list[str] = []

    if isinstance(value, dict):
        for key, nested_value in value.items():
            is_traceback = (
                isinstance(key, str)
                and key.casefold() in traceback_keys
            )

            if (
                is_traceback
                and isinstance(nested_value, str)
            ):
                found.append(nested_value)
                continue

            if (
                is_traceback
                and isinstance(nested_value, list)
                and all(
                    isinstance(line, str)
                    for line in nested_value
                )
            ):
                found.append(
                    "".join(nested_value)
                )
                continue

            found.extend(
                recursively_find_tracebacks(
                    nested_value
                )
            )

    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            found.extend(
                recursively_find_tracebacks(
                    nested_value
                )
            )

    return found


def find_traceback_containing(
    values: list[Any],
    expected_message: str,
) -> str:
    tracebacks: list[str] = []

    for value in values:
        tracebacks.extend(
            recursively_find_tracebacks(value)
        )

    matching_tracebacks = [
        traceback_text
        for traceback_text in tracebacks
        if expected_message in traceback_text
    ]

    assert matching_tracebacks, (
        "No persisted traceback contained "
        f"{expected_message!r}. "
        f"Found {len(tracebacks)} traceback value(s)."
    )

    return matching_tracebacks[-1]


def flush_sink(
    sink: object,
) -> None:
    flush = getattr(
        sink,
        "flush",
        None,
    )

    if callable(flush):
        flush()


def close_sink(
    sink: object,
) -> None:
    close = getattr(
        sink,
        "close",
        None,
    )

    if callable(close):
        close()


# ---------------------------------------------------------------------------
# FileSink
# ---------------------------------------------------------------------------


@pytest.fixture
def file_sink_path(
    tmp_path: Path,
) -> Path:
    return tmp_path / "monitaudit-file.log"


@pytest.fixture
def file_sink(
    file_sink_path: Path,
) -> Iterator[FileSink]:
    sink = FileSink(
        path=file_sink_path,
    )

    try:
        yield sink
    finally:
        flush_sink(sink)
        close_sink(sink)


@pytest.fixture
def file_observability(
    file_sink: FileSink,
) -> Observability:
    return Observability(
        "traceback-file-sink-test",
        "test",
        file_sink,
        timer=True,
    )


def test_file_sink_persists_traceback(
    file_observability: Observability,
    file_sink: FileSink,
    file_sink_path: Path,
) -> None:
    execute_failing_trace(
        file_observability
    )

    flush_sink(file_sink)

    assert file_sink_path.exists()
    assert file_sink_path.is_file()