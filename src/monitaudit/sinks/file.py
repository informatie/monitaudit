# src/monitaudit/sinks/file.py

from __future__ import annotations

import csv
import fcntl
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import IO, Literal

from monitaudit.models.base import BaseLog
from monitaudit.models.mapping import (
    LOG_FIELD_NAMES,
    log_record,
)
from monitaudit.sinks.base import Sink
from monitaudit.utilities.archive_files import (
    LogFileRotator,
    RotationError,
    write_cycle_start,
)


FileFormat = Literal["text", "csv"]


class FileSinkError(RuntimeError):
    """Raised when FileSink cannot read or write its output."""


class FileSinkLockTimeoutError(FileSinkError):
    """Raised when the inter-process lock cannot be acquired in time."""


class FileSink(Sink):
    """Write BaseLog records to a text or CSV file.

    Thread-level locking protects writers within the current process.

    On Linux and other POSIX systems, ``fcntl.flock`` provides
    cooperative locking between processes using the same lock file.

    When ``file_cycle`` is configured, the active output file is
    rotated after the configured number of days. The cycle age is
    stored separately from the output file modification time, so
    appending records does not postpone rotation.

    Rotation is checked immediately before each write. Merely creating
    a FileSink does not start a new logging cycle.

    If an existing output file has no cycle metadata, its current mtime
    is used once as the initial cycle-start timestamp. After metadata
    has been created, mtime is no longer used for rotation decisions.

    Text and CSV output files are compressed into ZIP archives during
    rotation. A new CSV file automatically receives the current
    MonitAudit CSV header.

    Rotation and writing occur while holding the same thread-level and
    inter-process locks.
    """

    def __init__(
        self,
        path: str,
        format: FileFormat = "text",
        delimiter: str = ";",
        lock_timeout_seconds: float = 10.0,
        lock_poll_interval_seconds: float = 0.05,
        fsync: bool = False,
        file_cycle: int | None = None,
    ) -> None:
        self._validate_settings(
            path=path,
            format=format,
            delimiter=delimiter,
            lock_timeout_seconds=lock_timeout_seconds,
            lock_poll_interval_seconds=lock_poll_interval_seconds,
            fsync=fsync,
            file_cycle=file_cycle,
        )

        self.format: FileFormat = format
        self.delimiter = delimiter
        self.lock_timeout_seconds = float(
            lock_timeout_seconds
        )
        self.lock_poll_interval_seconds = float(
            lock_poll_interval_seconds
        )
        self.fsync = fsync
        self.file_cycle = file_cycle

        self._thread_lock = Lock()

        base_path = Path(path).expanduser()

        suffix = (
            ".csv"
            if self.format == "csv"
            else ".txt"
        )

        self.path = base_path.with_suffix(suffix)
        self.lock_path = Path(f"{self.path}.lock")

        self._create_parent_directory()

        self._rotator: LogFileRotator | None = (
            LogFileRotator(
                path=self.path,
                file_cycle=self.file_cycle,
            )
            if self.file_cycle is not None
            else None
        )

        # Do not check rotation here. Initialising the sink must not
        # create cycle metadata or start a new logging cycle.
        #
        # Existing CSV files are still validated during initialisation.
        if self.format == "csv":
            with self._exclusive_write_lock():
                self._validate_existing_csv_header_unlocked()

    @staticmethod
    def _validate_settings(
        *,
        path: str,
        format: str,
        delimiter: str,
        lock_timeout_seconds: float,
        lock_poll_interval_seconds: float,
        fsync: bool,
        file_cycle: int | None,
    ) -> None:
        if not isinstance(path, str):
            raise TypeError(
                "FileSink path must be a string."
            )

        if not path.strip():
            raise ValueError(
                "FileSink path cannot be empty."
            )

        if format not in ("text", "csv"):
            raise ValueError(
                "Unsupported FileSink format "
                f"{format!r}; expected 'text' or 'csv'."
            )

        if not isinstance(delimiter, str):
            raise TypeError(
                "CSV delimiter must be a string."
            )

        if (
            format == "csv"
            and len(delimiter) != 1
        ):
            raise ValueError(
                "CSV delimiter must contain exactly one character; "
                f"received {delimiter!r}."
            )

        if (
            format == "csv"
            and delimiter in {
                "\r",
                "\n",
                "\0",
            }
        ):
            raise ValueError(
                "CSV delimiter cannot be a newline or null character."
            )

        if (
            not isinstance(
                lock_timeout_seconds,
                (int, float),
            )
            or isinstance(
                lock_timeout_seconds,
                bool,
            )
        ):
            raise TypeError(
                "lock_timeout_seconds must be numeric."
            )

        if lock_timeout_seconds < 0:
            raise ValueError(
                "lock_timeout_seconds cannot be negative."
            )

        if (
            not isinstance(
                lock_poll_interval_seconds,
                (int, float),
            )
            or isinstance(
                lock_poll_interval_seconds,
                bool,
            )
        ):
            raise TypeError(
                "lock_poll_interval_seconds must be numeric."
            )

        if lock_poll_interval_seconds <= 0:
            raise ValueError(
                "lock_poll_interval_seconds must be greater than zero."
            )

        if not isinstance(fsync, bool):
            raise TypeError(
                "fsync must be a boolean."
            )

        if (
            file_cycle is not None
            and (
                not isinstance(file_cycle, int)
                or isinstance(file_cycle, bool)
            )
        ):
            raise TypeError(
                "file_cycle must be an integer number of days or None."
            )

        if (
            file_cycle is not None
            and file_cycle <= 0
        ):
            raise ValueError(
                "file_cycle must be greater than zero."
            )

    def _create_parent_directory(self) -> None:
        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise FileSinkError(
                "Could not create the FileSink directory "
                f"{self.path.parent}: {exc}"
            ) from exc

    def write(
        self,
        log: BaseLog,
    ) -> None:
        """Write one BaseLog record to the configured output file."""
        if not isinstance(log, BaseLog):
            raise TypeError(
                "FileSink.write() expects a BaseLog instance; "
                f"received {type(log).__name__}."
            )

        if self.format == "csv":
            self._write_csv(log)
            return

        self._write_text(log)

    @contextmanager
    def _exclusive_write_lock(
        self,
    ) -> Iterator[None]:
        """Acquire the thread and cooperative process locks."""
        with self._thread_lock:
            lock_file: IO[str] | None = None
            process_lock_acquired = False

            try:
                try:
                    lock_file = self.lock_path.open(
                        mode="a+",
                        encoding="utf-8",
                    )
                except OSError as exc:
                    raise FileSinkError(
                        "Could not open the FileSink lock file "
                        f"{self.lock_path}: {exc}"
                    ) from exc

                self._acquire_process_lock(lock_file)
                process_lock_acquired = True

                yield

            finally:
                if lock_file is not None:
                    self._close_lock_file(
                        lock_file,
                        release_lock=process_lock_acquired,
                    )

    def _acquire_process_lock(
        self,
        lock_file: IO[str],
    ) -> None:
        deadline = (
            time.monotonic()
            + self.lock_timeout_seconds
        )

        while True:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                return

            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise FileSinkLockTimeoutError(
                        "Timed out waiting for the FileSink lock. "
                        f"Lock file: {self.lock_path}. "
                        f"Timeout: {self.lock_timeout_seconds} "
                        "seconds."
                    )

                time.sleep(
                    self.lock_poll_interval_seconds
                )

            except OSError as exc:
                raise FileSinkError(
                    "Could not acquire the FileSink process lock "
                    f"{self.lock_path}: {exc}"
                ) from exc

    @staticmethod
    def _close_lock_file(
        lock_file: IO[str],
        *,
        release_lock: bool,
    ) -> None:
        if release_lock:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )
            except OSError:
                pass

        try:
            lock_file.close()
        except OSError:
            pass

    def _rotate_if_required_unlocked(
        self,
    ) -> Path | None:
        """Rotate the active output file when its cycle has expired.

        The caller must already hold the exclusive write lock.

        An existing output file without cycle metadata is bootstrapped
        once using its mtime. Files managed after that point use only
        the persistent cycle metadata.
        """
        if self._rotator is None:
            return None

        try:
            self._bootstrap_existing_cycle_unlocked()

            return self._rotator.rotate_if_required()

        except RotationError as exc:
            raise FileSinkError(
                "Could not rotate FileSink output "
                f"{self.path}: {exc}"
            ) from exc

        except OSError as exc:
            raise FileSinkError(
                "Could not access FileSink output "
                f"{self.path}: {exc}"
            ) from exc

    def  _bootstrap_existing_cycle_unlocked(
        self,
    ) -> None:
        """Initialise cycle metadata from an existing file's mtime.

        This is a one-time migration path for output files created
        before persistent cycle metadata was introduced.

        The caller must already hold the exclusive write lock.
        """
        if self._rotator is None:
            return

        if self._rotator.metadata_path.exists():
            return

        if not self.path.exists():
            return

        if not self.path.is_file():
            raise FileSinkError(
                "FileSink output path exists but is not a regular file: "
                f"{self.path}."
            )

        try:
            modified_at = datetime.fromtimestamp(
                self.path.stat().st_mtime,
                tz=timezone.utc,
            )

            write_cycle_start(
                self.path,
                modified_at,
            )

        except RotationError as exc:
            raise FileSinkError(
                "Could not initialise FileSink cycle metadata "
                f"from {self.path}: {exc}"
            ) from exc

        except OSError as exc:
            raise FileSinkError(
                "Could not inspect existing FileSink output "
                f"{self.path}: {exc}"
            ) from exc

    def _write_csv(
        self,
        log: BaseLog,
    ) -> None:
        try:
            row = self._csv_row(log)

            with self._exclusive_write_lock():
                self._rotate_if_required_unlocked()
                self._validate_existing_csv_header_unlocked()

                write_header = (
                    not self.path.exists()
                    or self.path.stat().st_size == 0
                )

                with self.path.open(
                    mode="a",
                    encoding="utf-8",
                    newline="",
                ) as file:
                    writer = csv.DictWriter(
                        file,
                        fieldnames=LOG_FIELD_NAMES,
                        delimiter=self.delimiter,
                        quoting=csv.QUOTE_MINIMAL,
                        extrasaction="raise",
                    )

                    if write_header:
                        writer.writeheader()

                    writer.writerow(row)

                    self._flush(
                        file,
                        synchronise=self.fsync,
                    )

        except FileSinkError:
            raise

        except Exception as exc:
            raise FileSinkError(
                f"Could not write CSV log to {self.path}: {exc}"
            ) from exc

    def _write_text(
        self,
        log: BaseLog,
    ) -> None:
        try:
            text = self._format(log)

            with self._exclusive_write_lock():
                self._rotate_if_required_unlocked()

                with self.path.open(
                    mode="a",
                    encoding="utf-8",
                ) as file:
                    file.write(text)
                    file.write("\n")

                    self._flush(
                        file,
                        synchronise=self.fsync,
                    )

        except FileSinkError:
            raise

        except Exception as exc:
            raise FileSinkError(
                f"Could not write text log to {self.path}: {exc}"
            ) from exc

    @staticmethod
    def _flush(
        file: IO[str],
        *,
        synchronise: bool,
    ) -> None:
        file.flush()

        if synchronise:
            os.fsync(file.fileno())

    def _validate_existing_csv_header_unlocked(
        self,
    ) -> None:
        """Validate the header of a non-empty existing CSV file.

        The caller must already hold the exclusive write lock.
        """
        if not self.path.exists():
            return

        try:
            if self.path.stat().st_size == 0:
                return

            with self.path.open(
                mode="r",
                encoding="utf-8",
                newline="",
            ) as file:
                reader = csv.reader(
                    file,
                    delimiter=self.delimiter,
                )

                existing_header = next(
                    reader,
                    None,
                )

        except (OSError, csv.Error) as exc:
            raise FileSinkError(
                f"Could not read CSV header from {self.path}: "
                f"{exc}"
            ) from exc

        expected_header = list(LOG_FIELD_NAMES)

        if existing_header != expected_header:
            raise FileSinkError(
                "Existing CSV header does not match the current "
                "MonitAudit CSV schema. "
                f"File: {self.path}. "
                f"Expected: {expected_header!r}. "
                f"Found: {existing_header!r}."
            )

    @staticmethod
    def _csv_row(
        log: BaseLog,
    ) -> dict[str, str]:
        record = log_record(log)

        return {
            "timestamp": record["timestamp"].isoformat(),
            "level": FileSink._optional_text(
                record["level"]
            ),
            "application": FileSink._optional_text(
                record["application"]
            ),
            "environment": FileSink._optional_text(
                record["environment"]
            ),
            "module": FileSink._optional_text(
                record["module"]
            ),
            "function": FileSink._optional_text(
                record["function"]
            ),
            "correlation_id": FileSink._optional_text(
                record["correlation_id"]
            ),
            "run_id": FileSink._optional_text(
                record["run_id"]
            ),
            "call_id": FileSink._optional_text(
                record["call_id"]
            ),
            "parent_call_id": FileSink._optional_text(
                record["parent_call_id"]
            ),
            "event": FileSink._optional_text(
                record["event"]
            ),
            "message": FileSink._optional_text(
                record["message"]
            ),
            "parameters": FileSink._json_text(
                record["parameters"]
            ),
            "attributes": FileSink._json_text(
                record["attributes"]
            ),
            "duration_ms": FileSink._optional_text(
                record["duration_ms"]
            ),
            "error_type": FileSink._optional_text(
                record["error_type"]
            ),
            "error_message": FileSink._optional_text(
                record["error_message"]
            ),
            "traceback": FileSink._traceback_text(
                record["traceback"]
            ),
        }

    @staticmethod
    def _optional_text(
        value: object,
    ) -> str:
        if value is None:
            return ""

        try:
            return str(value)
        except Exception:
            return FileSink._safe_repr(value)

    @staticmethod
    def _json_text(
        value: object,
    ) -> str:
        try:
            return json.dumps(
                value,
                default=str,
                ensure_ascii=False,
                sort_keys=False,
                separators=(",", ":"),
            )

        except Exception as exc:
            fallback = {
                "serialization_error": type(exc).__name__,
                "value": FileSink._safe_repr(value),
            }

            try:
                return json.dumps(
                    fallback,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            except Exception:
                return (
                    '{"serialization_error":'
                    '"unrecoverable serialization failure"}'
                )

    @staticmethod
    def _safe_repr(
        value: object,
    ) -> str:
        try:
            return repr(value)
        except Exception:
            return (
                f"<unrepresentable "
                f"{type(value).__name__}>"
            )

    @staticmethod
    def _traceback_text(
        traceback_value: object,
    ) -> str:
        if traceback_value is None:
            return ""

        if isinstance(traceback_value, str):
            return traceback_value.rstrip()

        if isinstance(
            traceback_value,
            (list, tuple),
        ):
            try:
                return "".join(
                    str(item)
                    for item in traceback_value
                ).rstrip()
            except Exception:
                return FileSink._safe_repr(
                    traceback_value
                )

        return FileSink._optional_text(
            traceback_value
        ).rstrip()
    
    @staticmethod
    def _format(
        log: BaseLog,
    ) -> str:
        record = log_record(log)

        location = ".".join(
            FileSink._optional_text(part)
            for part in (
                record["module"],
                record["function"],
            )
            if part
        )

        parameters = FileSink._json_text(
            record["parameters"]
        )

        attributes = FileSink._json_text(
            record["attributes"]
        )

        run_id = (
            FileSink._optional_text(
                record["run_id"]
            )
            or "-"
        )

        call_id = (
            FileSink._optional_text(
                record["call_id"]
            )
            or "-"
        )

        parent_call_id = (
            FileSink._optional_text(
                record["parent_call_id"]
            )
            or "-"
        )

        event = (
            FileSink._optional_text(
                record["event"]
            )
            or "-"
        )

        duration_ms = (
            FileSink._optional_text(
                record["duration_ms"]
            )
            or "-"
        )

        line = (
            f"{record['timestamp'].isoformat()} "
            f"{FileSink._optional_text(record['level']):<8} "
            f"application="
            f"{FileSink._optional_text(record['application'])} "
            f"environment="
            f"{FileSink._optional_text(record['environment'])} "
            f"correlation_id="
            f"{FileSink._optional_text(record['correlation_id'])} "
            f"run_id={run_id} "
            f"call_id={call_id} "
            f"parent_call_id={parent_call_id} "
            f"event={event} "
            f"duration_ms={duration_ms} "
            f"{location:<32} "
            f"{FileSink._optional_text(record['message']):<32} "
            f"parameters={parameters} "
            f"attributes={attributes}"
        )

        error_details = FileSink._format_error_record(
            record
        )

        if error_details:
            return f"{line}\n{error_details}"

        return line

    @staticmethod
    def _format_error_record(
        record: dict[str, object],
    ) -> str:
        error_type = FileSink._optional_text(
            record["error_type"]
        )

        error_message = FileSink._optional_text(
            record["error_message"]
        )

        traceback_text = FileSink._traceback_text(
            record["traceback"]
        )

        if (
            not error_type
            and not error_message
            and not traceback_text
        ):
            return ""

        lines: list[str] = []

        if error_type:
            lines.append(
                f"error_type={error_type}"
            )

        if error_message:
            lines.append(
                f"error_message={error_message}"
            )

        if traceback_text:
            lines.append("traceback:")
            lines.append(traceback_text)

        return "\n".join(lines)
