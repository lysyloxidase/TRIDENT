"""Molecule generation agent combining SynFlowNet and REINVENT outputs."""

from __future__ import annotations

import re
from collections import OrderedDict

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.structure_agent import Pocket
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node
from trident.models.reinvent_wrapper import REINVENTWrapper
from trident.models.synflownet_wrapper import SynFlowNetWrapper


class GenerationQuery(BaseModel):
    target_symbol: str
    pocket: Pocket
    n_molecules: int = Field(default=200, ge=10, le=500)
    mode: str = "de_novo"


class MoleculeCandidate(BaseModel):
    smiles: str
    source: str
    pocket_id: str
    qed: float = Field(ge=0.0, le=1.0)
    synthetic_accessibility: float = Field(ge=0.0, le=1.0)
    boltz2_affinity_kcal_mol: float
    valid_smiles: bool
    rank: int | None = None


class GenerationResult(ProvenanceResult):
    target_symbol: str
    pocket_id: str
    molecules: list[MoleculeCandidate]
    unique_count: int
    qed_above_05_fraction: float


class GeneratorAgent:
    """Generate candidate molecules for validated pockets."""

    name = "generator"

    def __init__(
        self,
        synflownet: SynFlowNetWrapper | None = None,
        reinvent: REINVENTWrapper | None = None,
    ) -> None:
        self.synflownet = synflownet or SynFlowNetWrapper()
        self.reinvent = reinvent or REINVENTWrapper()
        self.tools = [
            ToolDefinition(
                "synflownet_generate", "Generate with SynFlowNet", self.synflownet.generate
            ),
            ToolDefinition("reinvent_generate", "Generate with REINVENT 4", self.reinvent.generate),
            ToolDefinition("merge_rank", "Merge, validate, and rank molecules", self.merge_rank),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def merge_rank(
        self, molecules: list[dict], pocket_id: str, limit: int = 200
    ) -> list[MoleculeCandidate]:
        deduped: OrderedDict[str, dict] = OrderedDict()
        for molecule in molecules:
            smiles = molecule["smiles"]
            if smiles not in deduped:
                deduped[smiles] = molecule

        candidates = []
        for smiles, molecule in deduped.items():
            valid = self.is_valid_smiles(smiles)
            qed = self.estimate_qed(smiles)
            affinity = self.estimate_boltz2_affinity(smiles)
            candidates.append(
                MoleculeCandidate(
                    smiles=smiles,
                    source=molecule["source"],
                    pocket_id=pocket_id,
                    qed=qed,
                    synthetic_accessibility=max(
                        0.0, min(1.0, molecule.get("synthetic_accessibility", 0.65))
                    ),
                    boltz2_affinity_kcal_mol=affinity,
                    valid_smiles=valid,
                )
            )
        candidates = [candidate for candidate in candidates if candidate.valid_smiles]
        candidates.sort(
            key=lambda candidate: (
                candidate.boltz2_affinity_kcal_mol,
                -candidate.qed,
                -candidate.synthetic_accessibility,
            )
        )
        for rank, candidate in enumerate(candidates[:limit], start=1):
            candidate.rank = rank
        return candidates[:limit]

    def run(self, query: GenerationQuery) -> GenerationResult:
        half = max(1, query.n_molecules // 2)
        syn = self.local_tool_node.call_tool(
            "synflownet_generate",
            n_molecules=half + 20,
            pocket_id=query.pocket.pocket_id,
        )
        rein = self.local_tool_node.call_tool(
            "reinvent_generate",
            n_molecules=query.n_molecules - half + 40,
            mode=query.mode,
            pocket_id=query.pocket.pocket_id,
        )
        molecules = self.local_tool_node.call_tool(
            "merge_rank",
            molecules=syn + rein,
            pocket_id=query.pocket.pocket_id,
            limit=query.n_molecules,
        )
        qed_fraction = (
            sum(1 for molecule in molecules if molecule.qed > 0.5) / len(molecules)
            if molecules
            else 0.0
        )
        return GenerationResult(
            target_symbol=query.target_symbol,
            pocket_id=query.pocket.pocket_id,
            molecules=molecules,
            unique_count=len({molecule.smiles for molecule in molecules}),
            qed_above_05_fraction=qed_fraction,
            source_urls=[
                "https://github.com/recursionpharma/boltz",
                "https://github.com/MolecularAI/REINVENT4",
            ],
            confidence_band=confidence_band(0.79 if len(molecules) >= 100 else 0.55),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    @staticmethod
    def is_valid_smiles(smiles: str) -> bool:
        if not smiles or len(smiles) > 180:
            return False
        if not re.fullmatch(r"[A-Za-z0-9@+\-\[\]\(\)=#\\/%.]+", smiles):
            return False
        if smiles.count("(") != smiles.count(")"):
            return False
        ring_digits = [char for char in smiles if char.isdigit()]
        return all(ring_digits.count(digit) % 2 == 0 for digit in set(ring_digits))

    @staticmethod
    def estimate_qed(smiles: str) -> float:
        heavy = sum(1 for char in smiles if char.isalpha() and char.isupper())
        hetero = smiles.count("N") + smiles.count("O") + smiles.count("S")
        aromatic = smiles.count("c")
        raw = 0.42 + min(0.20, hetero * 0.035) + min(0.18, aromatic * 0.018)
        raw += 0.08 if 18 <= heavy + aromatic <= 58 else -0.08
        raw -= 0.10 if smiles.count("Cl") > 2 else 0.0
        return round(max(0.05, min(0.93, raw)), 3)

    @staticmethod
    def estimate_boltz2_affinity(smiles: str) -> float:
        heavy = sum(1 for char in smiles if char in {"C", "N", "O", "S", "F"})
        hetero = smiles.count("N") + smiles.count("O")
        aromatic = 1 if "c1" in smiles or "c2" in smiles else 0
        return round(-5.8 - min(2.6, heavy / 25) - 0.18 * hetero - 0.55 * aromatic, 3)
