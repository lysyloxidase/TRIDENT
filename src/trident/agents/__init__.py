"""TRIDENT agent interfaces and Phase 2 implementations."""

from trident.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    ConfidenceBand,
    ProvenanceResult,
)
from trident.agents.contradiction_agent import ContradictionAgent
from trident.agents.generator_agent import GeneratorAgent
from trident.agents.lbd_agent import LBDAgent
from trident.agents.lit_agent import LitAgent
from trident.agents.mr_agent import MRAgent
from trident.agents.patent_agent import PatentAgent
from trident.agents.structure_agent import StructureAgent
from trident.agents.synthesis_agent import SynthesisAgent
from trident.agents.trial_agent import TrialAgent
from trident.agents.validator_agent import ValidatorAgent

__all__ = [
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "ConfidenceBand",
    "ContradictionAgent",
    "LBDAgent",
    "LitAgent",
    "MRAgent",
    "GeneratorAgent",
    "PatentAgent",
    "ProvenanceResult",
    "SynthesisAgent",
    "StructureAgent",
    "TrialAgent",
    "ValidatorAgent",
]
