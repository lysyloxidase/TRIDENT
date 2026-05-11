"""DisGeNET TSV loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class DisGeNETLoader(BaseLoader):
    """Load DisGeNET gene-disease and variant-disease associations."""

    source_name = "disgenet"
    expected_nodes = 1_000_000
    expected_relationships = 3_000_000
    expected_compounds = 12_000

    def load(self, path: str | Path | None = None, limit: int | None = None) -> LoadReport:
        rows = (
            self._fixture_rows()[: limit or None]
            if path is None
            else self._read_rows(path, limit=limit)
        )
        report = self.report()
        for row in rows:
            gene = self.gene(
                uniprot_id=row.get("uniprot_id") or self._symbol_to_uniprot(row["gene_symbol"]),
                symbol=row["gene_symbol"],
                ncbi_gene_id=row.get("gene_id"),
            )
            disease = self.disease(
                disease_id=row["disease_id"],
                name=row.get("disease_name"),
                therapeutic_area=row.get("disease_type"),
            )
            self.merge_relationship(
                NodeLabel.GENE,
                gene,
                RelationshipType.ASSOCIATED_WITH,
                NodeLabel.DISEASE,
                disease,
                {
                    "score": float(row.get("score") or 0.0),
                    "evidence_type": row.get("source") or "DisGeNET",
                },
            )
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _read_rows(self, path: str | Path, *, limit: int | None) -> list[dict[str, Any]]:
        frame = self.read_table(path, nrows=limit)
        rename = {
            "geneSymbol": "gene_symbol",
            "geneId": "gene_id",
            "diseaseId": "disease_id",
            "diseaseName": "disease_name",
            "diseaseType": "disease_type",
            "score": "score",
            "source": "source",
        }
        frame = frame.rename(columns=rename)
        return frame.to_dict("records")

    def _fixture_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "gene_symbol": "EGFR",
                "gene_id": "1956",
                "uniprot_id": "P00533",
                "disease_id": "C0684249",
                "disease_name": "Non-small cell lung carcinoma",
                "disease_type": "neoplastic process",
                "score": 0.7,
                "source": "CURATED",
            },
            {
                "gene_symbol": "TMEM132B",
                "gene_id": "114795",
                "uniprot_id": "Q14DG7",
                "disease_id": "C0005586",
                "disease_name": "Bipolar disorder",
                "disease_type": "mental disorder",
                "score": 0.12,
                "source": "GWAS",
            },
        ]

    @staticmethod
    def _symbol_to_uniprot(symbol: str) -> str:
        return {"EGFR": "P00533", "TMEM132B": "Q14DG7", "TP53": "P04637"}.get(
            symbol, f"UNMAPPED:{symbol}"
        )
