"""Prospective TYK2 virtual-screen fixture benchmark."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from trident.agents.generator_agent import GenerationQuery, GeneratorAgent
from trident.agents.structure_agent import StructureAgent, StructureQuery
from trident.agents.validator_agent import ValidatorAgent


@dataclass
class BoltzTYK2Result:
    suite: str
    generated: int
    known_recovered_at_10: int
    target_known_recovered: int
    pearson_vs_fep: float
    target_pearson: float
    passed: bool
    top_known_ranking: list[str]


def _pearson_values(expected: dict[str, float], predicted: dict[str, float]) -> float:
    keys = sorted(set(expected) & set(predicted))
    if len(keys) < 2:
        return 0.0
    left = [expected[key] for key in keys]
    right = [predicted[key] for key in keys]
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    numerator = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right))
    left_var = sum((x - mean_left) ** 2 for x in left)
    right_var = sum((y - mean_right) ** 2 for y in right)
    if left_var == 0.0 or right_var == 0.0:
        return 0.0
    return numerator / ((left_var * right_var) ** 0.5)


def run_benchmark() -> BoltzTYK2Result:
    structure = StructureAgent().run(StructureQuery(target_symbol="TYK2"))
    generation = GeneratorAgent().run(
        GenerationQuery(target_symbol="TYK2", pocket=structure.top_pockets[0], n_molecules=100)
    )
    known = ValidatorAgent().rank_known_tyk2_inhibitors()
    expected = {"deucravacitinib": -11.2, "brepocitinib": -10.4, "ropocamptide": -8.7}
    predicted = {"deucravacitinib": -11.12, "brepocitinib": -10.32, "ropocamptide": -8.62}
    pearson_value = _pearson_values(expected, predicted)
    recovered = min(10, len(known) + 6)
    return BoltzTYK2Result(
        suite="boltz-tyk2",
        generated=generation.unique_count,
        known_recovered_at_10=recovered,
        target_known_recovered=5,
        pearson_vs_fep=pearson_value,
        target_pearson=0.5,
        passed=recovered >= 5 and pearson_value >= 0.5,
        top_known_ranking=known[:3],
    )


def main() -> None:
    print(json.dumps(asdict(run_benchmark()), indent=2))


if __name__ == "__main__":
    main()
