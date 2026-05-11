"""Offline perturbation fixtures for Phase 5 ensemble tests."""

from __future__ import annotations

import math
from typing import Any

GENE_PANEL = [
    "FKBP5",
    "TSC22D3",
    "DUSP1",
    "PER1",
    "KLF9",
    "IL6",
    "CXCL8",
    "NFKBIA",
    "TNF",
    "JUN",
    "FOS",
    "KRAS",
    "NRAS",
    "BRAF",
    "RAF1",
    "MAPK1",
    "MAPK3",
    "DUSP6",
    "SPRY2",
    "ETV4",
    "ETV5",
    "MYC",
    "CCND1",
    "EGR1",
    "AREG",
    "EREG",
    "PIK3CA",
    "AKT1",
    "MTOR",
    "CDKN1A",
    "GADD45A",
    "BCL2L11",
    "MKI67",
    "TOP2A",
    "EPCAM",
    "KRT8",
    "KRT18",
    "IFNG",
    "GZMB",
    "PDCD1",
]

DEXAMETHASONE_SMILES = "CC12CCC3C(C1CCC2O)CCC4=CC(=O)C=CC34C"
SOTORASIB_SMILES = "CC(C)N1C(=O)C=CC2=C1C=CC(NC(=O)C3=CC=CC=C3F)=C2C"


def zero_profile() -> dict[str, float]:
    return {gene: 0.0 for gene in GENE_PANEL}


def profile(
    up: dict[str, float] | None = None, down: dict[str, float] | None = None
) -> dict[str, float]:
    values = zero_profile()
    for gene, value in (up or {}).items():
        values[gene] = value
    for gene, value in (down or {}).items():
        values[gene] = -abs(value)
    return values


DEX_A549_GROUND_TRUTH = profile(
    up={"FKBP5": 1.35, "TSC22D3": 1.10, "DUSP1": 0.82, "PER1": 0.62, "KLF9": 0.58, "NFKBIA": 0.42},
    down={"IL6": 0.95, "CXCL8": 0.72, "TNF": 0.50, "FOS": 0.34, "JUN": 0.28},
)

KRAS_SOTORASIB_TRUTH = profile(
    up={"DUSP6": 0.72, "SPRY2": 0.44, "CDKN1A": 0.36, "BCL2L11": 0.30},
    down={
        "KRAS": 0.82,
        "MAPK1": 0.48,
        "MAPK3": 0.55,
        "ETV4": 0.70,
        "ETV5": 0.66,
        "MYC": 0.64,
        "CCND1": 0.58,
        "FOS": 0.46,
        "JUN": 0.38,
        "AREG": 0.40,
        "EREG": 0.37,
        "MKI67": 0.45,
        "TOP2A": 0.42,
    },
)

REPL0GLE_KRAS_KO = profile(
    up={"DUSP6": 0.60, "SPRY2": 0.38, "CDKN1A": 0.28},
    down={"KRAS": 1.25, "MAPK1": 0.44, "MAPK3": 0.52, "MYC": 0.61, "CCND1": 0.54, "FOS": 0.35},
)

HELDOUT_PERTURBSEQ = [
    {
        "drug_smiles": SOTORASIB_SMILES,
        "target_gene": "KRAS",
        "cell_type": "tumor_epithelial",
        "truth": KRAS_SOTORASIB_TRUTH,
        "training_mean": profile(up={"DUSP6": 0.20}, down={"MYC": 0.20, "CCND1": 0.16}),
    },
    {
        "drug_smiles": DEXAMETHASONE_SMILES,
        "target_gene": "NR3C1",
        "cell_type": "A549",
        "truth": DEX_A549_GROUND_TRUTH,
        "training_mean": profile(up={"FKBP5": 0.30, "TSC22D3": 0.22}, down={"IL6": 0.16}),
    },
]

LINCS_COVERED_PAIRS = {
    (DEXAMETHASONE_SMILES, "A549"),
    (SOTORASIB_SMILES, "tumor_epithelial"),
}

TRAINING_CELL_COUNTS = {
    "A549": 3_500,
    "tumor_epithelial": 1_250,
    "lung_adenocarcinoma": 1_250,
    "CD8+ T cell": 850,
    "hepatocyte": 640,
    "novel_cell_type": 12,
}

BIOLOGICALLY_VARIABLE_GENES = {
    "IL6",
    "CXCL8",
    "FOS",
    "JUN",
    "MYC",
    "IFNG",
    "GZMB",
    "PDCD1",
    "ETV4",
    "ETV5",
    "AREG",
    "EREG",
    "MKI67",
    "TOP2A",
    "BCL2L11",
}


def known_training_compounds() -> dict[str, str]:
    return {
        DEXAMETHASONE_SMILES: "dexamethasone",
        SOTORASIB_SMILES: "sotorasib",
        "CC1=C(C=CC=C1)NC(=O)C2=CC=CC=C2": "trametinib_like",
        "CCOC(=O)N1CCC(CC1)NC2=NC=CC=N2": "jak_inhibitor_like",
    }


def patient_fixture(path: str, cell_type: str) -> dict[str, Any]:
    normalized = cell_type.strip()
    if "lung_adenocarcinoma" in path or normalized == "tumor_epithelial":
        return {
            "path": path,
            "cell_type": normalized,
            "n_cells": 480,
            "baseline": profile(up={"KRAS": 0.62, "EPCAM": 0.74, "KRT8": 0.55, "KRT18": 0.52}),
            "variable_genes": sorted(BIOLOGICALLY_VARIABLE_GENES),
        }
    return {
        "path": path,
        "cell_type": normalized,
        "n_cells": TRAINING_CELL_COUNTS.get(normalized, 20),
        "baseline": zero_profile(),
        "variable_genes": sorted(BIOLOGICALLY_VARIABLE_GENES),
    }


def vector_from_profile(values: dict[str, float]) -> list[float]:
    return [values.get(gene, 0.0) for gene in GENE_PANEL]


def profile_from_vector(values: list[float]) -> dict[str, float]:
    return {gene: round(values[index], 4) for index, gene in enumerate(GENE_PANEL)}


def pearson(a: dict[str, float], b: dict[str, float]) -> float:
    xs = vector_from_profile(a)
    ys = vector_from_profile(b)
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def tanimoto_like(smiles_a: str, smiles_b: str) -> float:
    def shingles(text: str) -> set[str]:
        return {text[index : index + 2] for index in range(max(0, len(text) - 1))}

    a = shingles(smiles_a)
    b = shingles(smiles_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
