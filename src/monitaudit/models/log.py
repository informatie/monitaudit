# src/monitaudit/models/log.py

from __future__ import annotations

from typing import Literal

from pydantic import Field

from monitaudit.models.base import BaseLog


class DebugLog(BaseLog):
    level: Literal["DEBUG"] = "DEBUG"


class InfoLog(BaseLog):
    level: Literal["INFO"] = "INFO"


class WarningLog(BaseLog):
    level: Literal["WARNING"] = "WARNING"


class ErrorLog(BaseLog):
    level: Literal["ERROR"] = "ERROR"
    error_type: str | None = None
    error_message: str | None = None
    traceback: list[str] = Field( default_factory=list )


class CriticalLog(BaseLog):
    level: Literal["CRITICAL"] = "CRITICAL"
    error_type: str | None = None
    error_message: str | None = None
    traceback: list[str] = Field( default_factory=list )
