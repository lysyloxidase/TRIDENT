"""DrugBank XML loader."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class DrugBankLoader(BaseLoader):
    """Load DrugBank XML drug-target records into TRIDENT."""

    source_name = "drugbank"
    expected_nodes = 20_000
    expected_relationships = 100_000

    def load(self, path: str | Path | None = None, limit: int | None = None) -> LoadReport:
        if path is None:
            return self._load_fixture(limit=limit)
        report = self.report()
        root = ET.parse(path).getroot()
        namespace = root.tag.split("}")[0].strip("{") if root.tag.startswith("{") else ""
        ns = {"db": namespace} if namespace else {}
        drug_path = "db:drug" if namespace else "drug"
        for drug in root.findall(drug_path, ns)[: limit or None]:
            self._merge_drug_element(drug, ns, report)
        return report

    def _load_fixture(self, limit: int | None) -> LoadReport:
        rows = [
            {
                "drugbank_id": "DB00317",
                "name": "Gefitinib",
                "target_symbol": "EGFR",
                "target_uniprot": "P00533",
                "mechanism": "Tyrosine kinase inhibitor",
                "phase": "approved",
            },
            {
                "drugbank_id": "DB00530",
                "name": "Erlotinib",
                "target_symbol": "EGFR",
                "target_uniprot": "P00533",
                "mechanism": "Tyrosine kinase inhibitor",
                "phase": "approved",
            },
        ][: limit or None]
        report = self.report()
        for row in rows:
            self.merge_relationship(
                NodeLabel.DRUG,
                self.drug(
                    drug_id=row["drugbank_id"],
                    drugbank_id=row["drugbank_id"],
                    name=row["name"],
                    phase=row["phase"],
                    mechanism=row["mechanism"],
                ),
                RelationshipType.TARGETS,
                NodeLabel.GENE,
                self.gene(uniprot_id=row["target_uniprot"], symbol=row["target_symbol"]),
                {"mechanism": row["mechanism"], "approval_status": row["phase"]},
            )
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _merge_drug_element(self, drug: ET.Element, ns: dict[str, str], report: LoadReport) -> None:
        prefix = "db:" if ns else ""
        primary_id = drug.findtext(
            f"{prefix}drugbank-id[@primary='true']", namespaces=ns
        ) or drug.findtext(f"{prefix}drugbank-id", namespaces=ns)
        name = drug.findtext(f"{prefix}name", namespaces=ns)
        groups = [
            group.text for group in drug.findall(f"{prefix}groups/{prefix}group", ns) if group.text
        ]
        for target in drug.findall(f"{prefix}targets/{prefix}target", ns):
            polypeptide = target.find(f"{prefix}polypeptide", ns)
            if polypeptide is None:
                continue
            uniprot_id = polypeptide.attrib.get("id")
            symbol = polypeptide.findtext(f"{prefix}gene-name", namespaces=ns)
            self.merge_relationship(
                NodeLabel.DRUG,
                self.drug(
                    drug_id=primary_id, drugbank_id=primary_id, name=name, phase=";".join(groups)
                ),
                RelationshipType.TARGETS,
                NodeLabel.GENE,
                self.gene(uniprot_id=uniprot_id, symbol=symbol),
                {"approval_status": ";".join(groups)},
            )
            report.add(records=1, nodes=2, relationships=1)
