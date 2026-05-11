"""Target ranking by TRIDENT novelty x confidence score."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.agents.hypothesis_fixtures import target_profiles
from trident.scoring.confidence import ConfidenceScorer, EvidenceStreams, confidence_score
from trident.scoring.novelty import NoveltyInput, NoveltyScorer
from trident.types import (
    ConfidenceInterval,
    DruggabilityInfo,
    EvidenceItem,
    EvidenceSource,
    TargetCandidate,
)


class TargetRankingQuery(BaseModel):
    disease_name: str
    top_k: int = Field(default=10, ge=1, le=100)
    min_pipeline_gap: float = Field(default=0.5, ge=0.0, le=1.0)
    require_druggable: bool = True


class RankedTarget(BaseModel):
    candidate: TargetCandidate
    quadrant: str
    rank: int


class TargetRanker:
    """Rank targets by TRIDENT score = Novelty x Confidence."""

    def __init__(
        self,
        novelty_scorer: NoveltyScorer | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
    ) -> None:
        self.novelty_scorer = novelty_scorer or NoveltyScorer()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()

    def rank(self, query: TargetRankingQuery) -> list[RankedTarget]:
        candidates = []
        for profile in target_profiles():
            if query.disease_name.lower() not in profile["disease_name"].lower():
                continue
            if profile["pipeline_gap"] < query.min_pipeline_gap:
                continue
            if query.require_druggable and not self._is_druggable(profile):
                continue
            candidate = self._candidate_from_profile(profile)
            candidates.append(candidate)

        candidates.sort(key=lambda candidate: candidate.trident_score, reverse=True)
        return [
            RankedTarget(
                candidate=candidate,
                quadrant=self.quadrant(candidate.novelty_score, candidate.confidence_score),
                rank=index,
            )
            for index, candidate in enumerate(candidates[: query.top_k], start=1)
        ]

    def rank_targets_for_disease(self, disease_name: str, top_k: int = 10) -> list[TargetCandidate]:
        return [
            item.candidate
            for item in self.rank(TargetRankingQuery(disease_name=disease_name, top_k=top_k))
        ]

    def rank_targets(self, disease_name: str, top_k: int = 10) -> list[TargetCandidate]:
        return self.rank_targets_for_disease(disease_name=disease_name, top_k=top_k)

    def _candidate_from_profile(self, profile: dict) -> TargetCandidate:
        novelty = self.novelty_scorer.score(
            NoveltyInput(
                gene_symbol=profile["gene_symbol"],
                disease_name=profile["disease_name"],
                pharos_tdl=profile["pharos_tdl"],
                publication_count=profile["publication_count"],
                uzzi_z_score=profile["uzzi_z"],
                llm_novelty_prior=profile["llm_novelty_prior"],
                pipeline_gap=profile["pipeline_gap"],
            )
        )
        evidence = EvidenceStreams(
            genetic_causal_p=profile["evidence"]["mr_posterior"],
            mr_p_value=0.0005 if profile["evidence"]["mr_posterior"] > 0.7 else 0.02,
            consistent_direction=profile["evidence"]["mr_posterior"] > 0.5,
            lbd_score=profile["evidence"]["lbd_score"],
            lbd_independent_paths=3 if profile["evidence"]["lbd_score"] > 0.65 else 2,
            gwas_pip=profile["evidence"]["gwas_pip"],
            expression_specificity=profile["evidence"]["expression_specificity"],
            depmap_dependency=profile["evidence"]["depmap_dependency"],
            relevant_depmap_lines=3 if profile["evidence"]["depmap_dependency"] > 0.55 else 1,
            primekg_path_strength=profile["evidence"]["primekg_path_strength"],
            patent_white_space=profile["evidence"]["patent_white_space"],
            trial_failure_gap=profile["evidence"]["trial_failure_gap"],
            contradictory_evidence=profile["evidence"]["contradictory_evidence"],
        )
        confidence = self.confidence_scorer.score(evidence)
        trident_score = novelty.novelty_score * confidence.confidence_score
        return TargetCandidate(
            gene_symbol=profile["gene_symbol"],
            uniprot_id=profile["uniprot_id"],
            disease_id=profile["disease_id"],
            disease_name=profile["disease_name"],
            pharos_tdl=profile["pharos_tdl"],
            novelty_score=novelty.novelty_score,
            confidence_score=confidence.confidence_score,
            trident_score=trident_score,
            evidence_trace=self._evidence_trace(profile, evidence),
            mr_posterior=profile["evidence"]["mr_posterior"],
            lbd_paths=None,
            pipeline_gap=profile["pipeline_gap"],
            druggability=DruggabilityInfo(**profile["druggability"]),
            uncertainty=confidence.credible_interval,
        )

    @staticmethod
    def quadrant(novelty: float, confidence: float) -> str:
        if novelty >= 0.55 and confidence >= 0.70:
            return "PRIORITY_TARGET"
        if novelty >= 0.55 and confidence < 0.70:
            return "SPECULATIVE"
        if novelty < 0.55 and confidence >= 0.70:
            return "VALIDATED"
        return "IGNORE"

    @staticmethod
    def _is_druggable(profile: dict) -> bool:
        druggability = profile["druggability"]
        return (
            druggability.get("pocketability", 0.0) >= 0.55
            or "PROTAC" in druggability.get("modalities", [])
            or druggability.get("has_structure", False)
        )

    @staticmethod
    def _evidence_trace(profile: dict, evidence: EvidenceStreams) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source=EvidenceSource.MR,
                relationship="CAUSAL_FOR",
                score=evidence.genetic_causal_p,
                evidence_type="Mendelian randomization posterior",
            ),
            EvidenceItem(
                source=EvidenceSource.LBD,
                relationship="ABC_SUPPORTS",
                score=evidence.lbd_score,
                evidence_type="Swanson ABC literature closure",
            ),
            EvidenceItem(
                source=EvidenceSource.GWAS,
                relationship="FINE_MAPPING",
                score=evidence.gwas_pip,
                evidence_type="GWAS credible set PIP",
            ),
            EvidenceItem(
                source=EvidenceSource.PATENT,
                relationship="WHITE_SPACE",
                score=evidence.patent_white_space,
                evidence_type=f"Pipeline gap {profile['pipeline_gap']:.2f}",
            ),
        ]


def fuse_evidence(evidence_scores: list[float], novelty: float) -> float:
    """Return TRIDENT's Phase 1 ranking score N x C."""

    return max(0.0, min(1.0, novelty)) * confidence_score(evidence_scores)


def credible_interval_from_score(score: float) -> ConfidenceInterval:
    return ConfidenceInterval(lower=max(0.0, score - 0.08), upper=min(1.0, score + 0.08))
