from __future__ import annotations

import json
from pathlib import Path

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink


class FileSink(Sink):
    def __init__(self, path: str) -> None:
        if not path:
            raise ValueError("File sink path cannot be empty.")

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, log: BaseLog) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(self._format(log))
            file.write("\n")

    @staticmethod
    def _format(log: BaseLog) -> str:
        location = ".".join(
            part for part in (log.module, log.function) if part
        )

        parameters = json.dumps(
            log.parameters,
            default=str,
            sort_keys=False,
        )

        line = (
            f"{log.timestamp.isoformat()} "
            f"{str(log.level):<8} "
            f"application={log.context.application} "
            f"environment={log.context.environment} "
            f"correlation_id={log.context.correlation_id} "
            f"run_id={log.context.run_id or '-'} "
            f"{location:<32} "
            f"{log.message:<32} "
            f"parameters={parameters}"
        )

        error_details = FileSink._format_error(log)

        if error_details:
            return f"{line}\n{error_details}"

        return line

    @staticmethod
    def _format_error(log: BaseLog) -> str:
        error_type = getattr(log, "error_type", None)
        error_message = getattr(log, "error_message", None)
        traceback_lines = getattr(log, "traceback", None)

        if not error_type and not error_message and not traceback_lines:
            return ""

        lines: list[str] = []

        if error_type:
            lines.append(f"error_type={error_type}")

        if error_message:
            lines.append(f"error_message={error_message}")

        if traceback_lines:
            lines.append("traceback:")
            lines.append("".join(traceback_lines).rstrip())

        return "\n".join(lines)
