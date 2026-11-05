# src/monitaudit/sinks/json.py

from __future__ import annotations

import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import IO

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.utilities.archive_files import (
    LogFileRotator,
    RotationError,
    write_cycle_start,
)


class JsonSinkError(RuntimeError):
    """Raised when JsonSink cannot read, write, or rotate its output."""


class JsonSinkLockTimeoutError(JsonSinkError):
    """Raised when the inter-process lock cannot be acquired in time."""


class JsonSink(Sink):
    """Write BaseLog records as JSON Lines.

    Thread-level locking protects writers within the current process.

    On Linux and other POSIX systems, ``fcntl.flock`` provides
    cooperative locking between processes using the same lock file.

    When ``file_cycle`` is configured, the active JSONL file is rotated
    after the configured number of days.

    The cycle age is stored separately from the JSONL file modification
    time, so appending records does not postpone rotation.

    Rotation is checked immediately before every write. Merely creating
    a JsonSink does not start a new logging cycle.

    If an existing JSONL file has no cycle metadata, its current mtime
    is used once as the initial cycle-start timestamp. After metadata
    has been created, mtime is no longer used for rotation decisions.

    Rotation and writing occur while holding the same thread-level and
    inter-process locks.
    """

    def __init__(
        self,
        path: str,
        file_cycle: int | None = None,
        lock_timeout_seconds: float = 10.0,
        lock_poll_interval_seconds: float = 0.05,
    ) -> None:
        self._validate_settings(
            path=path,
            file_cycle=file_cycle,
            lock_timeout_seconds=lock_timeout_seconds,
            lock_poll_interval_seconds=lock_poll_interval_seconds,
        )

        self.file_cycle = file_cycle
        self.lock_timeout_seconds = float(
            lock_timeout_seconds
        )
        self.lock_poll_interval_seconds = float(
            lock_poll_interval_seconds
        )

        self._thread_lock = Lock()

        base_path = Path(path).expanduser()

        self.path = base_path.with_suffix(".jsonl")
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

        # Important:
        # Do not rotate or create cycle metadata here.
        #
        # The cycle begins on the first actual write. If an existing
        # JSONL file is found at that time without cycle metadata, its
        # mtime is used once to bootstrap the cycle.

    @staticmethod
    def _validate_settings(
        *,
        path: str,
        file_cycle: int | None,
        lock_timeout_seconds: float,
        lock_poll_interval_seconds: float,
    ) -> None:
        if not isinstance(path, str):
            raise TypeError(
                "JsonSink path must be a string."
            )

        if not path.strip():
            raise ValueError(
                "JsonSink path cannot be empty."
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

    def _create_parent_directory(self) -> None:
        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise JsonSinkError(
                "Could not create the JsonSink directory "
                f"{self.path.parent}: {exc}"
            ) from exc

    def write(
        self,
        log: BaseLog,
    ) -> None:
        """Append one BaseLog record as JSON Lines."""
        if not isinstance(log, BaseLog):
            raise TypeError(
                "JsonSink.write() expects a BaseLog instance; "
                f"received {type(log).__name__}."
            )

        try:
            json_line = log.model_dump_json()

            with self._exclusive_write_lock():
                self._rotate_if_required_unlocked()

                with self.path.open(
                    mode="a",
                    encoding="utf-8",
                ) as file:
                    file.write(json_line)
                    file.write("\n")
                    file.flush()

        except JsonSinkError:
            raise

        except Exception as exc:
            raise JsonSinkError(
                f"Could not write JSON log to {self.path}: {exc}"
            ) from exc

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
                    raise JsonSinkError(
                        "Could not open the JsonSink lock file "
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
                    raise JsonSinkLockTimeoutError(
                        "Timed out waiting for the JsonSink lock. "
                        f"Lock file: {self.lock_path}. "
                        f"Timeout: {self.lock_timeout_seconds} "
                        "seconds."
                    )

                time.sleep(
                    self.lock_poll_interval_seconds
                )

            except OSError as exc:
                raise JsonSinkError(
                    "Could not acquire the JsonSink process lock "
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
        """Rotate the active JSONL file when its cycle has expired.

        The caller must already hold the exclusive write lock.

        An existing output file without cycle metadata is bootstrapped
        once using its mtime. After that, only persistent cycle metadata
        determines rotation.
        """
        if self._rotator is None:
            return None

        try:
            self._bootstrap_existing_cycle_unlocked()

            return self._rotator.rotate_if_required()

        except RotationError as exc:
            raise JsonSinkError(
                "Could not rotate JsonSink output "
                f"{self.path}: {exc}"
            ) from exc

        except OSError as exc:
            raise JsonSinkError(
                "Could not access JsonSink output "
                f"{self.path}: {exc}"
            ) from exc

    def _bootstrap_existing_cycle_unlocked(
        self,
    ) -> None:
        """Initialise cycle metadata from an existing file's mtime.

        This is a one-time migration path for JSONL files created
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
            raise JsonSinkError(
                "JsonSink output path exists but is not a regular file: "
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
            raise JsonSinkError(
                "Could not initialise JsonSink cycle metadata "
                f"from {self.path}: {exc}"
            ) from exc

        except OSError as exc:
            raise JsonSinkError(
                "Could not inspect existing JsonSink output "
                f"{self.path}: {exc}"
            ) from exc

