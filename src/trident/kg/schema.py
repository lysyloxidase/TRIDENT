"""Neo4j node and relationship type definitions for TRIDENT KG.

Node types (from Research Report — PrimeKG + Hetionet + DRKG superset):
- Gene/Protein: UniProt ID, symbol, name, Pharos TDL level, AlphaFold pLDDT
- Disease: MONDO/EFO/DOID, name, therapeutic_area
- Drug/Compound: ChEMBL ID, DrugBank ID, SMILES, phase, mechanism
- Pathway: Reactome ID, name
- CellType: CL ontology, tissue
- Phenotype: HPO/MP
- Patent: Lens.org ID, filing_date, claims
- ClinicalTrial: NCT ID, phase, status, primary_endpoint, result

Relationship types:
- TARGETS (Drug → Gene): source, affinity_nM, mechanism
- ASSOCIATED_WITH (Gene → Disease): source, score, evidence_type
- INTERACTS_WITH (Gene → Gene): STRING combined_score, experimental
- PARTICIPATES_IN (Gene → Pathway)
- EXPRESSED_IN (Gene → CellType): GTEx TPM, specificity_tau
- ESSENTIAL_IN (Gene → CellType): DepMap CERES score
- TREATS (Drug → Disease): phase, approval_status
- HAS_TRIAL (Drug → ClinicalTrial): role (experimental/comparator)
- PREDICATION (concept → concept): SemMedDB predicate, PMID, sentence
- PATENTED_FOR (Gene → Patent): claim_type

Counts (from Research Report):
- PrimeKG: 17,080 diseases, 4,050,249 relations
- Hetionet: 47,031 nodes, 2,250,197 relationships
- DRKG: 97,238 nodes, 5,874,261 edges, 13 node types, 107 edge types
- SemMedDB: 130,480,195 predications
- DisGeNET v25.1: >12,000 compounds
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class NodeLabel(str, Enum):
    GENE = "Gene"
    DISEASE = "Disease"
    DRUG = "Drug"
    COMPOUND = "Compound"
    PATHWAY = "Pathway"
    CELL_TYPE = "CellType"
    PHENOTYPE = "Phenotype"
    PATENT = "Patent"
    CLINICAL_TRIAL = "ClinicalTrial"
    CONCEPT = "Concept"


class RelationshipType(str, Enum):
    TARGETS = "TARGETS"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    INTERACTS_WITH = "INTERACTS_WITH"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    EXPRESSED_IN = "EXPRESSED_IN"
    ESSENTIAL_IN = "ESSENTIAL_IN"
    TREATS = "TREATS"
    HAS_TRIAL = "HAS_TRIAL"
    PREDICATION = "PREDICATION"
    PATENTED_FOR = "PATENTED_FOR"
    HAS_PHENOTYPE = "HAS_PHENOTYPE"
    SIMILAR_TO = "SIMILAR_TO"


@dataclass(frozen=True)
class NodeDefinition:
    label: NodeLabel
    primary_key: str
    aliases: tuple[str, ...] = ()
    description: str = ""


NODE_DEFINITIONS: dict[NodeLabel, NodeDefinition] = {
    NodeLabel.GENE: NodeDefinition(
        NodeLabel.GENE,
        "uniprot_id",
        ("symbol", "ensembl_id", "ncbi_gene_id"),
        "Gene or protein target merged across sources by UniProt ID.",
    ),
    NodeLabel.DISEASE: NodeDefinition(
        NodeLabel.DISEASE,
        "disease_id",
        ("mondo_id", "efo_id", "doid", "mesh_id"),
        "Disease, indication, or condition.",
    ),
    NodeLabel.DRUG: NodeDefinition(
        NodeLabel.DRUG,
        "drug_id",
        ("chembl_id", "drugbank_id", "name"),
        "Approved or investigational therapeutic.",
    ),
    NodeLabel.COMPOUND: NodeDefinition(
        NodeLabel.COMPOUND,
        "compound_id",
        ("chembl_id", "drugbank_id", "smiles", "name"),
        "Chemical matter, probe, metabolite, or small molecule.",
    ),
    NodeLabel.PATHWAY: NodeDefinition(NodeLabel.PATHWAY, "pathway_id", ("name",)),
    NodeLabel.CELL_TYPE: NodeDefinition(NodeLabel.CELL_TYPE, "cell_type_id", ("name", "tissue")),
    NodeLabel.PHENOTYPE: NodeDefinition(NodeLabel.PHENOTYPE, "phenotype_id", ("name",)),
    NodeLabel.PATENT: NodeDefinition(NodeLabel.PATENT, "lens_id", ("publication_number",)),
    NodeLabel.CLINICAL_TRIAL: NodeDefinition(NodeLabel.CLINICAL_TRIAL, "nct_id", ("brief_title",)),
    NodeLabel.CONCEPT: NodeDefinition(NodeLabel.CONCEPT, "concept_id", ("name", "cui")),
}


class GraphStore(Protocol):
    """Minimal graph writer protocol used by loaders and tests."""

    def merge_node(
        self,
        label: NodeLabel | str,
        key: str,
        properties: dict[str, Any],
    ) -> Any: ...

    def merge_relationship(
        self,
        start_label: NodeLabel | str,
        start_key: str,
        start_properties: dict[str, Any],
        relationship_type: RelationshipType | str,
        end_label: NodeLabel | str,
        end_key: str,
        end_properties: dict[str, Any],
        properties: dict[str, Any] | None = None,
    ) -> Any: ...

    def close(self) -> None: ...


def clean_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Remove nulls and coerce simple containers into Neo4j-friendly values."""

    cleaned: dict[str, Any] = {}
    for key, value in (properties or {}).items():
        if value is None:
            continue
        if isinstance(value, Enum):
            cleaned[key] = value.value
        elif isinstance(value, dict):
            cleaned[key] = json.dumps(value, sort_keys=True)
        elif isinstance(value, (list, tuple, set)):
            cleaned[key] = [
                item.value if isinstance(item, Enum) else item for item in value if item is not None
            ]
        else:
            cleaned[key] = value
    return cleaned


def definition_for(label: NodeLabel | str) -> NodeDefinition:
    node_label = NodeLabel(label)
    return NODE_DEFINITIONS[node_label]


def label_value(label: NodeLabel | str) -> str:
    return NodeLabel(label).value


def rel_value(relationship_type: RelationshipType | str) -> str:
    return RelationshipType(relationship_type).value


def _safe_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"Unsafe Neo4j identifier: {identifier!r}")
    return identifier


class Neo4jGraph:
    """Small Neo4j writer tuned for idempotent biomedical graph loading."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "trident-password",
        database: str | None = None,
    ) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:  # pragma: no cover - exercised by packaging checks
            raise RuntimeError("Install the 'neo4j' package to use Neo4jGraph.") from exc

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def run(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._driver.session(database=self._database) as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

    def create_constraints(self) -> None:
        for definition in NODE_DEFINITIONS.values():
            label = _safe_identifier(definition.label.value)
            key = _safe_identifier(definition.primary_key)
            name = _safe_identifier(f"trident_{label.lower()}_{key}_unique")
            self.run(
                f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            )

    def merge_node(
        self,
        label: NodeLabel | str,
        key: str,
        properties: dict[str, Any],
    ) -> list[dict[str, Any]]:
        node_label = _safe_identifier(label_value(label))
        node_key = _safe_identifier(key)
        props = clean_properties(properties)
        if node_key not in props:
            raise ValueError(f"Missing primary key {node_key!r} for {node_label}")
        return self.run(
            f"MERGE (n:{node_label} {{{node_key}: $key_value}}) SET n += $props RETURN n",
            {"key_value": props[node_key], "props": props},
        )

    def merge_relationship(
        self,
        start_label: NodeLabel | str,
        start_key: str,
        start_properties: dict[str, Any],
        relationship_type: RelationshipType | str,
        end_label: NodeLabel | str,
        end_key: str,
        end_properties: dict[str, Any],
        properties: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        s_label = _safe_identifier(label_value(start_label))
        e_label = _safe_identifier(label_value(end_label))
        s_key = _safe_identifier(start_key)
        e_key = _safe_identifier(end_key)
        rel = _safe_identifier(rel_value(relationship_type))
        s_props = clean_properties(start_properties)
        e_props = clean_properties(end_properties)
        r_props = clean_properties(properties)
        if s_key not in s_props or e_key not in e_props:
            raise ValueError("Relationship endpoints must include their primary keys.")
        return self.run(
            (
                f"MERGE (s:{s_label} {{{s_key}: $start_value}}) SET s += $start_props "
                f"MERGE (e:{e_label} {{{e_key}: $end_value}}) SET e += $end_props "
                f"MERGE (s)-[r:{rel}]->(e) SET r += $rel_props RETURN r"
            ),
            {
                "start_value": s_props[s_key],
                "end_value": e_props[e_key],
                "start_props": s_props,
                "end_props": e_props,
                "rel_props": r_props,
            },
        )

    def stats(self) -> dict[str, int]:
        rows = self.run(
            """
            MATCH (n)
            WITH count(n) AS nodes
            MATCH ()-[r]->()
            RETURN nodes, count(r) AS relationships
            """
        )
        return rows[0] if rows else {"nodes": 0, "relationships": 0}


class InMemoryGraph:
    """Deterministic test backend implementing the same writer protocol."""

    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str, Any], dict[str, Any]] = {}
        self.relationships: dict[tuple[Any, str, Any], dict[str, Any]] = {}

    def close(self) -> None:
        return None

    def merge_node(
        self,
        label: NodeLabel | str,
        key: str,
        properties: dict[str, Any],
    ) -> tuple[str, str, Any]:
        props = clean_properties(properties)
        node_label = label_value(label)
        if key not in props:
            raise ValueError(f"Missing primary key {key!r} for {node_label}")
        node_id = (node_label, key, props[key])
        current = self.nodes.setdefault(node_id, {key: props[key]})
        current.update(props)
        return node_id

    def merge_relationship(
        self,
        start_label: NodeLabel | str,
        start_key: str,
        start_properties: dict[str, Any],
        relationship_type: RelationshipType | str,
        end_label: NodeLabel | str,
        end_key: str,
        end_properties: dict[str, Any],
        properties: dict[str, Any] | None = None,
    ) -> tuple[tuple[str, str, Any], str, tuple[str, str, Any]]:
        start_id = self.merge_node(start_label, start_key, start_properties)
        end_id = self.merge_node(end_label, end_key, end_properties)
        rel = rel_value(relationship_type)
        rel_id = (start_id, rel, end_id)
        current = self.relationships.setdefault(rel_id, {})
        current.update(clean_properties(properties))
        return rel_id

    def count_nodes(self, label: NodeLabel | str | None = None) -> int:
        if label is None:
            return len(self.nodes)
        node_label = label_value(label)
        return sum(1 for node_label_key, _, _ in self.nodes if node_label_key == node_label)

    def count_relationships(self, relationship_type: RelationshipType | str | None = None) -> int:
        if relationship_type is None:
            return len(self.relationships)
        rel = rel_value(relationship_type)
        return sum(1 for _, rel_type, _ in self.relationships if rel_type == rel)

    def find_nodes(self, label: NodeLabel | str, **properties: Any) -> list[dict[str, Any]]:
        node_label = label_value(label)
        matches: list[dict[str, Any]] = []
        for (stored_label, _, _), node in self.nodes.items():
            if stored_label != node_label:
                continue
            if all(node.get(key) == value for key, value in properties.items()):
                matches.append(node)
        return matches

    def relationship_rows(
        self,
        relationship_type: RelationshipType | str | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for (start_id, rel_type, end_id), properties in self.relationships.items():
            if relationship_type is not None and rel_type != rel_value(relationship_type):
                continue
            rows.append(
                {
                    "start": self.nodes[start_id],
                    "type": rel_type,
                    "end": self.nodes[end_id],
                    "properties": properties,
                }
            )
        return rows

    def stats(self) -> dict[str, int]:
        by_label: dict[str, int] = defaultdict(int)
        by_rel: dict[str, int] = defaultdict(int)
        for label, _, _ in self.nodes:
            by_label[label] += 1
        for _, rel, _ in self.relationships:
            by_rel[rel] += 1
        return {
            "nodes": len(self.nodes),
            "relationships": len(self.relationships),
            **{f"nodes.{label}": count for label, count in sorted(by_label.items())},
            **{f"relationships.{rel}": count for rel, count in sorted(by_rel.items())},
        }


def expected_merged_counts(loader_counts: Iterable[dict[str, int]]) -> dict[str, int]:
    """Aggregate declared source sizes for reporting and CI smoke checks."""

    totals: dict[str, int] = defaultdict(int)
    for counts in loader_counts:
        for key, value in counts.items():
            totals[key] += value
    return dict(totals)
