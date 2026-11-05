# tests/utilities/test_archive_files.py

from __future__ import annotations

import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from monitaudit.utilities.archive_files import (
    LogFileRotator,
    archive_filename,
    create_archive,
    cycle_metadata_path,
    read_cycle_start,
    rotate_if_required,
    should_rotate,
    write_cycle_start,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def _file(
    tmp_path: Path,
    name: str = "monitaudit.txt",
    content: str = "test\n",
) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


class TestCycleMetadata:
    def test_metadata_path(self, tmp_path: Path) -> None:
        path = tmp_path / "monitaudit.txt"

        assert cycle_metadata_path(path) == (
            tmp_path / "monitaudit.txt.cycle.json"
        )

    def test_missing_metadata_returns_none(
        self,
        tmp_path: Path,
    ) -> None:
        assert read_cycle_start(
            tmp_path / "monitaudit.txt"
        ) is None

    def test_write_and_read_cycle_start(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "monitaudit.txt"

        write_cycle_start(path, NOW)

        assert read_cycle_start(path) == NOW


class TestShouldRotate:
    @pytest.mark.parametrize(
        ("age", "expected"),
        [
            (timedelta(days=9), False),
            (timedelta(days=10), True),
            (timedelta(days=20), True),
        ],
    )
    def test_cycle_age(
        self,
        age: timedelta,
        expected: bool,
    ) -> None:
        assert should_rotate(
            NOW - age,
            10,
            now=NOW,
        ) is expected

    @pytest.mark.parametrize(
        "file_cycle",
        [0, -1],
    )
    def test_invalid_file_cycle(
        self,
        file_cycle: int,
    ) -> None:
        with pytest.raises(ValueError):
            should_rotate(
                NOW,
                file_cycle,
                now=NOW,
            )


class TestArchiveFilename:
    def test_expected_name(
        self,
        tmp_path: Path,
    ) -> None:
        assert archive_filename(
            tmp_path,
            now=NOW,
        ) == (
            tmp_path / "monitaudit_202611031200.zip"
        )

    def test_collision_gets_sequence(
        self,
        tmp_path: Path,
    ) -> None:
        (
            tmp_path / "monitaudit_202611031200.zip"
        ).touch()

        assert archive_filename(
            tmp_path,
            now=NOW,
        ) == (
            tmp_path / "monitaudit_202611031200_01.zip"
        )


class TestCreateArchive:
    @pytest.mark.parametrize(
        "filename",
        [
            "monitaudit.txt",
            "monitaudit.csv",
            "monitaudit.jsonl",
        ],
    )
    def test_archives_supported_file(
        self,
        tmp_path: Path,
        filename: str,
    ) -> None:
        source = _file(
            tmp_path,
            filename,
            "important log\n",
        )

        archive_path = create_archive(
            source,
            now=NOW,
        )

        assert not source.exists()
        assert zipfile.is_zipfile(archive_path)

        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [filename]
            assert (
                archive.read(filename).decode("utf-8")
                == "important log\n"
            )

    def test_missing_source(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            create_archive(
                tmp_path / "missing.txt",
                now=NOW,
            )


class TestRotate:
    def test_active_cycle_is_not_rotated(
        self,
        tmp_path: Path,
    ) -> None:
        source = _file(tmp_path)
        write_cycle_start(
            source,
            NOW - timedelta(days=5),
        )

        result = rotate_if_required(
            source,
            10,
            now=NOW,
        )

        assert result is None
        assert source.exists()

    def test_expired_cycle_is_rotated(
        self,
        tmp_path: Path,
    ) -> None:
        source = _file(
            tmp_path,
            content="old log\n",
        )

        write_cycle_start(
            source,
            NOW - timedelta(days=10),
        )

        archive_path = rotate_if_required(
            source,
            10,
            now=NOW,
        )

        assert archive_path == (
            tmp_path / "monitaudit_202611031200.zip"
        )
        assert archive_path.exists()
        assert not source.exists()
        assert read_cycle_start(source) == NOW

        with zipfile.ZipFile(archive_path) as archive:
            assert archive.read(
                "monitaudit.txt"
            ).decode("utf-8") == "old log\n"

    def test_new_cycle_is_not_rotated(
        self,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "monitaudit.txt"

        result = rotate_if_required(
            source,
            10,
            now=NOW,
        )

        assert result is None
        assert read_cycle_start(source) == NOW

    def test_mtime_does_not_change_managed_cycle(
        self,
        tmp_path: Path,
    ) -> None:
        source = _file(tmp_path)
        cycle_start = NOW - timedelta(days=5)

        write_cycle_start(
            source,
            cycle_start,
        )

        source.write_text(
            "new log entry\n",
            encoding="utf-8",
        )

        result = rotate_if_required(
            source,
            10,
            now=NOW,
        )

        assert result is None
        assert read_cycle_start(source) == cycle_start


class TestLogFileRotator:
    def test_properties(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "monitaudit.jsonl"

        rotator = LogFileRotator(
            path=path,
            file_cycle=10,
            clock=lambda: NOW,
        )

        assert rotator.path == path
        assert rotator.file_cycle == 10
        assert rotator.metadata_path == (
            tmp_path / "monitaudit.jsonl.cycle.json"
        )

    def test_rotates_expired_file(
        self,
        tmp_path: Path,
    ) -> None:
        source = _file(
            tmp_path,
            "monitaudit.jsonl",
            '{"message":"test"}\n',
        )

        write_cycle_start(
            source,
            NOW - timedelta(days=20),
        )

        rotator = LogFileRotator(
            path=source,
            file_cycle=10,
            clock=lambda: NOW,
        )

        archive_path = rotator.rotate_if_required()

        assert archive_path is not None
        assert archive_path.exists()
        assert not source.exists()
        assert read_cycle_start(source) == NOW