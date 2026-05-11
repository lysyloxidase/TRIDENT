"""Bayesian confidence fusion for target hypotheses."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.types import ConfidenceInterval


class EvidenceStreams(BaseModel):
    genetic_causal_p: float = Field(default=0.0, ge=0.0, le=1.0)
    mr_p_value: float = Field(default=1.0, ge=0.0, le=1.0)
    consistent_direction: bool = False
    lbd_score: float = Field(default=0.0, ge=0.0, le=1.0)
    lbd_independent_paths: int = Field(default=0, ge=0)
    gwas_pip: float = Field(default=0.0, ge=0.0, le=1.0)
    expression_specificity: float = Field(default=0.0, ge=0.0, le=1.0)
    depmap_dependency: float = Field(default=0.0, ge=0.0, le=1.0)
    relevant_depmap_lines: int = Field(default=0, ge=0)
    primekg_path_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    patent_white_space: float = Field(default=0.0, ge=0.0, le=1.0)
    trial_failure_gap: float = Field(default=0.0, ge=0.0, le=1.0)
    contradictory_evidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ConfidenceBreakdown(BaseModel):
    confidence_score: float = Field(ge=0.0, le=1.0)
    credible_interval: ConfidenceInterval
    likelihood_ratios: dict[str, float]
    posterior_alpha: float
    posterior_beta: float


class ConfidenceScorer:
    """Bayesian fusion of multiple evidence streams for target confidence."""

    def bayes_fusion(self, evidence: EvidenceStreams) -> ConfidenceBreakdown:
        return self.score(evidence)

    def score(self, evidence: EvidenceStreams) -> ConfidenceBreakdown:
        likelihood_ratios = self.likelihood_ratios(evidence)
        odds = 1.0
        for value in likelihood_ratios.values():
            odds *= value
        confidence = odds / (1 + odds)
        support_mass = sum(max(0.0, value - 1.0) for value in likelihood_ratios.values())
        contradiction_mass = max(0.0, (1 / max(likelihood_ratios["contradiction"], 1e-9)) - 1.0)
        alpha = 1.0 + support_mass
        beta = 1.0 + contradiction_mass
        width = max(0.03, min(0.22, 0.18 / (alpha + beta) ** 0.5))
        interval = ConfidenceInterval(
            lower=max(0.0, confidence - width),
            upper=min(1.0, confidence + width),
            confidence_level=0.95,
        )
        return ConfidenceBreakdown(
            confidence_score=confidence,
            credible_interval=interval,
            likelihood_ratios=likelihood_ratios,
            posterior_alpha=alpha,
            posterior_beta=beta,
        )

    @staticmethod
    def likelihood_ratios(evidence: EvidenceStreams) -> dict[str, float]:
        lrs = {
            "mr": 10.0
            if evidence.mr_p_value < 0.001 and evidence.consistent_direction
            else 3.0
            if evidence.genetic_causal_p > 0.65
            else 1.2
            if evidence.genetic_causal_p > 0.45
            else 0.8,
            "gwas_pip": 8.0 if evidence.gwas_pip > 0.9 else 4.0 if evidence.gwas_pip > 0.7 else 1.0,
            "depmap": 5.0
            if evidence.depmap_dependency > 0.6 and evidence.relevant_depmap_lines >= 3
            else 2.0
            if evidence.depmap_dependency > 0.35
            else 1.0,
            "lbd": 3.0
            if evidence.lbd_independent_paths >= 3 or evidence.lbd_score >= 0.7
            else 1.8
            if evidence.lbd_independent_paths >= 2 or evidence.lbd_score >= 0.5
            else 1.0,
            "expression": 2.0 if evidence.expression_specificity > 0.8 else 1.3,
            "primekg": 2.5 if evidence.primekg_path_strength > 0.65 else 1.4,
            "patent_white_space": 1.8 if evidence.patent_white_space > 0.7 else 1.0,
            "trial_gap": 1.5 if evidence.trial_failure_gap > 0.6 else 1.0,
            "contradiction": max(0.05, 1.0 - 0.85 * evidence.contradictory_evidence),
        }
        return lrs


def confidence_score(evidence_scores: list[float]) -> float:
    """Compatibility noisy-or aggregation from Phase 1."""

    posterior = 0.0
    for score in evidence_scores:
        posterior = 1 - (1 - posterior) * (1 - max(0.0, min(1.0, score)))
    return posterior
