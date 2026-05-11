"""Shared Pydantic models used across TRIDENT phases."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    GWAS = "gwas"
    OMIM = "omim"
    LITERATURE = "literature"
    CLINICAL_TRIAL = "clinical_trial"
    PATENT = "patent"
    DEPMAP = "depmap"
    EXPRESSION = "expression"
    LBD = "literature_based_discovery"
    MR = "mendelian_randomization"
    OPENTARGETS = "opentargets"
    PHAROS = "pharos"
    PRIMEKG = "primekg"
    HETIONET = "hetionet"
    DRKG = "drkg"
    DISGENET = "disgenet"
    CHEMBL = "chembl"
    DRUGBANK = "drugbank"
    GTEX = "gtex"
    LENS = "lens"


class ConfidenceInterval(BaseModel):
    """Uncertainty interval for a score or model output."""

    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    """A single provenance-bearing evidence statement."""

    source: EvidenceSource
    relationship: str
    score: float | None = Field(default=None, ge=0.0)
    evidence_type: str | None = None
    pmid: str | None = None
    url: str | None = None
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LBDPath(BaseModel):
    """A Swanson A-B-C literature-based discovery path."""

    a_concept: str
    b_concept: str
    c_concept: str
    predicates: list[str] = Field(default_factory=list)
    pmids: list[str] = Field(default_factory=list)
    support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty_rationale: str | None = None


class DruggabilityInfo(BaseModel):
    """Target tractability and modality hints."""

    tractability: str | None = None
    modalities: list[str] = Field(default_factory=list)
    has_structure: bool = False
    alphafold_plddt: float | None = Field(default=None, ge=0.0, le=100.0)
    pocketability: float | None = Field(default=None, ge=0.0, le=1.0)
    safety_notes: list[str] = Field(default_factory=list)


class TargetCandidate(BaseModel):
    gene_symbol: str
    uniprot_id: str
    disease_id: str
    disease_name: str
    pharos_tdl: Literal["Tclin", "Tchem", "Tbio", "Tdark"] | str
    novelty_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    trident_score: float = Field(ge=0.0, le=1.0)
    evidence_trace: list[EvidenceItem] = Field(default_factory=list)
    mr_posterior: float | None = Field(default=None, ge=0.0, le=1.0)
    lbd_paths: list[LBDPath] | None = None
    pipeline_gap: float = Field(ge=0.0, le=1.0)
    druggability: DruggabilityInfo
    uncertainty: ConfidenceInterval


class PerturbationQuery(BaseModel):
    drug_smiles: str
    patient_h5ad_path: str
    target_cell_type: str
    target_gene: str
    dose_uM: float = Field(default=1.0, gt=0.0)
    time_hours: float = Field(default=24.0, gt=0.0)


class PerturbationResult(BaseModel):
    predicted_expression: dict[str, float]
    ensemble_variance: dict[str, float]
    high_disagreement_genes: list[str]
    causal_confidence: Literal["interventional", "observational_only"]
    do_calculus_warning: str | None = None
    model_contributions: dict[str, float]
