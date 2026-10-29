from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from monitaudit.models.context import LogContext


class BaseLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    level: str
    message: str
    context: LogContext

    call_id: str | None = None
    parent_call_id: str | None = None

    parameters: dict[str, Any] = Field(default_factory=dict)

    duration_ms: float | None = Field(default=None, ge=0)

    module: str | None = None
    function: str | None = None

    attributes: dict[str, Any] = Field(default_factory=dict)