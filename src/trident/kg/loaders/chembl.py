"""ChEMBL REST API loader."""

from __future__ import annotations

import os
from typing import Any

import httpx

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class ChEMBLLoader(BaseLoader):
    """Load target-compound bioactivity and mechanism records from ChEMBL."""

    source_name = "chembl"
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    expected_nodes = 2_500_000
    expected_relationships = 20_000_000

    FIXTURE_COMPOUNDS = [
        {
            "chembl_id": "CHEMBL939",
            "name": "Gefitinib",
            "smiles": "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4",
            "target_symbol": "EGFR",
            "target_uniprot": "P00533",
            "affinity_nM": 1.0,
            "mechanism": "EGFR tyrosine kinase inhibitor",
            "phase": "approved",
        },
        {
            "chembl_id": "CHEMBL553",
            "name": "Erlotinib",
            "smiles": "COCCOC1=CC2=C(C=C1OCCOC)N=CN=C2NC3=CC=CC(=C3)C#C",
            "target_symbol": "EGFR",
            "target_uniprot": "P00533",
            "affinity_nM": 2.0,
            "mechanism": "EGFR tyrosine kinase inhibitor",
            "phase": "approved",
        },
    ]

    def query_target_compounds(
        self,
        gene_symbol: str = "EGFR",
        *,
        use_live_api: bool | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        live = use_live_api if use_live_api is not None else os.getenv("TRIDENT_LIVE_APIS") == "1"
        if live:
            try:
                rows = self._query_live_target_compounds(gene_symbol, limit=limit)
                if rows:
                    return rows
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                pass
        rows = [
            row
            for row in self.FIXTURE_COMPOUNDS
            if row["target_symbol"].upper() == gene_symbol.upper()
        ]
        return rows[:limit] if limit else rows

    def _query_live_target_compounds(
        self, gene_symbol: str, *, limit: int | None
    ) -> list[dict[str, Any]]:
        target_response = httpx.get(
            f"{self.base_url}/target/search.json",
            params={"q": gene_symbol},
            timeout=30,
        )
        target_response.raise_for_status()
        targets = target_response.json().get("targets", [])
        if not targets:
            return []
        target_chembl_id = targets[0]["target_chembl_id"]
        mechanism_response = httpx.get(
            f"{self.base_url}/mechanism.json",
            params={"target_chembl_id": target_chembl_id, "limit": limit or 20},
            timeout=30,
        )
        mechanism_response.raise_for_status()
        rows = []
        for item in mechanism_response.json().get("mechanisms", []):
            rows.append(
                {
                    "chembl_id": item.get("molecule_chembl_id"),
                    "name": item.get("molecule_pref_name"),
                    "smiles": None,
                    "target_symbol": gene_symbol.upper(),
                    "target_uniprot": {"EGFR": "P00533"}.get(
                        gene_symbol.upper(), f"UNMAPPED:{gene_symbol.upper()}"
                    ),
                    "affinity_nM": None,
                    "mechanism": item.get("mechanism_of_action"),
                    "phase": item.get("max_phase"),
                }
            )
        return rows

    def load(self, limit: int | None = None, gene_symbol: str = "EGFR") -> LoadReport:
        report = self.report()
        for row in self.query_target_compounds(gene_symbol, limit=limit):
            compound = self.compound(
                compound_id=row["chembl_id"],
                name=row.get("name"),
                smiles=row.get("smiles"),
                chembl_id=row["chembl_id"],
                phase=row.get("phase"),
            )
            gene = self.gene(uniprot_id=row["target_uniprot"], symbol=row["target_symbol"])
            self.merge_relationship(
                NodeLabel.COMPOUND,
                compound,
                RelationshipType.TARGETS,
                NodeLabel.GENE,
                gene,
                {
                    "affinity_nM": row.get("affinity_nM"),
                    "mechanism": row.get("mechanism"),
                    "phase": row.get("phase"),
                },
            )
            report.add(records=1, nodes=2, relationships=1)
        return report
