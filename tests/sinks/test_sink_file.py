# tests/sinks/test_file.py

from __future__ import annotations

import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from monitaudit.sinks.file import (
    FileSink,
    FileSinkError,
)
from monitaudit.utilities.archive_files import (
    read_cycle_start,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def _set_mtime(
    path: Path,
    value: datetime,
) -> None:
    timestamp = value.timestamp()
    os.utime(path, (timestamp, timestamp))


def _sink(
    tmp_path: Path,
    *,
    format: str = "text",
    file_cycle: int | None = 10,
) -> FileSink:
    return FileSink(
        path=str(tmp_path / "monitaudit"),
        format=format,  # type: ignore[arg-type]
        file_cycle=file_cycle,
    )


class TestFileCycle:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            (1, 1),
            (10, 10),
            (365, 365),
        ],
    )
    def test_accepts_valid_values(
        self,
        tmp_path: Path,
        value: int | None,
        expected: int | None,
    ) -> None:
        assert _sink(
            tmp_path,
            file_cycle=value,
        ).file_cycle == expected

    @pytest.mark.parametrize(
        "value",
        [
            "10",
            10.0,
            True,
            False,
            [],
            {},
            object(),
        ],
    )
    def test_rejects_invalid_type(
        self,
        tmp_path: Path,
        value: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="file_cycle must be an integer",
        ):
            FileSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=value,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "value",
        [0, -1, -10],
    )
    def test_rejects_non_positive_value(
        self,
        tmp_path: Path,
        value: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="file_cycle must be greater than zero",
        ):
            _sink(
                tmp_path,
                file_cycle=value,
            )


class TestPath:
    @pytest.mark.parametrize(
        ("format", "suffix"),
        [
            ("text", ".txt"),
            ("csv", ".csv"),
        ],
    )
    def test_output_suffix(
        self,
        tmp_path: Path,
        format: str,
        suffix: str,
    ) -> None:
        sink = _sink(
            tmp_path,
            format=format,
        )

        assert sink.path == (
            tmp_path / f"monitaudit{suffix}"
        )

    def test_replaces_existing_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = FileSink(
            path=str(tmp_path / "monitaudit.log"),
        )

        assert sink.path == (
            tmp_path / "monitaudit.txt"
        )

    def test_creates_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        directory = tmp_path / "nested" / "logs"

        FileSink(
            path=str(directory / "monitaudit"),
        )

        assert directory.is_dir()

    def test_lock_path(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(
            tmp_path,
            file_cycle=None,
        )

        assert sink.lock_path == (
            tmp_path / "monitaudit.txt.lock"
        )


class TestRotationInitialisation:
    def test_text_initialisation_does_not_start_cycle(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)

        assert not sink.path.exists()
        assert not sink._rotator.metadata_path.exists()

    def test_existing_text_file_is_not_rotated_on_init(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "monitaudit.txt"
        path.write_text(
            "existing\n",
            encoding="utf-8",
        )

        _set_mtime(
            path,
            NOW - timedelta(days=20),
        )

        sink = _sink(tmp_path)

        assert sink.path.exists()
        assert not sink._rotator.metadata_path.exists()
        assert not list(
            tmp_path.glob("monitaudit_*.zip")
        )


class TestBootstrap:
    def test_existing_file_bootstraps_from_mtime(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)
        sink.path.write_text(
            "existing\n",
            encoding="utf-8",
        )

        modified_at = (
            NOW - timedelta(days=5)
        )
        _set_mtime(
            sink.path,
            modified_at,
        )

        with sink._exclusive_write_lock():
            sink._bootstrap_existing_cycle_unlocked()

        cycle_start = read_cycle_start(
            sink.path
        )

        assert cycle_start is not None
        assert cycle_start == modified_at

    def test_existing_metadata_is_preserved(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)
        sink.path.write_text(
            "existing\n",
            encoding="utf-8",
        )

        first = NOW - timedelta(days=5)
        _set_mtime(sink.path, first)

        with sink._exclusive_write_lock():
            sink._bootstrap_existing_cycle_unlocked()

        assert read_cycle_start(
            sink.path
        ) == first

        second = NOW
        _set_mtime(sink.path, second)

        with sink._exclusive_write_lock():
            sink._bootstrap_existing_cycle_unlocked()

        assert read_cycle_start(
            sink.path
        ) == first

    def test_no_file_does_not_create_metadata(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)

        with sink._exclusive_write_lock():
            sink._bootstrap_existing_cycle_unlocked()

        assert not sink._rotator.metadata_path.exists()


class TestRotation:
    def test_rotation_is_checked_while_locked(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)
        lock_exists = False

        def rotate() -> None:
            nonlocal lock_exists
            lock_exists = sink.lock_path.exists()

        with patch.object(
            sink,
            "_rotate_if_required_unlocked",
            side_effect=rotate,
        ):
            with sink._exclusive_write_lock():
                sink._rotate_if_required_unlocked()

        assert lock_exists

    def test_rotation_failure_is_not_silenced(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)

        with patch.object(
            sink._rotator,
            "rotate_if_required",
            side_effect=OSError("simulated failure"),
        ):
            with pytest.raises(
                FileSinkError,
                match="Could not access FileSink output",
            ):
                with sink._exclusive_write_lock():
                    sink._rotate_if_required_unlocked()


class TestArchiveIntegration:
    def test_expired_active_file_is_archived(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)

        sink.path.write_text(
            "old MonitAudit data\n",
            encoding="utf-8",
        )

        old = NOW - timedelta(days=20)
        _set_mtime(sink.path, old)

        with patch(
            "monitaudit.utilities.archive_files.utc_now",
            return_value=NOW,
        ):
            with sink._exclusive_write_lock():
                sink._rotate_if_required_unlocked()

        archives = list(
            tmp_path.glob("monitaudit_*.zip")
        )

        assert len(archives) == 1
        assert not sink.path.exists()

        with zipfile.ZipFile(archives[0]) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [
                "monitaudit.txt",
            ]
            assert (
                archive.read(
                    "monitaudit.txt"
                ).decode("utf-8")
                == "old MonitAudit data\n"
            )

    def test_recent_active_file_is_not_archived(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(tmp_path)

        sink.path.write_text(
            "recent\n",
            encoding="utf-8",
        )

        recent = NOW - timedelta(days=5)
        _set_mtime(sink.path, recent)

        with patch(
            "monitaudit.utilities.archive_files.utc_now",
            return_value=NOW,
        ):
            with sink._exclusive_write_lock():
                result = sink._rotate_if_required_unlocked()

        assert result is None
        assert sink.path.exists()
        assert not list(
            tmp_path.glob("monitaudit_*.zip")
        )

    def test_file_cycle_none_disables_rotation(
        self,
        tmp_path: Path,
    ) -> None:
        sink = _sink(
            tmp_path,
            file_cycle=None,
        )

        sink.path.write_text(
            "old\n",
            encoding="utf-8",
        )

        _set_mtime(
            sink.path,
            NOW - timedelta(days=100),
        )

        with sink._exclusive_write_lock():
            result = sink._rotate_if_required_unlocked()

        assert result is None
        assert sink.path.exists()
        assert not list(
            tmp_path.glob("monitaudit_*.zip")
        )