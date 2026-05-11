"""Information-theoretic novelty scoring for target hypotheses."""

from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel, Field


class NoveltyInput(BaseModel):
    gene_symbol: str
    disease_name: str
    pharos_tdl: str
    publication_count: int = Field(ge=0)
    uzzi_z_score: float = 0.0
    llm_novelty_prior: float = Field(default=0.5, ge=0.0, le=1.0)
    pipeline_gap: float = Field(default=0.5, ge=0.0, le=1.0)


class NoveltyBreakdown(BaseModel):
    uzzi_atypicality: float = Field(ge=0.0, le=1.0)
    llm_swiss_tournament_score: float = Field(ge=0.0, le=1.0)
    pharos_bonus: float = Field(ge=0.0, le=0.3)
    literature_penalty: float = Field(ge=0.0, le=1.0)
    pipeline_gap_bonus: float = Field(ge=0.0, le=1.0)
    novelty_score: float = Field(ge=0.0, le=1.0)


class NoveltyScorer:
    """Compute information-theoretic novelty of a target hypothesis.

    Components:
    - Uzzi atypicality from rare co-citation framing.
    - LLM Swiss-tournament novelty/plausibility prior.
    - Pharos TDL bonus for Tdark/Tbio under-studied proteins.
    """

    TDL_BONUS = {"Tdark": 0.30, "Tbio": 0.15, "Tchem": 0.03, "Tclin": 0.0}

    def compute(self, hypothesis: NoveltyInput) -> NoveltyBreakdown:
        return self.score(hypothesis)

    def score(self, hypothesis: NoveltyInput) -> NoveltyBreakdown:
        uzzi = self.uzzi_atypicality(hypothesis.uzzi_z_score)
        llm_score = hypothesis.llm_novelty_prior
        pharos_bonus = self.TDL_BONUS.get(hypothesis.pharos_tdl, 0.05)
        literature_penalty = min(0.35, hypothesis.publication_count / 20_000)
        pipeline_bonus = 0.12 * hypothesis.pipeline_gap
        raw = 0.36 * uzzi + 0.34 * llm_score + pharos_bonus + pipeline_bonus - literature_penalty
        score = max(0.0, min(1.0, raw))
        return NoveltyBreakdown(
            uzzi_atypicality=uzzi,
            llm_swiss_tournament_score=llm_score,
            pharos_bonus=pharos_bonus,
            literature_penalty=literature_penalty,
            pipeline_gap_bonus=pipeline_bonus,
            novelty_score=score,
        )

    def swiss_tournament(self, hypotheses: list[NoveltyInput]) -> dict[str, float]:
        """Pairwise novelty/plausibility ranking with a BTL-style update."""

        names = [hypothesis.gene_symbol for hypothesis in hypotheses]
        wins = {name: {other: 0 for other in names if other != name} for name in names}
        priors = {hypothesis.gene_symbol: hypothesis.llm_novelty_prior for hypothesis in hypotheses}
        for left, right in combinations(hypotheses, 2):
            winner = (
                left if self.score(left).novelty_score >= self.score(right).novelty_score else right
            )
            loser = right if winner is left else left
            if priors[winner.gene_symbol] >= priors[loser.gene_symbol] - 0.2:
                wins[winner.gene_symbol][loser.gene_symbol] += 1

        strengths = {name: 1.0 for name in names}
        for _ in range(50):
            updated = {}
            for name in names:
                total_wins = sum(wins[name].values()) + 1e-6
                denom = 0.0
                for other in names:
                    if other == name:
                        continue
                    games = wins[name].get(other, 0) + wins[other].get(name, 0)
                    denom += games / max(strengths[name] + strengths[other], 1e-9)
                updated[name] = total_wins / max(denom, 1e-9)
            total = sum(updated.values()) or 1.0
            strengths = {name: value / total for name, value in updated.items()}
        return strengths

    @staticmethod
    def uzzi_atypicality(z_score: float) -> float:
        """Map rare journal-pair z-scores into [0, 1] novelty."""

        if z_score >= 0:
            return max(0.0, 0.45 - min(z_score, 3.0) * 0.10)
        return min(1.0, 0.45 + min(abs(z_score), 3.0) * 0.18)


def novelty_score(publication_count: int, pharos_tdl: str, pipeline_gap: float) -> float:
    """Compatibility wrapper from Phase 1."""

    result = NoveltyScorer().score(
        NoveltyInput(
            gene_symbol="unknown",
            disease_name="unknown",
            pharos_tdl=pharos_tdl,
            publication_count=publication_count,
            uzzi_z_score=-1.0,
            llm_novelty_prior=0.55,
            pipeline_gap=pipeline_gap,
        )
    )
    return result.novelty_score
