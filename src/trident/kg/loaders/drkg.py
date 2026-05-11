"""DRKG TSV triple loader."""

from __future__ import annotations

from pathlib import Path

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class DRKGLoader(BaseLoader):
    """Load Drug Repurposing Knowledge Graph triples into TRIDENT schema."""

    source_name = "drkg"
    expected_nodes = 97_238
    expected_relationships = 5_874_261

    RELATION_MAP = {
        "DRUGBANK::target::Compound:Gene": RelationshipType.TARGETS,
        "DGIDB::INHIBITOR::Gene:Compound": RelationshipType.TARGETS,
        "Hetionet::CtD::Compound:Disease": RelationshipType.TREATS,
        "Hetionet::DaG::Disease:Gene": RelationshipType.ASSOCIATED_WITH,
        "STRING::INTERACTS::Gene:Gene": RelationshipType.INTERACTS_WITH,
    }

    def load(self, path: str | Path | None = None, limit: int | None = None) -> LoadReport:
        if path is None:
            return self._load_fixture(limit=limit)
        frame = self.read_table(path, header=None, names=["head", "relation", "tail"], nrows=limit)
        report = self.report()
        for row in frame.to_dict("records"):
            self._merge_triple(row["head"], row["relation"], row["tail"])
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _load_fixture(self, limit: int | None) -> LoadReport:
        triples = [
            ("Compound::DB00530", "DRUGBANK::target::Compound:Gene", "Gene::EGFR"),
            ("Disease::MESH:D008175", "Hetionet::DaG::Disease:Gene", "Gene::EGFR"),
            ("Gene::EGFR", "STRING::INTERACTS::Gene:Gene", "Gene::ERBB2"),
        ][: limit or None]
        report = self.report()
        for head, relation, tail in triples:
            self._merge_triple(head, relation, tail)
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _merge_triple(self, head: str, relation: str, tail: str) -> None:
        start_label, start_props = self._entity(head)
        end_label, end_props = self._entity(tail)
        rel_type = self.RELATION_MAP.get(relation, RelationshipType.ASSOCIATED_WITH)
        if relation == "DGIDB::INHIBITOR::Gene:Compound":
            start_label, end_label = end_label, start_label
            start_props, end_props = end_props, start_props
        self.merge_relationship(
            start_label, start_props, rel_type, end_label, end_props, {"drkg_relation": relation}
        )

    def _entity(self, value: str) -> tuple[NodeLabel, dict[str, str | None]]:
        kind, _, identifier = value.partition("::")
        if kind == "Gene":
            return NodeLabel.GENE, self.gene(
                uniprot_id=self._gene_uniprot(identifier),
                symbol=identifier,
                source=self.source_name,
            )
        if kind in {"Compound", "Drug"}:
            return NodeLabel.COMPOUND, self.compound(
                compound_id=identifier, name=identifier, source=self.source_name
            )
        if kind == "Disease":
            return NodeLabel.DISEASE, self.disease(
                disease_id=identifier, name=identifier, source=self.source_name
            )
        if kind == "Pathway":
            return NodeLabel.PATHWAY, {
                "pathway_id": identifier,
                "name": identifier,
                "source": self.source_name,
            }
        return NodeLabel.CONCEPT, self.concept(
            concept_id=value, name=value, source=self.source_name
        )

    @staticmethod
    def _gene_uniprot(symbol: str) -> str:
        return {"EGFR": "P00533", "ERBB2": "P04626", "TP53": "P04637"}.get(
            symbol, f"UNMAPPED:{symbol}"
        )
