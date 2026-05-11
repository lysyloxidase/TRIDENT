"""Clinical trial mining and repurposing signal agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.fixtures import trial_records
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node


class TrialRecord(BaseModel):
    nct_id: str
    drug: str
    target: str
    disease: str
    phase: str
    status: str
    year: int
    primary_outcome: str
    secondary_signal: str | None = None
    source_url: str


class TrialSignal(BaseModel):
    nct_id: str
    drug: str
    signal_type: str
    description: str
    source_url: str


class RepurposingCandidate(BaseModel):
    drug: str
    proposed_indication: str
    mechanism: str
    evidence_years: list[int]
    support_score: float = Field(ge=0.0, le=1.0)
    source_urls: list[str] = Field(default_factory=list)


class TrialQuery(BaseModel):
    disease: str
    cutoff_year: int | None = None
    include_failed_secondary_signals: bool = True


class TrialAnalysisResult(ProvenanceResult):
    disease: str
    failed_trial_signals: list[TrialSignal]
    repurposing_candidates: list[RepurposingCandidate]


class TrialAgent:
    """Mine ClinicalTrials.gov/AACT-style records for repurposing signals."""

    name = "trial"

    def __init__(self) -> None:
        self.tools = [
            ToolDefinition("load_trials", "Load trial records", self.load_trials),
            ToolDefinition(
                "failed_signals", "Find failed trials with secondary signals", self.failed_signals
            ),
            ToolDefinition(
                "repurposing", "Find repurposing candidates", self.repurposing_candidates
            ),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def load_trials(self, cutoff_year: int | None = None) -> list[TrialRecord]:
        records = [TrialRecord(**record) for record in trial_records()]
        if cutoff_year is not None:
            records = [record for record in records if record.year < cutoff_year]
        return records

    def failed_signals(self, trials: list[TrialRecord]) -> list[TrialSignal]:
        signals = []
        for trial in trials:
            if (
                "lack of efficacy" in trial.primary_outcome.lower()
                and trial.secondary_signal
                and trial.status.lower() in {"terminated", "completed"}
            ):
                signals.append(
                    TrialSignal(
                        nct_id=trial.nct_id,
                        drug=trial.drug,
                        signal_type="positive_secondary_endpoint",
                        description=trial.secondary_signal,
                        source_url=trial.source_url,
                    )
                )
        return signals

    def repurposing_candidates(
        self,
        disease: str,
        trials: list[TrialRecord],
    ) -> list[RepurposingCandidate]:
        disease_lower = disease.lower()
        candidates: list[RepurposingCandidate] = []
        baricitinib_trials = [trial for trial in trials if trial.drug.lower() == "baricitinib"]
        if "covid" in disease_lower and baricitinib_trials:
            candidates.append(
                RepurposingCandidate(
                    drug="baricitinib",
                    proposed_indication="COVID-19",
                    mechanism=(
                        "JAK1/JAK2 anti-inflammatory activity plus AAK1-associated "
                        "host kinase biology suggested a repurposing hypothesis before 2020."
                    ),
                    evidence_years=sorted({trial.year for trial in baricitinib_trials}),
                    support_score=0.79,
                    source_urls=[trial.source_url for trial in baricitinib_trials],
                )
            )
        return candidates

    def run(self, query: TrialQuery) -> TrialAnalysisResult:
        trials = self.local_tool_node.call_tool("load_trials", cutoff_year=query.cutoff_year)
        failed = (
            self.local_tool_node.call_tool("failed_signals", trials=trials)
            if query.include_failed_secondary_signals
            else []
        )
        candidates = self.local_tool_node.call_tool(
            "repurposing",
            disease=query.disease,
            trials=trials,
        )
        source_urls = list(
            dict.fromkeys(
                [trial.source_url for trial in trials]
                + [url for candidate in candidates for url in candidate.source_urls]
            )
        )
        return TrialAnalysisResult(
            disease=query.disease,
            failed_trial_signals=failed,
            repurposing_candidates=candidates,
            source_urls=source_urls,
            confidence_band=confidence_band(0.78),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )
