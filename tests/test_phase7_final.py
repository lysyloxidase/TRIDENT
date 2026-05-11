import json
import shutil
import subprocess
import sys
from pathlib import Path

from evals.boltz_tyk2 import run_benchmark as run_boltz_tyk2
from evals.lbd_replication import run_benchmark as run_lbd_replication
from evals.litqa2 import run_benchmark as run_litqa2
from evals.perturbseq_bench import run_benchmark as run_perturbseq
from trident.agents.orchestrator import TridentOrchestrator
from trident.caveats import MANDATORY_CAVEATS
from trident.models.perturbation_fixtures import SOTORASIB_SMILES

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui"


def test_phase7_evaluation_suite_hits_targets():
    litqa2 = run_litqa2()
    lbd = run_lbd_replication()
    boltz = run_boltz_tyk2()
    perturbseq = run_perturbseq()
    assert litqa2.passed
    assert litqa2.accuracy >= 0.85
    assert litqa2.hallucinated_citations == 0
    assert lbd.passed
    assert lbd.recovered >= 3
    assert boltz.passed
    assert boltz.pearson_vs_fep >= 0.5
    assert perturbseq.passed
    assert perturbseq.datasets_beaten >= 1


def test_full_ipf_pipeline_finishes_inside_cpu_gate_and_reports_caveats():
    state = TridentOrchestrator().run(
        disease="idiopathic pulmonary fibrosis",
        n_targets=5,
        design=True,
    )
    assert state.timings["total"] < 4 * 60 * 60
    assert state.report is not None
    for caveat in MANDATORY_CAVEATS:
        assert caveat in state.report
    assert all(
        record.source_url and record.agent_name and record.retrieval_timestamp
        for record in state.provenance
    )


def test_next_ui_routes_and_live_agent_graph_are_scaffolded():
    required = [
        UI / "app" / "page.tsx",
        UI / "app" / "run" / "[id]" / "page.tsx",
        UI / "app" / "run" / "[id]" / "targets" / "page.tsx",
        UI / "app" / "run" / "[id]" / "targets" / "[gene]" / "molecules" / "page.tsx",
        UI / "app" / "run" / "[id]" / "targets" / "[gene]" / "perturbation" / "page.tsx",
        UI / "app" / "run" / "[id]" / "report" / "page.tsx",
    ]
    assert all(path.exists() for path in required)
    graph = (UI / "components" / "AgentGraph.tsx").read_text()
    package_json = json.loads((UI / "package.json").read_text())
    report = (UI / "app" / "run" / "[id]" / "report" / "page.tsx").read_text()
    assert "ReactFlow" in graph
    assert "new WebSocket" in graph
    assert "@xyflow/react" in package_json["dependencies"]
    assert "3dmol" in package_json["dependencies"]
    assert "mandatoryCaveats" in report


def test_cli_all_final_commands_are_functional(tmp_path):
    commands = [
        ["run", "--disease", "idiopathic pulmonary fibrosis", "--n-targets", "1", "--design"],
        ["discover", "--disease", "dry AMD", "--n-targets", "5"],
        ["design", "--target", "TNIK", "--uniprot", "Q9UKE5", "--n-molecules", "10"],
        [
            "perturb",
            "--drug",
            SOTORASIB_SMILES,
            "--h5ad",
            "lung_adenocarcinoma_h5ad",
            "--cell-type",
            "tumor_epithelial",
            "--target-gene",
            "KRAS",
        ],
        ["search", "--query", "ROCK inhibitors RPE phagocytosis", "--n-papers", "20"],
        ["eval", "--suite", "perturbseq"],
    ]
    for command in commands:
        completed = subprocess.run(
            [sys.executable, "-m", "trident.cli", *command],
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stdout.strip()
    output = tmp_path / "results.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "trident.cli",
            "export",
            "--format",
            "json",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(output.read_text())["ranked_targets"]


def test_docker_compose_declares_full_stack():
    if shutil.which("docker") is None:
        return
    completed = subprocess.run(
        ["docker", "compose", "--profile", "gpu", "config", "--services"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    services = set(completed.stdout.splitlines())
    assert {"neo4j", "redis", "api", "worker", "ui", "gpu-worker"} <= services
