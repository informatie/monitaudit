# src/monitaudit/utilities/archive_files.py

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile


_ARCHIVE_PREFIX: Final[str] = "monitaudit_"
_ARCHIVE_SUFFIX: Final[str] = ".zip"
_METADATA_SUFFIX: Final[str] = ".cycle.json"
_TIMESTAMP_FORMAT: Final[str] = "%Y%m%d%H%M"


class RotationError(RuntimeError):
    """Raised when a log file cannot be rotated safely."""


class InvalidCycleMetadataError(RotationError):
    """Raised when persisted cycle metadata is invalid."""


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def normalise_utc(value: datetime) -> datetime:
    """
    Return a timezone-aware UTC datetime.

    Naive datetime values are interpreted as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def cycle_metadata_path(log_path: Path) -> Path:
    """
    Return the metadata path belonging to a log file.

    Example:
        monitaudit.log -> monitaudit.log.cycle.json
    """
    return log_path.with_name(f"{log_path.name}{_METADATA_SUFFIX}")


def format_datetime(value: datetime) -> str:
    """Serialise a datetime as an ISO 8601 UTC string."""
    return normalise_utc(value).isoformat()


def parse_datetime(value: object) -> datetime:
    """Parse and validate an ISO 8601 datetime value."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidCycleMetadataError(
            "Cycle metadata must contain a non-empty datetime string."
        )

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidCycleMetadataError(
            f"Invalid cycle-start datetime: {value!r}."
        ) from exc

    return normalise_utc(parsed)


def write_cycle_start(
    log_path: Path,
    cycle_started_at: datetime,
) -> Path:
    """
    Persist the cycle-start timestamp atomically.

    The metadata file is written beside the active log file.
    """
    metadata_path = cycle_metadata_path(log_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "cycle_started_at": format_datetime(cycle_started_at),
    }

    temporary_path: Path | None = None

    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{metadata_path.name}.",
            suffix=".tmp",
            dir=metadata_path.parent,
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary_path.replace(metadata_path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        raise RotationError(
            f"Could not write cycle metadata: {metadata_path}."
        ) from exc

    return metadata_path


def read_cycle_start(log_path: Path) -> datetime | None:
    """
    Read the cycle-start timestamp.

    Returns None when no metadata file exists.
    """
    metadata_path = cycle_metadata_path(log_path)

    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidCycleMetadataError(
            f"Could not read cycle metadata: {metadata_path}."
        ) from exc

    if not isinstance(payload, dict):
        raise InvalidCycleMetadataError(
            f"Cycle metadata must contain a JSON object: {metadata_path}."
        )

    return parse_datetime(payload.get("cycle_started_at"))


def initialise_cycle(
    log_path: Path,
    *,
    now: datetime | None = None,
) -> datetime:
    """
    Return the existing cycle start or create a new one.

    This function does not use file mtime. If metadata is absent, the current
    time becomes the beginning of the first managed cycle.
    """
    existing_cycle_start = read_cycle_start(log_path)

    if existing_cycle_start is not None:
        return existing_cycle_start

    cycle_started_at = normalise_utc(now or utc_now())
    write_cycle_start(log_path, cycle_started_at)

    return cycle_started_at


def should_rotate(
    cycle_started_at: datetime,
    file_cycle: int,
    *,
    now: datetime | None = None,
) -> bool:
    """
    Return True when the configured logging cycle has expired.

    file_cycle is expressed in complete 24-hour periods.
    """
    if isinstance(file_cycle, bool) or not isinstance(file_cycle, int):
        raise TypeError("file_cycle must be an integer.")

    if file_cycle <= 0:
        raise ValueError("file_cycle must be greater than zero.")

    started_at = normalise_utc(cycle_started_at)
    current_time = normalise_utc(now or utc_now())

    if current_time < started_at:
        return False

    expires_at = started_at + timedelta(days=file_cycle)

    return current_time >= expires_at


def archive_filename(
    directory: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """
    Build a unique MonitAudit archive filename.

    The first candidate is:
        monitaudit_YYYYMMDDHHMM.zip

    A numeric suffix is added if an archive with that minute already exists.
    """
    current_time = normalise_utc(now or utc_now())
    timestamp = current_time.strftime(_TIMESTAMP_FORMAT)

    candidate = directory / (
        f"{_ARCHIVE_PREFIX}{timestamp}{_ARCHIVE_SUFFIX}"
    )

    if not candidate.exists():
        return candidate

    sequence = 1

    while True:
        candidate = directory / (
            f"{_ARCHIVE_PREFIX}{timestamp}_{sequence:02d}"
            f"{_ARCHIVE_SUFFIX}"
        )

        if not candidate.exists():
            return candidate

        sequence += 1


def create_archive(
    log_path: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """
    Put one active log file into a ZIP archive atomically.

    The source file is only deleted after the completed temporary ZIP has been
    moved to its final location.
    """
    if not log_path.exists():
        raise FileNotFoundError(f"Log file does not exist: {log_path}.")

    if not log_path.is_file():
        raise RotationError(f"Log path is not a regular file: {log_path}.")

    if log_path.suffix.casefold() == _ARCHIVE_SUFFIX:
        raise RotationError(f"ZIP files cannot be rotated: {log_path}.")

    archive_path = archive_filename(log_path.parent, now=now)
    temporary_archive = archive_path.with_name(
        f".{archive_path.name}.tmp"
    )

    try:
        with ZipFile(
            temporary_archive,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as archive:
            archive.write(log_path, arcname=log_path.name)

        temporary_archive.replace(archive_path)
        log_path.unlink()
    except (OSError, ValueError) as exc:
        temporary_archive.unlink(missing_ok=True)
        archive_path.unlink(missing_ok=True)

        raise RotationError(
            f"Could not archive log file {log_path}."
        ) from exc

    return archive_path


def rotate_if_required(
    log_path: str | Path,
    file_cycle: int,
    *,
    now: datetime | None = None,
) -> Path | None:
    """
    Rotate an active log file when its cycle has expired.

    Returns:
        Path to the created ZIP archive when rotation occurred.
        None when the current cycle is still active.

    Behaviour:
        1. Read or initialise the persistent cycle start.
        2. Compare the cycle start with file_cycle.
        3. Archive the active file if it contains data.
        4. Remove stale cycle metadata.
        5. Start a new cycle.
    """
    path = Path(log_path).expanduser()
    current_time = normalise_utc(now or utc_now())

    if isinstance(file_cycle, bool) or not isinstance(file_cycle, int):
        raise TypeError("file_cycle must be an integer.")

    if file_cycle <= 0:
        raise ValueError("file_cycle must be greater than zero.")

    path.parent.mkdir(parents=True, exist_ok=True)

    cycle_started_at = initialise_cycle(path, now=current_time)

    if not should_rotate(
        cycle_started_at,
        file_cycle,
        now=current_time,
    ):
        return None

    metadata_path = cycle_metadata_path(path)
    archive_path: Path | None = None

    if path.exists() and path.is_file() and path.stat().st_size > 0:
        archive_path = create_archive(path, now=current_time)
    elif path.exists() and path.is_file():
        path.unlink()

    metadata_path.unlink(missing_ok=True)
    write_cycle_start(path, current_time)

    return archive_path


class LogFileRotator:
    """
    Manage rotation for one MonitAudit file-based sink.

    Rotation is based on a persistent cycle-start timestamp and not on mtime.
    """

    def __init__(
        self,
        path: str | Path,
        file_cycle: int,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if isinstance(file_cycle, bool) or not isinstance(file_cycle, int):
            raise TypeError("file_cycle must be an integer.")

        if file_cycle <= 0:
            raise ValueError("file_cycle must be greater than zero.")

        self._path = Path(path).expanduser()
        self._file_cycle = file_cycle
        self._clock = clock

    @property
    def path(self) -> Path:
        """Return the active log file path."""
        return self._path

    @property
    def file_cycle(self) -> int:
        """Return the configured rotation period in days."""
        return self._file_cycle

    @property
    def metadata_path(self) -> Path:
        """Return the cycle metadata path."""
        return cycle_metadata_path(self._path)

    def rotate_if_required(self) -> Path | None:
        """Rotate the active file if its cycle has expired."""
        return rotate_if_required(
            self._path,
            self._file_cycle,
            now=self._clock(),
        )