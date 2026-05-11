def novelty_score(publication_count: int, pharos_tdl: str, pipeline_gap: float) -> float:
    """Simple Phase 1 novelty prior used until the Phase 3 model lands."""

    tdl_bonus = {"Tdark": 0.45, "Tbio": 0.30, "Tchem": 0.12, "Tclin": 0.02}.get(pharos_tdl, 0.1)
    literature_penalty = min(0.45, publication_count / 10_000)
    return max(0.0, min(1.0, pipeline_gap * 0.55 + tdl_bonus - literature_penalty))
