"""Mandatory caveats surfaced in reports, UI, and documentation."""

MANDATORY_CAVEATS = [
    (
        "Single-cell foundation models (scGPT, Geneformer) frequently lose to a "
        "mean-of-training-data baseline on perturbation tasks. The ensemble variance "
        "is the most informative output."
    ),
    (
        "Boltz-2 TYK2 validation is in-silico-against-in-silico (Boltz-2 to ABFE). "
        "No wet-lab confirmation is available in the public preprint."
    ),
    (
        "LLMs hallucinate citations 78-90% of the time in unverified settings "
        "(OpenScholar paper). TRIDENT verifies every PMID against PubMed-compatible "
        "records, but errors may remain."
    ),
    (
        "Patent white-space extraction has a 5-15% expected error rate. All "
        "patent-derived claims are tagged legal_review_required=True."
    ),
    (
        "SemMedDB literature-based discovery has high false-positive rates. TRIDENT "
        "filters by at least two independent paths plus Bayesian priors."
    ),
    (
        "TRIDENT is a research platform for hypothesis generation. It is not for "
        "clinical decision-making or investment advice."
    ),
    (
        "Causal claims from co-expression embeddings are explicitly refused. TRIDENT "
        "distinguishes interventional from observational evidence."
    ),
]


def caveats_markdown() -> str:
    return "\n".join(f"- {caveat}" for caveat in MANDATORY_CAVEATS)
