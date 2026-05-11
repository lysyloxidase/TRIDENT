"""Beat-the-mean Perturb-seq fixture benchmark."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from trident.agents.perturbation_agent import PerturbationAgent


@dataclass
class PerturbSeqResult:
    suite: str
    ensemble_pearson: float
    training_mean_pearson: float
    improvement: float
    datasets_beaten: int
    target_datasets_beaten: int
    passed: bool


def run_benchmark() -> PerturbSeqResult:
    result = PerturbationAgent().evaluate_heldout_perturbseq()
    datasets_beaten = sum(
        1
        for case in result.per_case
        if float(case["ensemble_pearson"]) > float(case["training_mean_pearson"])
    )
    return PerturbSeqResult(
        suite="perturbseq",
        ensemble_pearson=result.ensemble_pearson,
        training_mean_pearson=result.training_mean_pearson,
        improvement=result.improvement,
        datasets_beaten=datasets_beaten,
        target_datasets_beaten=1,
        passed=datasets_beaten >= 1 and result.ensemble_pearson > result.training_mean_pearson,
    )


def main() -> None:
    print(json.dumps(asdict(run_benchmark()), indent=2))


if __name__ == "__main__":
    main()
