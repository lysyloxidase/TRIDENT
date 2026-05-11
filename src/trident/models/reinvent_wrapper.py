"""REINVENT 4 fixture generator."""

from __future__ import annotations

from trident.agents.design_fixtures import substituent_library


class REINVENTWrapper:
    def generate(self, n_molecules: int = 120, mode: str = "de_novo", **kwargs) -> list[dict]:
        pocket_id = kwargs.get("pocket_id", "pocket")
        substituents = substituent_library()
        molecules = []
        index = 0
        for left in reversed(substituents):
            for right in substituents:
                smiles = f"{left}N1CCN(CC1)C(=O)c2ccc({right})cc2"
                molecules.append(
                    {
                        "smiles": smiles,
                        "source": "REINVENT4",
                        "mode": mode,
                        "pocket_id": pocket_id,
                        "synthetic_accessibility": 0.76 - (index % 6) * 0.025,
                    }
                )
                index += 1
                if len(molecules) >= n_molecules:
                    return molecules
        return molecules
