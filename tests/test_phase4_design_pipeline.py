from trident.agents.design_fixtures import toxic_smiles
from trident.agents.generator_agent import GenerationQuery, GeneratorAgent, MoleculeCandidate
from trident.agents.structure_agent import StructureAgent, StructureQuery
from trident.agents.validator_agent import ValidationQuery, ValidatorAgent


def test_structure_agent_predicts_tyk2_within_2a_rmsd():
    result = StructureAgent().run(StructureQuery(target_symbol="TYK2", cross_validate_af3=True))
    assert result.prediction.rmsd_to_experimental is not None
    assert result.prediction.rmsd_to_experimental < 2.0
    assert result.prediction.af3_cross_validation_rmsd < 2.0
    assert result.prediction.experimental_pdb == "4GIH"


def test_structure_agent_fpocket_detects_kinase_atp_binding_pocket():
    result = StructureAgent().run(StructureQuery(target_symbol="TYK2"))
    assert result.druggable is True
    assert any("ATP-binding" in pocket.annotation for pocket in result.top_pockets)
    assert result.top_pockets[0].druggability_score > 0.85


def test_generator_agent_produces_at_least_100_unique_valid_smiles():
    structure = StructureAgent().run(StructureQuery(target_symbol="TYK2"))
    result = GeneratorAgent().run(
        GenerationQuery(target_symbol="TYK2", pocket=structure.top_pockets[0], n_molecules=120)
    )
    assert result.unique_count >= 100
    assert len(result.molecules) >= 100
    assert all(molecule.valid_smiles for molecule in result.molecules)


def test_generator_agent_at_least_half_outputs_have_qed_above_05():
    structure = StructureAgent().run(StructureQuery(target_symbol="TYK2"))
    result = GeneratorAgent().run(
        GenerationQuery(target_symbol="TYK2", pocket=structure.top_pockets[0], n_molecules=120)
    )
    assert result.qed_above_05_fraction >= 0.50
    assert sum(1 for molecule in result.molecules if molecule.qed > 0.5) >= 60


def test_validator_agent_boltz_abfe_ranks_known_tyk2_inhibitors_correctly():
    ranking = ValidatorAgent().rank_known_tyk2_inhibitors()
    assert ranking[:3] == ["deucravacitinib", "brepocitinib", "ropocamptide"]


def test_validator_agent_admet_filter_removes_known_toxic_compounds():
    structure = StructureAgent().run(StructureQuery(target_symbol="TYK2"))
    toxic = next(iter(toxic_smiles()))
    molecule = MoleculeCandidate(
        smiles=toxic,
        source="toxic_fixture",
        pocket_id=structure.top_pockets[0].pocket_id,
        qed=0.3,
        synthetic_accessibility=0.4,
        boltz2_affinity_kcal_mol=-7.0,
        valid_smiles=True,
        rank=1,
    )
    result = ValidatorAgent().run(
        ValidationQuery(
            target_symbol="TYK2",
            pocket=structure.top_pockets[0],
            molecules=[molecule],
        )
    )
    assert result.validated_candidates == []
    assert result.rejected
    assert "admet_failures" in result.rejected[0]["reasons"]


def test_full_design_pipeline_returns_validated_hits_under_cpu_budget():
    result = ValidatorAgent().run_full_pipeline("TYK2", n_molecules=120, top_k_abfe=10)
    assert result.generated_count >= 100
    assert result.validated_hits
    assert result.runtime_seconds < 2 * 60 * 60
    assert result.structure_pdb_path.endswith("TYK2_boltz2_fixture.pdb")
