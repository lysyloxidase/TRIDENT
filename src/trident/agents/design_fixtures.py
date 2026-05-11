"""Deterministic fixtures for Phase 4 structure and molecule design."""

from __future__ import annotations

from typing import Any

TYK2_SEQUENCE = (
    "MNNVQPTVVVKDGEHLCLVMEYMEKGSLVEQLRRELEDGQGQLVEQLKQLYHETQQLRPL"
    "GTPAGGGSFGVVKAIHRIDGKTYVIKRVKETGHEVLKVIHHFDTEDNVYLVMEYVPGGEMFS"
    "HLRRIGRFSEPHARFYAAQIVLTFEYLHSLDLIYRDLKPENILLDEEGHIKLTDFGLSKVLE"
    "DTSLQKFSVAKSCLEHLPEKRPTATVYHIKNILPIVRDYDPERFLSKFLQEKSDQGIQYQ"
)


def target_structures() -> dict[str, dict[str, Any]]:
    return {
        "TYK2": {
            "uniprot_id": "P29597",
            "sequence": TYK2_SEQUENCE,
            "experimental_pdb": "4GIH",
            "predicted_pdb_path": "data/predicted/TYK2_boltz2_fixture.pdb",
            "rmsd_to_experimental": 1.42,
            "plddt": 86.4,
            "lddt_pli": 0.69,
            "source_urls": [
                "https://www.uniprot.org/uniprotkb/P29597/entry",
                "https://www.rcsb.org/structure/4GIH",
            ],
            "pockets": [
                {
                    "pocket_id": "TYK2_ATP_1",
                    "rank": 1,
                    "center": [12.4, 18.2, 7.9],
                    "volume": 612.0,
                    "hydrophobicity": 0.64,
                    "enclosure": 0.71,
                    "druggability_score": 0.91,
                    "residues": ["V981", "A966", "K930", "D1042", "F995"],
                    "annotation": "ATP-binding kinase hinge pocket",
                },
                {
                    "pocket_id": "TYK2_ALLO_2",
                    "rank": 2,
                    "center": [7.8, 14.0, 3.6],
                    "volume": 355.0,
                    "hydrophobicity": 0.57,
                    "enclosure": 0.62,
                    "druggability_score": 0.68,
                    "residues": ["L905", "F929", "V943"],
                    "annotation": "regulatory allosteric cleft",
                },
                {
                    "pocket_id": "TYK2_SURF_3",
                    "rank": 3,
                    "center": [20.1, 9.4, 10.5],
                    "volume": 190.0,
                    "hydrophobicity": 0.42,
                    "enclosure": 0.35,
                    "druggability_score": 0.38,
                    "residues": ["E1002", "Q1005"],
                    "annotation": "shallow surface groove",
                },
            ],
        }
    }


def known_tyk2_inhibitors() -> list[dict[str, Any]]:
    return [
        {
            "name": "deucravacitinib",
            "smiles": "CC1=NC=C(C=C1)NC(=O)N2CCC(CC2)N3C=NC4=C3C=CN=C4",
            "experimental_delta_g": -11.2,
            "expected_rank": 1,
            "toxic": False,
        },
        {
            "name": "brepocitinib",
            "smiles": "CC(C)N1C=NC2=C1N=C(N=C2N)NC3=CC=CC=C3",
            "experimental_delta_g": -10.4,
            "expected_rank": 2,
            "toxic": False,
        },
        {
            "name": "ropocamptide",
            "smiles": "CC(C)C(NC(=O)CNC(=O)C1CCCN1)C(=O)NCC(=O)O",
            "experimental_delta_g": -8.7,
            "expected_rank": 3,
            "toxic": False,
        },
        {
            "name": "toluene",
            "smiles": "Cc1ccccc1",
            "experimental_delta_g": -4.0,
            "expected_rank": 4,
            "toxic": True,
        },
    ]


def toxic_smiles() -> set[str]:
    return {
        "O=[N+]([O-])c1ccc(Cl)cc1",
        "ClC(Cl)(Cl)Cl",
        "Cc1ccccc1",
        "NC(=O)N(CCCl)N=O",
    }


def substituent_library() -> list[str]:
    return [
        "C",
        "CC",
        "CCC",
        "CO",
        "CCO",
        "CN",
        "CCN",
        "OC",
        "OCC",
        "F",
        "Cl",
        "C#N",
        "C(=O)N",
        "C(=O)O",
        "N(C)C",
    ]
