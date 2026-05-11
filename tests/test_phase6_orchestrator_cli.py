import json
import subprocess
import sys
import time

from trident.agents.mr_agent import MRQuery
from trident.agents.orchestrator import TridentOrchestrator, TridentState
from trident.agents.perturbation_agent import sotorasib_query
from trident.models.perturbation_fixtures import SOTORASIB_SMILES


def test_orchestrator_full_pipeline_completes_for_ipf():
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=2,
        design=True,
    )
    assert state.report
    assert len(state.ranked_targets) == 2
    assert state.designed_molecules
    assert state.perturbation_predictions
    assert state.perturbation_predictions[0]["predicted_expression"]["KRAS"] < -0.5


def test_orchestrator_parallel_agents_run_in_parallel_timing_check():
    orchestrator = TridentOrchestrator()
    state = TridentState(disease="timing")

    def slow(value: int) -> int:
        time.sleep(0.15)
        return value

    started = time.perf_counter()
    outputs = orchestrator._run_parallel(
        {
            "a": lambda: slow(1),
            "b": lambda: slow(2),
            "c": lambda: slow(3),
        },
        state,
        stage="timing",
    )
    elapsed = time.perf_counter() - started
    assert outputs == {"a": 1, "b": 2, "c": 3}
    assert elapsed < 0.35


def test_trident_state_accumulates_all_core_fields_without_data_loss():
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=1,
        design=True,
    )
    assert state.disease_context is not None
    assert state.literature_evidence is not None
    assert state.patent_landscape is not None
    assert state.trial_evidence is not None
    assert state.mr_results
    assert state.lbd_discoveries is not None
    assert state.ranked_targets
    assert state.designed_molecules
    assert state.perturbation_predictions
    dumped = state.model_dump()
    assert dumped["ranked_targets"][0]["gene_symbol"] == state.ranked_targets[0]["gene_symbol"]


def test_cli_discover_dry_amd_returns_at_least_5_ranked_targets():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "trident.cli",
            "discover",
            "--disease",
            "dry AMD",
            "--n-targets",
            "5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert len(payload["ranked_targets"]) >= 5
    assert (
        payload["ranked_targets"][0]["trident_score"]
        >= payload["ranked_targets"][1]["trident_score"]
    )


def test_cli_perturb_returns_predictions_with_ensemble_variance():
    query = sotorasib_query()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "trident.cli",
            "perturb",
            "--drug",
            SOTORASIB_SMILES,
            "--h5ad",
            query.patient_h5ad_path,
            "--cell-type",
            query.target_cell_type,
            "--target-gene",
            query.target_gene,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["predicted_expression"]["KRAS"] < -0.5
    assert payload["ensemble_variance"]["ETV4"] > 0.02


def test_report_generates_markdown_with_at_least_10_verified_citations():
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=5,
        design=False,
    )
    assert state.report is not None
    assert state.report.count("PMID:") >= 10
    assert "## 8. References" in state.report


def test_provenance_records_have_source_url_and_agent_name():
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=3,
        design=True,
    )
    assert state.provenance
    assert all(record.agent_name for record in state.provenance)
    assert all(record.source_url for record in state.provenance)
    assert all(record.claim for record in state.provenance)


def test_orchestrator_gracefully_degrades_when_one_agent_fails():
    class BrokenMRAgent:
        name = "broken_mr"

        def run(self, query: MRQuery):
            raise RuntimeError("no instruments for target")

    state = TridentOrchestrator(mr_agent=BrokenMRAgent()).run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=3,
        design=False,
    )
    assert state.errors
    assert state.errors[0].stage == "parallel_analysis"
    assert "no instruments" in state.errors[0].message
    assert len(state.ranked_targets) == 3
    assert state.report
