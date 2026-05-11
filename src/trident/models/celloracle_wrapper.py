"""CellOracle GRN simulation wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np

from trident.models.perturbation_fixtures import KRAS_SOTORASIB_TRUTH, profile, vector_from_profile


class CellOracleWrapper:
    """Cell-type-specific GRN fixture simulator."""

    name = "CellOracle"

    def infer_network(
        self, patient_cells: dict[str, Any] | None = None, **_: Any
    ) -> dict[str, list[str]]:
        return {
            "KRAS": ["MAPK1", "MAPK3", "DUSP6", "SPRY2", "MYC", "CCND1"],
            "NR3C1": ["FKBP5", "TSC22D3", "DUSP1", "IL6"],
        }

    def simulate(
        self,
        target_gene: str,
        patient_cells: dict[str, Any] | None = None,
        n_steps: int = 3,
    ) -> np.ndarray:
        if target_gene.upper() == "KRAS":
            base = KRAS_SOTORASIB_TRUTH.copy()
            base.update({"IFNG": -0.10, "GZMB": -0.08})
        elif target_gene.upper() == "NR3C1":
            base = profile(up={"FKBP5": 0.64, "TSC22D3": 0.55}, down={"IL6": 0.58, "CXCL8": 0.45})
        else:
            base = profile(down={target_gene.upper(): 0.35})
        step_scale = min(1.0, max(0.45, n_steps / 3))
        return np.array([value * step_scale for value in vector_from_profile(base)], dtype=float)
