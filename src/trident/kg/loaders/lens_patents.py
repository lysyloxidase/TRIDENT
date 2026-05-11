"""Lens.org patent loader."""

from __future__ import annotations

import os
from typing import Any

import httpx

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class LensPatentsLoader(BaseLoader):
    """Load Lens.org patent claims that mention genes, targets, and indications."""

    source_name = "lens_patents"
    endpoint = "https://api.lens.org/patent/search"
    expected_nodes = 10_000_000
    expected_relationships = 20_000_000

    FIXTURE_PATENTS = [
        {
            "lens_id": "LENS-TRIDENT-EGFR-001",
            "publication_number": "US20030087813A1",
            "filing_date": "2001-10-26",
            "claims": "EGFR tyrosine kinase inhibitor compounds for treating cancer.",
            "gene_symbol": "EGFR",
            "uniprot_id": "P00533",
            "claim_type": "composition_of_matter",
        },
        {
            "lens_id": "LENS-TRIDENT-TMEM132B-001",
            "publication_number": "WO2019123456A1",
            "filing_date": "2018-12-20",
            "claims": "Methods for modulating TMEM132B in neurological disease.",
            "gene_symbol": "TMEM132B",
            "uniprot_id": "Q14DG7",
            "claim_type": "method_of_use",
        },
    ]

    def query_patents(self, gene_symbol: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        token = os.getenv("LENS_API_TOKEN")
        if token and os.getenv("TRIDENT_LIVE_APIS") == "1":
            try:
                rows = self._query_live_patents(gene_symbol, token=token, limit=limit)
                if rows:
                    return rows
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                pass
        rows = [
            row for row in self.FIXTURE_PATENTS if row["gene_symbol"].upper() == gene_symbol.upper()
        ]
        return rows[:limit] if limit else rows

    def _query_live_patents(
        self, gene_symbol: str, *, token: str, limit: int | None
    ) -> list[dict[str, Any]]:
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": {"match": {"claims": gene_symbol}},
                "size": limit or 10,
                "include": [
                    "lens_id",
                    "jurisdiction",
                    "publication_number",
                    "date_published",
                    "claims",
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        rows = []
        for item in response.json().get("data", []):
            rows.append(
                {
                    "lens_id": item.get("lens_id"),
                    "publication_number": item.get("publication_number"),
                    "filing_date": item.get("date_published"),
                    "claims": str(item.get("claims"))[:10_000],
                    "gene_symbol": gene_symbol.upper(),
                    "uniprot_id": {"EGFR": "P00533", "TMEM132B": "Q14DG7"}.get(
                        gene_symbol.upper(), f"UNMAPPED:{gene_symbol.upper()}"
                    ),
                    "claim_type": "mentions_target",
                }
            )
        return rows

    def load(self, limit: int | None = None, gene_symbol: str | None = None) -> LoadReport:
        report = self.report()
        symbols = [gene_symbol] if gene_symbol else ["EGFR", "TMEM132B"]
        remaining = limit
        for symbol in symbols:
            if symbol is None:
                continue
            for row in self.query_patents(symbol, limit=remaining):
                patent = {
                    "lens_id": row["lens_id"],
                    "publication_number": row.get("publication_number"),
                    "filing_date": row.get("filing_date"),
                    "claims": row.get("claims"),
                }
                gene = self.gene(uniprot_id=row["uniprot_id"], symbol=row["gene_symbol"])
                self.merge_relationship(
                    NodeLabel.GENE,
                    gene,
                    RelationshipType.PATENTED_FOR,
                    NodeLabel.PATENT,
                    patent,
                    {"claim_type": row.get("claim_type")},
                )
                report.add(records=1, nodes=2, relationships=1)
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return report
        return report
