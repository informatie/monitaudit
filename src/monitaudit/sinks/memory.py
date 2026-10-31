# src/monitaudit/sinks/memory.py

from __future__ import annotations

from collections.abc import Iterator

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink


class MemorySink(Sink):
    """
    Sink that stores Monitaudit log records in memory.

    Primarily intended for tests and temporary in-memory inspection.
    Log records are retained in insertion order until clear() is called
    or the MemorySink instance is discarded.
    """

    def __init__(self) -> None:
        self.logs: list[BaseLog] = []

    def write(
        self,
        log: BaseLog,
    ) -> None:
        self.logs.append(log)

    def clear(self) -> None:
        self.logs.clear()

    def __len__(self) -> int:
        return len(self.logs)

    def __iter__(
        self,
    ) -> Iterator[BaseLog]:
        return iter(self.logs)