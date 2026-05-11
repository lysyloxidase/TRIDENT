"""Biomedical data source loaders for TRIDENT KG."""

from trident.kg.loaders.chembl import ChEMBLLoader
from trident.kg.loaders.clinicaltrials import ClinicalTrialsLoader
from trident.kg.loaders.depmap import DepMapLoader
from trident.kg.loaders.disgenet import DisGeNETLoader
from trident.kg.loaders.drkg import DRKGLoader
from trident.kg.loaders.drugbank import DrugBankLoader
from trident.kg.loaders.gtex import GTExLoader
from trident.kg.loaders.hetionet import HetionetLoader
from trident.kg.loaders.lens_patents import LensPatentsLoader
from trident.kg.loaders.opentargets import OpenTargetsLoader
from trident.kg.loaders.pharos import PharosLoader
from trident.kg.loaders.primekg import PrimeKGLoader
from trident.kg.loaders.semmeddb import SemMedDBLoader

LOADER_CLASSES = {
    "opentargets": OpenTargetsLoader,
    "pharos": PharosLoader,
    "primekg": PrimeKGLoader,
    "hetionet": HetionetLoader,
    "drkg": DRKGLoader,
    "semmeddb": SemMedDBLoader,
    "disgenet": DisGeNETLoader,
    "chembl": ChEMBLLoader,
    "drugbank": DrugBankLoader,
    "clinicaltrials": ClinicalTrialsLoader,
    "gtex": GTExLoader,
    "depmap": DepMapLoader,
    "lens_patents": LensPatentsLoader,
}

__all__ = [
    "ChEMBLLoader",
    "ClinicalTrialsLoader",
    "DepMapLoader",
    "DisGeNETLoader",
    "DRKGLoader",
    "DrugBankLoader",
    "GTExLoader",
    "HetionetLoader",
    "LensPatentsLoader",
    "LOADER_CLASSES",
    "OpenTargetsLoader",
    "PharosLoader",
    "PrimeKGLoader",
    "SemMedDBLoader",
]
