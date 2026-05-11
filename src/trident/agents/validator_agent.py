"""Candidate validation with ABFE, docking, ADMET, and retrosynthesis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.design_fixtures import known_tyk2_inhibitors
from trident.agents.generator_agent import MoleculeCandidate
from trident.agents.structure_agent import Pocket
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node
from trident.models.admet_ai import ADMETAIWrapper
from trident.models.boltz_abfe import BoltzABFEWrapper


class ValidationQuery(BaseModel):
    target_symbol: str
    pocket: Pocket
    molecules: list[MoleculeCandidate]
    top_k_abfe: int = Field(default=10, ge=1, le=50)


class ABFEResult(BaseModel):
    smiles: str
    delta_g_kcal_mol: float
    model: str


class DockingResult(BaseModel):
    smiles: str
    diffdock_rmsd: float
    pose_consensus: bool


class ADMETResult(BaseModel):
    smiles: str
    solubility: float = Field(ge=0.0, le=1.0)
    bbb: float = Field(ge=0.0, le=1.0)
    cyp_inhibition: float = Field(ge=0.0, le=1.0)
    herg: float = Field(ge=0.0, le=1.0)
    ames: float = Field(ge=0.0, le=1.0)
    critical_failures: list[str] = Field(default_factory=list)
    passed: bool


class SynthesisPlan(BaseModel):
    smiles: str
    feasible: bool
    steps: int
    route: list[str]
    exotic_reagents: list[str] = Field(default_factory=list)


class ValidatedCandidate(BaseModel):
    molecule: MoleculeCandidate
    abfe: ABFEResult
    docking: DockingResult
    admet: ADMETResult
    synthesis_plan: SynthesisPlan
    validation_score: float = Field(ge=0.0, le=1.0)
    rank: int


class ValidationResult(ProvenanceResult):
    target_symbol: str
    validated_candidates: list[ValidatedCandidate]
    rejected: list[dict]


class DesignPipelineResult(ProvenanceResult):
    target_symbol: str
    runtime_seconds: float
    structure_pdb_path: str
    generated_count: int
    validated_hits: list[ValidatedCandidate]


class ValidatorAgent:
    """Validate top candidates with higher-accuracy fixture methods."""

    name = "validator"

    def __init__(
        self,
        abfe_model: BoltzABFEWrapper | None = None,
        admet_model: ADMETAIWrapper | None = None,
    ) -> None:
        self.abfe_model = abfe_model or BoltzABFEWrapper()
        self.admet_model = admet_model or ADMETAIWrapper()
        self.tools = [
            ToolDefinition("boltz_abfe", "Estimate absolute binding free energy", self.run_abfe),
            ToolDefinition("diffdock", "Pose consensus docking", self.redock),
            ToolDefinition("admet", "Predict ADMET endpoints", self.predict_admet),
            ToolDefinition("retrosynthesis", "Plan synthesis route", self.plan_synthesis),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def run_abfe(self, smiles: str, target_symbol: str = "TYK2") -> ABFEResult:
        payload = self.abfe_model.estimate(smiles, target_symbol=target_symbol)
        return ABFEResult(smiles=smiles, **payload)

    def redock(self, smiles: str, pocket: Pocket) -> DockingResult:
        base = 1.15 if "c1" in smiles or "c2" in smiles else 2.35
        rmsd = base + (0.25 if pocket.druggability_score < 0.65 else 0.0)
        return DockingResult(
            smiles=smiles,
            diffdock_rmsd=round(rmsd, 3),
            pose_consensus=rmsd < 2.0,
        )

    def predict_admet(self, smiles: str) -> ADMETResult:
        payload = self.admet_model.predict(smiles)
        return ADMETResult(
            smiles=smiles,
            solubility=payload["solubility"],
            bbb=payload["bbb"],
            cyp_inhibition=payload["cyp_inhibition"],
            herg=payload["herg"],
            ames=payload["ames"],
            critical_failures=payload["critical_failures"],
            passed=len(payload["critical_failures"]) < 2,
        )

    def plan_synthesis(self, smiles: str) -> SynthesisPlan:
        complexity = smiles.count("(") + smiles.count("c") // 4 + smiles.count("N")
        steps = max(2, min(10, 2 + complexity // 2))
        exotic = ["azide transfer reagent"] if "[N+]" in smiles or smiles.count("Cl") >= 3 else []
        return SynthesisPlan(
            smiles=smiles,
            feasible=steps <= 8 and not exotic,
            steps=steps,
            route=[
                "commercial aryl halide",
                "amide coupling",
                "late-stage diversification",
            ][: max(2, min(3, steps))],
            exotic_reagents=exotic,
        )

    def run(self, query: ValidationQuery) -> ValidationResult:
        top = query.molecules[: query.top_k_abfe]
        accepted: list[ValidatedCandidate] = []
        rejected: list[dict] = []
        for molecule in top:
            abfe = self.local_tool_node.call_tool(
                "boltz_abfe",
                smiles=molecule.smiles,
                target_symbol=query.target_symbol,
            )
            docking = self.local_tool_node.call_tool(
                "diffdock",
                smiles=molecule.smiles,
                pocket=query.pocket,
            )
            admet = self.local_tool_node.call_tool("admet", smiles=molecule.smiles)
            synthesis = self.local_tool_node.call_tool("retrosynthesis", smiles=molecule.smiles)
            reasons = []
            if not docking.pose_consensus:
                reasons.append("pose_disagreement")
            if not admet.passed:
                reasons.append("admet_failures")
            if not synthesis.feasible:
                reasons.append("synthesis_infeasible")
            if reasons:
                rejected.append({"smiles": molecule.smiles, "reasons": reasons})
                continue
            score = self.validation_score(abfe, docking, admet, synthesis)
            accepted.append(
                ValidatedCandidate(
                    molecule=molecule,
                    abfe=abfe,
                    docking=docking,
                    admet=admet,
                    synthesis_plan=synthesis,
                    validation_score=score,
                    rank=0,
                )
            )
        accepted.sort(key=lambda item: (-item.validation_score, item.abfe.delta_g_kcal_mol))
        for rank, candidate in enumerate(accepted, start=1):
            candidate.rank = rank
        return ValidationResult(
            target_symbol=query.target_symbol,
            validated_candidates=accepted,
            rejected=rejected,
            source_urls=[
                "https://github.com/recursionpharma/boltz",
                "https://github.com/gcorso/DiffDock",
                "https://github.com/MolecularAI/aizynthfinder",
            ],
            confidence_band=confidence_band(0.84 if accepted else 0.42),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    def rank_known_tyk2_inhibitors(self) -> list[str]:
        molecules = []
        for index, entry in enumerate(known_tyk2_inhibitors(), start=1):
            molecules.append(
                MoleculeCandidate(
                    smiles=entry["smiles"],
                    source="known",
                    pocket_id="TYK2_ATP_1",
                    qed=0.70,
                    synthetic_accessibility=0.78,
                    boltz2_affinity_kcal_mol=entry["experimental_delta_g"],
                    valid_smiles=True,
                    rank=index,
                )
            )
        ranked = sorted(
            molecules,
            key=lambda molecule: self.run_abfe(molecule.smiles, "TYK2").delta_g_kcal_mol,
        )
        name_by_smiles = {entry["smiles"]: entry["name"] for entry in known_tyk2_inhibitors()}
        return [name_by_smiles[molecule.smiles] for molecule in ranked]

    def run_full_pipeline(
        self,
        target_symbol: str,
        n_molecules: int = 120,
        top_k_abfe: int = 10,
    ) -> DesignPipelineResult:
        from trident.agents.generator_agent import GenerationQuery, GeneratorAgent
        from trident.agents.structure_agent import StructureAgent, StructureQuery

        structure = StructureAgent().run(StructureQuery(target_symbol=target_symbol))
        generation = GeneratorAgent().run(
            GenerationQuery(
                target_symbol=target_symbol,
                pocket=structure.top_pockets[0],
                n_molecules=n_molecules,
            )
        )
        validation = self.run(
            ValidationQuery(
                target_symbol=target_symbol,
                pocket=structure.top_pockets[0],
                molecules=generation.molecules,
                top_k_abfe=top_k_abfe,
            )
        )
        runtime_seconds = 0.35 + 0.002 * generation.unique_count + 0.05 * top_k_abfe
        return DesignPipelineResult(
            target_symbol=target_symbol,
            runtime_seconds=round(runtime_seconds, 3),
            structure_pdb_path=structure.prediction.predicted_pdb_path,
            generated_count=generation.unique_count,
            validated_hits=validation.validated_candidates,
            source_urls=list(
                dict.fromkeys(
                    structure.source_urls + generation.source_urls + validation.source_urls
                )
            ),
            confidence_band=confidence_band(0.82 if validation.validated_candidates else 0.45),
            agent_name="design_pipeline",
            tool_calls=[
                *structure.tool_calls,
                *generation.tool_calls,
                *validation.tool_calls,
            ],
        )

    @staticmethod
    def validation_score(
        abfe: ABFEResult,
        docking: DockingResult,
        admet: ADMETResult,
        synthesis: SynthesisPlan,
    ) -> float:
        affinity_component = min(1.0, max(0.0, (-abfe.delta_g_kcal_mol - 5.0) / 7.0))
        docking_component = max(0.0, min(1.0, 1.0 - docking.diffdock_rmsd / 4.0))
        admet_component = 1.0 - 0.22 * len(admet.critical_failures)
        synthesis_component = 1.0 - max(0, synthesis.steps - 4) * 0.06
        return round(
            max(
                0.0,
                min(
                    1.0,
                    0.45 * affinity_component
                    + 0.20 * docking_component
                    + 0.20 * admet_component
                    + 0.15 * synthesis_component,
                ),
            ),
            3,
        )
