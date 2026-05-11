from trident.kg.loaders import LOADER_CLASSES
from trident.kg.loaders.opentargets import OpenTargetsLoader
from trident.kg.loaders.pharos import PharosLoader
from trident.kg.loaders.primekg import PrimeKGLoader
from trident.kg.loaders.semmeddb import SemMedDBLoader
from trident.kg.schema import InMemoryGraph, NodeLabel, RelationshipType, expected_merged_counts


def test_all_named_loaders_import_and_run_on_test_subsets():
    assert len(LOADER_CLASSES) == 13
    for loader_cls in LOADER_CLASSES.values():
        graph = InMemoryGraph()
        report = loader_cls(graph=graph).load(limit=1)
        assert report.errors == []
        assert report.records >= 1


def test_opentargets_egfr_returns_at_least_50_disease_associations():
    loader = OpenTargetsLoader(graph=InMemoryGraph())
    rows = loader.query_target_disease_associations("EGFR")
    assert len(rows) >= 50
    assert all(row["gene_symbol"] == "EGFR" for row in rows)


def test_pharos_classifies_reference_targets():
    loader = PharosLoader(graph=InMemoryGraph())
    assert loader.classify_target("EGFR")["pharos_tdl"] == "Tclin"
    assert loader.classify_target("TMEM132B")["pharos_tdl"] == "Tdark"


def test_semmeddb_fish_oil_fixture_contains_treats_and_affects_predications():
    loader = SemMedDBLoader(graph=InMemoryGraph())
    predicates = {row["predicate"] for row in loader.predications_for("fish oil")}
    assert {"TREATS", "AFFECTS"} <= predicates


def test_primekg_reference_catalog_materializes_17080_diseases():
    graph = InMemoryGraph()
    report = PrimeKGLoader(graph=graph).load(materialize_reference_diseases=True)
    assert report.nodes >= 17_000
    assert graph.count_nodes(NodeLabel.DISEASE) == 17_080


def test_cross_source_gene_nodes_merge_by_uniprot_id():
    graph = InMemoryGraph()
    OpenTargetsLoader(graph=graph).load(limit=1, gene_symbol="EGFR")
    PharosLoader(graph=graph).load(symbols=["EGFR"])

    genes = graph.find_nodes(NodeLabel.GENE, uniprot_id="P00533")
    assert len(genes) == 1
    assert genes[0]["symbol"] == "EGFR"
    assert genes[0]["pharos_tdl"] == "Tclin"


def test_declared_kg_stats_exceed_phase1_scale_gates():
    counts = expected_merged_counts(
        loader_cls(graph=InMemoryGraph()).expected_counts for loader_cls in LOADER_CLASSES.values()
    )
    assert counts["nodes"] > 100_000
    assert counts["relationships"] > 5_000_000


def test_semmeddb_load_writes_predication_relationships():
    graph = InMemoryGraph()
    SemMedDBLoader(graph=graph).load()
    rows = graph.relationship_rows(RelationshipType.PREDICATION)
    assert rows
    assert {row["properties"]["predicate"] for row in rows} >= {"TREATS", "AFFECTS"}
