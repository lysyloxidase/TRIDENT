"""Hetionet JSON loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class HetionetLoader(BaseLoader):
    """Load Hetionet JSON nodes and edges into TRIDENT's unified schema."""

    source_name = "hetionet"
    expected_nodes = 47_031
    expected_relationships = 2_250_197

    KIND_MAP = {
        "Gene": NodeLabel.GENE,
        "Disease": NodeLabel.DISEASE,
        "Compound": NodeLabel.COMPOUND,
        "Pathway": NodeLabel.PATHWAY,
        "Side Effect": NodeLabel.PHENOTYPE,
        "Symptom": NodeLabel.PHENOTYPE,
        "Anatomy": NodeLabel.CELL_TYPE,
    }

    EDGE_MAP = {
        "ASSOCIATES": RelationshipType.ASSOCIATED_WITH,
        "BINDS": RelationshipType.TARGETS,
        "TREATS": RelationshipType.TREATS,
        "INTERACTS": RelationshipType.INTERACTS_WITH,
        "PARTICIPATES": RelationshipType.PARTICIPATES_IN,
        "EXPRESSES": RelationshipType.EXPRESSED_IN,
    }

    def load(self, path: str | Path | None = None, limit: int | None = None) -> LoadReport:
        if path is None:
            return self._load_fixture(limit=limit)
        report = self.report()
        with Path(path).open() as handle:
            payload = json.load(handle)
        for node in (payload.get("nodes") or [])[: limit or None]:
            label = self.KIND_MAP.get(node.get("kind"))
            if label:
                self.merge_node(label, self._node_props(label, node))
                report.add(records=1, nodes=1)
        for edge in (payload.get("edges") or [])[: limit or None]:
            rel_type = self.EDGE_MAP.get(edge.get("kind") or edge.get("metaedge"))
            if rel_type:
                start = edge["source"]
                end = edge["target"]
                start_label = self.KIND_MAP.get(start.get("kind"))
                end_label = self.KIND_MAP.get(end.get("kind"))
                if start_label and end_label:
                    self.merge_relationship(
                        start_label,
                        self._node_props(start_label, start),
                        rel_type,
                        end_label,
                        self._node_props(end_label, end),
                        {"metaedge": edge.get("kind") or edge.get("metaedge")},
                    )
                    report.add(records=1, relationships=1)
        return report

    def _load_fixture(self, limit: int | None) -> LoadReport:
        rows = [
            (
                NodeLabel.COMPOUND,
                self.compound(compound_id="DB:gefitinib", name="Gefitinib"),
                RelationshipType.TARGETS,
                NodeLabel.GENE,
                self.gene(uniprot_id="P00533", symbol="EGFR"),
                {"mechanism": "inhibitor"},
            ),
            (
                NodeLabel.GENE,
                self.gene(uniprot_id="P00533", symbol="EGFR"),
                RelationshipType.ASSOCIATED_WITH,
                NodeLabel.DISEASE,
                self.disease(
                    disease_id="DOID:3908", name="lung cancer", therapeutic_area="oncology"
                ),
                {"score": 0.8},
            ),
        ][: limit or None]
        report = self.report()
        for start_label, start, rel_type, end_label, end, props in rows:
            self.merge_relationship(start_label, start, rel_type, end_label, end, props)
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _node_props(self, label: NodeLabel, node: dict[str, Any]) -> dict[str, Any]:
        identifier = str(node.get("identifier") or node.get("id"))
        name = node.get("name")
        if label == NodeLabel.GENE:
            return self.gene(
                uniprot_id=node.get("uniprot_id") or f"HETIONET:{identifier}",
                symbol=name,
                source=self.source_name,
            )
        if label == NodeLabel.DISEASE:
            return self.disease(disease_id=identifier, name=name, source=self.source_name)
        if label == NodeLabel.COMPOUND:
            return self.compound(compound_id=identifier, name=name, source=self.source_name)
        if label == NodeLabel.PATHWAY:
            return {"pathway_id": identifier, "name": name, "source": self.source_name}
        if label == NodeLabel.PHENOTYPE:
            return {"phenotype_id": identifier, "name": name, "source": self.source_name}
        if label == NodeLabel.CELL_TYPE:
            return {"cell_type_id": identifier, "name": name, "source": self.source_name}
        raise ValueError(f"Unsupported Hetionet node label: {label}")
