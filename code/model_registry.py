"""Model registry shared by the desktop UI and the future web client.

The existing missions 1-35 are intentionally still bound to ``ecoli_core``.
This module adds a model-aware layer without mutating those mission constants.
New simulators and future missions can select a model explicitly through a
stable ``model_id`` that is also sent to ``POST /simulate``.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from utils import get_resource_path


MODEL_REGISTRY = {
    'ecoli_core': {
        'display_name': 'E. coli Core',
        'organism_name': 'Escherichia coli',
        'model_file': 'data/models/e_coli_core.xml.gz',
        'metadata_file': 'data/models/e_coli_core_meta.json',
        'default_objective': 'BIOMASS_Ecoli_core_w_GAM',
        'supported_methods': ('FBA', 'pFBA', 'lMOMA', 'ROOM'),
        'production_flux_ids': (
            'EX_ac_e', 'EX_acald_e', 'EX_akg_e', 'EX_co2_e', 'EX_etoh_e',
            'EX_for_e', 'EX_fum_e', 'EX_gln__L_e', 'EX_glu__L_e',
            'EX_lac__D_e', 'EX_mal__L_e', 'EX_pyr_e', 'EX_succ_e',
        ),
        'exchange_report_ids': (
            'EX_glc__D_e', 'EX_fru_e', 'EX_ac_e', 'EX_acald_e', 'EX_pyr_e',
            'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e', 'EX_succ_e', 'EX_etoh_e',
            'EX_for_e', 'EX_lac__D_e', 'EX_nh4_e', 'EX_pi_e', 'EX_o2_e',
            'EX_co2_e', 'EX_h2o_e', 'EX_h_e', 'EX_gln__L_e', 'EX_glu__L_e',
        ),
        'gene_ui_mode': 'toggles',
        'objective_ui_mode': 'all',
        # The core model only has 20 exchanges, so the long-standing visual
        # lower/upper-bound toggle list remains compact and convenient.
        'environment_ui_mode': 'toggles',
        'room_reference_target': 'CYTBD',
    },
    'yeast_iMM904': {
        'display_name': 'Yeast iMM904',
        'organism_name': 'Saccharomyces cerevisiae',
        'model_file': 'data/models/iMM904.xml.gz',
        'metadata_file': 'data/models/iMM904_meta.json',
        'default_objective': 'BIOMASS_SC5_notrace',
        # Only methods benchmarked for the large model are exposed in the UI.
        # The backend contract remains method-capable, but lMOMA/ROOM stay
        # hidden until they are deliberately validated on iMM904.
        'supported_methods': ('FBA', 'pFBA'),
        # A compact production panel keeps the large yeast model usable while
        # still exposing the exchanges most useful for upcoming missions.
        'production_flux_ids': (
            'EX_etoh_e', 'EX_ac_e', 'EX_glyc_e', 'EX_co2_e', 'EX_pyr_e',
            'EX_succ_e', 'EX_for_e',
        ),
        'exchange_report_ids': (
            'EX_glc__D_e', 'EX_o2_e', 'EX_nh4_e', 'EX_pi_e', 'EX_so4_e',
            'EX_h2o_e', 'EX_h_e', 'EX_co2_e', 'EX_etoh_e', 'EX_ac_e',
            'EX_acald_e', 'EX_glyc_e', 'EX_pyr_e', 'EX_succ_e', 'EX_for_e',
        ),
        # 905 genes are too many to instantiate as toggle widgets on every
        # menu opening, especially in pygbag.  The yeast UI therefore uses a
        # comma-separated knockout field validated against the full catalogue.
        'gene_ui_mode': 'text',
        # 1577 objectives are unsuitable for one giant drop-down.  The yeast
        # objective menu uses an exact reaction-id text field validated against
        # the complete catalogue instead.
        'objective_ui_mode': 'text',
        # iMM904 has 164 exchange reactions.  Building one label plus two
        # pygame-menu switches for every exchange creates hundreds of widgets
        # before the simulator can even be displayed.  That is unnecessarily
        # expensive on desktop and especially unsuitable for a browser/WASM
        # main thread.  Large models therefore edit only explicit deviations
        # from the model-default medium through four compact text fields.
        'environment_ui_mode': 'compact_text',
        'room_reference_target': None,
    },
}

DEFAULT_MODEL_ID = 'ecoli_core'


def normalise_model_id(model_id):
    candidate = str(model_id or DEFAULT_MODEL_ID).strip()
    if candidate not in MODEL_REGISTRY:
        raise ValueError(f'Unknown LabHero model_id: {candidate}')
    return candidate


def get_model_profile(model_id=DEFAULT_MODEL_ID):
    model_id = normalise_model_id(model_id)
    return dict(MODEL_REGISTRY[model_id])


@lru_cache(maxsize=None)
def load_model_metadata(model_id=DEFAULT_MODEL_ID):
    model_id = normalise_model_id(model_id)
    path = get_resource_path(MODEL_REGISTRY[model_id]['metadata_file'])
    with open(path, encoding='utf-8') as handle:
        metadata = json.load(handle)
    metadata = dict(metadata)
    metadata.setdefault('model_id', model_id)
    metadata.setdefault('display_name', MODEL_REGISTRY[model_id]['display_name'])
    metadata.setdefault('organism_name', MODEL_REGISTRY[model_id]['organism_name'])
    metadata.setdefault('objective', MODEL_REGISTRY[model_id]['default_objective'])
    metadata.setdefault('gene_names', {})
    return metadata



def parse_gene_knockout_text(value, gene_ids, gene_names=None):
    """Return a full boolean gene payload from scalable text input.

    Tokens may be systematic gene ids or unique common names.  Unknown and
    ambiguous values are returned explicitly so callers never silently run a
    different genotype.
    """
    gene_ids = [str(gene_id) for gene_id in (gene_ids or [])]
    names = gene_names or {}
    id_by_upper = {gene_id.upper(): gene_id for gene_id in gene_ids}
    name_matches = {}
    for gene_id in gene_ids:
        common = str(names.get(gene_id, '') or '').strip()
        if common:
            name_matches.setdefault(common.upper(), []).append(gene_id)

    text = str(value or '').strip()
    raw_tokens = re.split(r'[,;\s]+', text) if text else []
    knocked_out = []
    unknown = []
    ambiguous = []
    for token in raw_tokens:
        key = token.strip().upper()
        if not key:
            continue
        if key in id_by_upper:
            gene_id = id_by_upper[key]
        elif len(name_matches.get(key, [])) == 1:
            gene_id = name_matches[key][0]
        elif len(name_matches.get(key, [])) > 1:
            ambiguous.append(token)
            continue
        else:
            unknown.append(token)
            continue
        if gene_id not in knocked_out:
            knocked_out.append(gene_id)

    payload = {gene_id: gene_id not in knocked_out for gene_id in gene_ids}
    return payload, knocked_out, unknown, ambiguous


def build_gene_knockout_preview(value, gene_ids, gene_names=None):
    """Return compact validation feedback for the scalable gene text field.

    The preview uses the exact same parser as the simulation request, so common
    names are canonicalised once and invalid/ambiguous tokens are never shown
    as accepted selections.
    """
    _payload, knockouts, unknown, ambiguous = parse_gene_knockout_text(
        value, gene_ids, gene_names
    )
    names = gene_names or {}

    problems = []
    if unknown:
        problems.append('Unknown gene id/name: ' + ', '.join(unknown))
    if ambiguous:
        problems.append('Ambiguous common gene name: ' + ', '.join(ambiguous))
    if problems:
        return 'Selection not registered:\n' + '\n'.join(
            f'- {problem}' for problem in problems
        )

    if not knockouts:
        return 'Registered knockouts: none (wild type).'

    labels = []
    for gene_id in knockouts:
        common_name = str(names.get(gene_id, '') or '').strip()
        if common_name and common_name != gene_id:
            labels.append(f'{gene_id} ({common_name})')
        else:
            labels.append(gene_id)
    return 'Registered knockouts:\n' + '\n'.join(f'- {label}' for label in labels)


def parse_exchange_id_text(value, exchange_ids):
    """Parse a compact list of exact exchange-reaction ids.

    Large models use this helper instead of instantiating hundreds of bound
    widgets.  Exact ids keep the operation deterministic and avoid silently
    applying a bound to the wrong metabolite when names are duplicated.
    """
    exchange_ids = [str(reaction_id) for reaction_id in (exchange_ids or [])]
    exact_by_upper = {reaction_id.upper(): reaction_id for reaction_id in exchange_ids}
    text = str(value or '').strip()
    raw_tokens = re.split(r'[,;\s]+', text) if text else []
    selected = []
    unknown = []
    for token in raw_tokens:
        key = token.strip().upper()
        if not key:
            continue
        reaction_id = exact_by_upper.get(key)
        if reaction_id is None:
            unknown.append(token)
            continue
        if reaction_id not in selected:
            selected.append(reaction_id)
    return selected, unknown


def build_compact_environment_payload(
    exchanges,
    *,
    lower_open_text='',
    lower_close_text='',
    upper_open_text='',
    upper_close_text='',
):
    """Build the full legacy bound-toggle payload from compact text edits.

    The returned dictionary has the exact same ``reaction_<i>_lb/ub`` schema
    consumed by the existing simulator and web request builder.  Therefore a
    large-model UI can remain lightweight without creating a second solver
    contract or weakening reproducibility.

    Returns ``(payload, errors)``.  Unknown ids and contradictory requests are
    explicit errors; no invalid token is silently ignored.
    """
    rows = list(exchanges or [])
    exchange_ids = [str(row.get('id')) for row in rows]

    lower_open, unknown_lower_open = parse_exchange_id_text(lower_open_text, exchange_ids)
    lower_close, unknown_lower_close = parse_exchange_id_text(lower_close_text, exchange_ids)
    upper_open, unknown_upper_open = parse_exchange_id_text(upper_open_text, exchange_ids)
    upper_close, unknown_upper_close = parse_exchange_id_text(upper_close_text, exchange_ids)

    errors = []
    unknown_groups = (
        ('lower bounds to open', unknown_lower_open),
        ('lower bounds to close', unknown_lower_close),
        ('upper bounds to open', unknown_upper_open),
        ('upper bounds to close', unknown_upper_close),
    )
    for label, unknown in unknown_groups:
        if unknown:
            errors.append(f"Unknown exchange id(s) in {label}: {', '.join(unknown)}")

    lower_conflicts = sorted(set(lower_open) & set(lower_close))
    upper_conflicts = sorted(set(upper_open) & set(upper_close))
    if lower_conflicts:
        errors.append(
            'The same lower bound cannot be both opened and closed: '
            + ', '.join(lower_conflicts)
        )
    if upper_conflicts:
        errors.append(
            'The same upper bound cannot be both opened and closed: '
            + ', '.join(upper_conflicts)
        )

    payload = {}
    index_by_id = {}
    for index, row in enumerate(rows):
        reaction_id = str(row.get('id'))
        index_by_id[reaction_id] = index
        try:
            lower_bound = float(row.get('lb', 0.0))
        except (TypeError, ValueError):
            lower_bound = 0.0
        try:
            upper_bound = float(row.get('ub', 0.0))
        except (TypeError, ValueError):
            upper_bound = 0.0
        payload[f'reaction_{index}_lb'] = bool(lower_bound != 0.0)
        payload[f'reaction_{index}_ub'] = bool(upper_bound != 0.0)

    for reaction_id in lower_open:
        payload[f'reaction_{index_by_id[reaction_id]}_lb'] = True
    for reaction_id in lower_close:
        payload[f'reaction_{index_by_id[reaction_id]}_lb'] = False
    for reaction_id in upper_open:
        payload[f'reaction_{index_by_id[reaction_id]}_ub'] = True
    for reaction_id in upper_close:
        payload[f'reaction_{index_by_id[reaction_id]}_ub'] = False

    return payload, errors

def build_compact_environment_preview(
    exchanges,
    *,
    lower_open_text='',
    lower_close_text='',
    upper_open_text='',
    upper_close_text='',
):
    """Return validation feedback for the compact large-model environment UI.

    This helper never mutates a model or launches a solver. It reuses the same
    strict payload validator as a real run, then explains the effective bound
    requests relative to the model-default medium.
    """
    rows = list(exchanges or [])
    exchange_ids = [str(row.get('id')) for row in rows]
    _payload, errors = build_compact_environment_payload(
        rows,
        lower_open_text=lower_open_text,
        lower_close_text=lower_close_text,
        upper_open_text=upper_open_text,
        upper_close_text=upper_close_text,
    )
    if errors:
        return 'Changes not registered:\n' + '\n'.join(
            f'- {error}' for error in errors
        )

    lower_open, _ = parse_exchange_id_text(lower_open_text, exchange_ids)
    lower_close, _ = parse_exchange_id_text(lower_close_text, exchange_ids)
    upper_open, _ = parse_exchange_id_text(upper_open_text, exchange_ids)
    upper_close, _ = parse_exchange_id_text(upper_close_text, exchange_ids)

    if not any((lower_open, lower_close, upper_open, upper_close)):
        return 'Registered environmental changes: none (model defaults).'

    row_by_id = {str(row.get('id')): row for row in rows}
    lines = []

    def number(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        if abs(numeric) < 1e-12:
            numeric = 0.0
        return f'{numeric:.1f}'

    def label(reaction_id):
        row = row_by_id.get(reaction_id, {})
        name = str(row.get('name') or '').strip()
        return f'{name} ({reaction_id})' if name and name != reaction_id else reaction_id

    for reaction_id in lower_open:
        default = float(row_by_id.get(reaction_id, {}).get('lb', 0.0) or 0.0)
        detail = (
            f'already model default {number(default)}'
            if default != 0.0
            else 'model default 0.0 -> standard uptake capacity'
        )
        lines.append(f'- {label(reaction_id)}: lower bound OPEN ({detail})')

    for reaction_id in lower_close:
        default = float(row_by_id.get(reaction_id, {}).get('lb', 0.0) or 0.0)
        detail = (
            'already model default 0.0'
            if default == 0.0
            else f'{number(default)} -> 0.0'
        )
        lines.append(f'- {label(reaction_id)}: lower bound CLOSED ({detail})')

    for reaction_id in upper_open:
        default = float(row_by_id.get(reaction_id, {}).get('ub', 0.0) or 0.0)
        detail = (
            f'already model default {number(default)}'
            if default != 0.0
            else 'model default 0.0 -> standard secretion capacity'
        )
        lines.append(f'- {label(reaction_id)}: upper bound OPEN ({detail})')

    for reaction_id in upper_close:
        default = float(row_by_id.get(reaction_id, {}).get('ub', 0.0) or 0.0)
        detail = (
            'already model default 0.0'
            if default == 0.0
            else f'{number(default)} -> 0.0'
        )
        lines.append(f'- {label(reaction_id)}: upper bound CLOSED ({detail})')

    return 'Registered environmental changes:\n' + '\n'.join(lines)


def _exchange_name_map(metadata):
    table = metadata.get('reactions_ex') or {}
    return {
        str(reaction_id): str(name)
        for reaction_id, name in zip(table.get('index') or [], table.get('name') or [])
    }


def _clean_exchange_name(name):
    name = str(name).replace(' exchange', '').replace('Exchange', '').strip()
    return name or 'Unknown product'


def build_ui_context(model_id=DEFAULT_MODEL_ID):
    """Return JSON-safe UI data for one simulator model."""
    model_id = normalise_model_id(model_id)
    profile = get_model_profile(model_id)
    metadata = load_model_metadata(model_id)

    genes = [str(value) for value in metadata.get('genes') or []]
    gene_names = {
        str(key): str(value or '')
        for key, value in (metadata.get('gene_names') or {}).items()
    }
    gene_labels = {
        gene_id: (
            f'{gene_id} ({gene_names[gene_id]})'
            if gene_names.get(gene_id) and gene_names[gene_id] != gene_id
            else gene_id
        )
        for gene_id in genes
    }

    exchange_table = metadata.get('reactions_ex') or {}
    exchange_ids = [str(value) for value in exchange_table.get('index') or []]
    exchange_names = [str(value) for value in exchange_table.get('name') or []]
    exchange_lbs = [float(value) for value in exchange_table.get('lb') or []]
    exchange_ubs = [float(value) for value in exchange_table.get('ub') or []]
    exchange_rows = [
        {'id': rid, 'name': name, 'lb': lb, 'ub': ub}
        for rid, name, lb, ub in zip(exchange_ids, exchange_names, exchange_lbs, exchange_ubs)
    ]

    all_table = metadata.get('reactions_all') or {}
    all_ids = [str(value) for value in all_table.get('index') or []]
    all_names = [str(value) for value in all_table.get('name') or []]
    if len(all_names) != len(all_ids):
        all_names = list(all_ids)

    if profile['objective_ui_mode'] == 'exchange_plus_default':
        objective_ids = [profile['default_objective']]
        objective_ids.extend(rid for rid in exchange_ids if rid != profile['default_objective'])
    else:
        objective_ids = list(all_ids)

    exchange_names_by_id = _exchange_name_map(metadata)
    production_flux_options = []
    for reaction_id in profile['production_flux_ids']:
        if reaction_id not in exchange_ids:
            continue
        product_name = _clean_exchange_name(exchange_names_by_id.get(reaction_id, reaction_id))
        production_flux_options.append({
            'id': reaction_id,
            'name': product_name,
            'label': f'{product_name} ({reaction_id})',
        })

    return {
        'model_id': model_id,
        'display_name': profile['display_name'],
        'organism_name': profile['organism_name'],
        'default_objective': profile['default_objective'],
        'supported_methods': list(profile['supported_methods']),
        'genes': genes,
        'gene_names': gene_names,
        'gene_labels': gene_labels,
        'gene_ui_mode': profile['gene_ui_mode'],
        'objective_ui_mode': profile['objective_ui_mode'],
        'environment_ui_mode': profile.get('environment_ui_mode', 'toggles'),
        'objective_ids': objective_ids,
        'all_reaction_ids': all_ids,
        'all_reaction_names': all_names,
        'exchanges': exchange_rows,
        'production_flux_options': production_flux_options,
        'production_flux_ids': [item['id'] for item in production_flux_options],
        'production_flux_labels': {item['id']: item['label'] for item in production_flux_options},
        'production_flux_names': {item['id']: item['name'] for item in production_flux_options},
        'exchange_report_ids': [
            reaction_id for reaction_id in profile['exchange_report_ids']
            if reaction_id in exchange_ids
        ],
        'room_reference_target': profile.get('room_reference_target'),
    }


@lru_cache(maxsize=None)
def load_local_model(model_id=DEFAULT_MODEL_ID):
    """Load one immutable model template lazily on desktop.

    Callers must copy the returned model before changing objectives or bounds.
    Keeping the cached template immutable prevents cross-request/cross-window
    state leakage and mirrors the backend's per-request isolation.
    """
    model_id = normalise_model_id(model_id)
    from cobra.io import read_sbml_model

    path = get_resource_path(MODEL_REGISTRY[model_id]['model_file'])
    return read_sbml_model(path)


class _IndexableList:
    def __init__(self, items):
        self._items = list(items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __iter__(self):
        return iter(self._items)


class _Series(_IndexableList):
    @property
    def iloc(self):
        return self


class ModelTable:
    """Tiny pandas-like facade used by the existing pygame-menu code."""
    def __init__(self, index, name=None, lb=None, ub=None):
        self.index = _IndexableList(index)
        self.name = _Series(name if name is not None else index)
        self.lb = _Series(lb) if lb is not None else None
        self.ub = _Series(ub) if ub is not None else None

    def __len__(self):
        return len(self.index)


def build_legacy_tables(model_id=DEFAULT_MODEL_ID):
    context = build_ui_context(model_id)
    exchange_rows = context['exchanges']
    reactions = ModelTable(
        index=[row['id'] for row in exchange_rows],
        name=[row['name'] for row in exchange_rows],
        lb=[row['lb'] for row in exchange_rows],
        ub=[row['ub'] for row in exchange_rows],
    )
    reactions_all = ModelTable(
        index=context['all_reaction_ids'],
        name=context['all_reaction_names'],
    )
    return reactions, reactions_all
