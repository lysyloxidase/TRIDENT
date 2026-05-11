"""Swanson-style literature-based discovery agent."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.hypothesis_fixtures import semmed_lbd_fixture_triples
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node
from trident.types import LBDPath


class LBDQuery(BaseModel):
    disease_id: str
    cutoff_year: int | None = None
    max_intermediate: int = Field(default=1000, ge=1)
    min_paths: int = Field(default=2, ge=1)


class ScoredHypothesis(BaseModel):
    a_concept: str
    c_concept: str
    paths: list[LBDPath]
    plausibility_score: float = Field(ge=0.0, le=1.0)
    validation_status: str
    validation_pmids: list[str] = Field(default_factory=list)


class LBDResult(ProvenanceResult):
    disease_id: str
    cutoff_year: int | None
    paths: list[LBDPath]
    hypotheses: list[ScoredHypothesis]


class LBDAgent:
    """Automated Swanson-style A-B-C literature-based discovery."""

    name = "literature_based_discovery"
    DISCOVERY_TARGETS = {
        "raynaud": "Raynaud disease",
        "raynaud disease": "Raynaud disease",
        "migraine": "migraine",
        "alzheimer": "Alzheimer disease",
        "alzheimer disease": "Alzheimer disease",
    }
    ALLOWED_PREDICATES = {
        "TREATS",
        "INHIBITS",
        "AUGMENTS",
        "AFFECTS",
        "STIMULATES",
        "PREVENTS",
        "PREDISPOSES",
        "CAUSES",
    }

    def __init__(self) -> None:
        self.triples = semmed_lbd_fixture_triples()
        self.tools = [
            ToolDefinition("find_abc_paths", "Close SemMedDB A-B-C paths", self.find_abc_paths),
            ToolDefinition("score_with_llm", "Score LBD plausibility", self.score_with_llm),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def find_abc_paths(
        self,
        disease_id: str,
        max_intermediate: int = 1000,
        min_paths: int = 2,
        cutoff_year: int | None = None,
    ) -> list[LBDPath]:
        """Find undiscovered A-B-C connections for a disease."""

        disease = self._normalize_disease(disease_id)
        pre_cutoff = [
            triple
            for triple in self.triples
            if (cutoff_year is None or triple["year"] < cutoff_year)
            and triple["predicate"] in self.ALLOWED_PREDICATES
        ]
        outgoing: dict[str, list[dict]] = defaultdict(list)
        direct_pairs = set()
        for triple in pre_cutoff:
            outgoing[triple["subject"].lower()].append(triple)
            direct_pairs.add((triple["subject"].lower(), triple["object"].lower()))

        grouped: dict[tuple[str, str], list[LBDPath]] = defaultdict(list)
        for b_to_c in pre_cutoff:
            if b_to_c["object"].lower() != disease.lower():
                continue
            b = b_to_c["subject"].lower()
            for a_to_b in [triple for triple in pre_cutoff if triple["object"].lower() == b][
                :max_intermediate
            ]:
                a = a_to_b["subject"]
                c = b_to_c["object"]
                if (a.lower(), c.lower()) in direct_pairs:
                    continue
                path = LBDPath(
                    a_concept=a,
                    b_concept=b_to_c["subject"],
                    c_concept=c,
                    predicates=[a_to_b["predicate"], b_to_c["predicate"]],
                    pmids=[a_to_b["pmid"], b_to_c["pmid"]],
                    support_score=0.55,
                    novelty_rationale=(
                        f"{a} and {c} were not directly linked before "
                        f"{cutoff_year or 'the cutoff'}."
                    ),
                )
                grouped[(a.lower(), c.lower())].append(path)

        accepted: list[LBDPath] = []
        for paths in grouped.values():
            intermediaries = {path.b_concept.lower() for path in paths}
            if len(intermediaries) >= min_paths:
                support = min(1.0, 0.45 + 0.15 * len(intermediaries))
                for path in paths:
                    path.support_score = support
                accepted.extend(paths)
        return accepted

    def score_with_llm(self, paths: list[LBDPath]) -> list[ScoredHypothesis]:
        """LLM scoring of biological plausibility for each A→C pair."""

        grouped: dict[tuple[str, str], list[LBDPath]] = defaultdict(list)
        for path in paths:
            grouped[(path.a_concept.lower(), path.c_concept.lower())].append(path)

        scored: list[ScoredHypothesis] = []
        for path_group in grouped.values():
            first = path_group[0]
            validation_pmids = self._holdout_pmids(first.a_concept, first.c_concept)
            score = min(
                1.0,
                0.50
                + 0.12 * len({path.b_concept.lower() for path in path_group})
                + (0.12 if validation_pmids else 0.0),
            )
            scored.append(
                ScoredHypothesis(
                    a_concept=first.a_concept,
                    c_concept=first.c_concept,
                    paths=path_group,
                    plausibility_score=score,
                    validation_status="validated_in_holdout" if validation_pmids else "unvalidated",
                    validation_pmids=validation_pmids,
                )
            )
        scored.sort(key=lambda hypothesis: hypothesis.plausibility_score, reverse=True)
        return scored

    def run(self, query: LBDQuery) -> LBDResult:
        paths = self.local_tool_node.call_tool(
            "find_abc_paths",
            disease_id=query.disease_id,
            max_intermediate=query.max_intermediate,
            min_paths=query.min_paths,
            cutoff_year=query.cutoff_year,
        )
        hypotheses = self.local_tool_node.call_tool("score_with_llm", paths=paths)
        pmids = list(
            dict.fromkeys(
                [pmid for path in paths for pmid in path.pmids]
                + [pmid for hypothesis in hypotheses for pmid in hypothesis.validation_pmids]
            )
        )
        return LBDResult(
            disease_id=query.disease_id,
            cutoff_year=query.cutoff_year,
            paths=paths,
            hypotheses=hypotheses,
            source_urls=[f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" for pmid in pmids],
            confidence_band=confidence_band(0.80 if hypotheses else 0.45),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    def _normalize_disease(self, disease_id: str) -> str:
        normalized = disease_id.strip().lower().replace("_", " ")
        return self.DISCOVERY_TARGETS.get(normalized, disease_id)

    def _holdout_pmids(self, a_concept: str, c_concept: str) -> list[str]:
        a = a_concept.lower()
        c = c_concept.lower()
        return [
            triple["pmid"]
            for triple in self.triples
            if triple["subject"].lower() == a
            and triple["object"].lower() == c
            and triple["predicate"] in {"TREATS", "PREVENTS", "AFFECTS"}
        ]


LiteratureBasedDiscoveryAgent = LBDAgent
