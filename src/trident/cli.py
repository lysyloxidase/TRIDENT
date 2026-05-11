"""Command line interface for TRIDENT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from trident.agents.generator_agent import GenerationQuery, GeneratorAgent
from trident.agents.lit_agent import LitAgent
from trident.agents.orchestrator import (
    ReportWriter,
    TridentOrchestrator,
    state_to_json,
)
from trident.agents.perturbation_agent import PerturbationAgent, PerturbationQuery
from trident.agents.structure_agent import StructureAgent, StructureQuery
from trident.agents.validator_agent import ValidationQuery, ValidatorAgent
from trident.models.perturbation_fixtures import SOTORASIB_SMILES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trident", description="TRIDENT discovery platform CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="Full disease to target/molecule pipeline")
    run.add_argument("--disease", required=True)
    run.add_argument("--n-targets", type=int, default=5)
    run.add_argument("--design", action="store_true")
    run.add_argument("--format", choices=["json", "markdown"], default="json")

    discover = subcommands.add_parser("discover", help="Target discovery only")
    discover.add_argument("--disease", required=True)
    discover.add_argument("--n-targets", type=int, default=10)
    discover.add_argument("--format", choices=["json", "markdown"], default="json")

    design = subcommands.add_parser("design", help="Design molecules for a known target")
    design.add_argument("--target", required=True)
    design.add_argument("--uniprot")
    design.add_argument("--n-molecules", type=int, default=50)

    perturb = subcommands.add_parser("perturb", help="Predict perturbation response")
    perturb.add_argument("--drug", required=True)
    perturb.add_argument("--h5ad", required=True)
    perturb.add_argument("--cell-type", required=True)
    perturb.add_argument("--target-gene", default="KRAS")
    perturb.add_argument("--dose-uM", type=float, default=1.0)
    perturb.add_argument("--time-hours", type=float, default=24.0)

    search = subcommands.add_parser("search", help="Literature search only")
    search.add_argument("--query", required=True)
    search.add_argument("--n-papers", type=int, default=50)

    evaluate = subcommands.add_parser("eval", help="Evaluate a benchmark suite")
    evaluate.add_argument(
        "--suite",
        required=True,
        choices=["litqa2", "lbd-replication", "boltz-tyk2", "perturbseq"],
    )

    export = subcommands.add_parser("export", help="Export fixture report/results")
    export.add_argument("--format", choices=["pdf", "json", "markdown"], required=True)
    export.add_argument("--output", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        state = TridentOrchestrator().run(
            disease=args.disease,
            n_targets=args.n_targets,
            design=args.design,
        )
        print(state.report if args.format == "markdown" else state_to_json(state))
        return 0
    if args.command == "discover":
        state = TridentOrchestrator().discover(disease=args.disease, n_targets=args.n_targets)
        print(state.report if args.format == "markdown" else state_to_json(state))
        return 0
    if args.command == "design":
        print(json.dumps(run_design(args.target, args.n_molecules), indent=2, default=str))
        return 0
    if args.command == "perturb":
        result = PerturbationAgent().run(
            PerturbationQuery(
                drug_smiles=args.drug,
                patient_h5ad_path=args.h5ad,
                target_cell_type=args.cell_type,
                target_gene=args.target_gene,
                dose_uM=args.dose_uM,
                time_hours=args.time_hours,
            )
        )
        print(json.dumps(result.model_dump(), indent=2, default=str))
        return 0
    if args.command == "search":
        papers = LitAgent().search(args.query, n_papers=args.n_papers)
        print(json.dumps([paper.model_dump() for paper in papers], indent=2, default=str))
        return 0
    if args.command == "eval":
        print(json.dumps(run_eval(args.suite), indent=2, default=str))
        return 0
    if args.command == "export":
        export_fixture(args.format, Path(args.output))
        print(json.dumps({"output": args.output, "format": args.format}, indent=2))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


def run_design(target: str, n_molecules: int) -> dict[str, Any]:
    structure = StructureAgent().run(StructureQuery(target_symbol=target))
    generation = GeneratorAgent().run(
        GenerationQuery(
            target_symbol=target,
            pocket=structure.top_pockets[0],
            n_molecules=max(10, n_molecules),
        )
    )
    validation = ValidatorAgent().run(
        ValidationQuery(
            target_symbol=target,
            pocket=structure.top_pockets[0],
            molecules=generation.molecules,
            top_k_abfe=min(10, max(1, n_molecules)),
        )
    )
    return {
        "target": target,
        "structure": structure.model_dump(),
        "generation": generation.model_dump(),
        "validation": validation.model_dump(),
    }


def run_eval(suite: str) -> dict[str, Any]:
    if suite == "perturbseq":
        from evals.perturbseq_bench import run_benchmark

        return run_benchmark().__dict__
    if suite == "boltz-tyk2":
        from evals.boltz_tyk2 import run_benchmark

        return run_benchmark().__dict__
    if suite == "lbd-replication":
        from evals.lbd_replication import run_benchmark

        return run_benchmark().__dict__
    if suite == "litqa2":
        from evals.litqa2 import run_benchmark

        return run_benchmark().__dict__
    raise ValueError(f"Unknown eval suite: {suite}")


def export_fixture(format_name: str, output: Path) -> None:
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=5,
        design=format_name != "json",
    )
    if format_name == "json":
        output.write_text(state_to_json(state))
    else:
        output.write_text(state.report or ReportWriter().generate(state))


def default_sotorasib_args() -> list[str]:
    return [
        "perturb",
        "--drug",
        SOTORASIB_SMILES,
        "--h5ad",
        "lung_adenocarcinoma_h5ad",
        "--cell-type",
        "tumor_epithelial",
        "--target-gene",
        "KRAS",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
