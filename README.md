# TRIDENT

TRIDENT is a multi-agent platform for neglected-target discovery and drug design. Phase 1 establishes the Python repo, Neo4j knowledge graph schema, and biomedical source loaders that normalize evidence into a single graph.

## Phase 1 Contents

- Neo4j schema for genes, diseases, compounds, drugs, pathways, cell types, phenotypes, patents, clinical trials, and SemMedDB concepts.
- Idempotent graph writer with `MERGE`-based nodes and relationships.
- Deterministic in-memory graph backend for tests.
- Loaders for Open Targets, Pharos, PrimeKG, Hetionet, DRKG, SemMedDB, DisGeNET, ChEMBL, DrugBank, ClinicalTrials.gov, GTEx, DepMap, and Lens.org patents.
- Shared Pydantic models for target candidates, evidence traces, literature-based discovery paths, and perturbation queries.

The prompt calls this “12 data source loaders” but names 13 sources. This repo implements all named sources.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Start Neo4j:

```bash
docker compose up -d neo4j
```

Build a smoke-test graph:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=trident-password
trident-build-kg --limit 10
```

For live source APIs, set `TRIDENT_LIVE_APIS=1`. Without it, API-backed loaders use deterministic fixtures so CI and local development do not depend on external biomedical services or licensed dumps.

## Loader Notes

- Open Targets: GraphQL target-disease associations, with EGFR fixture coverage of more than 50 disease associations.
- Pharos: Target Development Level annotations, including EGFR as `Tclin` and TMEM132B as `Tdark`.
- SemMedDB: semantic predications, including the fish oil and Raynaud’s literature-based discovery example.
- PrimeKG, Hetionet, DRKG, DisGeNET, GTEx, and DepMap: file loaders for local dumps plus small fixture subsets.
- ChEMBL, ClinicalTrials.gov, and Lens.org: REST/API loaders with fixture fallbacks.
- DrugBank: XML loader for licensed exports plus fixture targets.

## Quality Gates

```bash
docker compose config
docker compose up -d neo4j
pytest
ruff check .
```

The tests cover:

- All loaders import and run on fixture subsets.
- Open Targets EGFR returns at least 50 associations.
- Pharos classifies EGFR and TMEM132B as expected.
- SemMedDB fish oil predications include `TREATS` and `AFFECTS`.
- PrimeKG can materialize the 17,080 disease reference catalog.
- UniProt IDs merge gene nodes across sources.
- Declared merged source scale exceeds 100K nodes and 5M edges.
