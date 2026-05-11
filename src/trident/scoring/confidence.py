def confidence_score(evidence_scores: list[float]) -> float:
    """Noisy-or evidence aggregation baseline for Phase 1 smoke tests."""

    posterior = 0.0
    for score in evidence_scores:
        posterior = 1 - (1 - posterior) * (1 - max(0.0, min(1.0, score)))
    return posterior
