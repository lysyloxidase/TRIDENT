"""CPA perturbation model wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np

from trident.models.perturbation_fixtures import (
    DEX_A549_GROUND_TRUTH,
    DEXAMETHASONE_SMILES,
    GENE_PANEL,
    KRAS_SOTORASIB_TRUTH,
    SOTORASIB_SMILES,
    profile,
    vector_from_profile,
)


class CPAWrapper:
    """Compositional Perturbation Autoencoder fixture adapter."""

    name = "CPA"

    def predict(
        self,
        drug_smiles: str,
        dose_uM: float,
        cell_type: str,
        covariates: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """Predict post-perturbation expression profile as log2FC vector."""

        dose_scale = min(1.35, max(0.35, np.log1p(dose_uM) / np.log1p(1.0)))
        if drug_smiles == DEXAMETHASONE_SMILES and cell_type == "A549":
            base = DEX_A549_GROUND_TRUTH
        elif drug_smiles == SOTORASIB_SMILES and cell_type in {
            "tumor_epithelial",
            "lung_adenocarcinoma",
        }:
            base = KRAS_SOTORASIB_TRUTH
        else:
            base = profile(up={"DUSP1": 0.18}, down={"MYC": 0.14})

        patient_shift = 0.0
        if covariates and covariates.get("stress_high"):
            patient_shift = 0.06
        values = [value * dose_scale + patient_shift for value in vector_from_profile(base)]
        return np.array(values, dtype=float)

    def predict_perturbation(self, *args: Any, **kwargs: Any) -> np.ndarray:
        return self.predict(*args, **kwargs)

    @property
    def genes(self) -> list[str]:
        return list(GENE_PANEL)
