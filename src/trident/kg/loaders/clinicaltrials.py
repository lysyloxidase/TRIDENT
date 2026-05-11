"""ClinicalTrials.gov / AACT loader."""

from __future__ import annotations

import os
from typing import Any

import httpx

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel, RelationshipType


class ClinicalTrialsLoader(BaseLoader):
    """Load clinical trial intervention, condition, phase, and result metadata."""

    source_name = "clinicaltrials"
    endpoint = "https://clinicaltrials.gov/api/v2/studies"
    expected_nodes = 500_000
    expected_relationships = 1_500_000

    FIXTURE_TRIALS = [
        {
            "nct_id": "NCT00101608",
            "brief_title": "Gefitinib in non-small cell lung cancer",
            "phase": "PHASE2",
            "status": "COMPLETED",
            "primary_endpoint": "Objective response rate",
            "result": "reported",
            "drug_id": "DB00317",
            "drug_name": "Gefitinib",
            "disease_id": "MONDO:0005233",
            "disease_name": "Non-small cell lung carcinoma",
        },
        {
            "nct_id": "NCT02151981",
            "brief_title": "Osimertinib for EGFR-mutated lung cancer",
            "phase": "PHASE3",
            "status": "COMPLETED",
            "primary_endpoint": "Progression-free survival",
            "result": "positive",
            "drug_id": "CHEMBL3353410",
            "drug_name": "Osimertinib",
            "disease_id": "MONDO:0005233",
            "disease_name": "Non-small cell lung carcinoma",
        },
    ]

    def query_trials(
        self, query: str = "EGFR lung cancer", *, limit: int | None = None
    ) -> list[dict[str, Any]]:
        if os.getenv("TRIDENT_LIVE_APIS") == "1":
            try:
                rows = self._query_live_trials(query, limit=limit)
                if rows:
                    return rows
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                pass
        return self.FIXTURE_TRIALS[:limit] if limit else self.FIXTURE_TRIALS

    def _query_live_trials(self, query: str, *, limit: int | None) -> list[dict[str, Any]]:
        response = httpx.get(
            self.endpoint,
            params={"query.term": query, "pageSize": limit or 10, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        rows = []
        for study in response.json().get("studies", []):
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})
            arms = protocol.get("armsInterventionsModule", {})
            conditions = protocol.get("conditionsModule", {})
            outcomes = protocol.get("outcomesModule", {})
            intervention = (arms.get("interventions") or [{}])[0]
            condition = (conditions.get("conditions") or [query])[0]
            rows.append(
                {
                    "nct_id": identification.get("nctId"),
                    "brief_title": identification.get("briefTitle"),
                    "phase": ",".join(design.get("phases") or []),
                    "status": status.get("overallStatus"),
                    "primary_endpoint": (outcomes.get("primaryOutcomes") or [{}])[0].get("measure"),
                    "result": None,
                    "drug_id": intervention.get("name"),
                    "drug_name": intervention.get("name"),
                    "disease_id": condition,
                    "disease_name": condition,
                }
            )
        return rows

    def load(self, limit: int | None = None) -> LoadReport:
        report = self.report()
        for row in self.query_trials(limit=limit):
            trial = {
                "nct_id": row["nct_id"],
                "brief_title": row.get("brief_title"),
                "phase": row.get("phase"),
                "status": row.get("status"),
                "primary_endpoint": row.get("primary_endpoint"),
                "result": row.get("result"),
            }
            drug = self.drug(
                drug_id=row["drug_id"], name=row.get("drug_name"), phase=row.get("phase")
            )
            disease = self.disease(disease_id=row["disease_id"], name=row.get("disease_name"))
            self.merge_relationship(
                NodeLabel.DRUG,
                drug,
                RelationshipType.HAS_TRIAL,
                NodeLabel.CLINICAL_TRIAL,
                trial,
                {"role": "experimental", "phase": row.get("phase"), "status": row.get("status")},
            )
            self.merge_relationship(
                NodeLabel.DRUG,
                drug,
                RelationshipType.TREATS,
                NodeLabel.DISEASE,
                disease,
                {"phase": row.get("phase"), "approval_status": None},
            )
            report.add(records=1, nodes=3, relationships=2)
        return report
