"""Shared loader utilities for mapping biomedical sources into TRIDENT KG."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trident.kg.schema import GraphStore, NodeLabel, RelationshipType, definition_for


@dataclass
class LoadReport:
    source: str
    records: int = 0
    nodes: int = 0
    relationships: int = 0
    errors: list[str] = field(default_factory=list)

    def add(self, *, records: int = 0, nodes: int = 0, relationships: int = 0) -> None:
        self.records += records
        self.nodes += nodes
        self.relationships += relationships


class BaseLoader:
    """Base class for idempotent Neo4j loaders."""

    source_name = "base"
    expected_nodes = 0
    expected_relationships = 0

    def __init__(
        self,
        graph: GraphStore,
        data_dir: str | Path = "data",
        batch_size: int = 1_000,
    ) -> None:
        self.graph = graph
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size

    @property
    def expected_counts(self) -> dict[str, int]:
        return {
            "nodes": self.expected_nodes,
            "relationships": self.expected_relationships,
        }

    def report(self) -> LoadReport:
        return LoadReport(source=self.source_name)

    def merge_node(self, label: NodeLabel, properties: dict[str, Any]) -> None:
        definition = definition_for(label)
        self.graph.merge_node(label, definition.primary_key, properties)

    def merge_relationship(
        self,
        start_label: NodeLabel,
        start_properties: dict[str, Any],
        relationship_type: RelationshipType,
        end_label: NodeLabel,
        end_properties: dict[str, Any],
        properties: dict[str, Any] | None = None,
    ) -> None:
        start_key = definition_for(start_label).primary_key
        end_key = definition_for(end_label).primary_key
        rel_props = {"source": self.source_name, **(properties or {})}
        self.graph.merge_relationship(
            start_label,
            start_key,
            start_properties,
            relationship_type,
            end_label,
            end_key,
            end_properties,
            rel_props,
        )

    def gene(
        self,
        *,
        uniprot_id: str | None = None,
        symbol: str | None = None,
        name: str | None = None,
        **properties: Any,
    ) -> dict[str, Any]:
        """Return a unified gene node, merging by UniProt whenever available."""

        key = uniprot_id or f"UNMAPPED:{symbol or name or 'gene'}"
        return {"uniprot_id": key, "symbol": symbol, "name": name, **properties}

    def disease(
        self,
        *,
        disease_id: str,
        name: str | None = None,
        therapeutic_area: str | None = None,
        **properties: Any,
    ) -> dict[str, Any]:
        return {
            "disease_id": disease_id,
            "name": name,
            "therapeutic_area": therapeutic_area,
            **properties,
        }

    def compound(
        self,
        *,
        compound_id: str,
        name: str | None = None,
        smiles: str | None = None,
        **properties: Any,
    ) -> dict[str, Any]:
        return {"compound_id": compound_id, "name": name, "smiles": smiles, **properties}

    def drug(
        self,
        *,
        drug_id: str,
        name: str | None = None,
        phase: str | None = None,
        mechanism: str | None = None,
        **properties: Any,
    ) -> dict[str, Any]:
        return {
            "drug_id": drug_id,
            "name": name,
            "phase": phase,
            "mechanism": mechanism,
            **properties,
        }

    def concept(
        self, *, concept_id: str, name: str, cui: str | None = None, **properties: Any
    ) -> dict[str, Any]:
        return {"concept_id": concept_id, "name": name, "cui": cui, **properties}

    def read_table(self, path: str | Path, **kwargs: Any):
        import pandas as pd

        path = Path(path)
        if path.suffix.lower() in {".tsv", ".tab"}:
            return pd.read_csv(path, sep="\t", **kwargs)
        return pd.read_csv(path, **kwargs)

    def batched(self, rows: Iterable[dict[str, Any]]) -> Iterable[list[dict[str, Any]]]:
        batch: list[dict[str, Any]] = []
        for row in rows:
            batch.append(row)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
