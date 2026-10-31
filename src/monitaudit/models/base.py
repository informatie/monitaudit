from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from monitaudit.models.context import LogContext


class BaseLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # WHEN
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    # SEVERITY
    level: str

    # WHERE / EXECUTION CONTEXT    
    context: LogContext

    # WHERE
    module: str | None = None
    function: str | None = None

    # WHICH EXECUTION / TRACE
    call_id: str | None = None
    parent_call_id: str | None = None
    
    # WHAT
    event: str | None = None
    message: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    # PERFORMANCE
    duration_ms: float | None = Field(default=None, ge=0)

    # FAILURE
    error_type: str | None = None
    error_message: str | None = None
    traceback: list[str] | None = None
    
    attributes: dict[str, Any] = Field(default_factory=dict)