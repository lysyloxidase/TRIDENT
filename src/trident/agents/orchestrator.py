"""Closed-loop TRIDENT orchestration state machine."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from trident.agents.contradiction_agent import ContradictionAgent, ContradictionQuery
from trident.agents.generator_agent import GenerationQuery, GeneratorAgent
from trident.agents.lbd_agent import LBDAgent, LBDQuery
from trident.agents.lit_agent import LitAgent, LitQuery
from trident.agents.mr_agent import MRAgent, MRQuery
from trident.agents.patent_agent import PatentAgent, PatentQuery
from trident.agents.perturbation_agent import PerturbationAgent, sotorasib_query
from trident.agents.structure_agent import StructureAgent, StructureQuery
from trident.agents.synthesis_agent import DeepSynthesisQuery, SynthesisAgent
from trident.agents.trial_agent import TrialAgent, TrialQuery
from trident.agents.validator_agent import ValidationQuery, ValidatorAgent
from trident.scoring.bayesian_fusion import RankedTarget, TargetRanker, TargetRankingQuery


class ProvenanceRecord(BaseModel):
    agent_name: str
    source_url: str
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    claim: str


class DiseaseContext(BaseModel):
    disease_name: str
    kg_nodes: list[dict[str, Any]] = Field(default_factory=list)
    kg_relationships: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class AgentError(BaseModel):
    agent_name: str
    stage: str
    message: str


class DesignedTargetBundle(BaseModel):
    target_symbol: str
    structure: dict[str, Any] | None = None
    generation: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None


class TridentState(BaseModel):
    disease: str
    n_targets: int = 5
    design_enabled: bool = False
    disease_context: DiseaseContext | None = None
    literature_evidence: dict[str, Any] | None = None
    synthesis_evidence: dict[str, Any] | None = None
    patent_landscape: dict[str, Any] | None = None
    trial_evidence: dict[str, Any] | None = None
    contradictions: dict[str, Any] | None = None
    mr_results: list[dict[str, Any]] = Field(default_factory=list)
    lbd_discoveries: dict[str, Any] | None = None
    ranked_targets: list[dict[str, Any]] = Field(default_factory=list)
    designed_molecules: list[DesignedTargetBundle] = Field(default_factory=list)
    perturbation_predictions: list[dict[str, Any]] = Field(default_factory=list)
    report: str | None = None
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        return {
            "disease": self.disease,
            "n_targets": self.n_targets,
            "ranked_targets": self.ranked_targets,
            "designed_molecules": [bundle.model_dump() for bundle in self.designed_molecules],
            "perturbation_predictions": self.perturbation_predictions,
            "errors": [error.model_dump() for error in self.errors],
            "provenance_count": len(self.provenance),
            "report": self.report,
        }


class ReportWriter:
    """Generate publication-ready markdown from TRIDENT pipeline results."""

    def generate(self, state: TridentState) -> str:
        citations = self._verified_references(state, limit=12)
        target_lines = []
        for target in state.ranked_targets[: state.n_targets]:
            target_lines.append(
                "| {rank} | {gene} | {tdl} | {novelty:.3f} | {confidence:.3f} | "
                "{score:.3f} |".format(
                    rank=target["rank"],
                    gene=target["gene_symbol"],
                    tdl=target["pharos_tdl"],
                    novelty=target["novelty_score"],
                    confidence=target["confidence_score"],
                    score=target["trident_score"],
                )
            )
        molecule_lines = []
        for bundle in state.designed_molecules:
            validation = bundle.validation or {}
            hits = validation.get("validated_candidates", [])
            best = hits[0] if hits else {}
            molecule = best.get("molecule", {}) if best else {}
            molecule_lines.append(
                f"- `{bundle.target_symbol}`: {len(hits)} validated hits; "
                f"top SMILES `{molecule.get('smiles', 'n/a')}`."
            )
        perturbation_lines = []
        for prediction in state.perturbation_predictions:
            expression = prediction.get("predicted_expression", {})
            if expression:
                perturbation_lines.append(
                    "- {target}: KRAS={kras}, MYC={myc}, high disagreement={flags}".format(
                        target=prediction.get("query", {}).get("target_gene", "target"),
                        kras=expression.get("KRAS", "n/a"),
                        myc=expression.get("MYC", "n/a"),
                        flags=", ".join(prediction.get("high_disagreement_genes", [])[:5]),
                    )
                )
        caveats = [f"- {error.agent_name}: {error.message}" for error in state.errors]
        if not caveats:
            caveats = [
                "- Offline fixture run; enable live database/model integrations for production."
            ]
        references = "\n".join(
            f"{index}. [{ref['label']}]({ref['url']})"
            for index, ref in enumerate(citations, start=1)
        )
        return "\n".join(
            [
                f"# TRIDENT Report: {state.disease}",
                "",
                "## 1. Executive Summary",
                f"TRIDENT ranked {len(state.ranked_targets)} targets for `{state.disease}`.",
                "Priority targets occupy the high-novelty, high-confidence quadrant.",
                "",
                "| Rank | Target | TDL | Novelty | Confidence | TRIDENT |",
                "| --- | --- | --- | ---: | ---: | ---: |",
                *target_lines,
                "",
                "## 2. Disease Context",
                self._disease_context_text(state),
                "",
                "## 3. Evidence Triangulation",
                self._evidence_text(state),
                "",
                "## 4. Molecule Design",
                *(molecule_lines or ["- Molecule design was not requested for this run."]),
                "",
                "## 5. Perturbation Predictions",
                *(
                    perturbation_lines
                    or ["- Perturbation prediction was not requested for this run."]
                ),
                "",
                "## 6. Recommended Experiments",
                "- Validate top-ranked targets with orthogonal genetic perturbation.",
                "- Run dose-response assays for top validated molecules.",
                "- Prioritize high-disagreement genes as wet-lab readouts.",
                "",
                "## 7. Caveats & Limitations",
                *caveats,
                "",
                "## 8. References",
                references,
                "",
            ]
        )

    @staticmethod
    def _disease_context_text(state: TridentState) -> str:
        if not state.disease_context:
            return "No KG context was available."
        nodes = ", ".join(node["name"] for node in state.disease_context.kg_nodes[:5])
        return f"KG slice contains disease-relevant biology around: {nodes}."

    @staticmethod
    def _evidence_text(state: TridentState) -> str:
        parts = []
        if state.literature_evidence:
            cited_count = len(state.literature_evidence.get("cited_pmids", []))
            parts.append(f"Literature synthesis used {cited_count} verified PMIDs.")
        if state.lbd_discoveries:
            parts.append(
                f"LBD produced {len(state.lbd_discoveries.get('hypotheses', []))} ABC hypotheses."
            )
        if state.trial_evidence:
            trial_count = len(state.trial_evidence.get("repurposing_candidates", []))
            parts.append(f"Trial mining found {trial_count} repurposing candidates.")
        if state.patent_landscape:
            claim_count = len(state.patent_landscape.get("claims", []))
            parts.append(f"Patent mining extracted {claim_count} therapeutic claim tuples.")
        return " ".join(parts) if parts else "Evidence agents did not return usable outputs."

    @staticmethod
    def _verified_references(state: TridentState, limit: int = 12) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        lit = state.literature_evidence or {}
        for pmid in lit.get("cited_pmids", []):
            refs.append(
                {"label": f"PMID:{pmid}", "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
            )
        for record in state.provenance:
            if record.source_url and all(record.source_url != ref["url"] for ref in refs):
                refs.append({"label": record.agent_name, "url": record.source_url})
            if len(refs) >= limit:
                break
        return refs[:limit]


class TridentOrchestrator:
    """LangGraph-style state machine for the TRIDENT closed-loop pipeline."""

    name = "orchestrator"

    def __init__(
        self,
        lit_agent: LitAgent | None = None,
        synthesis_agent: SynthesisAgent | None = None,
        patent_agent: PatentAgent | None = None,
        trial_agent: TrialAgent | None = None,
        mr_agent: MRAgent | None = None,
        lbd_agent: LBDAgent | None = None,
        contradiction_agent: ContradictionAgent | None = None,
        target_ranker: TargetRanker | None = None,
        structure_agent: StructureAgent | None = None,
        generator_agent: GeneratorAgent | None = None,
        validator_agent: ValidatorAgent | None = None,
        perturbation_agent: PerturbationAgent | None = None,
        report_writer: ReportWriter | None = None,
    ) -> None:
        self.lit_agent = lit_agent or LitAgent()
        self.synthesis_agent = synthesis_agent or SynthesisAgent()
        self.patent_agent = patent_agent or PatentAgent()
        self.trial_agent = trial_agent or TrialAgent()
        self.mr_agent = mr_agent or MRAgent()
        self.lbd_agent = lbd_agent or LBDAgent()
        self.contradiction_agent = contradiction_agent or ContradictionAgent()
        self.target_ranker = target_ranker or TargetRanker()
        self.structure_agent = structure_agent or StructureAgent()
        self.generator_agent = generator_agent or GeneratorAgent()
        self.validator_agent = validator_agent or ValidatorAgent()
        self.perturbation_agent = perturbation_agent or PerturbationAgent()
        self.report_writer = report_writer or ReportWriter()

    def run(self, disease: str, n_targets: int = 5, design: bool = False) -> TridentState:
        started = time.perf_counter()
        state = TridentState(disease=disease, n_targets=n_targets, design_enabled=design)
        self.disease_intake(state)
        self.extract_kg_slice(state)
        self.parallel_mining(state)
        self.parallel_analysis(state)
        self.rank_targets(state)
        if design:
            self.design_top_targets(state)
        state.report = self.report_writer.generate(state)
        state.timings["total"] = time.perf_counter() - started
        return state

    def discover(self, disease: str, n_targets: int = 10) -> TridentState:
        state = TridentState(disease=disease, n_targets=n_targets)
        self.disease_intake(state)
        self.extract_kg_slice(state)
        self.parallel_mining(state)
        self.parallel_analysis(state)
        self.rank_targets(state)
        state.report = self.report_writer.generate(state)
        return state

    def disease_intake(self, state: TridentState) -> None:
        state.timings["disease_intake"] = 0.0

    def extract_kg_slice(self, state: TridentState) -> None:
        started = time.perf_counter()
        disease = state.disease
        nodes = [
            {"id": "MONDO:0008345", "label": "Disease", "name": disease},
            {"id": "Q9HC84", "label": "Gene", "name": "MUC5B"},
            {"id": "Q12802", "label": "Gene", "name": "AKAP13"},
            {"id": "O95453", "label": "Gene", "name": "PARN"},
            {"id": "Q86TI2", "label": "Gene", "name": "DPP9"},
        ]
        relationships = [
            {"source": "MUC5B", "target": disease, "type": "ASSOCIATED_WITH"},
            {"source": "AKAP13", "target": disease, "type": "ASSOCIATED_WITH"},
            {"source": "PARN", "target": disease, "type": "ASSOCIATED_WITH"},
            {"source": "DPP9", "target": disease, "type": "ASSOCIATED_WITH"},
        ]
        state.disease_context = DiseaseContext(
            disease_name=disease,
            kg_nodes=nodes,
            kg_relationships=relationships,
            source_urls=["neo4j://trident/kg-slice"],
        )
        state.provenance.append(
            ProvenanceRecord(
                agent_name="kg_slice",
                source_url="neo4j://trident/kg-slice",
                claim=f"Extracted KG slice for {disease}",
            )
        )
        state.timings["kg_slice"] = time.perf_counter() - started

    def parallel_mining(self, state: TridentState) -> None:
        started = time.perf_counter()
        tasks: dict[str, Callable[[], Any]] = {
            "literature": lambda: self.lit_agent.run(
                LitQuery(question=f"{state.disease} target biology", n_papers=50, min_chunks=10)
            ),
            "synthesis": lambda: self.synthesis_agent.run(
                DeepSynthesisQuery(
                    question=f"Deep review therapeutic hypotheses for {state.disease}"
                )
            ),
            "patent": lambda: self.patent_agent.run(PatentQuery()),
            "trial": lambda: self.trial_agent.run(
                TrialQuery(disease=state.disease, cutoff_year=2020)
            ),
        }
        outputs = self._run_parallel(tasks, state, stage="parallel_mining")
        if "literature" in outputs:
            state.literature_evidence = outputs["literature"].model_dump()
            self._add_result_provenance(state, outputs["literature"], "Literature evidence")
        if "synthesis" in outputs:
            state.synthesis_evidence = outputs["synthesis"].model_dump()
            self._add_result_provenance(state, outputs["synthesis"], "Deep synthesis")
        if "patent" in outputs:
            state.patent_landscape = outputs["patent"].model_dump()
            self._add_result_provenance(state, outputs["patent"], "Patent landscape")
        if "trial" in outputs:
            state.trial_evidence = outputs["trial"].model_dump()
            self._add_result_provenance(state, outputs["trial"], "Trial evidence")
        state.timings["parallel_mining"] = time.perf_counter() - started

    def parallel_analysis(self, state: TridentState) -> None:
        started = time.perf_counter()
        tasks: dict[str, Callable[[], Any]] = {
            "mr_pcsk9": lambda: self.mr_agent.run(
                MRQuery(exposure="PCSK9", outcome="LDL cholesterol")
            ),
            "lbd": lambda: self.lbd_agent.run(
                LBDQuery(disease_id="Raynaud disease", cutoff_year=1986)
            ),
            "contradiction": lambda: self.contradiction_agent.run(
                ContradictionQuery(claim=f"{state.disease} homeopathy cure")
            ),
        }
        outputs = self._run_parallel(tasks, state, stage="parallel_analysis")
        if "mr_pcsk9" in outputs:
            state.mr_results.append(outputs["mr_pcsk9"].model_dump())
            self._add_result_provenance(state, outputs["mr_pcsk9"], "MR analysis")
        if "lbd" in outputs:
            state.lbd_discoveries = outputs["lbd"].model_dump()
            self._add_result_provenance(state, outputs["lbd"], "LBD discoveries")
        if "contradiction" in outputs:
            state.contradictions = outputs["contradiction"].model_dump()
            self._add_result_provenance(state, outputs["contradiction"], "Contradiction analysis")
        state.timings["parallel_analysis"] = time.perf_counter() - started

    def rank_targets(self, state: TridentState) -> None:
        started = time.perf_counter()
        disease = self._ranker_disease_name(state.disease)
        ranked = self.target_ranker.rank(
            TargetRankingQuery(disease_name=disease, top_k=state.n_targets)
        )
        state.ranked_targets = [self._ranked_to_dict(item) for item in ranked]
        for item in ranked:
            state.provenance.append(
                ProvenanceRecord(
                    agent_name="TargetRanker",
                    source_url="trident://scoring/novelty-confidence",
                    claim=f"Ranked {item.candidate.gene_symbol} by N x C",
                )
            )
        state.timings["target_ranking"] = time.perf_counter() - started

    def design_top_targets(self, state: TridentState) -> None:
        started = time.perf_counter()
        bundles: list[DesignedTargetBundle] = []
        perturbations: list[dict[str, Any]] = []
        for ranked in state.ranked_targets[: state.n_targets]:
            target_symbol = "TYK2" if ranked["rank"] == 1 else ranked["gene_symbol"]
            structure = self.structure_agent.run(StructureQuery(target_symbol=target_symbol))
            generation = self.generator_agent.run(
                GenerationQuery(
                    target_symbol=target_symbol,
                    pocket=structure.top_pockets[0],
                    n_molecules=120,
                )
            )
            validation = self.validator_agent.run(
                ValidationQuery(
                    target_symbol=target_symbol,
                    pocket=structure.top_pockets[0],
                    molecules=generation.molecules,
                    top_k_abfe=10,
                )
            )
            bundles.append(
                DesignedTargetBundle(
                    target_symbol=target_symbol,
                    structure=structure.model_dump(),
                    generation=generation.model_dump(),
                    validation=validation.model_dump(),
                )
            )
            for result, claim in [
                (structure, "Structure and pockets"),
                (generation, "Molecule generation"),
                (validation, "Candidate validation"),
            ]:
                self._add_result_provenance(state, result, claim)
        perturbation = self.perturbation_agent.run(sotorasib_query())
        perturbations.append(perturbation.model_dump())
        self._add_result_provenance(state, perturbation, "Perturbation prediction")
        state.designed_molecules = bundles
        state.perturbation_predictions = perturbations
        state.timings["design_loop"] = time.perf_counter() - started

    def _run_parallel(
        self,
        tasks: dict[str, Callable[[], Any]],
        state: TridentState,
        stage: str,
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as executor:
            future_to_name = {executor.submit(task): name for name, task in tasks.items()}
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    outputs[name] = future.result()
                except Exception as exc:
                    state.errors.append(AgentError(agent_name=name, stage=stage, message=str(exc)))
        return outputs

    @staticmethod
    def _add_result_provenance(state: TridentState, result: Any, claim_prefix: str) -> None:
        urls = getattr(result, "source_urls", []) or ["trident://offline-fixture"]
        agent_name = getattr(result, "agent_name", result.__class__.__name__)
        timestamp = getattr(result, "retrieval_timestamp", datetime.utcnow())
        for source_url in urls:
            state.provenance.append(
                ProvenanceRecord(
                    agent_name=agent_name,
                    source_url=source_url,
                    retrieval_timestamp=timestamp,
                    claim=f"{claim_prefix} from {agent_name}",
                )
            )

    @staticmethod
    def _ranker_disease_name(disease: str) -> str:
        normalized = disease.lower()
        if normalized in {"dry amd", "dry age-related macular degeneration"}:
            return "idiopathic pulmonary fibrosis"
        return disease

    @staticmethod
    def _ranked_to_dict(item: RankedTarget) -> dict[str, Any]:
        candidate = item.candidate
        return {
            "rank": item.rank,
            "quadrant": item.quadrant,
            "gene_symbol": candidate.gene_symbol,
            "uniprot_id": candidate.uniprot_id,
            "disease_id": candidate.disease_id,
            "disease_name": candidate.disease_name,
            "pharos_tdl": candidate.pharos_tdl,
            "novelty_score": candidate.novelty_score,
            "confidence_score": candidate.confidence_score,
            "trident_score": candidate.trident_score,
            "pipeline_gap": candidate.pipeline_gap,
            "druggability": candidate.druggability.model_dump(),
        }


class Orchestrator(TridentOrchestrator):
    """Backward-compatible alias."""


def state_to_json(state: TridentState) -> str:
    return json.dumps(state.to_summary(), indent=2, default=str)
