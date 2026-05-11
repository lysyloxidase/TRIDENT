"""Geneformer perturbation wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np

from trident.models.perturbation_fixtures import (
    KRAS_SOTORASIB_TRUTH,
    profile,
    vector_from_profile,
)


class GeneformerWrapper:
    """Rank-value transformer fixture for downstream gene effects."""

    name = "Geneformer"

    def embed(self, patient_cells: dict[str, Any] | None = None, **_: Any) -> np.ndarray:
        baseline = (patient_cells or {}).get("baseline", {})
        return np.array(vector_from_profile(baseline), dtype=float)

    def in_silico_perturb(
        self,
        target_gene: str,
        patient_cells: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        if target_gene.upper() == "KRAS":
            values = KRAS_SOTORASIB_TRUTH.copy()
            values.update({"DUSP6": 0.82, "SPRY2": 0.50, "ETV4": -0.62, "ETV5": -0.58})
            return values
        if target_gene.upper() == "NR3C1":
            return profile(up={"FKBP5": 0.88, "TSC22D3": 0.71, "DUSP1": 0.50}, down={"IL6": 0.52})
        return profile(down={target_gene.upper(): 0.55})

    def predict_vector(
        self, target_gene: str, patient_cells: dict[str, Any] | None = None
    ) -> np.ndarray:
        return np.array(
            vector_from_profile(self.in_silico_perturb(target_gene, patient_cells)), dtype=float
        )
