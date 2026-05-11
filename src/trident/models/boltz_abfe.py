"""Boltz-ABFE2 fixture scoring."""

from __future__ import annotations

from trident.agents.design_fixtures import known_tyk2_inhibitors


class BoltzABFEWrapper:
    def estimate(self, smiles: str, target_symbol: str = "TYK2", **kwargs) -> dict:
        known = {entry["smiles"]: entry for entry in known_tyk2_inhibitors()}
        if smiles in known:
            value = known[smiles]["experimental_delta_g"] + 0.08
        else:
            heavy = sum(1 for char in smiles if char in {"C", "N", "O", "S", "F", "P"})
            aromatic_bonus = 1.1 if "c1" in smiles or "c2" in smiles else 0.0
            hetero_bonus = 0.5 if "N" in smiles and "O" in smiles else 0.0
            value = -6.2 - min(3.2, heavy / 18) - aromatic_bonus - hetero_bonus
        return {
            "target_symbol": target_symbol,
            "delta_g_kcal_mol": round(value, 3),
            "model": "Boltz-ABFE2-fixture",
        }
