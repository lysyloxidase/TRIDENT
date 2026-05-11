from trident.agents.lbd_agent import LBDAgent, LBDQuery
from trident.agents.mr_agent import MRAgent, MRQuery
from trident.scoring.bayesian_fusion import TargetRanker, TargetRankingQuery
from trident.scoring.confidence import ConfidenceScorer, EvidenceStreams
from trident.scoring.novelty import NoveltyInput, NoveltyScorer


def test_mr_agent_pcsk9_ldl_returns_significant_causal_estimate():
    result = MRAgent().run(MRQuery(exposure="PCSK9", outcome="LDL cholesterol"))
    ivw = next(estimate for estimate in result.estimates if estimate.method == "IVW")
    assert result.significant is True
    assert ivw.p_value < 0.001
    assert result.posterior_causal_probability > 0.9
    assert result.sensitivity.coloc_h4 > 0.8


def test_mr_agent_negative_control_height_diabetes_is_non_significant():
    result = MRAgent().run(MRQuery(exposure="height", outcome="diabetes"))
    ivw = next(estimate for estimate in result.estimates if estimate.method == "IVW")
    assert result.significant is False
    assert ivw.p_value > 0.05
    assert result.posterior_causal_probability < 0.5


def test_lbd_agent_recovers_fish_oil_raynaud_from_pre_1986_subset():
    result = LBDAgent().run(LBDQuery(disease_id="Raynaud disease", cutoff_year=1986))
    hypotheses = {
        (hypothesis.a_concept.lower(), hypothesis.c_concept.lower())
        for hypothesis in result.hypotheses
    }
    assert ("fish oil", "raynaud disease") in hypotheses
    fish_oil = next(
        hypothesis for hypothesis in result.hypotheses if hypothesis.a_concept.lower() == "fish oil"
    )
    assert len({path.b_concept for path in fish_oil.paths}) >= 2
    assert fish_oil.validation_status == "validated_in_holdout"


def test_lbd_agent_recovers_magnesium_migraine_from_pre_1988_subset():
    result = LBDAgent().run(LBDQuery(disease_id="migraine", cutoff_year=1988))
    hypotheses = {
        (hypothesis.a_concept.lower(), hypothesis.c_concept.lower())
        for hypothesis in result.hypotheses
    }
    assert ("magnesium", "migraine") in hypotheses


def test_lbd_agent_recovers_additional_swanson_validated_discovery():
    result = LBDAgent().run(LBDQuery(disease_id="Alzheimer disease", cutoff_year=1986))
    hypotheses = {
        (hypothesis.a_concept.lower(), hypothesis.c_concept.lower())
        for hypothesis in result.hypotheses
    }
    assert ("indomethacin", "alzheimer disease") in hypotheses


def test_novelty_scorer_tdark_scores_higher_than_tclin():
    scorer = NoveltyScorer()
    tdark = scorer.score(
        NoveltyInput(
            gene_symbol="TMEM132B",
            disease_name="IPF",
            pharos_tdl="Tdark",
            publication_count=40,
            uzzi_z_score=-2.1,
            llm_novelty_prior=0.80,
            pipeline_gap=0.95,
        )
    )
    tclin = scorer.score(
        NoveltyInput(
            gene_symbol="EGFR",
            disease_name="IPF",
            pharos_tdl="Tclin",
            publication_count=18_000,
            uzzi_z_score=0.3,
            llm_novelty_prior=0.20,
            pipeline_gap=0.50,
        )
    )
    assert tdark.novelty_score > tclin.novelty_score
    assert tdark.pharos_bonus == 0.30


def test_confidence_scorer_egfr_lung_cancer_scores_above_09():
    result = ConfidenceScorer().score(
        EvidenceStreams(
            genetic_causal_p=0.91,
            mr_p_value=1e-6,
            consistent_direction=True,
            lbd_score=0.72,
            lbd_independent_paths=3,
            gwas_pip=0.94,
            expression_specificity=0.82,
            depmap_dependency=0.72,
            relevant_depmap_lines=4,
            primekg_path_strength=0.86,
            patent_white_space=0.35,
            trial_failure_gap=0.40,
            contradictory_evidence=0.02,
        )
    )
    assert result.confidence_score > 0.9
    assert result.credible_interval.lower > 0.85


def test_target_ranker_top5_ipf_include_at_least_two_tbio_or_tdark_targets():
    ranked = TargetRanker().rank(
        TargetRankingQuery(disease_name="idiopathic pulmonary fibrosis", top_k=5)
    )
    top5 = [item.candidate for item in ranked]
    underappreciated = [
        candidate for candidate in top5 if candidate.pharos_tdl in {"Tbio", "Tdark"}
    ]
    assert len(top5) == 5
    assert len(underappreciated) >= 2
    assert ranked[0].quadrant == "PRIORITY_TARGET"


def test_bayesian_fusion_adding_contradictory_evidence_lowers_confidence():
    scorer = ConfidenceScorer()
    base = EvidenceStreams(
        genetic_causal_p=0.82,
        mr_p_value=1e-5,
        consistent_direction=True,
        lbd_score=0.70,
        lbd_independent_paths=3,
        gwas_pip=0.93,
        expression_specificity=0.85,
        depmap_dependency=0.65,
        relevant_depmap_lines=3,
        primekg_path_strength=0.75,
    )
    confident = scorer.score(base)
    contradicted = scorer.score(base.model_copy(update={"contradictory_evidence": 0.85}))
    assert contradicted.confidence_score < confident.confidence_score
