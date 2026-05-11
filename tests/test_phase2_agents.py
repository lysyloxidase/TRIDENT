from pydantic import BaseModel

from trident.agents.base import ProvenanceResult
from trident.agents.contradiction_agent import ContradictionAgent, ContradictionQuery
from trident.agents.lit_agent import LitAgent, LitQuery
from trident.agents.patent_agent import PatentAgent, PatentQuery
from trident.agents.synthesis_agent import DeepSynthesisQuery, SynthesisAgent
from trident.agents.trial_agent import TrialAgent, TrialQuery


def assert_provenance(result: ProvenanceResult, agent_name: str) -> None:
    assert isinstance(result, BaseModel)
    assert result.agent_name == agent_name
    assert result.retrieval_timestamp is not None
    assert result.confidence_band.low <= result.confidence_band.mid <= result.confidence_band.high
    assert isinstance(result.source_urls, list)
    assert result.tool_calls


def test_lit_agent_search_returns_at_least_20_relevant_egfr_papers():
    papers = LitAgent().search("EGFR inhibitors lung cancer", n_papers=50)
    assert len(papers) >= 20
    assert all("EGFR" in f"{paper.title} {paper.abstract}" for paper in papers[:20])


def test_lit_agent_verifies_every_cited_pmid_without_hallucinations():
    result = LitAgent().run(LitQuery(question="EGFR inhibitors lung cancer", min_chunks=10))
    assert result.cited_pmids
    assert result.hallucinated_pmids == []
    assert all(result.citation_verification[pmid] for pmid in result.cited_pmids)
    assert_provenance(result, "literature")


def test_synthesis_agent_btl_tournament_ranks_known_drugs_by_efficacy():
    agent = SynthesisAgent()
    ranking = agent.rank_known_drugs_by_efficacy()
    assert ranking == ["osimertinib", "afatinib", "dacomitinib", "erlotinib", "gefitinib"]

    result = agent.run(DeepSynthesisQuery(question="Rank EGFR inhibitors by clinical efficacy"))
    assert result.top_candidate == "osimertinib"
    assert_provenance(result, "synthesis")


def test_patent_agent_extracts_compound_target_tuples_from_test_patents():
    result = PatentAgent().run(PatentQuery())
    compound_target = {(claim.compound, claim.target) for claim in result.claims}
    assert len([pair for pair in compound_target if pair[0] and pair[1]]) >= 3
    assert ("gefitinib", "EGFR") in compound_target
    assert ("erlotinib", "EGFR") in compound_target
    assert ("osimertinib", "EGFR") in compound_target
    assert all(claim.legal_review_required for claim in result.claims)
    assert_provenance(result, "patent")


def test_trial_agent_identifies_baricitinib_covid_candidate_from_pre_2020_data():
    result = TrialAgent().run(TrialQuery(disease="COVID-19", cutoff_year=2020))
    names = {candidate.drug.lower() for candidate in result.repurposing_candidates}
    assert "baricitinib" in names
    baricitinib = next(
        candidate for candidate in result.repurposing_candidates if candidate.drug == "baricitinib"
    )
    assert max(baricitinib.evidence_years) < 2020
    assert_provenance(result, "trial")


def test_contradiction_agent_flags_homeopathy_for_cancer():
    result = ContradictionAgent().run(ContradictionQuery(claim="homeopathy for cancer"))
    assert result.flagged is True
    assert result.contradiction_score == 5
    assert len(result.contradicting_pmids) >= 3
    assert_provenance(result, "contradiction")


def test_all_phase2_agents_return_pydantic_results_with_provenance_fields():
    results = [
        LitAgent().run(LitQuery(question="EGFR inhibitors lung cancer", min_chunks=8)),
        SynthesisAgent().run(DeepSynthesisQuery(question="Rank EGFR inhibitors")),
        PatentAgent().run(PatentQuery(target="EGFR")),
        TrialAgent().run(TrialQuery(disease="COVID-19", cutoff_year=2020)),
        ContradictionAgent().run(ContradictionQuery(claim="homeopathy for cancer")),
    ]
    for result in results:
        assert isinstance(result, ProvenanceResult)
        assert result.source_urls
        assert result.retrieval_timestamp
        assert 0.0 <= result.confidence_band.low <= result.confidence_band.high <= 1.0
        assert result.agent_name
