from __future__ import annotations

from pathlib import Path

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink


class JsonSink(Sink):
    def __init__(self, path: str) -> None:
        if not path:
            raise ValueError("JSON sink path cannot be empty.")

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, log: BaseLog) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(log.model_dump_json())
            file.write("\n")