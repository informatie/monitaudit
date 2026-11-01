# src/monitaudit/__init__.py
from __future__ import annotations

from .logger import monitauditLogger
from .models.context import LogContext
from .models.monitaudit import Monitaudit
from .sinks import (
    ConsoleSink,
    DeltaSink,
    FileSink,
    JsonSink,
)
from monitaudit.utilities.build_monitaudit import build_monitaudit

def monitaudit_init():
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
]