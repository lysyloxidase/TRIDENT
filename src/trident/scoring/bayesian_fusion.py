from trident.scoring.confidence import confidence_score


def fuse_evidence(evidence_scores: list[float], novelty: float) -> float:
    """Return TRIDENT's Phase 1 ranking score N x C."""

    return max(0.0, min(1.0, novelty)) * confidence_score(evidence_scores)
