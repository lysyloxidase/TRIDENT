"""Shared agent protocol and provenance models."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, Field

QueryT = TypeVar("QueryT", bound=BaseModel)
ResultT = TypeVar("ResultT", bound="ProvenanceResult")


PRIMARY_LLM_MODEL = os.getenv("TRIDENT_LLM_PRIMARY", "anthropic/claude-sonnet-4-5")
FALLBACK_LLM_MODEL = os.getenv("TRIDENT_LLM_FALLBACK", "meta-llama/Llama-3.3-70B-Instruct")


class ConfidenceBand(BaseModel):
    """Low/mid/high confidence estimate required on every agent output."""

    low: float = Field(ge=0.0, le=1.0)
    mid: float = Field(ge=0.0, le=1.0)
    high: float = Field(ge=0.0, le=1.0)


class ProvenanceResult(BaseModel):
    """Base result for all TRIDENT agents."""

    source_urls: list[str] = Field(default_factory=list)
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence_band: ConfidenceBand = Field(
        default_factory=lambda: ConfidenceBand(low=0.35, mid=0.5, high=0.65)
    )
    agent_name: str = "unknown"
    model_name: str = PRIMARY_LLM_MODEL
    fallback_model_name: str = FALLBACK_LLM_MODEL
    tool_calls: list[str] = Field(default_factory=list)


class AgentContext(BaseModel):
    """Legacy context retained for Phase 1 placeholder compatibility."""

    task_id: str
    disease_id: str | None = None
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(ProvenanceResult):
    """Generic result shape for lightweight utility agents."""

    agent: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BaseAgent(Protocol, Generic[QueryT, ResultT]):
    """Protocol for all TRIDENT agents.

    Every result MUST include:
    - source_urls: list of URLs consulted
    - retrieval_timestamp: when data was fetched
    - confidence_band: low/mid/high estimate
    - agent_name: which agent produced this
    """

    name: str

    def run(self, query: QueryT) -> ResultT: ...


def confidence_band(mid: float, spread: float = 0.12) -> ConfidenceBand:
    """Build a clipped low/mid/high confidence band."""

    mid = max(0.0, min(1.0, mid))
    return ConfidenceBand(
        low=max(0.0, mid - spread),
        mid=mid,
        high=min(1.0, mid + spread),
    )
