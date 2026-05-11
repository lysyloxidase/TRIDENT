"""scGPT cell-state encoder wrapper."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from trident.models.perturbation_fixtures import patient_fixture


class ScGPTWrapper:
    """scGPT fixture encoder.

    TRIDENT uses scGPT as a patient/cell-state embedding only, never as direct
    causal perturbation output.
    """

    name = "scGPT"

    def embed(self, patient_h5ad_path: str, cell_type: str, **_: Any) -> dict[str, Any]:
        fixture = patient_fixture(patient_h5ad_path, cell_type)
        seed = int(hashlib.sha1(f"{patient_h5ad_path}:{cell_type}".encode()).hexdigest()[:8], 16)
        vector = np.array([((seed >> (index % 16)) & 0xF) / 15 for index in range(16)], dtype=float)
        return {
            "embedding": vector,
            "n_cells": fixture["n_cells"],
            "baseline": fixture["baseline"],
            "variable_genes": fixture["variable_genes"],
            "caveat": (
                "Embedding only; attention/co-expression is not causal perturbation evidence."
            ),
        }
