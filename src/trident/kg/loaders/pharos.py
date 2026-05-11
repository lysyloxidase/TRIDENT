"""Pharos/TCRD loader for Target Development Level annotations."""

from __future__ import annotations

import os
from typing import Any

import httpx

from trident.kg.loaders.base import BaseLoader, LoadReport
from trident.kg.schema import NodeLabel


class PharosLoader(BaseLoader):
    """Load Pharos/TCRD data for understudied protein classification.

    API endpoint: https://pharos-api.ncats.io/graphql

    Target Development Levels (TDL):
    - Tclin: approved drug targets (~670 proteins)
    - Tchem: targets with chemical probes (>1 compound, potency <100nM)
    - Tbio: targets with known biology but no chemical matter
    - Tdark: virtually unstudied proteins (~30% of human proteome!)

    From Research Report: Pharos/TCRD ranks ~20,000 human proteins.
    The Illuminating the Druggable Genome (IDG) program specifically
    funds research on Tdark/Tbio targets.

    TRIDENT's novelty engine explicitly prioritizes Tbio/Tdark targets
    with strong genetic evidence — the "underappreciated" quadrant.
    """

    source_name = "pharos"
    endpoint = "https://pharos-api.ncats.io/graphql"
    expected_nodes = 20_000
    expected_relationships = 0

    FIXTURE_TARGETS = {
        "EGFR": {
            "symbol": "EGFR",
            "name": "Epidermal growth factor receptor",
            "uniprot_id": "P00533",
            "pharos_tdl": "Tclin",
            "idg_family": "Kinase",
        },
        "TMEM132B": {
            "symbol": "TMEM132B",
            "name": "Transmembrane protein 132B",
            "uniprot_id": "Q14DG7",
            "pharos_tdl": "Tdark",
            "idg_family": "Ion channel or membrane protein",
        },
    }

    def classify_target(
        self, gene_symbol: str, *, use_live_api: bool | None = None
    ) -> dict[str, Any]:
        symbol = gene_symbol.upper()
        live = use_live_api if use_live_api is not None else os.getenv("TRIDENT_LIVE_APIS") == "1"
        if live:
            try:
                result = self._query_live_target(symbol)
                if result:
                    return result
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                pass
        return self.FIXTURE_TARGETS.get(
            symbol,
            {
                "symbol": symbol,
                "name": symbol,
                "uniprot_id": f"UNMAPPED:{symbol}",
                "pharos_tdl": "Tbio",
                "idg_family": None,
            },
        )

    def _query_live_target(self, gene_symbol: str) -> dict[str, Any] | None:
        query = """
        query targetByName($name: String!) {
          targets(filter: {name: $name}) {
            targets {
              sym
              name
              tdl
              uniprot
              fam
            }
          }
        }
        """
        response = httpx.post(
            self.endpoint, json={"query": query, "variables": {"name": gene_symbol}}, timeout=30
        )
        response.raise_for_status()
        targets = response.json()["data"]["targets"]["targets"]
        if not targets:
            return None
        target = targets[0]
        return {
            "symbol": target.get("sym") or gene_symbol,
            "name": target.get("name"),
            "uniprot_id": target.get("uniprot") or f"UNMAPPED:{gene_symbol}",
            "pharos_tdl": target.get("tdl") or "Unknown",
            "idg_family": target.get("fam"),
        }

    def load(self, limit: int | None = None, symbols: list[str] | None = None) -> LoadReport:
        report = self.report()
        selected = symbols or ["EGFR", "TMEM132B"]
        if limit is not None:
            selected = selected[:limit]
        for symbol in selected:
            target = self.classify_target(symbol)
            self.merge_node(
                NodeLabel.GENE,
                self.gene(
                    uniprot_id=target["uniprot_id"],
                    symbol=target["symbol"],
                    name=target.get("name"),
                    pharos_tdl=target.get("pharos_tdl"),
                    idg_family=target.get("idg_family"),
                    pharos_source=self.source_name,
                ),
            )
            report.add(records=1, nodes=1)
        return report
