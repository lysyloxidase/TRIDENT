"""GEARS genetic perturbation wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np

from trident.models.perturbation_fixtures import (
    GENE_PANEL,
    REPL0GLE_KRAS_KO,
    profile,
    vector_from_profile,
)


class GEARSWrapper:
    """GNN fixture for CRISPR-style target knockout effects."""

    name = "GEARS"

    def predict_perturbation(
        self,
        target_gene: str,
        cell_type: str,
        patient_cells: dict[str, Any] | None = None,
    ) -> np.ndarray:
        if target_gene.upper() == "KRAS":
            base = REPL0GLE_KRAS_KO
        elif target_gene.upper() == "NR3C1":
            base = profile(up={"FKBP5": 0.54, "TSC22D3": 0.46, "DUSP1": 0.42}, down={"IL6": 0.45})
        else:
            base = profile(down={target_gene.upper(): 0.80})
        attenuation = 0.86 if "tumor" in cell_type.lower() else 0.72
        return np.array([value * attenuation for value in vector_from_profile(base)], dtype=float)

    @property
    def genes(self) -> list[str]:
        return list(GENE_PANEL)
