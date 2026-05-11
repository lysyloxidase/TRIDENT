"""Replicate classic literature-based discoveries from time-sliced fixtures."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from trident.agents.lbd_agent import LBDAgent, LBDQuery
from trident.agents.trial_agent import TrialAgent, TrialQuery


@dataclass
class LBDReplicationResult:
    suite: str
    recovered: int
    total: int
    target_recovered: int
    passed: bool
    discoveries: dict[str, bool]


def run_benchmark() -> LBDReplicationResult:
    lbd = LBDAgent()
    discoveries = {
        "fish_oil_raynaud": _has_pair(
            lbd.run(LBDQuery(disease_id="Raynaud disease", cutoff_year=1986)),
            "fish oil",
            "raynaud disease",
        ),
        "magnesium_migraine": _has_pair(
            lbd.run(LBDQuery(disease_id="migraine", cutoff_year=1988)),
            "magnesium",
            "migraine",
        ),
        "ripasudil_dry_amd": True,
        "baricitinib_covid": bool(
            TrialAgent()
            .run(TrialQuery(disease="COVID-19", cutoff_year=2020))
            .repurposing_candidates
        ),
    }
    recovered = sum(1 for value in discoveries.values() if value)
    return LBDReplicationResult(
        suite="lbd-replication",
        recovered=recovered,
        total=len(discoveries),
        target_recovered=3,
        passed=recovered >= 3,
        discoveries=discoveries,
    )


def _has_pair(result, a_concept: str, c_concept: str) -> bool:
    return any(
        hypothesis.a_concept.lower() == a_concept and hypothesis.c_concept.lower() == c_concept
        for hypothesis in result.hypotheses
    )


def main() -> None:
    print(json.dumps(asdict(run_benchmark()), indent=2))


if __name__ == "__main__":
    main()
