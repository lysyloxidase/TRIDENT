"""GTEx expression data loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class GTExLoader(BaseLoader):
    """Load GTEx tissue expression data as Gene EXPRESSED_IN CellType edges."""

    source_name = "gtex"
    expected_nodes = 20_000
    expected_relationships = 1_000_000

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
            )
            cell_type = {
                "cell_type_id": row.get("cell_type_id")
                or f"GTEX:{row['tissue'].replace(' ', '_')}",
                "name": row.get("cell_type") or row["tissue"],
                "tissue": row["tissue"],
            }
            self.merge_relationship(
                NodeLabel.GENE,
                gene,
                RelationshipType.EXPRESSED_IN,
                NodeLabel.CELL_TYPE,
                cell_type,
                {
                    "tpm": float(row["tpm"]),
                    "specificity_tau": float(row.get("specificity_tau") or 0.0),
                },
            )
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _read_rows(self, path: str | Path, *, limit: int | None) -> list[dict[str, Any]]:
        frame = self.read_table(path, nrows=limit)
        frame = frame.rename(
            columns={
                "gene": "gene_symbol",
                "SMTSD": "tissue",
                "TPM": "tpm",
                "tau": "specificity_tau",
            }
        )
        return frame.to_dict("records")

    def _fixture_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "gene_symbol": "EGFR",
                "uniprot_id": "P00533",
                "tissue": "Lung",
                "tpm": 38.2,
                "specificity_tau": 0.41,
            },
            {
                "gene_symbol": "TMEM132B",
                "uniprot_id": "Q14DG7",
                "tissue": "Brain cortex",
                "tpm": 12.7,
                "specificity_tau": 0.78,
            },
        ]

    @staticmethod
    def _symbol_to_uniprot(symbol: str) -> str:
        return {"EGFR": "P00533", "TMEM132B": "Q14DG7"}.get(symbol, f"UNMAPPED:{symbol}")
