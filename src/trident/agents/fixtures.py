"""Deterministic Phase 2 fixtures for offline agent tests."""

from __future__ import annotations

from typing import Any


def egfr_lung_cancer_papers() -> list[dict[str, Any]]:
    titles = [
        "Activating mutations in EGFR underlying responsiveness of lung cancer to gefitinib",
        "EGFR mutations predict sensitivity to gefitinib in non-small cell lung cancer",
        "Erlotinib in previously treated non-small-cell lung cancer",
        "Gefitinib or carboplatin-paclitaxel in pulmonary adenocarcinoma",
        "Osimertinib in untreated EGFR-mutated advanced non-small-cell lung cancer",
        "Afatinib versus chemotherapy in EGFR mutation-positive lung adenocarcinoma",
        "Dacomitinib versus gefitinib for EGFR-mutated non-small-cell lung cancer",
        "Resistance mechanisms to EGFR kinase inhibitors in lung cancer",
        "T790M mutation and acquired resistance to EGFR inhibitors",
        "MET amplification in EGFR inhibitor resistant lung cancer",
        "Combination EGFR blockade and antiangiogenic therapy in lung cancer",
        "CNS activity of osimertinib in EGFR-mutant lung cancer",
        "First-line erlotinib for EGFR mutation-positive lung cancer",
        "Gefitinib maintenance therapy in advanced non-small-cell lung cancer",
        "EGFR exon 20 insertion inhibitors in lung cancer",
        "Amivantamab for EGFR exon 20 insertion non-small-cell lung cancer",
        "Mobocertinib in platinum-pretreated EGFR exon 20 insertion lung cancer",
        "Real-world outcomes for EGFR tyrosine kinase inhibitors in lung cancer",
        "Adjuvant osimertinib in resected EGFR-mutated lung cancer",
        "Minimal residual disease after EGFR inhibitor therapy in lung cancer",
        "EGFR inhibitor dermatologic toxicity and treatment response",
        "Liquid biopsy monitoring of EGFR resistance mutations",
        "HER2 and EGFR signaling bypass in lung adenocarcinoma",
        "EGFR inhibitor sequencing after osimertinib progression",
        "Immunotherapy outcomes after EGFR tyrosine kinase inhibitors",
    ]
    pmids = [
        "15118125",
        "15118073",
        "16014882",
        "19380444",
        "29151359",
        "22452895",
        "28958502",
        "20033041",
        "15737014",
        "17909029",
        "29466156",
        "30138593",
        "21825164",
        "20516440",
        "33406420",
        "34077256",
        "34614331",
        "32004476",
        "32955177",
        "36053578",
        "22162584",
        "26878339",
        "24722171",
        "34348155",
        "30739196",
    ]
    papers = []
    for index, (pmid, title) in enumerate(zip(pmids, titles), start=1):
        papers.append(
            {
                "pmid": pmid,
                "doi": f"10.1000/trident.egfr.{index}",
                "title": title,
                "abstract": (
                    "This study evaluates EGFR inhibitors in lung cancer, including "
                    "clinical response, progression-free survival, resistance, and "
                    "biomarker-selected non-small-cell lung cancer populations."
                ),
                "journal": "TRIDENT fixture journal",
                "year": 2004 + min(index, 19),
                "authors": ["TRIDENT Evidence Group"],
                "source": "PubMed",
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "relevance_score": round(1.0 - index * 0.01, 3),
            }
        )
    return papers


def pubmed_fixture_index() -> dict[str, dict[str, Any]]:
    return {paper["pmid"]: paper for paper in egfr_lung_cancer_papers()} | {
        "10000001": {"title": "Systematic reviews show no cancer survival effect from homeopathy"},
        "10000002": {"title": "Homeopathy is not biologically plausible as cancer therapy"},
        "10000003": {"title": "No objective tumor response from homeopathic cancer treatment"},
        "7201675": {"title": "Fish oil affects blood viscosity"},
        "3943917": {"title": "Fish oil in Raynaud disease"},
    }


def patent_documents() -> list[dict[str, Any]]:
    return [
        {
            "patent_id": "US20030087813A1",
            "lens_id": "LENS-TRIDENT-EGFR-001",
            "filing_year": 2001,
            "source_url": "https://patents.google.com/patent/US20030087813A1",
            "claims": (
                "A composition comprising gefitinib for inhibiting EGFR in a patient "
                "with non-small cell lung cancer."
            ),
        },
        {
            "patent_id": "US20050215555A1",
            "lens_id": "LENS-TRIDENT-EGFR-002",
            "filing_year": 2004,
            "source_url": "https://patents.google.com/patent/US20050215555A1",
            "claims": "Erlotinib compounds and methods for targeting EGFR driven lung tumors.",
        },
        {
            "patent_id": "WO2013014448A1",
            "lens_id": "LENS-TRIDENT-EGFR-003",
            "filing_year": 2012,
            "source_url": "https://patents.google.com/patent/WO2013014448A1",
            "claims": "Osimertinib selectively inhibits mutant EGFR including T790M mutations.",
        },
        {
            "patent_id": "WO2019123456A1",
            "lens_id": "LENS-TRIDENT-TMEM132B-001",
            "filing_year": 2018,
            "source_url": "https://patents.google.com/patent/WO2019123456A1",
            "claims": "Methods of modulating TMEM132B in neurological indications.",
        },
    ]


def trial_records() -> list[dict[str, Any]]:
    return [
        {
            "nct_id": "NCT01823640",
            "drug": "baricitinib",
            "target": "JAK1/JAK2",
            "disease": "rheumatoid arthritis",
            "phase": "PHASE3",
            "status": "completed",
            "year": 2017,
            "primary_outcome": "ACR20 response",
            "secondary_signal": "reduced inflammatory cytokine signaling",
            "source_url": "https://clinicaltrials.gov/study/NCT01823640",
        },
        {
            "nct_id": "NCT01721057",
            "drug": "baricitinib",
            "target": "AAK1/JAK",
            "disease": "rheumatoid arthritis",
            "phase": "PHASE2",
            "status": "completed",
            "year": 2013,
            "primary_outcome": "dose response",
            "secondary_signal": "host kinase biology relevant to viral entry and inflammation",
            "source_url": "https://clinicaltrials.gov/study/NCT01721057",
        },
        {
            "nct_id": "NCT03099174",
            "drug": "rilonacept",
            "target": "IL1",
            "disease": "pericarditis",
            "phase": "PHASE2",
            "status": "terminated",
            "year": 2019,
            "primary_outcome": "lack of efficacy",
            "secondary_signal": "symptom improvement in inflammatory subgroup",
            "source_url": "https://clinicaltrials.gov/study/NCT03099174",
        },
    ]


def contradiction_records() -> list[dict[str, Any]]:
    return [
        {
            "pmid": "10000001",
            "title": "Systematic reviews show no cancer survival effect from homeopathy",
            "claim_area": "homeopathy for cancer",
            "journal_impact": 9.0,
            "year": 2018,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/10000001/",
            "summary": "Controlled evidence does not support homeopathy as cancer treatment.",
        },
        {
            "pmid": "10000002",
            "title": "Homeopathy is not biologically plausible as cancer therapy",
            "claim_area": "homeopathy for cancer",
            "journal_impact": 7.5,
            "year": 2019,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/10000002/",
            "summary": "Mechanistic claims conflict with dose-response pharmacology.",
        },
        {
            "pmid": "10000003",
            "title": "No objective tumor response from homeopathic cancer treatment",
            "claim_area": "homeopathy for cancer",
            "journal_impact": 8.0,
            "year": 2021,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/10000003/",
            "summary": "Clinical series report no reproducible anticancer activity.",
        },
    ]
