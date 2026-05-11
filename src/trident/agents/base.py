"""Base agent protocol for later TRIDENT phases."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    task_id: str
    disease_id: str | None = None
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BaseAgent(Protocol):
    name: str

    def run(self, context: AgentContext) -> AgentResult: ...
