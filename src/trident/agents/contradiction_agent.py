"""Evidence contradiction detection agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.fixtures import contradiction_records
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node


class ContradictionQuery(BaseModel):
    claim: str
    min_high_quality_papers: int = Field(default=3, ge=1, le=20)


class ContradictingEvidence(BaseModel):
    pmid: str
    title: str
    summary: str
    journal_impact: float = Field(ge=0.0)
    year: int
    source_url: str


class ContradictionResult(ProvenanceResult):
    claim: str
    contradiction_score: int = Field(ge=0, le=5)
    evidence: list[ContradictingEvidence]
    flagged: bool
    contradicting_pmids: list[str]
    rationale: str


class ContradictionAgent:
    """Detect contradicted claims in the evidence base."""

    name = "contradiction"

    def __init__(self) -> None:
        self.tools = [
            ToolDefinition("search_contradictions", "Search contradiction fixtures", self.search),
            ToolDefinition("score_contradictions", "Score contradiction strength", self.score),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def search(self, claim: str) -> list[ContradictingEvidence]:
        claim_lower = claim.lower()
        records = []
        for record in contradiction_records():
            if record["claim_area"] in claim_lower or all(
                token in claim_lower for token in record["claim_area"].split()
            ):
                records.append(
                    ContradictingEvidence(
                        pmid=record["pmid"],
                        title=record["title"],
                        summary=record["summary"],
                        journal_impact=record["journal_impact"],
                        year=record["year"],
                        source_url=record["source_url"],
                    )
                )
        return records

    def score(self, evidence: list[ContradictingEvidence]) -> int:
        if not evidence:
            return 0
        quality_points = sum(1 for item in evidence if item.journal_impact >= 7.0)
        recency_points = sum(1 for item in evidence if item.year >= 2018)
        raw = len(evidence) + 0.5 * quality_points + 0.25 * recency_points
        return max(0, min(5, round(raw)))

    def run(self, query: ContradictionQuery) -> ContradictionResult:
        evidence = self.local_tool_node.call_tool("search_contradictions", claim=query.claim)
        contradiction_score = self.local_tool_node.call_tool(
            "score_contradictions",
            evidence=evidence,
        )
        flagged = (
            contradiction_score >= 4
            and len([item for item in evidence if item.journal_impact >= 7.0])
            >= query.min_high_quality_papers
        )
        source_urls = list(dict.fromkeys(item.source_url for item in evidence))
        return ContradictionResult(
            claim=query.claim,
            contradiction_score=contradiction_score,
            evidence=evidence,
            flagged=flagged,
            contradicting_pmids=[item.pmid for item in evidence],
            rationale=(
                "Flagged because at least three high-quality papers contradict the claim."
                if flagged
                else "No strong contradiction cluster found."
            ),
            source_urls=source_urls,
            confidence_band=confidence_band(0.88 if flagged else 0.55),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )
