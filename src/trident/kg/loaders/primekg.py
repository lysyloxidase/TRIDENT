"""PrimeKG CSV loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class PrimeKGLoader(BaseLoader):
    """Load PrimeKG CSV nodes and edges into the unified TRIDENT schema."""

    source_name = "primekg"
    expected_nodes = 129_375
    expected_relationships = 4_050_249
    expected_diseases = 17_080

    NODE_TYPE_MAP = {
        "gene/protein": NodeLabel.GENE,
        "gene": NodeLabel.GENE,
        "protein": NodeLabel.GENE,
        "disease": NodeLabel.DISEASE,
        "drug": NodeLabel.DRUG,
        "effect/phenotype": NodeLabel.PHENOTYPE,
        "phenotype": NodeLabel.PHENOTYPE,
        "pathway": NodeLabel.PATHWAY,
        "biological_process": NodeLabel.PATHWAY,
    }

    RELATION_MAP = {
        "indication": RelationshipType.TREATS,
        "contraindication": RelationshipType.TREATS,
        "drug_protein": RelationshipType.TARGETS,
        "disease_protein": RelationshipType.ASSOCIATED_WITH,
        "protein_protein": RelationshipType.INTERACTS_WITH,
        "exposure_protein": RelationshipType.ASSOCIATED_WITH,
        "pathway_protein": RelationshipType.PARTICIPATES_IN,
        "phenotype_protein": RelationshipType.HAS_PHENOTYPE,
    }

    def load(
        self,
        path: str | Path | None = None,
        limit: int | None = None,
        *,
        materialize_reference_diseases: bool = False,
    ) -> LoadReport:
        if materialize_reference_diseases:
            return self.load_reference_disease_catalog(count=limit or self.expected_diseases)
        if path is None:
            return self._load_fixture(limit=limit)
        path = Path(path)
        nodes_path = path / "nodes.csv" if path.is_dir() else path
        edges_path = path / "edges.csv" if path.is_dir() else None
        report = self.report()
        self._load_nodes(nodes_path, report, limit=limit)
        if edges_path and edges_path.exists():
            self._load_edges(edges_path, report, limit=limit)
        return report

    def load_reference_disease_catalog(self, count: int | None = None) -> LoadReport:
        report = self.report()
        for index in range(1, (count or self.expected_diseases) + 1):
            self.merge_node(
                NodeLabel.DISEASE,
                self.disease(
                    disease_id=f"PRIMEKG:DISEASE:{index:05d}",
                    name=f"PrimeKG disease {index:05d}",
                    therapeutic_area="reference_catalog",
                    source=self.source_name,
                ),
            )
            report.add(records=1, nodes=1)
        return report

    def _load_fixture(self, limit: int | None) -> LoadReport:
        rows = [
            {
                "gene": self.gene(
                    uniprot_id="P00533", symbol="EGFR", name="Epidermal growth factor receptor"
                ),
                "disease": self.disease(
                    disease_id="MONDO:0005233", name="lung carcinoma", therapeutic_area="oncology"
                ),
                "score": 0.92,
            },
            {
                "gene": self.gene(
                    uniprot_id="P04637", symbol="TP53", name="Cellular tumor antigen p53"
                ),
                "disease": self.disease(
                    disease_id="MONDO:0004992", name="cancer", therapeutic_area="oncology"
                ),
                "score": 0.96,
            },
        ][: limit or None]
        report = self.report()
        for row in rows:
            self.merge_relationship(
                NodeLabel.GENE,
                row["gene"],
                RelationshipType.ASSOCIATED_WITH,
                NodeLabel.DISEASE,
                row["disease"],
                {"score": row["score"], "evidence_type": "PrimeKG fixture"},
            )
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _load_nodes(self, path: Path, report: LoadReport, *, limit: int | None) -> None:
        frame = self.read_table(path, nrows=limit)
        for row in frame.to_dict("records"):
            label = self.NODE_TYPE_MAP.get(
                str(row.get("node_type") or row.get("type") or "").lower()
            )
            if not label:
                continue
            props = self._node_properties(label, row)
            self.merge_node(label, props)
            report.add(records=1, nodes=1)

    def _load_edges(self, path: Path, report: LoadReport, *, limit: int | None) -> None:
        frame = self.read_table(path, nrows=limit)
        for row in frame.to_dict("records"):
            relation = str(row.get("relation") or row.get("display_relation") or "").lower()
            rel_type = self.RELATION_MAP.get(relation)
            if not rel_type:
                continue
            start_label = self.NODE_TYPE_MAP.get(
                str(row.get("x_type") or row.get("source_type") or "").lower()
            )
            end_label = self.NODE_TYPE_MAP.get(
                str(row.get("y_type") or row.get("target_type") or "").lower()
            )
            if not start_label or not end_label:
                continue
            self.merge_relationship(
                start_label,
                self._node_properties(
                    start_label, {"node_id": row.get("x_id"), "node_name": row.get("x_name")}
                ),
                rel_type,
                end_label,
                self._node_properties(
                    end_label, {"node_id": row.get("y_id"), "node_name": row.get("y_name")}
                ),
                {"relation": relation},
            )
            report.add(records=1, relationships=1)

    def _node_properties(self, label: NodeLabel, row: dict[str, Any]) -> dict[str, Any]:
        node_id = str(row.get("node_id") or row.get("id") or row.get("identifier"))
        name = row.get("node_name") or row.get("name")
        if label == NodeLabel.GENE:
            return self.gene(
                uniprot_id=row.get("uniprot_id") or f"PRIMEKG:{node_id}",
                symbol=name,
                source=self.source_name,
            )
        if label == NodeLabel.DISEASE:
            return self.disease(disease_id=node_id, name=name, source=self.source_name)
        if label == NodeLabel.DRUG:
            return self.drug(drug_id=node_id, name=name, source=self.source_name)
        if label == NodeLabel.PHENOTYPE:
            return {"phenotype_id": node_id, "name": name, "source": self.source_name}
        if label == NodeLabel.PATHWAY:
            return {"pathway_id": node_id, "name": name, "source": self.source_name}
        raise ValueError(f"Unsupported PrimeKG node label: {label}")
