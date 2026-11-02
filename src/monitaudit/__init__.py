# src/monitaudit/__init__.py

from __future__ import annotations

from monitaudit.logger import monitauditLogger
from monitaudit.models.context import LogContext
from monitaudit.models.monitaudit import Monitaudit
from monitaudit.sinks import (
    ConsoleSink,
    DeltaSink,
    FileSink,
    JsonSink,
)
from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


def monitaudit_init() -> Monitaudit:
    return build_monitaudit()


__version__ = "1.2.5"


__all__ = [
    "ConsoleSink",
    "DeltaSink",
    "FileSink",
    "JsonSink",
    "LogContext",
    "Monitaudit",
    "monitauditLogger",
    "build_monitaudit",
    "monitaudit_init",
]