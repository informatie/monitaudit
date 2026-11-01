from __future__ import annotations

import json
from threading import Lock

from monitaudit.constants import (
    FUNCTION_END,
    FUNCTION_ERROR,
    FUNCTION_START,
)
from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink

TRACE_END_EVENTS = frozenset(
    {
        FUNCTION_END,
        FUNCTION_ERROR,
    }
)


class ConsoleSink(Sink):
    def __init__(
        self,
        indent_size: int = 4,
        location_width: int = 30,
        parameters: list[str] | None = None,
    ) -> None:
        if indent_size < 0:
            raise ValueError("indent_size must be 0 or greater.")

        if location_width < 0:
            raise ValueError("location_width must be 0 or greater.")

        self.indent_size = indent_size
        self.location_width = location_width
        self._depths: dict[str, int] = {}
        self._lock = Lock()
        self.parameters = tuple(
            parameters or ()
        )

    def write(self, log: BaseLog) -> None:
        with self._lock:
            depth = self._get_depth(log)
            indent = " " * (depth * self.indent_size)
            location = self._format_location(log)
            parameters = self._format_parameters(log)
            print(
                f"{log.timestamp.isoformat()} "
                f"{log.level!s:<8} "
                f"{location:<{self.location_width}} "
                f"{indent}{log.message}",
                f"{parameters}"
            )

            self._update_depth(log, depth)
    def _format_parameters(
            self,
            log: BaseLog,
        ) -> str:
            if not self.parameters:
                return ""

            selected = {
                name: log.parameters[name]
                for name in self.parameters
                if name in log.parameters
            }

            if not selected:
                return ""

            return (
                " "
                "parameters="
                + json.dumps(
                    selected,
                    default=str,
                    sort_keys=False,
                )
            )
    def _get_depth(self, log: BaseLog) -> int:
        if log.call_id is None:
            return 0

        event = log.attributes.get("event")

        if event == FUNCTION_START:
            if log.parent_call_id is None:
                return 0

            parent_depth = self._depths.get(
                log.parent_call_id,
                0,
            )
            return parent_depth + 1

        call_depth = self._depths.get(
            log.call_id,
            0,
        )

        if event in TRACE_END_EVENTS:
            return call_depth

        return call_depth + 1

    def _update_depth(
        self,
        log: BaseLog,
        depth: int,
    ) -> None:
        if log.call_id is None:
            return

        event = log.attributes.get("event")

        if event == FUNCTION_START:
            self._depths[log.call_id] = depth
        elif event in TRACE_END_EVENTS:
            self._depths.pop(log.call_id, None)

    @staticmethod
    def _format_location(log: BaseLog) -> str:
        return ".".join(
            part
            for part in (log.module, log.function)
            if part
        )