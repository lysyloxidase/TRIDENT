"""DepMap essentiality loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class DepMapLoader(BaseLoader):
    """Load DepMap CRISPR CERES essentiality scores into TRIDENT."""

    source_name = "depmap"
    expected_nodes = 2_000
    expected_relationships = 1_500_000

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
                "cell_type_id": row.get("cell_line_id") or f"DEPMAP:{row['cell_line']}",
                "name": row["cell_line"],
                "tissue": row.get("lineage"),
            }
            self.merge_relationship(
                NodeLabel.GENE,
                gene,
                RelationshipType.ESSENTIAL_IN,
                NodeLabel.CELL_TYPE,
                cell_type,
                {
                    "ceres_score": float(row["ceres_score"]),
                    "dependency_probability": float(row.get("dependency_probability") or 0.0),
                },
            )
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _read_rows(self, path: str | Path, *, limit: int | None) -> list[dict[str, Any]]:
        frame = self.read_table(path, nrows=limit)
        frame = frame.rename(
            columns={
                "gene": "gene_symbol",
                "cell_line": "cell_line",
                "lineage": "lineage",
                "CERES": "ceres_score",
                "dependency": "dependency_probability",
            }
        )
        return frame.to_dict("records")

    def _fixture_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "gene_symbol": "EGFR",
                "uniprot_id": "P00533",
                "cell_line_id": "ACH-000769",
                "cell_line": "HCC827",
                "lineage": "lung",
                "ceres_score": -1.31,
                "dependency_probability": 0.96,
            },
            {
                "gene_symbol": "TMEM132B",
                "uniprot_id": "Q14DG7",
                "cell_line_id": "ACH-000001",
                "cell_line": "NIHOVCAR3",
                "lineage": "ovary",
                "ceres_score": -0.08,
                "dependency_probability": 0.12,
            },
        ]

    @staticmethod
    def _symbol_to_uniprot(symbol: str) -> str:
        return {"EGFR": "P00533", "TMEM132B": "Q14DG7"}.get(symbol, f"UNMAPPED:{symbol}")
