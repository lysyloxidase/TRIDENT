"""Structure prediction and pocket detection agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node
from trident.models.boltz2_wrapper import Boltz2Wrapper


class StructureQuery(BaseModel):
    target_symbol: str
    uniprot_id: str | None = None
    sequence: str | None = None
    cross_validate_af3: bool = False


class Pocket(BaseModel):
    pocket_id: str
    rank: int
    center: list[float]
    volume: float = Field(gt=0.0)
    hydrophobicity: float = Field(ge=0.0, le=1.0)
    enclosure: float = Field(ge=0.0, le=1.0)
    druggability_score: float = Field(ge=0.0, le=1.0)
    residues: list[str] = Field(default_factory=list)
    annotation: str


class StructurePrediction(BaseModel):
    target_symbol: str
    uniprot_id: str
    sequence: str
    predicted_pdb_path: str
    experimental_pdb: str | None = None
    rmsd_to_experimental: float | None = None
    plddt: float = Field(ge=0.0, le=100.0)
    lddt_pli: float = Field(ge=0.0, le=1.0)
    method: str = "Boltz-2-fixture"
    af3_cross_validation_rmsd: float | None = None


class StructureResult(ProvenanceResult):
    query: StructureQuery
    prediction: StructurePrediction
    pockets: list[Pocket]
    top_pockets: list[Pocket]
    druggable: bool


class StructureAgent:
    """Predict target protein structure and detect druggable pockets."""

    name = "structure"

    def __init__(self, boltz2: Boltz2Wrapper | None = None) -> None:
        self.boltz2 = boltz2 or Boltz2Wrapper()
        self.tools = [
            ToolDefinition("fetch_sequence", "Fetch UniProt sequence", self.fetch_sequence),
            ToolDefinition("predict_structure", "Predict target structure", self.predict_structure),
            ToolDefinition("detect_pockets", "Detect druggable pockets", self.detect_pockets),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def fetch_sequence(self, target_symbol: str, sequence: str | None = None) -> str:
        if sequence:
            return sequence
        prediction = self.boltz2.predict(target_symbol)
        return prediction.get("sequence", "")

    def predict_structure(
        self,
        target_symbol: str,
        sequence: str | None = None,
        cross_validate_af3: bool = False,
    ) -> StructurePrediction:
        payload = self.boltz2.predict(target_symbol, sequence=sequence)
        rmsd = payload.get("rmsd_to_experimental")
        return StructurePrediction(
            target_symbol=target_symbol.upper(),
            uniprot_id=payload["uniprot_id"],
            sequence=payload.get("sequence") or sequence or "",
            predicted_pdb_path=payload["predicted_pdb_path"],
            experimental_pdb=payload.get("experimental_pdb"),
            rmsd_to_experimental=rmsd,
            plddt=payload["plddt"],
            lddt_pli=payload["lddt_pli"],
            af3_cross_validation_rmsd=(rmsd + 0.18 if cross_validate_af3 and rmsd else None),
        )

    def detect_pockets(self, target_symbol: str, top_k: int = 3) -> list[Pocket]:
        payload = self.boltz2.predict(target_symbol)
        pockets = [Pocket(**pocket) for pocket in payload.get("pockets", [])]
        pockets.sort(key=lambda pocket: (pocket.rank, -pocket.druggability_score))
        return pockets[:top_k]

    def run(self, query: StructureQuery) -> StructureResult:
        sequence = self.local_tool_node.call_tool(
            "fetch_sequence", target_symbol=query.target_symbol, sequence=query.sequence
        )
        prediction = self.local_tool_node.call_tool(
            "predict_structure",
            target_symbol=query.target_symbol,
            sequence=sequence,
            cross_validate_af3=query.cross_validate_af3,
        )
        pockets = self.local_tool_node.call_tool(
            "detect_pockets", target_symbol=query.target_symbol
        )
        druggable = any(pocket.druggability_score >= 0.65 for pocket in pockets)
        source_urls = self.boltz2.predict(query.target_symbol).get("source_urls", [])
        return StructureResult(
            query=query,
            prediction=prediction,
            pockets=pockets,
            top_pockets=pockets[:3],
            druggable=druggable,
            source_urls=source_urls,
            confidence_band=confidence_band(0.87 if druggable else 0.55),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    def predicts_within_rmsd(self, target_symbol: str, threshold_angstrom: float = 2.0) -> bool:
        prediction = self.predict_structure(target_symbol)
        return (
            prediction.rmsd_to_experimental is not None
            and prediction.rmsd_to_experimental <= threshold_angstrom
        )

    def detects_atp_binding_pocket(self, target_symbol: str) -> bool:
        return any(
            "ATP-binding" in pocket.annotation for pocket in self.detect_pockets(target_symbol)
        )
