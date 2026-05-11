"""TRIDENT agent interfaces and Phase 2 implementations."""

from trident.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    ConfidenceBand,
    ProvenanceResult,
)
from trident.agents.contradiction_agent import ContradictionAgent
from trident.agents.lit_agent import LitAgent
from trident.agents.patent_agent import PatentAgent
from trident.agents.synthesis_agent import SynthesisAgent
from trident.agents.trial_agent import TrialAgent

__all__ = [
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "ConfidenceBand",
    "ContradictionAgent",
    "LitAgent",
    "PatentAgent",
    "ProvenanceResult",
    "SynthesisAgent",
    "TrialAgent",
]
