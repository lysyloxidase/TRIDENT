"""Master graph builder for TRIDENT Phase 1."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from trident.kg.loaders import LOADER_CLASSES
from trident.kg.loaders.base import LoadReport
from trident.kg.schema import Neo4jGraph, expected_merged_counts


def build_graph(
    data_dir: str | Path = "data",
    loader_names: list[str] | None = None,
    limit: int | None = None,
) -> list[LoadReport]:
    graph = Neo4jGraph(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "trident-password"),
        database=os.getenv("NEO4J_DATABASE") or None,
    )
    graph.create_constraints()
    try:
        selected = loader_names or list(LOADER_CLASSES)
        reports: list[LoadReport] = []
        for name in selected:
            loader_cls = LOADER_CLASSES[name]
            loader = loader_cls(graph=graph, data_dir=data_dir)
            reports.append(loader.load(limit=limit))
        return reports
    finally:
        graph.close()


def declared_source_counts() -> dict[str, int]:
    return expected_merged_counts(
        loader_cls(graph=None).expected_counts for loader_cls in LOADER_CLASSES.values()
    )  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the TRIDENT Neo4j knowledge graph.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument(
        "--loader",
        action="append",
        choices=sorted(LOADER_CLASSES),
        help="Run one loader. Repeatable.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Optional per-loader record cap for smoke tests."
    )
    args = parser.parse_args(argv)

    reports = build_graph(data_dir=args.data_dir, loader_names=args.loader, limit=args.limit)
    for report in reports:
        status = "ok" if not report.errors else f"errors={len(report.errors)}"
        print(
            f"{report.source}: {status}, records={report.records}, "
            f"nodes={report.nodes}, relationships={report.relationships}"
        )


if __name__ == "__main__":
    main()
