# tests/sinks/test_sink_json.py

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import monitaudit.sinks.json as json_sink_module
from monitaudit.models.base import BaseLog
from monitaudit.sinks.json import (
    JsonSink,
    JsonSinkError,
    JsonSinkLockTimeoutError,
)
from monitaudit.utilities.archive_files import RotationError


class FakeLog(BaseLog):
    json_line: str = '{"message":"test"}'

    def model_dump_json(
        self,
        **kwargs: Any,
    ) -> str:
        del kwargs
        return self.json_line


class FailingLog(BaseLog):
    def model_dump_json(
        self,
        **kwargs: Any,
    ) -> str:
        del kwargs
        raise RuntimeError(
            "serialization failed"
        )


def _base_log(
    json_line: str = '{"message":"test"}',
) -> BaseLog:
    return FakeLog.model_construct(
        json_line=json_line,
    )


class TestJsonSinkValidation:
    @pytest.mark.parametrize(
        "path",
        [
            Path("output/monitaudit"),
            123,
            1.5,
            True,
            [],
            {},
            object(),
        ],
    )
    def test_path_must_be_string(
        self,
        path: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="JsonSink path must be a string",
        ):
            JsonSink(
                path=path,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "path",
        [
            "",
            " ",
            "   ",
            "\t",
            "\n",
        ],
    )
    def test_path_cannot_be_empty_or_whitespace(
        self,
        path: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="JsonSink path cannot be empty",
        ):
            JsonSink(
                path=path,
            )

    def test_file_cycle_accepts_none(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=None,
        )

        assert sink.file_cycle is None

    @pytest.mark.parametrize(
        "file_cycle",
        [
            1,
            10,
            30,
            100,
        ],
    )
    def test_file_cycle_accepts_positive_integer(
        self,
        tmp_path: Path,
        file_cycle: int,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=file_cycle,
        )

        assert sink.file_cycle == file_cycle

    @pytest.mark.parametrize(
        "file_cycle",
        [
            True,
            False,
            1.0,
            10.0,
            "10",
            [],
            {},
            object(),
        ],
    )
    def test_file_cycle_rejects_non_integer_values(
        self,
        tmp_path: Path,
        file_cycle: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "file_cycle must be an integer "
                "number of days or None"
            ),
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=file_cycle,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "file_cycle",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_file_cycle_rejects_non_positive_integer(
        self,
        tmp_path: Path,
        file_cycle: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="file_cycle must be greater than zero",
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=file_cycle,
            )

    @pytest.mark.parametrize(
        "timeout",
        [
            0,
            0.1,
            1,
            10.5,
        ],
    )
    def test_lock_timeout_accepts_non_negative_number(
        self,
        tmp_path: Path,
        timeout: float,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            lock_timeout_seconds=timeout,
        )

        assert sink.lock_timeout_seconds == float(
            timeout
        )

    @pytest.mark.parametrize(
        "timeout",
        [
            True,
            False,
            "10",
            [],
            {},
            object(),
        ],
    )
    def test_lock_timeout_rejects_non_numeric_values(
        self,
        tmp_path: Path,
        timeout: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="lock_timeout_seconds must be numeric",
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                lock_timeout_seconds=timeout,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "timeout",
        [
            -0.001,
            -1,
            -10.5,
        ],
    )
    def test_lock_timeout_rejects_negative_values(
        self,
        tmp_path: Path,
        timeout: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="lock_timeout_seconds cannot be negative",
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                lock_timeout_seconds=timeout,
            )

    @pytest.mark.parametrize(
        "interval",
        [
            0.001,
            0.05,
            1,
            10.5,
        ],
    )
    def test_poll_interval_accepts_positive_number(
        self,
        tmp_path: Path,
        interval: float,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            lock_poll_interval_seconds=interval,
        )

        assert sink.lock_poll_interval_seconds == float(
            interval
        )

    @pytest.mark.parametrize(
        "interval",
        [
            True,
            False,
            "0.05",
            [],
            {},
            object(),
        ],
    )
    def test_poll_interval_rejects_non_numeric_values(
        self,
        tmp_path: Path,
        interval: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "lock_poll_interval_seconds "
                "must be numeric"
            ),
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                lock_poll_interval_seconds=interval,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "interval",
        [
            0,
            0.0,
            -0.001,
            -1,
        ],
    )
    def test_poll_interval_rejects_non_positive_values(
        self,
        tmp_path: Path,
        interval: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "lock_poll_interval_seconds "
                "must be greater than zero"
            ),
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                lock_poll_interval_seconds=interval,
            )


class TestJsonSinkInitialization:
    def test_adds_jsonl_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        assert sink.path == (
            tmp_path / "monitaudit.jsonl"
        )

    def test_preserves_jsonl_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "monitaudit.jsonl"

        sink = JsonSink(
            path=str(path),
        )

        assert sink.path == path

    def test_replaces_existing_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit.log"),
        )

        assert sink.path == (
            tmp_path / "monitaudit.jsonl"
        )

    def test_creates_lock_path(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        assert sink.lock_path == (
            tmp_path / "monitaudit.jsonl.lock"
        )

    def test_creates_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "nested"
            / "logs"
        )

        JsonSink(
            path=str(
                directory / "monitaudit"
            ),
        )

        assert directory.is_dir()

    def test_directory_creation_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        expected = OSError(
            "permission denied"
        )

        with (
            patch.object(
                Path,
                "mkdir",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not create the "
                    "JsonSink directory"
                ),
            ) as exception_info,
        ):
            JsonSink(
                path=str(
                    tmp_path / "monitaudit"
                ),
            )

        assert (
            exception_info.value.__cause__
            is expected
        )

    def test_rotator_not_created_without_cycle(
        self,
        tmp_path: Path,
    ) -> None:
        with patch.object(
            json_sink_module,
            "LogFileRotator",
        ) as constructor:
            sink = JsonSink(
                path=str(
                    tmp_path / "monitaudit"
                ),
                file_cycle=None,
            )

        constructor.assert_not_called()
        assert sink._rotator is None

    def test_rotator_created_with_cycle(
        self,
        tmp_path: Path,
    ) -> None:
        rotator = MagicMock()

        with patch.object(
            json_sink_module,
            "LogFileRotator",
            return_value=rotator,
        ) as constructor:
            sink = JsonSink(
                path=str(
                    tmp_path / "monitaudit"
                ),
                file_cycle=10,
            )

        constructor.assert_called_once_with(
            path=(
                tmp_path
                / "monitaudit.jsonl"
            ),
            file_cycle=10,
        )

        assert sink._rotator is rotator

    def test_initialization_does_not_rotate(
        self,
        tmp_path: Path,
    ) -> None:
        rotator = MagicMock()

        with patch.object(
            json_sink_module,
            "LogFileRotator",
            return_value=rotator,
        ):
            JsonSink(
                path=str(
                    tmp_path / "monitaudit"
                ),
                file_cycle=10,
            )

        rotator.rotate_if_required.assert_not_called()

    def test_initialization_does_not_create_output_or_lock_file(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        assert not sink.path.exists()
        assert not sink.lock_path.exists()


class TestJsonSinkWrite:
    def test_write_requires_base_log(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        with pytest.raises(
            TypeError,
            match=(
                r"JsonSink\.write\(\) expects "
                "a BaseLog instance"
            ),
        ):
            sink.write(  # type: ignore[arg-type]
                {
                    "message": "invalid",
                }
            )

    def test_write_creates_jsonl_file(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        sink.write(
            _base_log()
        )

        assert sink.path.is_file()

    def test_write_appends_newline(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        sink.write(
            _base_log(
                '{"message":"test"}'
            )
        )

        assert sink.path.read_text(
            encoding="utf-8",
        ) == '{"message":"test"}\n'

    def test_write_appends_multiple_records(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        sink.write(
            _base_log(
                '{"message":"first"}'
            )
        )

        sink.write(
            _base_log(
                '{"message":"second"}'
            )
        )

        assert sink.path.read_text(
            encoding="utf-8",
        ).splitlines() == [
            '{"message":"first"}',
            '{"message":"second"}',
        ]

    def test_write_preserves_existing_content(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "monitaudit.jsonl"
        )

        path.write_text(
            '{"message":"existing"}\n',
            encoding="utf-8",
        )

        sink = JsonSink(
            path=str(path),
        )

        sink.write(
            _base_log(
                '{"message":"new"}'
            )
        )

        assert path.read_text(
            encoding="utf-8",
        ).splitlines() == [
            '{"message":"existing"}',
            '{"message":"new"}',
        ]

    def test_written_line_is_valid_json(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        sink.write(
            _base_log(
                json.dumps(
                    {
                        "level": "INFO",
                        "message": "test",
                    }
                )
            )
        )

        line = sink.path.read_text(
            encoding="utf-8",
        ).strip()

        assert json.loads(line) == {
            "level": "INFO",
            "message": "test",
        }

    def test_write_uses_utf8(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        sink.write(
            _base_log(
                json.dumps(
                    {
                        "message": (
                            "München 日本語"
                        ),
                    },
                    ensure_ascii=False,
                )
            )
        )

        assert (
            "München 日本語"
            in sink.path.read_text(
                encoding="utf-8",
            )
        )

    def test_serialization_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        log = FailingLog.model_construct()

        with pytest.raises(
            JsonSinkError,
            match="Could not write JSON log",
        ) as exception_info:
            sink.write(log)

        assert isinstance(
            exception_info.value.__cause__,
            RuntimeError,
        )

        assert not sink.path.exists()

    def test_existing_json_sink_error_is_not_rewrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        expected = JsonSinkError(
            "existing failure"
        )

        with (
            patch.object(
                sink,
                "_exclusive_write_lock",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError
            ) as exception_info,
        ):
            sink.write(
                _base_log()
            )

        assert exception_info.value is expected


class TestJsonSinkWriteOrder:
    def test_serialization_occurs_before_lock(
        self,
        tmp_path: Path,
    ) -> None:
        events: list[str] = []

        class OrderedLog(BaseLog):
            def model_dump_json(
                self,
                **kwargs: Any,
            ) -> str:
                del kwargs
                events.append(
                    "serialize"
                )

                return '{"message":"test"}'

        class LockContext:
            def __enter__(
                self,
            ) -> None:
                events.append(
                    "lock"
                )

            def __exit__(
                self,
                exc_type: object,
                exc_value: object,
                traceback: object,
            ) -> None:
                del (
                    exc_type,
                    exc_value,
                    traceback,
                )

        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        with (
            patch.object(
                sink,
                "_exclusive_write_lock",
                return_value=LockContext(),
            ),
            patch.object(
                sink,
                "_rotate_if_required_unlocked",
                side_effect=lambda: (
                    events.append(
                        "rotate"
                    )
                ),
            ),
        ):
            sink.write(
                OrderedLog.model_construct()
            )

        assert events == [
            "serialize",
            "lock",
            "rotate",
        ]


class TestJsonSinkProcessLock:
    def test_acquire_process_lock_succeeds(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with patch.object(
            json_sink_module.fcntl,
            "flock",
        ) as flock:
            sink._acquire_process_lock(
                lock_file
            )

        flock.assert_called_once_with(
            42,
            (
                json_sink_module.fcntl.LOCK_EX
                | json_sink_module.fcntl.LOCK_NB
            ),
        )

    def test_lock_retries_after_blocking(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            lock_timeout_seconds=1,
            lock_poll_interval_seconds=0.05,
        )

        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with (
            patch.object(
                json_sink_module.fcntl,
                "flock",
                side_effect=[
                    BlockingIOError(),
                    None,
                ],
            ) as flock,
            patch.object(
                json_sink_module.time,
                "monotonic",
                side_effect=[
                    10.0,
                    10.1,
                ],
            ),
            patch.object(
                json_sink_module.time,
                "sleep",
            ) as sleep,
        ):
            sink._acquire_process_lock(
                lock_file
            )

        assert flock.call_count == 2

        sleep.assert_called_once_with(
            0.05
        )

    def test_lock_timeout_raises_specific_error(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            lock_timeout_seconds=0,
        )

        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with (
            patch.object(
                json_sink_module.fcntl,
                "flock",
                side_effect=BlockingIOError(),
            ),
            patch.object(
                json_sink_module.time,
                "monotonic",
                side_effect=[
                    10.0,
                    10.0,
                ],
            ),
            pytest.raises(
                JsonSinkLockTimeoutError,
                match=(
                    "Timed out waiting for "
                    "the JsonSink lock"
                ),
            ),
        ):
            sink._acquire_process_lock(
                lock_file
            )

    def test_lock_os_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        expected = OSError(
            "locking unavailable"
        )

        with (
            patch.object(
                json_sink_module.fcntl,
                "flock",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not acquire the "
                    "JsonSink process lock"
                ),
            ) as exception_info,
        ):
            sink._acquire_process_lock(
                lock_file
            )

        assert (
            exception_info.value.__cause__
            is expected
        )

    def test_timeout_not_rewrapped_by_write(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        expected = (
            JsonSinkLockTimeoutError(
                "timeout"
            )
        )

        with (
            patch.object(
                sink,
                "_exclusive_write_lock",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkLockTimeoutError
            ) as exception_info,
        ):
            sink.write(
                _base_log()
            )

        assert exception_info.value is expected


class TestJsonSinkExclusiveLock:
    def test_lock_file_open_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        expected = OSError(
            "cannot open lock file"
        )

        with (
            patch.object(
                Path,
                "open",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not open the "
                    "JsonSink lock file"
                ),
            ) as exception_info,
        ):
            with sink._exclusive_write_lock():
                pytest.fail(
                    "Must not enter lock context"
                )

        assert (
            exception_info.value.__cause__
            is expected
        )

    def test_lock_cleanup_called_after_success(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        lock_file = MagicMock()

        with (
            patch.object(
                Path,
                "open",
                return_value=lock_file,
            ),
            patch.object(
                sink,
                "_acquire_process_lock",
            ) as acquire,
            patch.object(
                sink,
                "_close_lock_file",
            ) as close,
        ):
            with sink._exclusive_write_lock():
                pass

        acquire.assert_called_once_with(
            lock_file
        )

        close.assert_called_once_with(
            lock_file,
            release_lock=True,
        )

    def test_lock_cleanup_called_when_body_raises(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        lock_file = MagicMock()
        expected = RuntimeError(
            "body failed"
        )

        with (
            patch.object(
                Path,
                "open",
                return_value=lock_file,
            ),
            patch.object(
                sink,
                "_acquire_process_lock",
            ),
            patch.object(
                sink,
                "_close_lock_file",
            ) as close,
            pytest.raises(
                RuntimeError
            ) as exception_info,
        ):
            with sink._exclusive_write_lock():
                raise expected

        assert exception_info.value is expected

        close.assert_called_once_with(
            lock_file,
            release_lock=True,
        )

    def test_failed_acquisition_closes_without_unlock(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        lock_file = MagicMock()

        expected = (
            JsonSinkLockTimeoutError(
                "timeout"
            )
        )

        with (
            patch.object(
                Path,
                "open",
                return_value=lock_file,
            ),
            patch.object(
                sink,
                "_acquire_process_lock",
                side_effect=expected,
            ),
            patch.object(
                sink,
                "_close_lock_file",
            ) as close,
            pytest.raises(
                JsonSinkLockTimeoutError
            ),
        ):
            with sink._exclusive_write_lock():
                pytest.fail(
                    "Must not enter lock context"
                )

        close.assert_called_once_with(
            lock_file,
            release_lock=False,
        )

    def test_close_lock_file_releases_lock(
        self,
    ) -> None:
        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with patch.object(
            json_sink_module.fcntl,
            "flock",
        ) as flock:
            JsonSink._close_lock_file(
                lock_file,
                release_lock=True,
            )

        flock.assert_called_once_with(
            42,
            json_sink_module.fcntl.LOCK_UN,
        )

        lock_file.close.assert_called_once_with()

    def test_unlock_error_is_suppressed(
        self,
    ) -> None:
        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with patch.object(
            json_sink_module.fcntl,
            "flock",
            side_effect=OSError(
                "unlock failed"
            ),
        ):
            JsonSink._close_lock_file(
                lock_file,
                release_lock=True,
            )

        lock_file.close.assert_called_once_with()

    def test_close_error_is_suppressed(
        self,
    ) -> None:
        lock_file = MagicMock()

        lock_file.close.side_effect = (
            OSError(
                "close failed"
            )
        )

        JsonSink._close_lock_file(
            lock_file,
            release_lock=False,
        )

        lock_file.close.assert_called_once_with()


class TestJsonSinkRotation:
    def test_rotation_disabled_without_rotator(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=None,
        )

        assert (
            sink._rotate_if_required_unlocked()
            is None
        )

    def test_bootstrap_occurs_before_rotation(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        events: list[str] = []

        with (
            patch.object(
                sink,
                "_bootstrap_existing_cycle_unlocked",
                side_effect=lambda: (
                    events.append(
                        "bootstrap"
                    )
                ),
            ),
            patch.object(
                sink._rotator,
                "rotate_if_required",
                side_effect=lambda: (
                    events.append(
                        "rotate"
                    )
                ),
            ),
        ):
            sink._rotate_if_required_unlocked()

        assert events == [
            "bootstrap",
            "rotate",
        ]

    def test_rotation_returns_path(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        expected = (
            tmp_path / "archive.zip"
        )

        with (
            patch.object(
                sink,
                "_bootstrap_existing_cycle_unlocked",
            ),
            patch.object(
                sink._rotator,
                "rotate_if_required",
                return_value=expected,
            ),
        ):
            result = (
                sink._rotate_if_required_unlocked()
            )

        assert result == expected

    def test_rotation_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        expected = RotationError(
            "rotation failed"
        )

        with (
            patch.object(
                sink._rotator,
                "rotate_if_required",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not rotate "
                    "JsonSink output"
                ),
            ) as exception_info,
        ):
            sink._rotate_if_required_unlocked()

        assert (
            exception_info.value.__cause__
            is expected
        )

    def test_rotation_os_error_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        expected = OSError(
            "filesystem unavailable"
        )

        with (
            patch.object(
                sink,
                "_bootstrap_existing_cycle_unlocked",
            ),
            patch.object(
                sink._rotator,
                "rotate_if_required",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not access "
                    "JsonSink output"
                ),
            ) as exception_info,
        ):
            sink._rotate_if_required_unlocked()

        assert (
            exception_info.value.__cause__
            is expected
        )


class TestJsonSinkCycleBootstrap:
    def test_does_nothing_without_rotator(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=None,
        )

        with patch.object(
            json_sink_module,
            "write_cycle_start",
        ) as writer:
            sink._bootstrap_existing_cycle_unlocked()

        writer.assert_not_called()

    def test_does_nothing_when_metadata_exists(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        sink.path.write_text(
            '{"message":"existing"}\n',
            encoding="utf-8",
        )

        sink._rotator.metadata_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        sink._rotator.metadata_path.write_text(
            "metadata",
            encoding="utf-8",
        )

        with patch.object(
            json_sink_module,
            "write_cycle_start",
        ) as writer:
            sink._bootstrap_existing_cycle_unlocked()

        writer.assert_not_called()

    def test_does_nothing_without_output_file(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None
        assert not sink.path.exists()
        assert not (
            sink._rotator.metadata_path.exists()
        )

        with patch.object(
            json_sink_module,
            "write_cycle_start",
        ) as writer:
            sink._bootstrap_existing_cycle_unlocked()

        writer.assert_not_called()

    def test_rejects_output_directory(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        sink.path.mkdir()

        with pytest.raises(
            JsonSinkError,
            match=(
                "exists but is not "
                "a regular file"
            ),
        ):
            sink._bootstrap_existing_cycle_unlocked()

    def test_uses_existing_file_mtime(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        sink.path.write_text(
            '{"message":"existing"}\n',
            encoding="utf-8",
        )

        expected = datetime(
            2026,
            10,
            20,
            14,
            35,
            tzinfo=timezone.utc,
        )

        timestamp = expected.timestamp()

        os.utime(
            sink.path,
            (
                timestamp,
                timestamp,
            ),
        )

        actual = datetime.fromtimestamp(
            sink.path.stat().st_mtime,
            tz=timezone.utc,
        )

        with patch.object(
            json_sink_module,
            "write_cycle_start",
        ) as writer:
            sink._bootstrap_existing_cycle_unlocked()

        writer.assert_called_once_with(
            sink.path,
            actual,
        )

    def test_rotation_error_from_metadata_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        sink.path.write_text(
            '{"message":"existing"}\n',
            encoding="utf-8",
        )

        expected = RotationError(
            "metadata write failed"
        )

        with (
            patch.object(
                json_sink_module,
                "write_cycle_start",
                side_effect=expected,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not initialise "
                    "JsonSink cycle metadata"
                ),
            ) as exception_info,
        ):
            sink._bootstrap_existing_cycle_unlocked()

        assert (
            exception_info.value.__cause__
            is expected
        )

    def test_os_error_during_stat_is_wrapped(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
            file_cycle=10,
        )

        assert sink._rotator is not None

        sink.path.write_text(
            '{"message":"existing"}\n',
            encoding="utf-8",
        )

        original_stat = Path.stat
        expected = OSError(
            "stat failed"
        )

        def fake_stat(
            path: Path,
            *args: Any,
            **kwargs: Any,
        ) -> os.stat_result:
            if path == sink.path:
                raise expected

            return original_stat(
                path,
                *args,
                **kwargs,
            )

        with (
            patch.object(
                Path,
                "stat",
                fake_stat,
            ),
            pytest.raises(
                JsonSinkError,
                match=(
                    "Could not inspect existing "
                    "JsonSink output"
                ),
            ) as exception_info,
        ):
            sink._bootstrap_existing_cycle_unlocked()

        assert (
            exception_info.value.__cause__
            is expected
        )


class TestJsonSinkThreadSafety:
    def test_concurrent_writes_produce_complete_json_lines(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit"
            ),
        )

        count = 25

        errors: list[
            BaseException
        ] = []

        def write_log(
            index: int,
        ) -> None:
            try:
                sink.write(
                    _base_log(
                        json.dumps(
                            {
                                "index": index,
                            }
                        )
                    )
                )
            except BaseException as exc:
                errors.append(
                    exc
                )

        threads = [
            Thread(
                target=write_log,
                args=(index,),
            )
            for index in range(count)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(
                timeout=10
            )

        assert not errors

        assert all(
            not thread.is_alive()
            for thread in threads
        )

        lines = sink.path.read_text(
            encoding="utf-8",
        ).splitlines()

        assert len(lines) == count

        indexes = {
            json.loads(
                line
            )["index"]
            for line in lines
        }

        assert indexes == set(
            range(count)
        )