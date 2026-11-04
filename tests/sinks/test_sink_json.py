# tests/sinks/test_sink_json.py

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from monitaudit.models.base import BaseLog
from monitaudit.sinks.json import JsonSink


def _base_log() -> BaseLog:
    """Create a BaseLog without depending on required model fields."""

    return BaseLog.model_construct()


def _set_modified_at(
    path: Path,
    modified_at: datetime,
) -> None:
    """Set a file's access and modification timestamps."""

    timestamp = modified_at.timestamp()

    os.utime(
        path,
        (
            timestamp,
            timestamp,
        ),
    )


def _set_file_age(
    path: Path,
    *,
    days: int,
) -> datetime:
    """Set a file's modification time to the requested age."""

    modified_at = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    ).replace(
        second=0,
        microsecond=0,
    )

    _set_modified_at(
        path,
        modified_at,
    )

    return modified_at


def _expected_archive_path(
    source: Path,
    *,
    modified_at: datetime,
) -> Path:
    """Return the expected timestamped archive path."""

    timestamp = modified_at.astimezone(
        timezone.utc
    ).strftime(
        "%Y%m%d%H%M"
    )

    return source.parent / (
        f"monitaudit_{timestamp}.zip"
    )


def _create_jsonl(
    directory: Path,
    *,
    filename: str = "previous.jsonl",
    contents: str = '{"message":"old"}\n',
    days: int = 20,
) -> tuple[Path, datetime]:
    """Create a JSONL file with a configured modification age."""

    source = directory / filename

    source.write_text(
        contents,
        encoding="utf-8",
    )

    modified_at = _set_file_age(
        source,
        days=days,
    )

    return source, modified_at


class TestJsonSinkValidation:
    def test_path_object_currently_raises_attribute_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Record the current path validation behaviour."""

        with pytest.raises(
            AttributeError,
        ):
            JsonSink(
                path=tmp_path,  # type: ignore[arg-type]
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
        "value",
        [
            1,
            10,
            30,
            90,
        ],
    )
    def test_file_cycle_accepts_positive_integer(
        self,
        tmp_path: Path,
        value: int,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=value,
        )

        assert sink.file_cycle == value

    @pytest.mark.parametrize(
        (
            "value",
            "expected",
        ),
        [
            (1.0, 1.0),
            (10.0, 10.0),
            (True, True),
        ],
    )
    def test_file_cycle_currently_accepts_compatible_numeric_values(
        self,
        tmp_path: Path,
        value: object,
        expected: object,
    ) -> None:
        """Record current non-strict validation behaviour."""

        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=value,  # type: ignore[arg-type]
        )

        assert sink.file_cycle == expected

    @pytest.mark.parametrize(
        "value",
        [
            "10",
            [],
            {},
            object(),
        ],
    )
    def test_file_cycle_rejects_non_numeric_types(
        self,
        tmp_path: Path,
        value: object,
    ) -> None:
        with pytest.raises(
            TypeError,
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=value,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "value",
        [
            False,
            0,
            -1,
            -10,
            -1.0,
        ],
    )
    def test_file_cycle_rejects_non_positive_value(
        self,
        tmp_path: Path,
        value: object,
    ) -> None:
        with pytest.raises(
            ValueError,
        ):
            JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=value,  # type: ignore[arg-type]
            )


class TestJsonSinkPath:
    def test_json_sink_adds_jsonl_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        assert sink.path == (
            tmp_path / "monitaudit.jsonl"
        )

    def test_json_sink_preserves_jsonl_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(
                tmp_path / "monitaudit.jsonl"
            ),
        )

        assert sink.path == (
            tmp_path / "monitaudit.jsonl"
        )

    def test_json_sink_replaces_existing_suffix(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit.log"),
        )

        assert sink.path == (
            tmp_path / "monitaudit.jsonl"
        )

    def test_parent_directory_is_created(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "nested"
            / "logs"
        )

        JsonSink(
            path=str(directory / "monitaudit"),
        )

        assert directory.is_dir()


class TestJsonSinkArchiveUtility:
    def test_archive_utility_receives_jsonl_extension(
        self,
        tmp_path: Path,
    ) -> None:
        with patch(
            "monitaudit.sinks.json.archive_expired_files"
        ) as archive:
            sink = JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=10,
            )

        archive.assert_called_once_with(
            directory=tmp_path,
            file_cycle=10,
            extensions={".jsonl"},
            exclude={
                sink.path,
            },
        )

    def test_none_file_cycle_is_forwarded(
        self,
        tmp_path: Path,
    ) -> None:
        with patch(
            "monitaudit.sinks.json.archive_expired_files"
        ) as archive:
            sink = JsonSink(
                path=str(tmp_path / "monitaudit"),
                file_cycle=None,
            )

        archive.assert_called_once_with(
            directory=tmp_path,
            file_cycle=None,
            extensions={".jsonl"},
            exclude={
                sink.path,
            },
        )

    def test_archive_utility_receives_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "output"
        )

        with patch(
            "monitaudit.sinks.json.archive_expired_files"
        ) as archive:
            sink = JsonSink(
                path=str(
                    directory / "monitaudit"
                ),
                file_cycle=10,
            )

        archive.assert_called_once_with(
            directory=directory,
            file_cycle=10,
            extensions={".jsonl"},
            exclude={
                sink.path,
            },
        )


class TestJsonSinkArchiveIntegration:
    def test_old_jsonl_file_is_archived(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            days=20,
        )

        expected_archive = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert not source.exists()
        assert expected_archive.is_file()

    def test_archive_uses_required_filename(
        self,
        tmp_path: Path,
    ) -> None:
        source = (
            tmp_path
            / "previous.jsonl"
        )

        source.write_text(
            '{"message":"old"}\n',
            encoding="utf-8",
        )

        modified_at = datetime(
            2026,
            10,
            20,
            14,
            35,
            tzinfo=timezone.utc,
        )

        _set_modified_at(
            source,
            modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        archive_path = (
            tmp_path
            / "monitaudit_202610201435.zip"
        )

        assert archive_path.is_file()
        assert not source.exists()

    def test_archive_contains_original_jsonl_filename(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            filename="previous.jsonl",
            contents=(
                '{"message":"first"}\n'
                '{"message":"second"}\n'
            ),
            days=20,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        with zipfile.ZipFile(
            archive_path,
            mode="r",
        ) as archive:
            assert archive.namelist() == [
                source.name,
            ]

    def test_archive_preserves_jsonl_contents(
        self,
        tmp_path: Path,
    ) -> None:
        contents = (
            '{"level":"INFO","message":"first"}\n'
            '{"level":"ERROR","message":"second"}\n'
        )

        source, modified_at = _create_jsonl(
            tmp_path,
            contents=contents,
            days=20,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        with zipfile.ZipFile(
            archive_path,
            mode="r",
        ) as archive:
            archived_contents = archive.read(
                source.name
            ).decode(
                "utf-8"
            )

        assert archived_contents == contents

    def test_created_archive_is_valid_zip(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            days=20,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert zipfile.is_zipfile(
            archive_path
        )

        with zipfile.ZipFile(
            archive_path,
            mode="r",
        ) as archive:
            assert archive.testzip() is None

    def test_recent_jsonl_file_is_not_archived(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            filename="recent.jsonl",
            days=5,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert source.exists()
        assert not archive_path.exists()

    def test_file_cycle_none_disables_archiving(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            days=100,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=None,
        )

        assert source.exists()
        assert not archive_path.exists()

    def test_active_jsonl_file_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        active = (
            tmp_path
            / "monitaudit.jsonl"
        )

        active.write_text(
            '{"message":"active"}\n',
            encoding="utf-8",
        )

        modified_at = _set_file_age(
            active,
            days=100,
        )

        archive_path = _expected_archive_path(
            active,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert active.exists()
        assert not archive_path.exists()

    def test_source_is_deleted_after_successful_archive(
        self,
        tmp_path: Path,
    ) -> None:
        source, modified_at = _create_jsonl(
            tmp_path,
            days=20,
        )

        archive_path = _expected_archive_path(
            source,
            modified_at=modified_at,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert archive_path.exists()
        assert not source.exists()


class TestJsonSinkArchiveOwnership:
    @pytest.mark.parametrize(
        "filename",
        [
            "previous.txt",
            "previous.csv",
            "previous.log",
            "previous.json",
            "previous.yaml",
            "previous.properties",
        ],
    )
    def test_non_jsonl_file_is_not_archived(
        self,
        tmp_path: Path,
        filename: str,
    ) -> None:
        source = (
            tmp_path
            / filename
        )

        source.write_text(
            "data\n",
            encoding="utf-8",
        )

        _set_file_age(
            source,
            days=20,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert source.exists()


class TestJsonSinkArchiveExclusions:
    def test_existing_zip_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        archive_path = (
            tmp_path
            / "monitaudit_202610201435.zip"
        )

        with zipfile.ZipFile(
            archive_path,
            mode="w",
        ) as archive:
            archive.writestr(
                "previous.jsonl",
                '{"message":"old"}\n',
            )

        original_contents = (
            archive_path.read_bytes()
        )

        _set_file_age(
            archive_path,
            days=100,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert archive_path.exists()

        assert (
            archive_path.read_bytes()
            == original_contents
        )

        assert not (
            tmp_path
            / "monitaudit_202610201435.zip.zip"
        ).exists()

    def test_zip_tmp_file_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        temporary_file = (
            tmp_path
            / ".previous.jsonl.test.zip.tmp"
        )

        temporary_file.write_bytes(
            b"temporary archive"
        )

        _set_file_age(
            temporary_file,
            days=100,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert temporary_file.exists()

    def test_lock_file_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        lock_file = (
            tmp_path
            / "previous.jsonl.lock"
        )

        lock_file.write_text(
            "",
            encoding="utf-8",
        )

        _set_file_age(
            lock_file,
            days=100,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert lock_file.exists()

    def test_directory_with_jsonl_suffix_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "directory.jsonl"
        )

        directory.mkdir()

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert directory.is_dir()

    def test_jsonl_symlink_is_excluded(
        self,
        tmp_path: Path,
    ) -> None:
        target = (
            tmp_path
            / "target.data"
        )

        target.write_text(
            "target",
            encoding="utf-8",
        )

        _set_file_age(
            target,
            days=100,
        )

        link = (
            tmp_path
            / "previous.jsonl"
        )

        try:
            link.symlink_to(
                target
            )
        except OSError:
            pytest.skip(
                "Symbolic links are unavailable."
            )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert link.is_symlink()
        assert target.exists()


class TestJsonSinkArchiveCollision:
    def test_existing_timestamped_archive_is_not_overwritten(
        self,
        tmp_path: Path,
    ) -> None:
        source = (
            tmp_path
            / "previous.jsonl"
        )

        source.write_text(
            '{"message":"new"}\n',
            encoding="utf-8",
        )

        modified_at = datetime(
            2026,
            10,
            20,
            14,
            35,
            tzinfo=timezone.utc,
        )

        _set_modified_at(
            source,
            modified_at,
        )

        archive_path = (
            tmp_path
            / "monitaudit_202610201435.zip"
        )

        with zipfile.ZipFile(
            archive_path,
            mode="w",
        ) as archive:
            archive.writestr(
                "existing.jsonl",
                '{"message":"existing"}\n',
            )

        original_archive = (
            archive_path.read_bytes()
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        assert source.exists()

        assert (
            archive_path.read_bytes()
            == original_archive
        )

        with zipfile.ZipFile(
            archive_path,
            mode="r",
        ) as archive:
            assert archive.namelist() == [
                "existing.jsonl",
            ]

    def test_different_minutes_create_different_archives(
        self,
        tmp_path: Path,
    ) -> None:
        first = (
            tmp_path
            / "first.jsonl"
        )

        second = (
            tmp_path
            / "second.jsonl"
        )

        first.write_text(
            '{"message":"first"}\n',
            encoding="utf-8",
        )

        second.write_text(
            '{"message":"second"}\n',
            encoding="utf-8",
        )

        first_time = datetime(
            2026,
            10,
            20,
            14,
            35,
            tzinfo=timezone.utc,
        )

        second_time = datetime(
            2026,
            10,
            20,
            14,
            36,
            tzinfo=timezone.utc,
        )

        _set_modified_at(
            first,
            first_time,
        )

        _set_modified_at(
            second,
            second_time,
        )

        JsonSink(
            path=str(tmp_path / "monitaudit"),
            file_cycle=10,
        )

        first_archive = (
            tmp_path
            / "monitaudit_202610201435.zip"
        )

        second_archive = (
            tmp_path
            / "monitaudit_202610201436.zip"
        )

        assert first_archive.exists()
        assert second_archive.exists()
        assert not first.exists()
        assert not second.exists()


class TestJsonSinkWrite:
    def test_write_creates_jsonl_file(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        log = _base_log()

        with patch.object(
            BaseLog,
            "model_dump_json",
            return_value='{"message":"test"}',
        ):
            sink.write(
                log
            )

        assert sink.path.is_file()

    def test_write_appends_newline(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        log = _base_log()

        with patch.object(
            BaseLog,
            "model_dump_json",
            return_value='{"message":"test"}',
        ):
            sink.write(
                log
            )

        assert sink.path.read_text(
            encoding="utf-8",
        ) == '{"message":"test"}\n'

    def test_write_appends_multiple_json_lines(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        log = _base_log()

        with patch.object(
            BaseLog,
            "model_dump_json",
            side_effect=[
                '{"message":"first"}',
                '{"message":"second"}',
            ],
        ):
            sink.write(
                log
            )

            sink.write(
                log
            )

        lines = sink.path.read_text(
            encoding="utf-8",
        ).splitlines()

        assert lines == [
            '{"message":"first"}',
            '{"message":"second"}',
        ]

    def test_written_lines_are_valid_json(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            path=str(tmp_path / "monitaudit"),
        )

        log = _base_log()

        expected = {
            "level": "INFO",
            "message": "test",
        }

        with patch.object(
            BaseLog,
            "model_dump_json",
            return_value=json.dumps(
                expected
            ),
        ):
            sink.write(
                log
            )

        line = sink.path.read_text(
            encoding="utf-8",
        ).strip()

        assert json.loads(
            line
        ) == expected