"""Ensemble perturbation prediction agent."""

from __future__ import annotations

import itertools
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node
from trident.models.celloracle_wrapper import CellOracleWrapper
from trident.models.cpa_wrapper import CPAWrapper
from trident.models.gears_wrapper import GEARSWrapper
from trident.models.geneformer_wrapper import GeneformerWrapper
from trident.models.perturbation_fixtures import (
    BIOLOGICALLY_VARIABLE_GENES,
    GENE_PANEL,
    HELDOUT_PERTURBSEQ,
    LINCS_COVERED_PAIRS,
    SOTORASIB_SMILES,
    known_training_compounds,
    patient_fixture,
    pearson,
    profile_from_vector,
    tanimoto_like,
)
from trident.models.scgpt_wrapper import ScGPTWrapper
from trident.types import PerturbationQuery as SharedPerturbationQuery


class PerturbationQuery(SharedPerturbationQuery):
    refusal_similarity_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    min_training_cells: int = Field(default=100, ge=1)


class ModelPrediction(BaseModel):
    model_name: str
    predicted_expression: dict[str, float]
    reliability_weight: float = Field(ge=0.0, le=1.0)
    caveat: str | None = None


class PerturbationEnsembleResult(ProvenanceResult):
    query: PerturbationQuery
    predicted_expression: dict[str, float]
    ensemble_variance: dict[str, float]
    model_predictions: list[ModelPrediction]
    high_disagreement_genes: list[str]
    causal_confidence: Literal["interventional", "observational_only"]
    do_calculus_warning: str | None = None
    model_contributions: dict[str, float]
    scgpt_embedding_summary: dict[str, float | int | str]
    refused: bool = False
    refusal_reasons: list[str] = Field(default_factory=list)


class HeldoutBenchmarkResult(BaseModel):
    ensemble_pearson: float
    training_mean_pearson: float
    improvement: float
    per_case: list[dict[str, float | str]]


class PerturbationAgent:
    """Ensemble perturbation predictor answering the core TRIDENT question."""

    name = "perturbation"
    weights = {
        "CPA": 0.42,
        "GEARS": 0.22,
        "Geneformer": 0.20,
        "CellOracle": 0.16,
    }

    def __init__(
        self,
        cpa: CPAWrapper | None = None,
        scgpt: ScGPTWrapper | None = None,
        geneformer: GeneformerWrapper | None = None,
        gears: GEARSWrapper | None = None,
        celloracle: CellOracleWrapper | None = None,
    ) -> None:
        self.cpa = cpa or CPAWrapper()
        self.scgpt = scgpt or ScGPTWrapper()
        self.geneformer = geneformer or GeneformerWrapper()
        self.gears = gears or GEARSWrapper()
        self.celloracle = celloracle or CellOracleWrapper()
        self.tools = [
            ToolDefinition("scgpt_embed", "Embed patient cells", self.scgpt.embed),
            ToolDefinition("cpa_predict", "CPA drug perturbation", self.cpa.predict),
            ToolDefinition("gears_predict", "GEARS target KO", self.gears.predict_perturbation),
            ToolDefinition(
                "geneformer_predict", "Geneformer in-silico perturbation", self._geneformer_vector
            ),
            ToolDefinition(
                "celloracle_simulate", "CellOracle GRN simulation", self.celloracle.simulate
            ),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def run(self, query: PerturbationQuery) -> PerturbationEnsembleResult:
        patient_cells = patient_fixture(query.patient_h5ad_path, query.target_cell_type)
        refusal_reasons = self.refusal_reasons(query, patient_cells)
        if refusal_reasons:
            return self._refusal_result(query, patient_cells, refusal_reasons)

        embedding = self.local_tool_node.call_tool(
            "scgpt_embed",
            patient_h5ad_path=query.patient_h5ad_path,
            cell_type=query.target_cell_type,
        )
        covariates = {
            "embedding_norm": float(np.linalg.norm(embedding["embedding"])),
            "stress_high": "tumor" in query.target_cell_type.lower(),
        }
        cpa_vec = self.local_tool_node.call_tool(
            "cpa_predict",
            drug_smiles=query.drug_smiles,
            dose_uM=query.dose_uM,
            cell_type=query.target_cell_type,
            covariates=covariates,
        )
        gears_vec = self.local_tool_node.call_tool(
            "gears_predict",
            target_gene=query.target_gene,
            cell_type=query.target_cell_type,
            patient_cells=patient_cells,
        )
        gf_vec = self.local_tool_node.call_tool(
            "geneformer_predict",
            target_gene=query.target_gene,
            patient_cells=patient_cells,
        )
        co_vec = self.local_tool_node.call_tool(
            "celloracle_simulate",
            target_gene=query.target_gene,
            patient_cells=patient_cells,
            n_steps=3,
        )
        raw_predictions = {
            "CPA": cpa_vec,
            "GEARS": gears_vec,
            "Geneformer": gf_vec,
            "CellOracle": co_vec,
        }
        if self.all_models_disagree(raw_predictions):
            return self._refusal_result(
                query, patient_cells, ["all_models_disagree_pairwise_pearson_lt_0.3"]
            )

        expression, variance = self.ensemble(raw_predictions)
        disagreement = self.high_disagreement(variance)
        causal_confidence = (
            "interventional"
            if (query.drug_smiles, query.target_cell_type) in LINCS_COVERED_PAIRS
            else "observational_only"
        )
        warning = None
        if causal_confidence == "observational_only":
            warning = (
                "No interventional data for this drug-cell combination. Predictions are "
                "extrapolation from related compounds/cell types. Recommend wet-lab validation "
                "before clinical interpretation."
            )
        model_predictions = [
            ModelPrediction(
                model_name=name,
                predicted_expression=profile_from_vector(vector.tolist()),
                reliability_weight=self.weights[name],
                caveat=(
                    "CRISPR KO approximates pharmacologic inhibition."
                    if name == "GEARS"
                    else "Co-expression prior, not causal."
                    if name == "Geneformer"
                    else None
                ),
            )
            for name, vector in raw_predictions.items()
        ]
        return PerturbationEnsembleResult(
            query=query,
            predicted_expression=expression,
            ensemble_variance=variance,
            model_predictions=model_predictions,
            high_disagreement_genes=disagreement,
            causal_confidence=causal_confidence,
            do_calculus_warning=warning,
            model_contributions={
                **self.weights,
                "scGPT_embedding": 0.10,
            },
            scgpt_embedding_summary={
                "n_cells": embedding["n_cells"],
                "embedding_norm": round(float(np.linalg.norm(embedding["embedding"])), 4),
                "role": "cell_state_prior_only",
            },
            source_urls=[
                "https://www.nature.com/articles/s41592-024-02201-0",
                "https://www.nature.com/articles/s41587-023-01905-6",
                "https://www.nature.com/articles/s41586-023-06139-9",
            ],
            confidence_band=confidence_band(
                0.82 if causal_confidence == "interventional" else 0.62
            ),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    def refusal_reasons(self, query: PerturbationQuery, patient_cells: dict) -> list[str]:
        reasons = []
        max_similarity = max(
            tanimoto_like(query.drug_smiles, known) for known in known_training_compounds()
        )
        if max_similarity < query.refusal_similarity_threshold:
            reasons.append("drug_structurally_dissimilar_to_training_compounds")
        training_cells = patient_cells["n_cells"]
        if training_cells < query.min_training_cells:
            reasons.append("cell_type_has_fewer_than_100_training_cells")
        return reasons

    def ensemble(
        self, predictions: dict[str, np.ndarray]
    ) -> tuple[dict[str, float], dict[str, float]]:
        total_weight = sum(self.weights.values())
        stacked = np.vstack([predictions[name] for name in self.weights])
        weights = np.array([self.weights[name] / total_weight for name in self.weights])
        mean = np.average(stacked, axis=0, weights=weights)
        variance = np.average((stacked - mean) ** 2, axis=0, weights=weights)
        return profile_from_vector(mean.tolist()), profile_from_vector(variance.tolist())

    @staticmethod
    def high_disagreement(variance: dict[str, float], threshold: float = 0.02) -> list[str]:
        return [
            gene
            for gene, value in sorted(variance.items(), key=lambda item: item[1], reverse=True)
            if value > threshold
        ]

    @staticmethod
    def all_models_disagree(predictions: dict[str, np.ndarray]) -> bool:
        correlations = []
        for left, right in itertools.combinations(predictions.values(), 2):
            left_profile = profile_from_vector(left.tolist())
            right_profile = profile_from_vector(right.tolist())
            correlations.append(pearson(left_profile, right_profile))
        return bool(correlations) and all(correlation < 0.3 for correlation in correlations)

    def evaluate_heldout_perturbseq(self) -> HeldoutBenchmarkResult:
        cases = []
        ensemble_scores = []
        mean_scores = []
        for case in HELDOUT_PERTURBSEQ:
            query = PerturbationQuery(
                drug_smiles=case["drug_smiles"],
                patient_h5ad_path="lung_adenocarcinoma_h5ad"
                if case["cell_type"] == "tumor_epithelial"
                else "A549_h5ad",
                target_cell_type=case["cell_type"],
                target_gene=case["target_gene"],
            )
            result = self.run(query)
            ensemble_r = pearson(result.predicted_expression, case["truth"])
            baseline_r = pearson(case["training_mean"], case["truth"])
            ensemble_scores.append(ensemble_r)
            mean_scores.append(baseline_r)
            cases.append(
                {
                    "cell_type": case["cell_type"],
                    "target_gene": case["target_gene"],
                    "ensemble_pearson": round(ensemble_r, 4),
                    "training_mean_pearson": round(baseline_r, 4),
                }
            )
        ensemble_mean = sum(ensemble_scores) / len(ensemble_scores)
        baseline_mean = sum(mean_scores) / len(mean_scores)
        return HeldoutBenchmarkResult(
            ensemble_pearson=ensemble_mean,
            training_mean_pearson=baseline_mean,
            improvement=ensemble_mean - baseline_mean,
            per_case=cases,
        )

    def _geneformer_vector(self, target_gene: str, patient_cells: dict) -> np.ndarray:
        return self.geneformer.predict_vector(target_gene=target_gene, patient_cells=patient_cells)

    def _refusal_result(
        self,
        query: PerturbationQuery,
        patient_cells: dict,
        reasons: list[str],
    ) -> PerturbationEnsembleResult:
        warning = "; ".join(reasons)
        return PerturbationEnsembleResult(
            query=query,
            predicted_expression={},
            ensemble_variance={},
            model_predictions=[],
            high_disagreement_genes=[],
            causal_confidence="observational_only",
            do_calculus_warning=f"Prediction refused: {warning}",
            model_contributions={},
            scgpt_embedding_summary={
                "n_cells": patient_cells["n_cells"],
                "embedding_norm": 0.0,
                "role": "not_computed_due_to_refusal",
            },
            refused=True,
            refusal_reasons=reasons,
            source_urls=[],
            confidence_band=confidence_band(0.05),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    @staticmethod
    def disagreement_enrichment(high_disagreement_genes: list[str]) -> float:
        if not high_disagreement_genes:
            return 0.0
        hits = sum(1 for gene in high_disagreement_genes if gene in BIOLOGICALLY_VARIABLE_GENES)
        observed = hits / len(high_disagreement_genes)
        background = len(BIOLOGICALLY_VARIABLE_GENES) / len(GENE_PANEL)
        return observed / background if background else 0.0


def sotorasib_query() -> PerturbationQuery:
    return PerturbationQuery(
        drug_smiles=SOTORASIB_SMILES,
        patient_h5ad_path="lung_adenocarcinoma_h5ad",
        target_cell_type="tumor_epithelial",
        target_gene="KRAS",
        dose_uM=1.0,
        time_hours=24.0,
    )
