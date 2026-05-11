"""SynFlowNet fixture generator."""

from __future__ import annotations

from trident.agents.design_fixtures import substituent_library


class SynFlowNetWrapper:
    def generate(self, n_molecules: int = 120, **kwargs) -> list[dict]:
        pocket_id = kwargs.get("pocket_id", "pocket")
        substituents = substituent_library()
        molecules = []
        index = 0
        for left in substituents:
            for right in substituents:
                smiles = f"{left}Oc1ccc(NC(=O){right})cc1"
                molecules.append(
                    {
                        "smiles": smiles,
                        "source": "SynFlowNet",
                        "pocket_id": pocket_id,
                        "synthetic_accessibility": 0.82 - (index % 7) * 0.03,
                    }
                )
                index += 1
                if len(molecules) >= n_molecules:
                    return molecules
        return molecules
