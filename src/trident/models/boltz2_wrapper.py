"""Local Boltz-2 adapter seam used by Phase 4 agents."""

from __future__ import annotations

from typing import Any

from trident.agents.design_fixtures import target_structures


class Boltz2Wrapper:
    """Deterministic fixture adapter with the same shape as a Boltz-2 call."""

    def predict(self, target_symbol: str, sequence: str | None = None, **_: Any) -> dict[str, Any]:
        key = target_symbol.upper()
        structures = target_structures()
        if key in structures:
            return structures[key]
        return {
            "uniprot_id": f"UNMAPPED:{key}",
            "sequence": sequence or "",
            "experimental_pdb": None,
            "predicted_pdb_path": f"data/predicted/{key}_boltz2_fixture.pdb",
            "rmsd_to_experimental": None,
            "plddt": 72.0,
            "lddt_pli": 0.55,
            "source_urls": [],
            "pockets": [],
        }
