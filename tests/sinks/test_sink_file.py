# tests/sinks/test_file.py

from __future__ import annotations

import csv
import errno
import importlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

file_module = importlib.import_module(
    "monitaudit.sinks.file"
)

from monitaudit.models.base import BaseLog
from monitaudit.models.mapping import (
    LOG_FIELD_NAMES,
)
from monitaudit.sinks.base import Sink
from monitaudit.sinks.file import (
    FileSink,
    FileSinkError,
    FileSinkLockTimeoutError,
)

TIMESTAMP = datetime(
    2026,
    11,
    2,
    19,
    30,
    tzinfo=UTC,
)


def make_log() -> BaseLog:
    """
    Construct a lightweight BaseLog instance.

    FileSink validates only that the supplied value is a BaseLog instance.
    Record mapping is mocked where a complete record is required.
    """

    model_construct = getattr(
        BaseLog,
        "model_construct",
        None,
    )

    if callable(model_construct):
        return cast(
            BaseLog,
            model_construct(),
        )

    construct = getattr(
        BaseLog,
        "construct",
        None,
    )

    if callable(construct):
        return cast(
            BaseLog,
            construct(),
        )

    return cast(
        BaseLog,
        object.__new__(BaseLog),
    )


def make_record(
    **overrides: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "timestamp": TIMESTAMP,
        "level": "INFO",
        "application": "monitaudit-test",
        "environment": "dev",
        "module": "tests.test_module",
        "function": "test_function",
        "correlation_id": "correlation-1",
        "run_id": "run-1",
        "call_id": "call-1",
        "parent_call_id": "parent-1",
        "event": "function_end",
        "message": "Processing completed",
        "parameters": {
            "customer_id": 42,
        },
        "attributes": {
            "batch": "nightly",
        },
        "duration_ms": 125.5,
        "error_type": None,
        "error_message": None,
        "traceback": None,
    }

    record.update(overrides)

    return record


def patch_log_record(
    monkeypatch: pytest.MonkeyPatch,
    record: dict[str, object],
) -> list[BaseLog]:
    received: list[BaseLog] = []

    def fake_log_record(
        log: BaseLog,
    ) -> dict[str, object]:
        received.append(log)
        return dict(record)

    monkeypatch.setattr(
        file_module,
        "log_record",
        fake_log_record,
    )

    return received


class FaultyString:
    def __str__(self) -> str:
        raise RuntimeError("string conversion failed")

    def __repr__(self) -> str:
        return "<FaultyString>"


class FaultyStringAndRepr:
    def __str__(self) -> str:
        raise RuntimeError("string conversion failed")

    def __repr__(self) -> str:
        raise RuntimeError("representation failed")


class FaultyJsonObject:
    def __repr__(self) -> str:
        return "<FaultyJsonObject>"


class TestFileSinkTypes:
    def test_file_sink_inherits_from_sink(
        self,
    ) -> None:
        assert issubclass(
            FileSink,
            Sink,
        )

    def _error_is_runtime_error(
        self,
    ) -> None:
        assert issubclass(
            FileSinkError,
            RuntimeError,
        )

    def test_lock_timeout_error_is_file_sink_error(
        self,
    ) -> None:
        assert issubclass(
            FileSinkLockTimeoutError,
            FileSinkError,
        )


class TestSettingsValidation:
    @pytest.mark.parametrize(
        "path",
        [
            None,
            1,
            Path("output/log"),
            object(),
        ],
    )
    def test_rejects_non_string_path(
        self,
        path: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="FileSink path must be a string",
        ):
            FileSink(
                path,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "path",
        [
            "",
            " ",
            "\t",
            "\n",
        ],
    )
    def test_rejects_empty_path(
        self,
        path: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="FileSink path cannot be empty",
        ):
            FileSink(path)

    @pytest.mark.parametrize(
        "format_value",
        [
            "",
            "json",
            "CSV",
            "TEXT",
            None,
            1,
        ],
    )
    def test_rejects_unsupported_format(
        self,
        format_value: object,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Unsupported FileSink format",
        ):
            FileSink(
                "output/log",
                format=format_value,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "delimiter",
        [
            None,
            1,
            object(),
        ],
    )
    def test_rejects_non_string_delimiter(
        self,
        delimiter: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="CSV delimiter must be a string",
        ):
            FileSink(
                "output/log",
                format="csv",
                delimiter=delimiter,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "delimiter",
        [
            "",
            ";;",
            "ab",
        ],
    )
    def test_rejects_invalid_csv_delimiter_length(
        self,
        delimiter: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="exactly one character",
        ):
            FileSink(
                "output/log",
                format="csv",
                delimiter=delimiter,
            )

    @pytest.mark.parametrize(
        "delimiter",
        [
            "\r",
            "\n",
            "\0",
        ],
    )
    def test_rejects_newline_or_null_delimiter(
        self,
        delimiter: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="newline or null character",
        ):
            FileSink(
                "output/log",
                format="csv",
                delimiter=delimiter,
            )

    def test_text_format_allows_multi_character_delimiter(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            format="text",
            delimiter=" | ",
        )

        assert sink.delimiter == " | "

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "10",
            True,
            False,
            object(),
        ],
    )
    def test_rejects_non_numeric_lock_timeout(
        self,
        value: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="lock_timeout_seconds must be numeric",
        ):
            FileSink(
                "output/log",
                lock_timeout_seconds=value,  # type: ignore[arg-type]
            )

    def test_rejects_negative_lock_timeout(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="cannot be negative",
        ):
            FileSink(
                "output/log",
                lock_timeout_seconds=-0.1,
            )

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "0.05",
            True,
            False,
            object(),
        ],
    )
    def test_rejects_non_numeric_poll_interval(
        self,
        value: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "lock_poll_interval_seconds "
                "must be numeric"
            ),
        ):
            FileSink(
                "output/log",
                lock_poll_interval_seconds=value,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "value",
        [
            0,
            0.0,
            -0.1,
            -1,
        ],
    )
    def test_rejects_non_positive_poll_interval(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="must be greater than zero",
        ):
            FileSink(
                "output/log",
                lock_poll_interval_seconds=value,
            )

    @pytest.mark.parametrize(
        "value",
        [
            None,
            0,
            1,
            "true",
            object(),
        ],
    )
    def test_rejects_non_boolean_fsync(
        self,
        value: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="fsync must be a boolean",
        ):
            FileSink(
                "output/log",
                fsync=value,  # type: ignore[arg-type]
            )


class TestConstruction:
    def test_text_sink_uses_txt_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application.log"),
        )

        assert sink.path == (
            tmp_path / "application.txt"
        )

    def test_csv_sink_uses_csv_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application.log"),
            format="csv",
        )

        assert sink.path == (
            tmp_path / "application.csv"
        )

    def test_path_without_suffix_receives_format_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        text_sink = FileSink(
            str(tmp_path / "text-log"),
        )
        csv_sink = FileSink(
            str(tmp_path / "csv-log"),
            format="csv",
        )

        assert text_sink.path.name == "text-log.txt"
        assert csv_sink.path.name == "csv-log.csv"

    def test_creates_parent_directories(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "one"
            / "two"
            / "application"
        )

        sink = FileSink(
            str(path)
        )

        assert sink.path.parent.is_dir()

    def test_sets_lock_path(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )

        assert sink.lock_path == Path(
            f"{sink.path}.lock"
        )

    def test_normalises_numeric_settings_to_float(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            lock_timeout_seconds=5,
            lock_poll_interval_seconds=1,
        )

        assert sink.lock_timeout_seconds == 5.0
        assert (
            sink.lock_poll_interval_seconds
            == 1.0
        )

    def test_directory_creation_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        parent_file = tmp_path / "parent"
        parent_file.write_text(
            "not a directory",
            encoding="utf-8",
        )

        with pytest.raises(
            FileSinkError,
            match="Could not create the FileSink directory",
        ) as exception_info:
            FileSink(
                str(
                    parent_file
                    / "application"
                )
            )

        assert isinstance(
            exception_info.value.__cause__,
            OSError,
        )


class TestWriteValidation:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            object(),
            {},
            "log",
            42,
        ],
    )
    def test_write_rejects_non_base_log(
        self,
        tmp_path: Path,
        value: object,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )

        with pytest.raises(
            TypeError,
            match=(
                r"FileSink\.write\(\) expects "
                "a BaseLog instance"
            ),
        ):
            sink.write(
                value,  # type: ignore[arg-type]
            )


class TestOptionalText:
    def test_none_becomes_empty_string(
        self,
    ) -> None:
        assert FileSink._optional_text(None) == ""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("value", "value"),
            (42, "42"),
            (1.5, "1.5"),
            (True, "True"),
        ],
    )
    def test_values_use_string_conversion(
        self,
        value: object,
        expected: str,
    ) -> None:
        assert (
            FileSink._optional_text(value)
            == expected
        )

    def test_faulty_string_uses_repr(
        self,
    ) -> None:
        assert FileSink._optional_text(
            FaultyString()
        ) == "<FaultyString>"

    def test_faulty_string_and_repr_uses_safe_fallback(
        self,
    ) -> None:
        assert FileSink._optional_text(
            FaultyStringAndRepr()
        ) == "<unrepresentable FaultyStringAndRepr>"


class TestSafeRepr:
    def test_returns_repr(
        self,
    ) -> None:
        assert FileSink._safe_repr(
            FaultyJsonObject()
        ) == "<FaultyJsonObject>"

    def test_returns_fallback_when_repr_fails(
        self,
    ) -> None:
        assert FileSink._safe_repr(
            FaultyStringAndRepr()
        ) == "<unrepresentable FaultyStringAndRepr>"


class TestJsonText:
    def test_serialises_mapping_compactly(
        self,
    ) -> None:
        result = FileSink._json_text(
            {
                "name": "test",
                "count": 42,
            }
        )

        assert result == (
            '{"name":"test","count":42}'
        )

    def test_preserves_unicode(
        self,
    ) -> None:
        result = FileSink._json_text(
            {
                "message": "München 日本語",
            }
        )

        assert result == (
            '{"message":"München 日本語"}'
        )

    def test_uses_str_for_unsupported_value(
        self,
    ) -> None:
        result = FileSink._json_text(
            {
                "value": Path("output/log"),
            }
        )

        assert result == (
            '{"value":"output/log"}'
        )

    def test_serialisation_failure_returns_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        original_dumps = json.dumps
        calls = 0

        def fake_dumps(
            value: object,
            **kwargs: object,
        ) -> str:
            nonlocal calls
            calls += 1

            if calls == 1:
                raise TypeError(
                    "serialization failed"
                )

            return original_dumps(
                value,
                **kwargs,
            )

        monkeypatch.setattr(
            file_module.json,
            "dumps",
            fake_dumps,
        )

        result = FileSink._json_text(
            {
                "value": object(),
            }
        )

        decoded = json.loads(result)

        assert decoded[
            "serialization_error"
        ] == "TypeError"
        assert "value" in decoded

    def test_unrecoverable_serialisation_returns_fixed_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def always_fail(
            *_args: object,
            **_kwargs: object,
        ) -> str:
            raise TypeError(
                "serialization failed"
            )

        monkeypatch.setattr(
            file_module.json,
            "dumps",
            always_fail,
        )

        result = FileSink._json_text(
            object()
        )

        assert result == (
            '{"serialization_error":'
            '"unrecoverable serialization failure"}'
        )


class TestTracebackText:
    @pytest.mark.parametrize(
        "value",
        [
            None,
        ],
    )
    def test_none_becomes_empty_string(
        self,
        value: object,
    ) -> None:
        assert FileSink._traceback_text(value) == ""

    def test_string_has_trailing_whitespace_removed(
        self,
    ) -> None:
        result = FileSink._traceback_text(
            "ValueError: failed\n\n"
        )

        assert result == "ValueError: failed"

    def test_list_is_joined(
        self,
    ) -> None:
        result = FileSink._traceback_text(
            [
                "Traceback:\n",
                "ValueError: failed\n",
            ]
        )

        assert result == (
            "Traceback:\n"
            "ValueError: failed"
        )

    def test_tuple_is_joined(
        self,
    ) -> None:
        result = FileSink._traceback_text(
            (
                "first\n",
                "second\n",
            )
        )

        assert result == "first\nsecond"

    def test_non_collection_uses_optional_text(
        self,
    ) -> None:
        assert FileSink._traceback_text(
            42
        ) == "42"


class TestCsvRow:
    def test_converts_record_to_csv_mapping(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = make_log()
        record = make_record()

        received = patch_log_record(
            monkeypatch,
            record,
        )

        result = FileSink._csv_row(log)

        assert received == [log]
        assert list(result) == list(
            LOG_FIELD_NAMES
        )
        assert result["timestamp"] == (
            TIMESTAMP.isoformat()
        )
        assert result["level"] == "INFO"
        assert result["message"] == (
            "Processing completed"
        )
        assert result["duration_ms"] == "125.5"
        assert result["parameters"] == (
            '{"customer_id":42}'
        )
        assert result["attributes"] == (
            '{"batch":"nightly"}'
        )
        assert result["error_type"] == ""
        assert result["traceback"] == ""

    def test_csv_row_formats_error_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = make_log()

        patch_log_record(
            monkeypatch,
            make_record(
                error_type="ValueError",
                error_message="invalid value",
                traceback=[
                    "Traceback:\n",
                    "ValueError: invalid value\n",
                ],
            ),
        )

        result = FileSink._csv_row(log)

        assert result["error_type"] == "ValueError"
        assert result["error_message"] == (
            "invalid value"
        )
        assert result["traceback"] == (
            "Traceback:\n"
            "ValueError: invalid value"
        )


class TestErrorFormatting:
    def test_empty_error_record_returns_empty_string(
        self,
    ) -> None:
        result = FileSink._format_error_record(
            {
                "error_type": None,
                "error_message": None,
                "traceback": None,
            }
        )

        assert result == ""

    def test_formats_error_type(
        self,
    ) -> None:
        result = FileSink._format_error_record(
            {
                "error_type": "ValueError",
                "error_message": None,
                "traceback": None,
            }
        )

        assert result == "error_type=ValueError"

    def test_formats_complete_error_record(
        self,
    ) -> None:
        result = FileSink._format_error_record(
            {
                "error_type": "ValueError",
                "error_message": "invalid value",
                "traceback": [
                    "Traceback:\n",
                    "ValueError: invalid value\n",
                ],
            }
        )

        assert result == (
            "error_type=ValueError\n"
            "error_message=invalid value\n"
            "traceback:\n"
            "Traceback:\n"
            "ValueError: invalid value"
        )


class TestTextFormatting:
    def test_formats_standard_record(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = make_log()

        patch_log_record(
            monkeypatch,
            make_record(),
        )

        result = FileSink._format(log)

        assert TIMESTAMP.isoformat() in result
        assert "INFO" in result
        assert "application=monitaudit-test" in result
        assert "environment=dev" in result
        assert "correlation_id=correlation-1" in result
        assert "run_id=run-1" in result
        assert "call_id=call-1" in result
        assert "parent_call_id=parent-1" in result
        assert "event=function_end" in result
        assert "duration_ms=125.5" in result
        assert (
            "tests.test_module.test_function"
            in result
        )
        assert "Processing completed" in result
        assert (
            'parameters={"customer_id":42}'
            in result
        )
        assert (
            'attributes={"batch":"nightly"}'
            in result
        )

    def test_missing_optional_identifiers_use_dash(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        patch_log_record(
            monkeypatch,
            make_record(
                run_id=None,
                call_id=None,
                parent_call_id=None,
                event=None,
                duration_ms=None,
            ),
        )

        result = FileSink._format(
            make_log()
        )

        assert "run_id=-" in result
        assert "call_id=-" in result
        assert "parent_call_id=-" in result
        assert "event=-" in result
        assert "duration_ms=-" in result

    def test_error_details_are_added_on_new_lines(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        patch_log_record(
            monkeypatch,
            make_record(
                level="ERROR",
                error_type="ValueError",
                error_message="invalid value",
                traceback=[
                    "Traceback:\n",
                    "ValueError: invalid value\n",
                ],
            ),
        )

        result = FileSink._format(
            make_log()
        )

        assert "\nerror_type=ValueError" in result
        assert (
            "\nerror_message=invalid value"
            in result
        )
        assert "\ntraceback:\n" in result


class TestTextWriting:
    def test_writes_text_record(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )
        log = make_log()

        monkeypatch.setattr(
            sink,
            "_format",
            lambda _log: "formatted log",
        )

        sink.write(log)

        assert sink.path.read_text(
            encoding="utf-8"
        ) == "formatted log\n"

    def test_appends_multiple_text_records(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )
        log = make_log()
        values = iter(
            [
                "first",
                "second",
                "third",
            ]
        )

        monkeypatch.setattr(
            sink,
            "_format",
            lambda _log: next(values),
        )

        sink.write(log)
        sink.write(log)
        sink.write(log)

        assert sink.path.read_text(
            encoding="utf-8"
        ) == (
            "first\n"
            "second\n"
            "third\n"
        )

    def test_text_write_failure_is_wrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )

        def fail_format(
            _log: BaseLog,
        ) -> str:
            raise RuntimeError(
                "format failed"
            )

        monkeypatch.setattr(
            sink,
            "_format",
            fail_format,
        )

        with pytest.raises(
            FileSinkError,
            match="Could not write text log",
        ) as exception_info:
            sink.write(
                make_log()
            )

        assert isinstance(
            exception_info.value.__cause__,
            RuntimeError,
        )

    def test_existing_file_sink_error_is_not_rewrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )
        expected = FileSinkError(
            "lock failed"
        )

        def fail_format(
            _log: BaseLog,
        ) -> str:
            raise expected

        monkeypatch.setattr(
            sink,
            "_format",
            fail_format,
        )

        with pytest.raises(
            FileSinkError
        ) as exception_info:
            sink.write(
                make_log()
            )

        assert exception_info.value is expected


class TestCsvWriting:
    def test_writes_header_and_row(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            format="csv",
            delimiter=";",
        )
        log = make_log()

        monkeypatch.setattr(
            sink,
            "_csv_row",
            lambda _log: {
                name: (
                    "INFO"
                    if name == "level"
                    else "value"
                )
                for name in LOG_FIELD_NAMES
            },
        )

        sink.write(log)

        with sink.path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            rows = list(
                csv.reader(
                    file,
                    delimiter=";",
                )
            )

        assert rows[0] == list(
            LOG_FIELD_NAMES
        )
        assert len(rows) == 2

    def test_header_is_written_only_once(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            format="csv",
        )
        log = make_log()

        monkeypatch.setattr(
            sink,
            "_csv_row",
            lambda _log: {
                name: "value"
                for name in LOG_FIELD_NAMES
            },
        )

        sink.write(log)
        sink.write(log)

        with sink.path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            rows = list(
                csv.reader(
                    file,
                    delimiter=";",
                )
            )

        assert rows[0] == list(
            LOG_FIELD_NAMES
        )
        assert len(rows) == 3

    def test_csv_write_failure_is_wrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            format="csv",
        )

        def fail_row(
            _log: BaseLog,
        ) -> dict[str, str]:
            raise RuntimeError(
                "row failed"
            )

        monkeypatch.setattr(
            sink,
            "_csv_row",
            fail_row,
        )

        with pytest.raises(
            FileSinkError,
            match="Could not write CSV log",
        ) as exception_info:
            sink.write(
                make_log()
            )

        assert isinstance(
            exception_info.value.__cause__,
            RuntimeError,
        )


class TestCsvHeaderValidation:
    def test_missing_csv_file_is_allowed(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            format="csv",
        )

        assert not sink.path.exists()

    def test_empty_csv_file_is_allowed(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "application.csv"
        path.touch()

        sink = FileSink(
            str(path),
            format="csv",
        )

        assert sink.path == path

    def test_matching_existing_header_is_allowed(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "application.csv"

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.writer(
                file,
                delimiter=";",
            )
            writer.writerow(
                LOG_FIELD_NAMES
            )

        sink = FileSink(
            str(path),
            format="csv",
        )

        assert sink.path == path

    def test_mismatched_header_is_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "application.csv"

        path.write_text(
            "wrong;header\n",
            encoding="utf-8",
        )

        with pytest.raises(
            FileSinkError,
            match=(
                "Existing CSV header does not match"
            ),
        ):
            FileSink(
                str(path),
                format="csv",
            )


class TestFlush:
    def test_flush_always_flushes_file(
        self,
    ) -> None:
        file = io.StringIO()
        calls = 0
        original_flush = file.flush

        def tracked_flush() -> None:
            nonlocal calls
            calls += 1
            original_flush()

        file.flush = tracked_flush  # type: ignore[method-assign]

        FileSink._flush(
            file,
            synchronise=False,
        )

        assert calls == 1

    def test_fsync_runs_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeFile:
            def __init__(self) -> None:
                self.flush_calls = 0
                self.fileno_calls = 0

            def flush(self) -> None:
                self.flush_calls += 1

            def fileno(self) -> int:
                self.fileno_calls += 1
                return 42

        file = FakeFile()
        fsync_calls: list[int] = []

        monkeypatch.setattr(
            file_module.os,
            "fsync",
            fsync_calls.append,
        )

        FileSink._flush(
            cast(Any, file),
            synchronise=True,
        )

        assert file.flush_calls == 1
        assert file.fileno_calls == 1
        assert fsync_calls == [42]

    def test_fsync_does_not_run_when_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeFile:
            def flush(self) -> None:
                pass

            def fileno(self) -> int:
                raise AssertionError(
                    "fileno must not be called"
                )

        monkeypatch.setattr(
            file_module.os,
            "fsync",
            lambda _fd: pytest.fail(
                "fsync must not be called"
            ),
        )

        FileSink._flush(
            cast(Any, FakeFile()),
            synchronise=False,
        )


class TestProcessLock:
    def test_process_lock_is_acquired(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )
        lock_file = io.StringIO()
        calls: list[tuple[int, int]] = []

        monkeypatch.setattr(
            lock_file,
            "fileno",
            lambda: 11,
        )
        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            lambda descriptor, operation: calls.append(
                (
                    descriptor,
                    operation,
                )
            ),
        )

        sink._acquire_process_lock(
            lock_file
        )

        assert calls == [
            (
                11,
                file_module.fcntl.LOCK_EX
                | file_module.fcntl.LOCK_NB,
            )
        ]

    def test_process_lock_retries_after_blocking(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            lock_timeout_seconds=10,
            lock_poll_interval_seconds=0.25,
        )
        lock_file = io.StringIO()
        flock_calls = 0
        sleep_calls: list[float] = []

        monkeypatch.setattr(
            lock_file,
            "fileno",
            lambda: 12,
        )

        def fake_flock(
            _descriptor: int,
            _operation: int,
        ) -> None:
            nonlocal flock_calls
            flock_calls += 1

            if flock_calls == 1:
                raise BlockingIOError(
                    errno.EAGAIN,
                    "locked",
                )

        monotonic_values = iter(
            [
                0.0,
                1.0,
            ]
        )

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            fake_flock,
        )
        monkeypatch.setattr(
            file_module.time,
            "monotonic",
            lambda: next(
                monotonic_values
            ),
        )
        monkeypatch.setattr(
            file_module.time,
            "sleep",
            sleep_calls.append,
        )

        sink._acquire_process_lock(
            lock_file
        )

        assert flock_calls == 2
        assert sleep_calls == [0.25]

    def test_process_lock_timeout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
            lock_timeout_seconds=0,
        )
        lock_file = io.StringIO()

        monkeypatch.setattr(
            lock_file,
            "fileno",
            lambda: 13,
        )
        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            lambda *_args: (
                _raise_blocking_error()
            ),
        )
        monkeypatch.setattr(
            file_module.time,
            "monotonic",
            lambda: 10.0,
        )

        with pytest.raises(
            FileSinkLockTimeoutError,
            match="Timed out waiting",
        ):
            sink._acquire_process_lock(
                lock_file
            )

    def test_process_lock_os_error_is_wrapped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sink = FileSink(
            str(tmp_path / "application"),
        )
        lock_file = io.StringIO()

        monkeypatch.setattr(
            lock_file,
            "fileno",
            lambda: 14,
        )

        def fail_flock(
            *_args: object,
        ) -> None:
            raise OSError(
                "flock failed"
            )

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            fail_flock,
        )

        with pytest.raises(
            FileSinkError,
            match=(
                "Could not acquire the FileSink "
                "process lock"
            ),
        ) as exception_info:
            sink._acquire_process_lock(
                lock_file
            )

        assert isinstance(
            exception_info.value.__cause__,
            OSError,
        )


def _raise_blocking_error() -> None:
    raise BlockingIOError(
        errno.EAGAIN,
        "locked",
    )


class TestCloseLockFile:
    def test_releases_and_closes_lock(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeLockFile:
            def __init__(self) -> None:
                self.closed = False

            def fileno(self) -> int:
                return 21

            def close(self) -> None:
                self.closed = True

        lock_file = FakeLockFile()
        calls: list[tuple[int, int]] = []

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            lambda descriptor, operation: calls.append(
                (
                    descriptor,
                    operation,
                )
            ),
        )

        FileSink._close_lock_file(
            cast(Any, lock_file),
            release_lock=True,
        )

        assert calls == [
            (
                21,
                file_module.fcntl.LOCK_UN,
            )
        ]
        assert lock_file.closed is True

    def test_closes_without_releasing_when_not_acquired(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeLockFile:
            def __init__(self) -> None:
                self.closed = False

            def fileno(self) -> int:
                raise AssertionError(
                    "fileno must not be called"
                )

            def close(self) -> None:
                self.closed = True

        lock_file = FakeLockFile()

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            lambda *_args: pytest.fail(
                "flock must not be called"
            ),
        )

        FileSink._close_lock_file(
            cast(Any, lock_file),
            release_lock=False,
        )

        assert lock_file.closed is True

    def test_release_failure_is_suppressed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeLockFile:
            def __init__(self) -> None:
                self.closed = False

            def fileno(self) -> int:
                return 22

            def close(self) -> None:
                self.closed = True

        lock_file = FakeLockFile()

        def fail_release(
            *_args: object,
        ) -> None:
            raise OSError(
                "unlock failed"
            )

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            fail_release,
        )

        FileSink._close_lock_file(
            cast(Any, lock_file),
            release_lock=True,
        )

        assert lock_file.closed is True

    def test_close_failure_is_suppressed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeLockFile:
            def fileno(self) -> int:
                return 23

            def close(self) -> None:
                raise OSError(
                    "close failed"
                )

        monkeypatch.setattr(
            file_module.fcntl,
            "flock",
            lambda *_args: None,
        )

        FileSink._close_lock_file(
            cast(
                Any,
                FakeLockFile(),
            ),
            release_lock=True,
        )