"""SemMedDB semantic predication loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class SemMedDBLoader(BaseLoader):
    """Load SemMedDB semantic predications for Literature-Based Discovery.

    Source: semmedVER43_2024_R — 130,480,195 predications from PubMed
    Extracted by SemRep NLP tool from UMLS Metathesaurus concepts.

    Each predication: (Subject, Predicate, Object, PMID, Sentence)
    Key predicates for LBD: TREATS, INHIBITS, AUGMENTS, CAUSES,
    PREVENTS, PREDISPOSES, AFFECTS, STIMULATES, DISRUPTS

    Swanson's ABC model (1986):
    - If literature says A→B (e.g., "fish oil reduces blood viscosity")
    - And literature says B→C (e.g., "blood viscosity linked to Raynaud's")
    - Then A→C may be undiscovered (fish oil → treats Raynaud's)
    - This was CONFIRMED experimentally after Swanson's prediction!

    TRIDENT uses SemMedDB as the substrate for automated LBD with
    LLM-augmented scoring of candidate A→C pairs.
    """

    source_name = "semmeddb"
    expected_nodes = 30_000_000
    expected_relationships = 130_480_195

    KEY_PREDICATES = {
        "TREATS",
        "INHIBITS",
        "AUGMENTS",
        "CAUSES",
        "PREVENTS",
        "PREDISPOSES",
        "AFFECTS",
        "STIMULATES",
        "DISRUPTS",
        "ASSOCIATED_WITH",
    }

    FIXTURE_PREDICATIONS = [
        {
            "subject_id": "C0016157",
            "subject_name": "Fish Oils",
            "predicate": "AFFECTS",
            "object_id": "C0005847",
            "object_name": "Blood Viscosity",
            "pmid": "7201675",
            "sentence": "Dietary fish oil affects blood viscosity and platelet aggregation.",
        },
        {
            "subject_id": "C0005847",
            "subject_name": "Blood Viscosity",
            "predicate": "AFFECTS",
            "object_id": "C0034734",
            "object_name": "Raynaud Disease",
            "pmid": "6338748",
            "sentence": "Blood viscosity affects symptoms observed in Raynaud disease.",
        },
        {
            "subject_id": "C0016157",
            "subject_name": "Fish Oils",
            "predicate": "TREATS",
            "object_id": "C0034734",
            "object_name": "Raynaud Disease",
            "pmid": "3943917",
            "sentence": (
                "Fish oil supplementation was investigated as a treatment for Raynaud disease."
            ),
        },
    ]

    def predications_for(self, term: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        needle = term.lower()
        matches = [
            row
            for row in self.FIXTURE_PREDICATIONS
            if needle in row["subject_name"].lower() or needle in row["object_name"].lower()
        ]
        return matches[:limit] if limit is not None else matches

    def load(self, path: str | Path | None = None, limit: int | None = None) -> LoadReport:
        report = self.report()
        rows = (
            self._read_predications(path, limit=limit)
            if path
            else self.FIXTURE_PREDICATIONS[: limit or None]
        )
        for row in rows:
            self._merge_predication(row)
            report.add(records=1, nodes=2, relationships=1)
        return report

    def _read_predications(self, path: str | Path, *, limit: int | None) -> list[dict[str, Any]]:
        frame = self.read_table(path, nrows=limit)
        rename = {
            "SUBJECT_CUI": "subject_id",
            "SUBJECT_NAME": "subject_name",
            "PREDICATE": "predicate",
            "OBJECT_CUI": "object_id",
            "OBJECT_NAME": "object_name",
            "PMID": "pmid",
            "SENTENCE": "sentence",
        }
        frame = frame.rename(columns=rename)
        required = ["subject_id", "subject_name", "predicate", "object_id", "object_name"]
        return frame[
            required + [column for column in ["pmid", "sentence"] if column in frame.columns]
        ].to_dict("records")

    def _merge_predication(self, row: dict[str, Any]) -> None:
        subject = self.concept(
            concept_id=row["subject_id"], name=row["subject_name"], cui=row["subject_id"]
        )
        obj = self.concept(
            concept_id=row["object_id"], name=row["object_name"], cui=row["object_id"]
        )
        self.merge_relationship(
            NodeLabel.CONCEPT,
            subject,
            RelationshipType.PREDICATION,
            NodeLabel.CONCEPT,
            obj,
            {
                "predicate": str(row["predicate"]).upper(),
                "pmid": str(row.get("pmid")) if row.get("pmid") is not None else None,
                "sentence": row.get("sentence"),
            },
        )
