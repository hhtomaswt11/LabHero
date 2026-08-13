"""Backend model registry.

Model templates are cached read-only.  Every /simulate request works on fresh
copies, preventing one student's objective/bounds from leaking into another
request when LabHero is deployed as a multi-user web service.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from cobra.io import read_sbml_model


MODELS_DIR = Path(__file__).resolve().parent.parent / 'models'
MODEL_REGISTRY = {
    'ecoli_core': {
        'file': MODELS_DIR / 'e_coli_core.xml.gz',
        'default_objective': 'BIOMASS_Ecoli_core_w_GAM',
        'supported_methods': ('FBA', 'pFBA', 'lMOMA', 'ROOM'),
        'room_reference_target': 'CYTBD',
    },
    'yeast_iMM904': {
        'file': MODELS_DIR / 'iMM904.xml.gz',
        'default_objective': 'BIOMASS_SC5_notrace',
        'supported_methods': ('FBA', 'pFBA'),
        'room_reference_target': None,
    },
}
DEFAULT_MODEL_ID = 'ecoli_core'


def normalise_model_id(model_id: str | None) -> str:
    candidate = str(model_id or DEFAULT_MODEL_ID).strip()
    if candidate not in MODEL_REGISTRY:
        raise ValueError(f'Unknown LabHero model_id: {candidate}')
    return candidate


def get_model_profile(model_id: str | None):
    model_id = normalise_model_id(model_id)
    return MODEL_REGISTRY[model_id]


@lru_cache(maxsize=None)
def load_model_template(model_id: str = DEFAULT_MODEL_ID):
    model_id = normalise_model_id(model_id)
    path = MODEL_REGISTRY[model_id]['file']
    if not path.is_file():
        raise FileNotFoundError(f'Model file is missing for {model_id}: {path}')
    return read_sbml_model(str(path))
