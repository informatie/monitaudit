from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LogContext(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    application: str = Field(min_length=1)
    environment: str = Field(min_length=1)

    correlation_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    run_id: str | None = None

    attributes: dict[str, Any] = Field(default_factory=dict)