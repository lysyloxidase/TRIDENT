"""Patent mining and therapeutic white-space detection."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.fixtures import patent_documents
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node


class PatentDocument(BaseModel):
    patent_id: str
    lens_id: str | None = None
    filing_year: int
    claims: str
    source_url: str


class PatentClaimTuple(BaseModel):
    compound: str | None
    claim: str
    target: str | None
    indication: str | None
    patent_id: str
    source_url: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    legal_review_required: bool = True


class WhiteSpaceSignal(BaseModel):
    target: str
    is_white_space: bool
    open_targets_score: float
    composition_patents_last_10y: int
    active_trials: int
    rationale: str


class PatentQuery(BaseModel):
    target: str | None = None
    indication: str | None = None
    include_white_space: bool = True
    open_targets_score: float = Field(default=0.0, ge=0.0, le=1.0)
    active_trials: int = Field(default=0, ge=0)


class PatentMiningResult(ProvenanceResult):
    claims: list[PatentClaimTuple]
    white_space: WhiteSpaceSignal | None = None
    legal_review_required: bool = True


class PatentAgent:
    """Extract therapeutic claims from patent databases.

    The extraction path is intentionally conservative: all LLM-extracted tuples
    are tagged legal_review_required=True because patent claim extraction has a
    non-trivial error rate and needs expert review.
    """

    name = "patent"
    COMPOUNDS = ("gefitinib", "erlotinib", "osimertinib", "afatinib", "baricitinib")
    TARGETS = ("EGFR", "TMEM132B", "JAK1", "JAK2", "AAK1")

    def __init__(self) -> None:
        self.tools = [
            ToolDefinition("load_patents", "Load patent documents", self.load_patents),
            ToolDefinition("extract_claims", "Extract compound-target claims", self.extract_claims),
            ToolDefinition(
                "white_space", "Detect target patent white-space", self.detect_white_space
            ),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def load_patents(self, target: str | None = None) -> list[PatentDocument]:
        docs = [PatentDocument(**doc) for doc in patent_documents()]
        if target:
            target_upper = target.upper()
            docs = [doc for doc in docs if target_upper in doc.claims.upper()]
        return docs

    def extract_claims(self, patents: list[PatentDocument]) -> list[PatentClaimTuple]:
        tuples: list[PatentClaimTuple] = []
        for patent in patents:
            claim_text = patent.claims
            compounds = self._find_terms(claim_text, self.COMPOUNDS)
            targets = self._find_terms(claim_text, self.TARGETS)
            indication = self._extract_indication(claim_text)
            if not compounds and targets:
                compounds = [None]
            for compound in compounds:
                for target in targets or [None]:
                    tuples.append(
                        PatentClaimTuple(
                            compound=compound,
                            claim=claim_text,
                            target=target,
                            indication=indication,
                            patent_id=patent.patent_id,
                            source_url=patent.source_url,
                            extraction_confidence=0.84 if compound and target else 0.62,
                        )
                    )
        return tuples

    def detect_white_space(
        self,
        target: str,
        patents: list[PatentDocument],
        open_targets_score: float,
        active_trials: int,
    ) -> WhiteSpaceSignal:
        current_year = datetime.utcnow().year
        target_patents = [
            patent
            for patent in patents
            if target.upper() in patent.claims.upper() and current_year - patent.filing_year <= 10
        ]
        composition_patents = [
            patent
            for patent in target_patents
            if "composition" in patent.claims.lower() or "compound" in patent.claims.lower()
        ]
        is_white_space = (
            open_targets_score > 0.5 and len(composition_patents) == 0 and active_trials == 0
        )
        return WhiteSpaceSignal(
            target=target,
            is_white_space=is_white_space,
            open_targets_score=open_targets_score,
            composition_patents_last_10y=len(composition_patents),
            active_trials=active_trials,
            rationale=(
                "Strong genetics, no recent composition-of-matter patents, and no active trials."
                if is_white_space
                else "At least one white-space criterion was not met."
            ),
        )

    def run(self, query: PatentQuery) -> PatentMiningResult:
        patents = self.local_tool_node.call_tool("load_patents", target=query.target)
        claims = self.local_tool_node.call_tool("extract_claims", patents=patents)
        white_space = None
        if query.include_white_space and query.target:
            white_space = self.local_tool_node.call_tool(
                "white_space",
                target=query.target,
                patents=patents,
                open_targets_score=query.open_targets_score,
                active_trials=query.active_trials,
            )
        source_urls = list(dict.fromkeys(patent.source_url for patent in patents))
        return PatentMiningResult(
            claims=claims,
            white_space=white_space,
            source_urls=source_urls,
            confidence_band=confidence_band(0.74),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    @staticmethod
    def _find_terms(text: str, terms: tuple[str, ...]) -> list[str]:
        found = []
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                found.append(term if term.isupper() else term.lower())
        return found

    @staticmethod
    def _extract_indication(claim: str) -> str | None:
        match = re.search(r"(lung cancer|lung tumors|neurological indications)", claim, re.I)
        return match.group(1).lower() if match else None
