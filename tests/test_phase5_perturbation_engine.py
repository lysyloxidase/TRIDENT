from trident.agents.perturbation_agent import PerturbationAgent, PerturbationQuery, sotorasib_query
from trident.models.cpa_wrapper import CPAWrapper
from trident.models.gears_wrapper import GEARSWrapper
from trident.models.geneformer_wrapper import GeneformerWrapper
from trident.models.perturbation_fixtures import (
    DEX_A549_GROUND_TRUTH,
    DEXAMETHASONE_SMILES,
    GENE_PANEL,
    REPL0GLE_KRAS_KO,
    SOTORASIB_SMILES,
    pearson,
    profile_from_vector,
)


def test_cpa_predicts_dexamethasone_a549_lincs_ground_truth():
    prediction = CPAWrapper().predict(DEXAMETHASONE_SMILES, dose_uM=1.0, cell_type="A549")
    predicted = profile_from_vector(prediction.tolist())
    assert pearson(predicted, DEX_A549_GROUND_TRUTH) > 0.3
    assert predicted["FKBP5"] > 0.8
    assert predicted["IL6"] < -0.5


def test_gears_predicts_crispr_ko_effect_matching_replogle_fixture():
    prediction = GEARSWrapper().predict_perturbation("KRAS", "tumor_epithelial")
    predicted = profile_from_vector(prediction.tolist())
    assert pearson(predicted, REPL0GLE_KRAS_KO) > 0.6
    assert predicted["KRAS"] < -0.8


def test_geneformer_identifies_known_kras_downstream_targets():
    predicted = GeneformerWrapper().in_silico_perturb("KRAS")
    top = sorted(predicted, key=lambda gene: abs(predicted[gene]), reverse=True)[:8]
    assert {"MAPK1", "MAPK3", "DUSP6", "MYC"} & set(top)
    assert predicted["ETV4"] < 0
    assert predicted["DUSP6"] > 0


def test_ensemble_outperforms_training_mean_baseline_on_heldout_perturbseq():
    benchmark = PerturbationAgent().evaluate_heldout_perturbseq()
    assert benchmark.ensemble_pearson > benchmark.training_mean_pearson
    assert benchmark.improvement > 0.1


def test_high_disagreement_genes_are_enriched_for_variable_genes():
    agent = PerturbationAgent()
    result = agent.run(sotorasib_query())
    assert result.high_disagreement_genes
    assert agent.disagreement_enrichment(result.high_disagreement_genes) > 1.0


def test_causal_grounding_labels_lincs_covered_pairs_as_interventional():
    result = PerturbationAgent().run(
        PerturbationQuery(
            drug_smiles=DEXAMETHASONE_SMILES,
            patient_h5ad_path="A549_h5ad",
            target_cell_type="A549",
            target_gene="NR3C1",
        )
    )
    assert result.causal_confidence == "interventional"
    assert result.do_calculus_warning is None


def test_refuses_completely_novel_drug_and_novel_cell_type():
    result = PerturbationAgent().run(
        PerturbationQuery(
            drug_smiles="XeXeXeXeXe",
            patient_h5ad_path="unknown_patient.h5ad",
            target_cell_type="novel_cell_type",
            target_gene="ZZZ1",
        )
    )
    assert result.refused is True
    assert "drug_structurally_dissimilar_to_training_compounds" in result.refusal_reasons
    assert "cell_type_has_fewer_than_100_training_cells" in result.refusal_reasons
    assert result.predicted_expression == {}


def test_full_sotorasib_lung_adenocarcinoma_query_downregulates_kras_pathway():
    result = PerturbationAgent().run(sotorasib_query())
    assert result.refused is False
    assert result.causal_confidence == "interventional"
    assert result.predicted_expression["KRAS"] < -0.5
    assert result.predicted_expression["MAPK1"] < -0.3
    assert result.predicted_expression["MAPK3"] < -0.3
    assert result.predicted_expression["MYC"] < -0.4
    assert result.predicted_expression["CCND1"] < -0.3
    assert result.predicted_expression["DUSP6"] > 0.4
    assert set(result.predicted_expression) == set(GENE_PANEL)
    assert {"CPA", "GEARS", "Geneformer", "CellOracle", "scGPT_embedding"} <= set(
        result.model_contributions
    )


def test_observational_only_warning_for_uncovered_but_similar_pair():
    result = PerturbationAgent().run(
        PerturbationQuery(
            drug_smiles=SOTORASIB_SMILES,
            patient_h5ad_path="hepatocyte_patient.h5ad",
            target_cell_type="hepatocyte",
            target_gene="KRAS",
        )
    )
    assert result.refused is False
    assert result.causal_confidence == "observational_only"
    assert result.do_calculus_warning is not None
