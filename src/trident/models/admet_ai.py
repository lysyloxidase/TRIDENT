"""ADMET-AI fixture endpoint predictions."""

from __future__ import annotations

from trident.agents.design_fixtures import toxic_smiles


class ADMETAIWrapper:
    def predict(self, smiles: str, **kwargs) -> dict:
        toxic = smiles in toxic_smiles()
        nitro = "[N+]" in smiles or "N=O" in smiles
        halogenated = smiles.count("Cl") >= 3
        failures = []
        if toxic or nitro:
            failures.extend(["Ames", "hERG"])
        if halogenated:
            failures.extend(["CYP3A4", "solubility"])
        bbb = 0.35 if "N" in smiles and "O" in smiles else 0.62
        return {
            "solubility": 0.28 if "solubility" in failures else 0.72,
            "bbb": bbb,
            "cyp_inhibition": 0.82 if "CYP3A4" in failures else 0.22,
            "herg": 0.86 if "hERG" in failures else 0.18,
            "ames": 0.91 if "Ames" in failures else 0.10,
            "critical_failures": sorted(set(failures)),
        }
