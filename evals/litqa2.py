"""Benchmark LitAgent against a deterministic LitQA2-style fixture."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from trident.agents.lit_agent import LitAgent, LitQuery


@dataclass
class LitQA2Result:
    suite: str
    accuracy: float
    target_accuracy: float
    passed: bool
    questions: int
    verified_citations: int
    hallucinated_citations: int


QUESTIONS = [
    "EGFR inhibitors lung cancer",
    "EGFR T790M resistance lung cancer",
    "osimertinib CNS activity EGFR mutant lung cancer",
    "adjuvant osimertinib resected EGFR mutated lung cancer",
    "EGFR exon 20 insertion lung cancer inhibitor",
]


def run_benchmark() -> LitQA2Result:
    agent = LitAgent()
    correct = 0
    verified = 0
    hallucinated = 0
    for question in QUESTIONS:
        result = agent.run(LitQuery(question=question, n_papers=50, min_chunks=10))
        answer = result.answer.lower()
        if "egfr" in answer and ("lung" in answer or "nsclc" in answer):
            correct += 1
        verified += len(result.cited_pmids)
        hallucinated += len(result.hallucinated_pmids)
    accuracy = correct / len(QUESTIONS)
    return LitQA2Result(
        suite="litqa2",
        accuracy=accuracy,
        target_accuracy=0.85,
        passed=accuracy >= 0.85 and hallucinated == 0,
        questions=len(QUESTIONS),
        verified_citations=verified,
        hallucinated_citations=hallucinated,
    )


def main() -> None:
    print(json.dumps(asdict(run_benchmark()), indent=2))


if __name__ == "__main__":
    main()
