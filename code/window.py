import asyncio
import copy
import sys

import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from simulation import *
from functions import animation_text_save
from async_menu import run_menu
from scientific_display import GROWTH_RATE_UNIT, FLUX_UNIT, AGGREGATE_FLUX_UNIT, format_growth_rate, format_flux
from model_registry import (
    build_ui_context,
    build_legacy_tables,
    normalise_model_id,
    parse_gene_knockout_text,
    build_gene_knockout_preview,
    build_compact_environment_payload,
    build_compact_environment_preview,
)


_YIELD_ON_WEB = sys.platform == 'emscripten'


def _selected_menu_value(data, key):
    """Return a pygame-menu input value without corrupting plain text fields.

    DropSelect widgets expose a nested tuple/list value, while TextInput widgets
    expose a plain string.  Indexing a string as ``value[0][0]`` silently turns
    ``BIOMASS_SC5_notrace`` into ``B``; large-model text objectives therefore
    need an explicit string branch.
    """
    value = data.get(key)

    if isinstance(value, str):
        selected = value
    else:
        try:
            selected = value[0][0]
        except Exception:
            selected = str(value)
    return normalise_method_name(selected) if key == 'method' else selected


def _method_display_name(method_name):
    return LMOMA_DISPLAY_NAME if normalise_method_name(method_name) == 'lMOMA' else method_name


def _format_gene(gene_id, gene_labels=None):
    labels = GENE_LABELS if gene_labels is None else gene_labels
    return labels.get(gene_id, gene_id)


def _format_reaction_menu_label(reaction_name, reaction_id):
    return f"{reaction_name} ({reaction_id})"


def _normalise_gene_search_text(value):
    """Normalise gene search text so b1241, 1241, adhE or adh e all match."""
    return ''.join(
        char.lower()
        for char in str(value)
        if char.isalnum()
    )


def _gene_matches_search(gene_id, search_text, gene_names=None, gene_labels=None):
    query = _normalise_gene_search_text(search_text)
    if not query:
        return True

    names = GENE_NAMES if gene_names is None else gene_names
    labels = GENE_LABELS if gene_labels is None else gene_labels
    gene_name = names.get(gene_id, '')
    gene_label = labels.get(gene_id, gene_id)
    gene_number = gene_id[1:] if gene_id.startswith('b') else gene_id

    searchable_values = (
        gene_id,
        gene_number,
        gene_name,
        gene_label,
        f'{gene_id}{gene_name}',
        f'{gene_name}{gene_id}',
    )

    return any(
        query in _normalise_gene_search_text(value)
        for value in searchable_values
    )



def _reaction_matches_search(reaction_id, reaction_name, search_text):
    """Return whether an exchange reaction matches an id/name search."""
    query = _normalise_gene_search_text(search_text)
    if not query:
        return True

    searchable_values = (
        reaction_id,
        reaction_name,
        f'{reaction_name}{reaction_id}',
        f'{reaction_id}{reaction_name}',
    )
    return any(
        query in _normalise_gene_search_text(value)
        for value in searchable_values
    )


def _parse_gene_knockout_text(value, gene_ids, gene_names=None):
    """Backward-compatible UI wrapper around the model-registry parser."""
    return parse_gene_knockout_text(value, gene_ids, gene_names)


def _build_clean_gene_data(raw_gene_data, gene_ids=None):
    """Keep only real model genes, ignoring UI-only widgets like search fields."""
    active_gene_ids = list(GENES if gene_ids is None else gene_ids)
    return {
        gene_id: bool((raw_gene_data or {}).get(gene_id, True))
        for gene_id in active_gene_ids
    }


def _build_gene_summary(genes, gene_labels=None):
    knocked_out_genes = [
        gene_id for gene_id, is_active in genes.items()
        if not is_active
    ]

    if not knocked_out_genes:
        return 'No gene knockouts.'

    return '\n'.join(
        f'- {_format_gene(gene_id, gene_labels)}'
        for gene_id in knocked_out_genes
    )



def _build_clean_reaction_data(raw_reaction_data, reactions_table=None):
    """Keep only scientific LB/UB toggles, excluding UI-only search fields."""
    table = REACTIONS if reactions_table is None else reactions_table
    raw_reaction_data = raw_reaction_data or {}
    clean = {}

    for i in range(len(table.index)):
        lb_key = f'reaction_{i}_lb'
        ub_key = f'reaction_{i}_ub'
        clean[lb_key] = bool(
            raw_reaction_data.get(lb_key, bool(table.lb.iloc[i] != 0))
        )
        clean[ub_key] = bool(
            raw_reaction_data.get(ub_key, bool(table.ub.iloc[i] != 0))
        )

    return clean


def _build_environmental_summary(reactions):
    changed_conditions = []
    reaction_values = list(reactions.values())

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = reaction_values[lb_index]
        upper_bound_open = reaction_values[ub_index]

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        if (
            lower_bound_open != default_lower_bound_open
            or upper_bound_open != default_upper_bound_open
        ):
            reaction_id = REACTIONS.index[i]
            reaction_name = REACTIONS.name.iloc[i]

            lower_bound_value = resolve_exchange_bound_value(
                REACTIONS.lb.iloc[i], lower_bound_open, 'lower'
            )
            upper_bound_value = resolve_exchange_bound_value(
                REACTIONS.ub.iloc[i], upper_bound_open, 'upper'
            )

            changed_conditions.append(
                f'- {reaction_name} ({reaction_id}): '
                f'Lower Bound {"Open" if lower_bound_open else "Closed"} ({lower_bound_value} {FLUX_UNIT}), '
                f'Upper Bound {"Open" if upper_bound_open else "Closed"} ({upper_bound_value} {FLUX_UNIT})'
            )

    if not changed_conditions:
        return 'No environmental changes.'

    return '\n'.join(changed_conditions)



def _build_environmental_summary_for_table(reactions, reactions_table):
    changed_conditions = []
    reaction_values = list((reactions or {}).values())

    for i in range(len(reactions_table.index)):
        lb_key = f'reaction_{i}_lb'
        ub_key = f'reaction_{i}_ub'
        if lb_key in (reactions or {}) and ub_key in (reactions or {}):
            lower_bound_open = bool(reactions[lb_key])
            upper_bound_open = bool(reactions[ub_key])
        else:
            lb_index = i * 2
            ub_index = lb_index + 1
            if ub_index >= len(reaction_values):
                break
            lower_bound_open = bool(reaction_values[lb_index])
            upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = reactions_table.lb.iloc[i] != 0
        default_upper_bound_open = reactions_table.ub.iloc[i] != 0
        if lower_bound_open != default_lower_bound_open or upper_bound_open != default_upper_bound_open:
            reaction_id = reactions_table.index[i]
            reaction_name = reactions_table.name.iloc[i]
            lower_bound_value = resolve_exchange_bound_value(
                reactions_table.lb.iloc[i], lower_bound_open, 'lower'
            )
            upper_bound_value = resolve_exchange_bound_value(
                reactions_table.ub.iloc[i], upper_bound_open, 'upper'
            )
            changed_conditions.append(
                f'- {reaction_name} ({reaction_id}): '
                f'Lower Bound {"Open" if lower_bound_open else "Closed"} ({lower_bound_value} {FLUX_UNIT}), '
                f'Upper Bound {"Open" if upper_bound_open else "Closed"} ({upper_bound_value} {FLUX_UNIT})'
            )

    return '\n'.join(changed_conditions) if changed_conditions else 'No environmental changes.'


def _build_production_flux_summary_for_options(production_flux_data, options):
    selected = [option for option in options if bool((production_flux_data or {}).get(option['id'], False))]
    if not selected:
        return 'No production fluxes selected.'
    return '\n'.join(f"- {option['label']}" for option in selected)


def _build_clean_production_flux_data(raw_flux_data):
    """Keep only curated production flux toggles from the menu input data."""
    raw_flux_data = raw_flux_data or {}
    return {
        option['id']: bool(raw_flux_data.get(option['id'], False))
        for option in PRODUCTION_FLUX_OPTIONS
    }


def _selected_production_flux_ids(production_flux_data):
    return [
        option['id']
        for option in PRODUCTION_FLUX_OPTIONS
        if bool(production_flux_data.get(option['id'], False))
    ]


def _build_production_flux_summary(production_flux_data):
    selected_ids = _selected_production_flux_ids(production_flux_data)
    if not selected_ids:
        return 'No production fluxes selected.'

    return '\n'.join(
        f"- {PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)}"
        for reaction_id in selected_ids
    )


def _build_production_fluxes_text(production_fluxes):
    if not production_fluxes or not production_fluxes.get('selected_ids'):
        return ''

    lines = [
        'Production fluxes tracked:',
        '(positive exchange flux = product secreted/exported)'
    ]

    if production_fluxes.get('error'):
        lines.append(f"Error: {production_fluxes.get('error')}")
        return '\n'.join(lines)

    items = production_fluxes.get('items') or []
    if not items:
        lines.append('No flux values were returned for the selected products.')
        return '\n'.join(lines)

    for item in items:
        label = item.get('label') or item.get('reaction_id')
        if item.get('error'):
            lines.append(f"- {label}: not available")
        else:
            lines.append(f"- {label}: {format_flux(item.get('production_flux', 0.0))}")

    return '\n'.join(lines)



def _exchange_items_by_id(exchange_fluxes):
    items = {}
    if not exchange_fluxes or exchange_fluxes.get('error'):
        return items

    for item in exchange_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if reaction_id:
            items[reaction_id] = item
    return items


def _clean_report_number(value, tolerance=0.0005):
    """Prepare a value for three-decimal reports without displaying -0.000."""
    numeric = float(value)
    if abs(numeric) < tolerance:
        numeric = 0.0
    return numeric


def _format_exchange_flux_line(reaction_id, items_by_id):
    item = items_by_id.get(reaction_id)
    if not item:
        return f'- {reaction_id}: not measured'

    label = item.get('label') or reaction_id
    if item.get('error'):
        return f'- {label}: not available'

    raw_flux = _clean_report_number(item.get('raw_flux', 0.0))
    uptake_flux = _clean_report_number(item.get('uptake_flux', 0.0))
    secretion_flux = _clean_report_number(item.get('secretion_flux', 0.0))

    if uptake_flux > 0.001:
        status = f'consumed / uptake {format_flux(uptake_flux)}'
    elif secretion_flux > 0.001:
        status = f'secreted / export {format_flux(secretion_flux)}'
    else:
        status = 'no exchange detected'

    return f'- {label}: raw flux {format_flux(raw_flux)} -> {status}'


def _build_exchange_flux_report_text(exchange_fluxes):
    if not exchange_fluxes:
        return 'Exchange Flux Report\n\nRun a simulation first to generate exchange-flux evidence.'

    if exchange_fluxes.get('error'):
        return f"Exchange Flux Report\n\nError: {exchange_fluxes.get('error')}"

    items_by_id = _exchange_items_by_id(exchange_fluxes)
    model_id = exchange_fluxes.get('model_id', 'ecoli_core')
    model_line = None
    if model_id != 'ecoli_core':
        try:
            context = build_ui_context(model_id)
            model_line = f"Model: {context['display_name']} | {context['organism_name']}"
        except Exception:
            model_line = f'Model: {model_id}'

    sections = [
        (
            'Carbon and medium sources',
            ['EX_glc__D_e', 'EX_fru_e', 'EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e', 'EX_succ_e', 'EX_gln__L_e', 'EX_glu__L_e']
        ),
        (
            'Essential nutrients and respiration',
            ['EX_nh4_e', 'EX_pi_e', 'EX_o2_e', 'EX_co2_e', 'EX_h2o_e', 'EX_h_e']
        ),
        (
            'Products and byproducts',
            ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e', 'EX_co2_e']
        ),
    ]

    lines = [
        'Exchange Flux Report',
        '',
    ]
    if model_line:
        lines.extend([model_line, ''])
    lines.extend([
        'Exchange reactions connect the cell to the medium.',
        'Negative flux means uptake/consumption. Positive flux means secretion/export.',
        '',
    ])

    rendered_ids = set()
    for title, reaction_ids in sections:
        measured_ids = [reaction_id for reaction_id in reaction_ids if reaction_id in items_by_id]
        if not measured_ids:
            continue
        lines.append(f'{title}:')
        for reaction_id in measured_ids:
            lines.append(_format_exchange_flux_line(reaction_id, items_by_id))
            rendered_ids.add(reaction_id)
        lines.append('')

    additional_ids = [reaction_id for reaction_id in items_by_id if reaction_id not in rendered_ids]
    if additional_ids:
        lines.append('Additional measured exchanges:')
        for reaction_id in additional_ids:
            lines.append(_format_exchange_flux_line(reaction_id, items_by_id))
        lines.append('')

    lines.extend([
        'Use this report to verify what the model consumes from the medium and what it secretes after the simulation.',
        '',
        'FBA note: this is one optimal flux distribution returned by the solver. Alternative optimal solutions may preserve the same objective value while changing some individual byproduct fluxes.',
    ])
    return '\n'.join(lines)



def _format_sweep_number(value):
    try:
        return f'{float(value):.3f}'
    except Exception:
        return str(value)


def _build_bound_sweep_report_text(sweep_data):
    if not sweep_data:
        return 'Bound Sweep Report\n\nRun a Bound Sweep to generate sensitivity data.'

    if sweep_data.get('error') and not sweep_data.get('rows'):
        return f"Bound Sweep Report\n\nError: {sweep_data.get('error')}"

    reaction_id = sweep_data.get('reaction_id')
    reaction_name = sweep_data.get('reaction_name') or reaction_id
    bound = sweep_data.get('bound')
    bound_label = sweep_data.get('bound_label') or bound
    tracked_fluxes = sweep_data.get('tracked_fluxes') or []
    rows = sweep_data.get('rows') or []

    if bound == 'upper':
        bound_value_label = 'UB value'
        measured_label = 'Tested export'
    else:
        bound_value_label = 'LB value'
        if reaction_id == 'EX_o2_e':
            measured_label = 'O2 uptake'
        elif reaction_id == 'EX_glc__D_e':
            measured_label = 'Glucose uptake'
        else:
            measured_label = 'Tested uptake'

    if sweep_data.get('model_id') == 'yeast_iMM904':
        lines = [
            'Bound Sweep Report', '',
            f'Variable tested: {reaction_name} ({reaction_id}) {bound_label}',
            f"Method: {sweep_data.get('method')} | Objective: {sweep_data.get('objective')}",
            'The glucose bound varies while the base oxygen bound remains fixed.', '',
            'Rows:',
            f'Glucose LB ({FLUX_UNIT}) | growth rate ({GROWTH_RATE_UNIT}) | glucose uptake ({FLUX_UNIT}) | O2 uptake ({FLUX_UNIT}) | ethanol ({FLUX_UNIT}) | CO2 ({FLUX_UNIT}) | total absolute flux ({AGGREGATE_FLUX_UNIT})',
        ]
        for row in rows:
            tracked = row.get('tracked_flux_values') or {}
            diagnostics = row.get('method_diagnostics') or {}
            status_note = '' if row.get('status') == 'ok' else f" {row.get('status', 'unknown')}"
            lines.append(
                f"{_format_sweep_number(row.get('bound_value'))} | "
                f"{_format_sweep_number(row.get('growth_value'))}{status_note} | "
                f"{_format_sweep_number(row.get('tested_reaction_uptake'))} | "
                f"{_format_sweep_number(row.get('oxygen_uptake'))} | "
                f"{_format_sweep_number(tracked.get('EX_etoh_e'))} | "
                f"{_format_sweep_number(tracked.get('EX_co2_e'))} | "
                f"{_format_sweep_number(diagnostics.get('total_absolute_flux'))}"
            )
        if len(rows) >= 2:
            try:
                first, last = rows[0], rows[-1]
                lines.extend([
                    '', 'Trend summary:',
                    f"- Growth-rate change from first to last point: {format_growth_rate(float(last.get('growth_value')) - float(first.get('growth_value')))}",
                    f"- Glucose uptake change: {format_flux(float(last.get('tested_reaction_uptake')) - float(first.get('tested_reaction_uptake')))}",
                    f"- O2 uptake change: {format_flux(float(last.get('oxygen_uptake')) - float(first.get('oxygen_uptake')))}",
                ])
            except Exception:
                pass
        lines.extend([
            '', 'Interpretation guide:',
            '- Increasing glucose availability can make a different fixed constraint become binding.',
            '- Compare realised O2 uptake with its configured capacity; configured does not automatically mean binding.',
            '- Then inspect when ethanol secretion becomes positive. Derive the transition from the visible rows.',
        ])
        return '\n'.join(lines)

    lines = [
        'Bound Sweep Report',
        '',
        f'Variable tested: {reaction_name} ({reaction_id}) {bound_label}',
        f"Method: {sweep_data.get('method')} | Objective: {sweep_data.get('objective')}",
        'A sweep runs the same setup several times while changing only this bound.',
        '',
        'Rows:',
        f'{bound_value_label} ({FLUX_UNIT}) | growth rate ({GROWTH_RATE_UNIT}) | {measured_label} ({FLUX_UNIT}) | tracked products ({FLUX_UNIT})',
    ]

    measured_values = []
    for row in rows:
        values = row.get('tracked_flux_values') or {}
        product_parts = []
        for flux_id in tracked_fluxes:
            label = PRODUCTION_FLUX_NAMES.get(flux_id, flux_id)
            product_parts.append(f"{label}: {_format_sweep_number(values.get(flux_id))}")
        product_text = '; '.join(product_parts) if product_parts else 'none'
        if bound == 'upper':
            measured = row.get('tested_reaction_raw_flux')
        else:
            measured = row.get('tested_reaction_uptake')
            if measured is None:
                measured = row.get('oxygen_uptake')
        measured_values.append(measured)
        status_note = '' if row.get('status') == 'ok' else f" {row.get('status', 'unknown')}"
        lines.append(
            f"{_format_sweep_number(row.get('bound_value'))} | "
            f"{_format_sweep_number(row.get('growth_value'))}{status_note} | "
            f"{_format_sweep_number(measured)} | "
            f"{product_text}"
        )

    if len(rows) >= 2:
        first = rows[0]
        last = rows[-1]
        try:
            growth_drop = float(first.get('growth_value', 0.0)) - float(last.get('growth_value', 0.0))
            first_measured = measured_values[0]
            last_measured = measured_values[-1]
            measured_drop = float(first_measured or 0.0) - float(last_measured or 0.0)
            lines.extend([
                '',
                'Trend summary:',
                f"- Growth-rate change from first to last point: {format_growth_rate(growth_drop)} drop",
                f"- {measured_label} change from first to last point: {format_flux(measured_drop)} drop",
            ])
        except Exception:
            pass

    if reaction_id == 'EX_nh4_e' and bound == 'lower':
        guide_lines = [
            '- Lower bound closer to 0 means less ammonium can be consumed.',
            '- Compare the non-limiting point with the first point where growth decreases.',
            '- A secretion may appear at the onset of limitation and then change non-linearly across tighter bounds.',
        ]
    elif reaction_id == 'EX_co2_e' and bound == 'upper':
        guide_lines = [
            '- An upper-bound cap is non-binding while realised CO2 export remains below it.',
            '- Identify the first cap that the solution reaches, then inspect which tracked secretion appears.',
            '- Compare the next tighter cap to determine whether another compensatory route activates later.',
        ]
    elif reaction_id == 'EX_glc__D_e':
        guide_lines = [
            '- Lower bound closer to 0 means less glucose can be consumed.',
            '- When carbon intake becomes limiting, growth and secretion should fall together.',
            '- Do not read only the final row: identify the trend and the collapse zone.',
        ]
    elif reaction_id == 'EX_o2_e':
        guide_lines = [
            '- Lower bound closer to 0 means less oxygen can be consumed.',
            '- If growth and product secretion change across the rows, the model is sensitive to oxygen availability.',
            '- This is different from Compare Runs: here you read a trend across several points, not just A vs B.',
        ]
    else:
        guide_lines = [
            '- Lower bound closer to 0 means less of the selected alternative source can be consumed.',
            '- A useful source should support growth when available and lose growth when the bound closes.',
            '- Check both source uptake and product/byproduct changes before delivering the mission.',
        ]

    lines.extend(['', 'Interpretation guide:'] + guide_lines)
    return '\n'.join(lines)


def _build_mission26_text(report_data):
    return build_mission26_interaction_report_text(report_data)


def _build_mission30_text(report_data):
    return build_mission30_redundancy_threshold_report_text(report_data)


def _build_mission31_text(report_data):
    return build_mission31_environmental_suppression_report_text(report_data)


def _build_mission32_text(report_data):
    return build_mission32_respiratory_cut_set_report_text(report_data)


def _build_mission33_text(report_data):
    return build_mission33_reference_adjustment_report_text(report_data)


def _build_mission34_text(report_data):
    return build_mission34_shared_subunit_report_text(report_data)


def _build_mission35_text(report_data):
    return build_mission35_final_certification_report_text(report_data)

def _visible_biomass_flux(results):
    """Read predicted biomass from the same visible simulation solution."""
    try:
        production_data = results[2]
        if isinstance(production_data, dict):
            value = production_data.get('biomass_raw')
            if value is not None:
                return max(float(value), 0.0)
            biomass_reaction = production_data.get('biomass_reaction')
            if biomass_reaction and results[0] == biomass_reaction:
                return max(float(results[1]), 0.0)
    except Exception:
        pass

    try:
        if results[0] == MISSION07_BIOMASS_OBJECTIVE:
            return max(float(results[1]), 0.0)
    except Exception:
        pass
    return None


def _build_simulation_results_text(results):
    try:
        objective_name = results[0]
        objective_result = results[1]
    except Exception:
        return str(results)

    diagnostics = {}
    try:
        diagnostics = (results[2] or {}).get('method_diagnostics') or {}
    except Exception:
        diagnostics = {}
    method_name = diagnostics.get('method')
    model_id = diagnostics.get('model_id')
    model_prefix = ''
    if model_id and model_id != 'ecoli_core':
        try:
            context = build_ui_context(model_id)
            model_prefix = f"Model: {context['display_name']} | {context['organism_name']}\n\n"
        except Exception:
            model_prefix = f'Model: {model_id}\n\n'
    biomass_reaction = MISSION07_BIOMASS_OBJECTIVE
    try:
        biomass_reaction = (results[2] or {}).get('biomass_reaction') or biomass_reaction
    except Exception:
        pass

    text = model_prefix + f'Primary objective:\n{objective_name}'
    if objective_name == biomass_reaction:
        text += f'\n{format_growth_rate(objective_result)}'
        text = text.replace(
            f'Primary objective:\n{objective_name}\n',
            f'Primary objective:\n{objective_name}\nPredicted growth rate: ',
            1,
        )
    else:
        objective_heading = 'Primary objective flux' if method_name == 'pFBA' else 'Objective flux'
        text += f'\n{objective_heading}: {format_flux(objective_result)}'

    if method_name == 'pFBA':
        total_flux = diagnostics.get('total_absolute_flux')
        active_count = diagnostics.get('active_reaction_count')
        text += '\n\npFBA secondary criterion:'
        if total_flux is not None:
            text += f'\nTotal absolute flux: {_clean_report_number(total_flux):.3f} {AGGREGATE_FLUX_UNIT}'
        else:
            text += '\nTotal absolute flux: not available'
        if active_count is not None:
            text += f'\nActive reactions: {int(active_count)}'
        text += '\nThe secondary value is not the selected primary objective flux.'
    elif method_name == 'lMOMA':
        adjustment = diagnostics.get('method_score')
        text += f'\n\n{LMOMA_DISPLAY_NAME} adjustment criterion:'
        if adjustment is not None:
            text += f'\nTotal absolute flux adjustment: {_clean_report_number(adjustment):.3f} {AGGREGATE_FLUX_UNIT}'
        else:
            text += '\nTotal absolute flux adjustment: not available'
        text += '\nThe adjustment score is not biomass; biomass is the selected reaction flux above.'
    elif method_name == 'ROOM':
        score = diagnostics.get('method_score')
        text += '\n\nROOM significant-change criterion:'
        if score is not None:
            text += f'\nSignificant flux changes: {_clean_report_number(score):.3f}'
        else:
            text += '\nSignificant flux changes: not available'
        text += '\n\nExplicit reference:'
        text += f"\nMethod: {diagnostics.get('reference_method') or 'not available'}"
        reference_growth = diagnostics.get('reference_primary_objective_flux')
        reference_target = diagnostics.get('reference_target_reaction')
        reference_target_flux = diagnostics.get('reference_target_flux')
        reference_cytbd = diagnostics.get('reference_cytbd_flux')
        if objective_name == biomass_reaction:
            if reference_growth is not None:
                text += f'\nReference predicted growth rate: {format_growth_rate(reference_growth)}'
            else:
                text += '\nReference predicted growth rate: not available'
        else:
            if reference_growth is not None:
                text += f'\nReference objective flux: {format_flux(reference_growth)}'
            else:
                text += '\nReference objective flux: not available'
        if reference_cytbd is not None:
            text += f'\nReference CYTBD flux: {format_flux(reference_cytbd)}'
        else:
            text += '\nReference CYTBD flux: not available'
        mutant_cytbd = diagnostics.get('cytbd_flux')
        if mutant_cytbd is not None:
            text += f'\nMutant CYTBD flux: {format_flux(mutant_cytbd)}'
        else:
            text += '\nMutant CYTBD flux: not available'
        same_environment = diagnostics.get('reference_uses_same_environment')
        no_knockouts = diagnostics.get('reference_has_no_gene_knockouts')
        text += f"\nSame environment: {'yes' if same_environment is True else 'no'}"
        text += f"\nReference genotype: {'wild type' if no_knockouts is True else 'not confirmed'}"
        text += f"\nROOM parameters: delta {diagnostics.get('room_delta')}, epsilon {diagnostics.get('room_epsilon')}, integer {'yes' if diagnostics.get('room_linear') is False else 'no'}"
        solver_name = diagnostics.get('room_solver')
        if solver_name:
            text += f'\nMILP solver: {solver_name}'
        time_limit = diagnostics.get('room_time_limit_seconds')
        if time_limit is not None:
            text += f' (safety limit {float(time_limit):g} s)'
        text += '\nThe ROOM score is not biomass, total absolute flux or the active-reaction count.'
    biomass_flux = _visible_biomass_flux(results)
    biomass_reaction = MISSION07_BIOMASS_OBJECTIVE
    try:
        biomass_reaction = (results[2] or {}).get('biomass_reaction') or biomass_reaction
    except Exception:
        pass
    if objective_name != biomass_reaction and biomass_flux is not None:
        biomass_flux = _clean_report_number(biomass_flux)
        text += f'\n\nPredicted growth rate: {format_growth_rate(biomass_flux)}'
        if biomass_flux <= MISSION07_FLUX_TOLERANCE:
            text += '\nGrowth interpretation: no predicted growth in this solution.'

    production_text = ''
    try:
        production_text = _build_production_fluxes_text(results[2])
    except Exception:
        production_text = ''

    if production_text:
        text += '\n\n' + production_text

    return text





def _build_mission27_text(report_data):
    return build_mission27_rescue_report_text(report_data)

def _build_mission28_text(report_data):
    return build_mission28_dependency_report_text(report_data)


def _build_mission29_text(report_data):
    return build_mission29_redundancy_report_text(report_data)

def _build_mission07_text(objective_data):
    return build_mission07_objective_comparison_report_text(objective_data)


def _build_mission08_text(objective_data):
    return build_mission08_constraint_comparison_report_text(objective_data)



def _build_mission09_text(design_data):
    return build_mission09_evidence_report_text(design_data)



def _build_mission10_text(design_data):
    return build_mission10_evidence_report_text(design_data)



def _build_mission11_text(fingerprint_data):
    return build_mission11_fingerprint_report_text(fingerprint_data)


def _build_mission12_text(byproduct_data):
    return build_mission12_comparison_report_text(byproduct_data)


def _build_mission13_text(method_data):
    return build_mission13_parsimony_report_text(method_data)



def _build_mission14_text(reduction_data):
    return build_mission14_tradeoff_report_text(reduction_data)



def _build_mission15_text(report_data):
    return build_mission15_viability_report_text(report_data)


def _build_mission16_text(report_data):
    return build_mission16_context_report_text(report_data)


def _build_mission17_text(report_data):
    return build_mission17_essential_routes_report_text(report_data)


def _build_mission18_text(report_data):
    return build_mission18_binding_export_report_text(report_data)

def _build_mission04_text(production_data):
    return build_mission04_evidence_report_text(production_data)



def _build_mission05_text(production_data):
    return build_mission05_evidence_report_text(production_data)


def _build_challenge_text(challenge_data):
    return build_mission06_challenge_report_text(challenge_data)

def _add_summary_section(menu, title, text):
    menu.add.label(title, font_size=32, font_color=(20, 0, 150))
    menu.add.vertical_margin(10)
    menu.add.label(
        text,
        wordwrap=True,
        padding=(20, 20, 20, 20),
        background_color='white',
        font_size=24
    )
    menu.add.vertical_margin(25)

def _build_mission19_text(report_data):
    return build_mission19_method_comparison_report_text(report_data)

def _build_mission20_text(report_data):
    return build_mission20_context_report_text(report_data)



def _build_mission01_text(compare_data):
    if not compare_data:
        return 'Mission 01 Anaerobic Growth\n\nRun two simulations to generate the controlled comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 01 Anaerobic Growth\n\n{compare_data.get('error')}"

    baseline_status = (
        'Baseline: valid aerobic FBA run found.'
        if compare_data.get('baseline_run_found')
        else 'Baseline: missing. Run FBA with biomass objective and the unchanged default environment.'
    )
    anaerobic_status = (
        'Anaerobic run: valid oxygen-blocked run found.'
        if compare_data.get('anaerobic_run_found')
        else 'Anaerobic run: missing. Keep the setup unchanged and close only the oxygen lower bound.'
    )
    viability_status = (
        'Viability: the model still predicts growth without oxygen.'
        if compare_data.get('anaerobic_growth_viable')
        else 'Viability: anaerobic growth is not yet positive/viable.'
    )
    growth_status = (
        'Comparison: anaerobic growth is lower than aerobic growth.'
        if compare_data.get('growth_decreased')
        else 'Comparison: a clear growth decrease has not been demonstrated yet.'
    )
    oxygen_status = (
        'Oxygen evidence: baseline uptake is positive and anaerobic uptake is zero.'
        if compare_data.get('baseline_uses_oxygen') and compare_data.get('anaerobic_oxygen_blocked')
        else 'Oxygen evidence: inspect EX_o2_e in the Exchange Flux Report.'
    )
    final_status = (
        'Mission comparison ready. Return to Dr. Martinez and deliver the results.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Run the aerobic baseline first, then change only oxygen.'
    )

    def fmt_growth(value):
        return format_growth_rate(value)

    def fmt_flux(value):
        return format_flux(value)

    return (
        'Mission 01 Anaerobic Growth\n\n'
        f"Method: {compare_data.get('target_method')}\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Oxygen exchange: {compare_data.get('oxygen_reaction')}\n\n"
        f"Growth comparison:\n"
        f"- Aerobic baseline: {fmt_growth(compare_data.get('baseline_growth'))}\n"
        f"- Anaerobic growth: {fmt_growth(compare_data.get('anaerobic_growth'))}\n"
        f"- Growth-rate decrease: {fmt_growth(compare_data.get('growth_drop'))}\n\n"
        f"Oxygen uptake magnitude:\n"
        f"- Aerobic baseline: {fmt_flux(compare_data.get('baseline_oxygen_uptake'))}\n"
        f"- Anaerobic run: {fmt_flux(compare_data.get('anaerobic_oxygen_uptake'))}\n"
        f"  (Uptake is shown as a positive magnitude; raw EX_o2_e flux is negative when oxygen is consumed.)\n\n"
        f"{baseline_status}\n"
        f"{anaerobic_status}\n"
        f"{viability_status}\n"
        f"{growth_status}\n"
        f"{oxygen_status}\n\n"
        f"FBA interpretation: the mission validates growth and oxygen evidence, not one unique byproduct profile; alternative optimal flux distributions may exist.\n\n"
        f"{final_status}"
    )


def _build_mission21_text(report_data):
    return build_mission21_compensatory_report_text(report_data)


def _build_mission22_text(report_data):
    return build_mission22_phenotype_equivalence_report_text(report_data)

def _build_mission23_text(report_data):
    return build_mission23_nutrient_sensitivity_report_text(report_data)


def _build_mission24_text(report_data):
    return build_mission24_export_capacity_report_text(report_data)


def _build_mission25_text(report_data):
    return build_mission25_context_report_text(report_data)


class Window:
    def __init__(self, toggle_menu, player, model_id='ecoli_core') -> None:

        # general setup
        self.player = player
        self.toggle_menu = toggle_menu
        self.model_id = normalise_model_id(model_id)
        self.model_context = build_ui_context(self.model_id)
        self.model_reactions, self.model_reactions_all = build_legacy_tables(self.model_id)
        # Preserve the richer E. coli display names already loaded by the
        # legacy module while using metadata-driven names for yeast.
        if self.model_id == 'ecoli_core':
            self.model_reactions = REACTIONS
            self.model_reactions_all = REACTIONS_v0
            self.model_context['genes'] = list(GENES)
            self.model_context['gene_names'] = dict(GENE_NAMES)
            self.model_context['gene_labels'] = dict(GENE_LABELS)
            self.model_context['production_flux_options'] = list(PRODUCTION_FLUX_OPTIONS)
            self.model_context['production_flux_ids'] = list(PRODUCTION_FLUX_REACTION_IDS)
            self.model_context['production_flux_labels'] = dict(PRODUCTION_FLUX_LABELS)
            self.model_context['production_flux_names'] = dict(PRODUCTION_FLUX_NAMES)
            self.model_context['default_objective'] = str(objective)
        self.display_surface = pygame.display.get_surface()
        # font_path = get_resource_path('font/LycheeSoda.ttf')
        # font2_path = get_resource_path('font/NotoColorEmoji-Regular.ttf')
        # self.font = pygame.font.Font(font_path,30)
        self.results = ''

        # self.index = 0
        self.timer = Timer(200)



    async def setup(self):

        # Model-local aliases keep the long-standing Mission 1-35 code bound
        # to E. coli while allowing this same Window class to render iMM904.
        REACTIONS = self.model_reactions
        REACTIONS_v0 = self.model_reactions_all
        GENES = list(self.model_context['genes'])
        GENE_NAMES = self.model_context['gene_names']
        GENE_LABELS = self.model_context['gene_labels']
        PRODUCTION_FLUX_OPTIONS = self.model_context['production_flux_options']
        PRODUCTION_FLUX_REACTION_IDS = self.model_context['production_flux_ids']
        PRODUCTION_FLUX_LABELS = self.model_context['production_flux_labels']
        PRODUCTION_FLUX_NAMES = self.model_context['production_flux_names']
        objective = self.model_context['default_objective']
        is_ecoli = self.model_id == 'ecoli_core'

        ecoli_rip = get_resource_path('graphics/environment/ecoli_rip.jpg')
        
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title=('Simulation Menu' if is_ecoli else f"{self.model_context['display_name']} Simulator"),
            width=1280,
        )

        menu_genes = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Genes',
            width=1280
        )


        menu_reactions = pygame_menu.Menu(
            height=720,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Environmental Conditions',
            width=1280
        )

        # MENU REACTIONS
        menu_reactions.add.vertical_margin(50)
        if is_ecoli and '02' in self.player.missions_activated and '02' not in self.player.missions_completed:
            environment_help = (
                'Mission 02 reflection:\n'
                'Use exchange reactions to design a fair nutrient-replacement experiment. '
                'Change the carbon source while keeping unrelated biological assumptions comparable. '
                'Optional step-by-step hints are available from Dr. Martinez.'
            )
        else:
            environment_help = (
                'Environmental conditions:\n'
                'Exchange-reaction bounds control whether compounds can enter or leave the model. '
                'A negative exchange flux represents uptake and a positive flux represents secretion.'
            )
        menu_reactions.add.label(
            environment_help,
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color='white',
            font_size=26,
        )
        menu_reactions.add.vertical_margin(20)

        # A compact large-model editor avoids creating hundreds of pygame-menu
        # widgets up-front.  iMM904 has 164 exchanges, which previously meant
        # ~500 labels/switches plus margins before the main menu could even be
        # displayed.  The compact editor preserves the exact same underlying
        # reaction_<i>_lb/ub payload used by desktop and web simulations.
        compact_environment_inputs = None
        if self.model_context.get('environment_ui_mode') == 'compact_text':
            menu_reactions.add.label(
                f"Large-model mode: {len(self.model_context.get('exchanges') or [])} exchange reactions are available. "
                "The model-default medium is preserved unless you list an exact exchange id below.",
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24,
            )
            menu_reactions.add.vertical_margin(10)
            menu_reactions.add.label(
                'Lower bound controls uptake; upper bound controls secretion. '
                'Examples: close oxygen uptake with EX_o2_e, or open a normally closed nutrient uptake by listing its exchange id under lower bounds to open.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu_reactions.add.vertical_margin(10)
            lower_open_input = None
            lower_close_input = None
            upper_open_input = None
            upper_close_input = None
            environment_preview_label = None

            def refresh_environment_preview(*_args, **_kwargs):
                if environment_preview_label is None:
                    return
                environment_preview_label.set_title(
                    build_compact_environment_preview(
                        self.model_context.get('exchanges') or [],
                        lower_open_text=lower_open_input.get_value() if lower_open_input is not None else '',
                        lower_close_text=lower_close_input.get_value() if lower_close_input is not None else '',
                        upper_open_text=upper_open_input.get_value() if upper_open_input is not None else '',
                        upper_close_text=upper_close_input.get_value() if upper_close_input is not None else '',
                    )
                )

            lower_open_input = menu_reactions.add.text_input(
                'Lower bounds to open: ', default='', input_underline='_',
                input_underline_len=44, maxchar=500, maxwidth=44,
                maxwidth_dynamically_update=False, textinput_id='env_lower_open',
                background_color='white', font_color=(20, 0, 150),
                onreturn=refresh_environment_preview,
            )
            lower_close_input = menu_reactions.add.text_input(
                'Lower bounds to close: ', default='', input_underline='_',
                input_underline_len=44, maxchar=500, maxwidth=44,
                maxwidth_dynamically_update=False, textinput_id='env_lower_close',
                background_color='white', font_color=(20, 0, 150),
                onreturn=refresh_environment_preview,
            )
            upper_open_input = menu_reactions.add.text_input(
                'Upper bounds to open: ', default='', input_underline='_',
                input_underline_len=44, maxchar=500, maxwidth=44,
                maxwidth_dynamically_update=False, textinput_id='env_upper_open',
                background_color='white', font_color=(20, 0, 150),
                onreturn=refresh_environment_preview,
            )
            upper_close_input = menu_reactions.add.text_input(
                'Upper bounds to close: ', default='', input_underline='_',
                input_underline_len=44, maxchar=500, maxwidth=44,
                maxwidth_dynamically_update=False, textinput_id='env_upper_close',
                background_color='white', font_color=(20, 0, 150),
                onreturn=refresh_environment_preview,
            )
            compact_environment_inputs = (
                lower_open_input,
                lower_close_input,
                upper_open_input,
                upper_close_input,
            )
            menu_reactions.add.vertical_margin(10)

            environment_preview_label = menu_reactions.add.label(
                'Registered environmental changes: none (model defaults).',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )

            menu_reactions.add.button(
                'Validate / Preview Environment',
                refresh_environment_preview,
                font_color='white',
                background_color=(20, 100, 100),
            )
            menu_reactions.add.label(
                'After editing a field, press Enter or use Validate / Preview Environment to refresh the registered-change preview.',
                wordwrap=True,
                padding=(15, 15, 15, 15),
                background_color='white',
                font_size=20,
            )
            menu_reactions.add.vertical_margin(10)
            common_exchanges = ', '.join(self.model_context.get('exchange_report_ids') or [])
            menu_reactions.add.label(
                'Common exchanges in this simulator: ' + common_exchanges,
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=21,
            )
        else:
            # Small-model mode: keep the direct toggle interface, with the same
            # search/clear/reset navigation pattern used by the Genes menu.
            menu_reactions.add.label(
                'Search by exchange reaction id or name. Examples: EX_o2_e, oxygen, acetate. '
                'Reset Environment restores every lower/upper bound to the model-default state.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24,
            )
            menu_reactions.add.vertical_margin(10)

            reaction_widgets = {}
            reaction_default_states = {}
            reaction_search_input = None
            reaction_search_status = menu_reactions.add.label(
                f'Showing all {len(REACTIONS.index)} exchange reactions.',
                font_size=22,
                font_color=(20, 0, 150),
            )

            def apply_reaction_search(search_text=None, **_kwargs):
                current_search = '' if search_text is None else str(search_text)
                if search_text is None and reaction_search_input is not None:
                    current_search = str(reaction_search_input.get_value())

                visible_count = 0
                for reaction_id, entry in reaction_widgets.items():
                    if _reaction_matches_search(
                        reaction_id,
                        entry['name'],
                        current_search,
                    ):
                        for widget in entry['widgets']:
                            widget.show()
                        visible_count += 1
                    else:
                        for widget in entry['widgets']:
                            widget.hide()

                if current_search.strip():
                    reaction_search_status.set_title(
                        f'Search: {current_search} | {visible_count} exchange reaction(s) found.'
                    )
                else:
                    reaction_search_status.set_title(
                        f'Showing all {len(REACTIONS.index)} exchange reactions.'
                    )

            def clear_reaction_search(*_args, **_kwargs):
                if reaction_search_input is not None:
                    reaction_search_input.set_value('')
                apply_reaction_search('')

            def reset_reaction_toggles(*_args, **_kwargs):
                for reaction_id, entry in reaction_widgets.items():
                    default_lb, default_ub = reaction_default_states[reaction_id]
                    entry['lb'].set_value(default_lb)
                    entry['ub'].set_value(default_ub)
                if reaction_search_input is not None:
                    reaction_search_input.set_value('')
                apply_reaction_search('')
                reaction_search_status.set_title(
                    'Environment restored to the model-default bounds.'
                )

            reaction_search_input = menu_reactions.add.text_input(
                'Search exchange: ',
                default='',
                input_underline='_',
                maxchar=40,
                maxwidth=40,
                onchange=apply_reaction_search,
                onreturn=apply_reaction_search,
                textinput_id='reaction_search',
                background_color='white',
                font_color=(20, 0, 150),
            )
            menu_reactions.add.vertical_margin(10)
            menu_reactions.add.button(
                'Search / Refresh',
                apply_reaction_search,
                font_color='white',
                background_color=(20, 100, 100),
            )
            menu_reactions.add.button(
                'Clear Search',
                clear_reaction_search,
                font_color='white',
                background_color=(70, 70, 70),
            )
            menu_reactions.add.button(
                'Reset Environment',
                reset_reaction_toggles,
                font_color='white',
                background_color=(150, 40, 40),
            )
            menu_reactions.add.vertical_margin(20)

            for i in range(len(REACTIONS.name)):
                reaction_id = REACTIONS.index[i]
                reaction_name = REACTIONS.name.iloc[i]
                reaction_label = _format_reaction_menu_label(reaction_name, reaction_id)
                label_widget = menu_reactions.add.label(reaction_label, wordwrap=True)
                # MEWpy's native E. coli reaction table can yield numpy.bool_
                # from comparisons. pygame-menu 4.4.3 deliberately accepts only
                # built-in bool/int toggle defaults, so normalise explicitly.
                default_lb_bool = bool(REACTIONS.lb.iloc[i] != 0)
                default_ub_bool = bool(REACTIONS.ub.iloc[i] != 0)
                lb_widget = menu_reactions.add.toggle_switch(
                    'Lower Bound',
                    default_lb_bool,
                    onchange=None,
                    state_text=('Closed', 'Open'),
                    state_text_font_size=20,
                    font_size=24,
                    state_color=('grey', 'gold'),
                    state_text_font_color=('black', 'black'),
                    toggleswitch_id=f'reaction_{i}_lb',
                )
                ub_widget = menu_reactions.add.toggle_switch(
                    'Upper Bound',
                    default_ub_bool,
                    onchange=None,
                    state_text=('Closed', 'Open'),
                    state_text_font_size=20,
                    font_size=24,
                    state_color=('grey', 'gold'),
                    state_text_font_color=('black', 'black'),
                    toggleswitch_id=f'reaction_{i}_ub',
                )
                margin_widget = menu_reactions.add.vertical_margin(30)

                reaction_default_states[reaction_id] = (
                    default_lb_bool,
                    default_ub_bool,
                )
                reaction_widgets[reaction_id] = {
                    'name': reaction_name,
                    'label': label_widget,
                    'lb': lb_widget,
                    'ub': ub_widget,
                    'margin': margin_widget,
                    'widgets': (
                        label_widget,
                        lb_widget,
                        ub_widget,
                        margin_widget,
                    ),
                }

                if _YIELD_ON_WEB and (i + 1) % 4 == 0:
                    await asyncio.sleep(0)

            apply_reaction_search('')
        menu_reactions.add.vertical_margin(20)
        menu_reactions.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_reactions.add.vertical_margin(20)

        # menu_reactions_backup = pygame_menu.Menu(
        #     height=720,
        #     onclose=pygame_menu.events.BACK,
        #     theme=mytheme,
        #     title='Environmental Conditions',
        #     width=1280
        # )

        # # MENU REACTIONS
        # menu_reactions_backup.add.vertical_margin(50)
        # # Reactions (Range slider) // pode-se alterar as bounds para text inputs de forma a alterar para 0,0 (com range slider não é possível)  
        
        # for i in range(len(REACTIONS.name)):
        #     menu_reactions_backup.add.range_slider(REACTIONS.name[i], (REACTIONS.lb[i],REACTIONS.ub[i]), (-1000, 1000), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]) #, rangeslider_id=OPTIONS['Reactions'][i])
        #     menu_reactions_backup.add.toggle_switch('Bounds',True, onchange=None, state_text=('Deactivated', 'Active'), state_text_font_size=20, font_size = 24, state_color=('grey','gold')) #, kwargs=txt, toggleswitch_id=txt)
        #     menu_reactions_backup.add.vertical_margin(30)
        # menu_reactions_backup.add.vertical_margin(20)
        # menu_reactions_backup.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        # menu_reactions_backup.add.vertical_margin(20)



        # def toggle_reaction(txt, **id):
        #     if not txt:
        #         REACTIONS.lb[i] = 0
        #         REACTIONS.ub[i] = 0
        #     else:
        #         pass

        # MENU SUB (Genes)
        menu_genes.add.vertical_margin(50)
        # menu_genes.add.label('TIP')
        active_gene_mission_candidates = set()
        active_gene_mission_ids = []
        gene_mission_candidates = [
            ('03', MISSION03_CANDIDATE_GENES),
            ('04', MISSION04_CANDIDATE_GENES),
            ('05', MISSION05_CANDIDATE_GENES),
            ('06', MISSION06_CANDIDATE_GENES),
            ('09', MISSION09_CANDIDATE_GENES),
            ('10', MISSION10_CANDIDATE_GENES),
            ('14', MISSION14_CANDIDATE_GENES),
            ('19', [MISSION19_TARGET_GENE]),
            ('22', list(MISSION22_TARGET_GENES)),
            ('25', [MISSION25_TARGET_GENE]),
            ('26', [MISSION26_TARGET_GENE]),
            ('27', [MISSION27_TARGET_GENE]),
            ('28', [MISSION28_PRIMARY_GENE, *MISSION28_SECONDARY_GENES]),
            ('29', list(MISSION29_SINGLE_GENES)),
            ('30', [MISSION30_GENE_A, MISSION30_GENE_B]),
            ('31', [MISSION31_GENE_A, MISSION31_GENE_B]),
            ('32', list(MISSION32_GENE_NAMES)),
            ('33', list(MISSION33_TARGET_GENES)),
            ('34', list(MISSION34_GENE_NAMES)),
            ('35', ['b0114', 'b0726', 'b0116']),
        ]
        for mission_id, candidates in gene_mission_candidates:
            if is_ecoli and mission_id in self.player.missions_activated and mission_id not in self.player.missions_completed:
                active_gene_mission_candidates.update(candidates)
                active_gene_mission_ids.append(mission_id)

        if active_gene_mission_candidates:
            mission_names = ', '.join(active_gene_mission_ids)
            gene_tip = (
                f'Mission candidate genes currently highlighted: {mission_names}. '
                'Use the mission evidence and isolate only the genetic changes required by the experiment.'
            )
        else:
            gene_tip = (
                'Gene knockouts can reveal conditional essentiality or redirect metabolism. '
                'Activate a genetic mission to highlight its current candidate set.'
            )

        menu_genes.add.label(
            gene_tip,
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color='white',
            font_size=26,
        )
        menu_genes.add.vertical_margin(20)

        yeast_knockout_input = None
        if self.model_context.get('gene_ui_mode') == 'text':
            menu_genes.add.label(
                f"This model contains {len(GENES)} genes. Enter knockout gene ids or common names separated by commas. "
                "The complete iMM904 catalogue is validated when you run the simulation. Example: YOL086C or ADH1.",
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color="white",
                font_size=24,
            )
            menu_genes.add.vertical_margin(10)
            gene_preview_label = None

            def refresh_gene_preview(*_args, **_kwargs):
                if gene_preview_label is None or yeast_knockout_input is None:
                    return
                gene_preview_label.set_title(
                    build_gene_knockout_preview(
                        yeast_knockout_input.get_value(), GENES, GENE_NAMES
                    )
                )

            yeast_knockout_input = menu_genes.add.text_input(
                'Knockout genes: ',
                default='',
                input_underline='_',
                input_underline_len=52,
                maxchar=240,
                maxwidth=52,
                maxwidth_dynamically_update=False,
                textinput_id='gene_knockout_text',
                background_color='white',
                font_color=(20, 0, 150),
                onreturn=refresh_gene_preview,
            )
            menu_genes.add.vertical_margin(10)

            gene_preview_label = menu_genes.add.label(
                'Registered knockouts: none (wild type).',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )

            menu_genes.add.button(
                'Validate / Preview Genes',
                refresh_gene_preview,
                font_color='white',
                background_color=(20, 100, 100),
            )
            menu_genes.add.vertical_margin(10)
            menu_genes.add.label(
                'Leave the field empty for wild type. Common names are accepted only when they map unambiguously to one model gene. '
                'After editing, press Enter or use Validate / Preview Genes to refresh the canonical selection shown above.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
        else:
            menu_genes.add.label(
                "Search by gene id, number or name. Examples: b1241, 1241, adhE, pta. Use Reset Genes to reactivate all genes.",
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color="white",
                font_size=24
            )
            menu_genes.add.vertical_margin(10)

            gene_toggle_widgets = {}
            gene_search_input = None
            gene_search_status = menu_genes.add.label(
                f"Showing all {len(GENES)} genes.",
                font_size=22,
                font_color=(20, 0, 150)
            )

            def apply_gene_search(search_text=None, **_kwargs):
                current_search = '' if search_text is None else str(search_text)
                if search_text is None and gene_search_input is not None:
                    current_search = str(gene_search_input.get_value())

                visible_count = 0
                for gene_id, widget in gene_toggle_widgets.items():
                    if _gene_matches_search(gene_id, current_search, GENE_NAMES, GENE_LABELS):
                        widget.show()
                        visible_count += 1
                    else:
                        widget.hide()

                if current_search.strip():
                    gene_search_status.set_title(
                        f"Search: {current_search} | {visible_count} gene(s) found."
                    )
                else:
                    gene_search_status.set_title(f"Showing all {len(GENES)} genes.")

            def clear_gene_search(*_args, **_kwargs):
                if gene_search_input is not None:
                    gene_search_input.set_value('')
                apply_gene_search('')

            def reset_gene_toggles(*_args, **_kwargs):
                for widget in gene_toggle_widgets.values():
                    widget.set_value(True)
                if gene_search_input is not None:
                    gene_search_input.set_value('')
                apply_gene_search('')
                gene_search_status.set_title(f"All {len(GENES)} genes are active again.")

            gene_search_input = menu_genes.add.text_input(
                'Search gene: ',
                default='',
                input_underline='_',
                maxchar=30,
                maxwidth=30,
                onchange=apply_gene_search,
                onreturn=apply_gene_search,
                textinput_id='gene_search',
                background_color="white",
                font_color=(20, 0, 150)
            )
            menu_genes.add.vertical_margin(10)
            menu_genes.add.button('Search / Refresh', apply_gene_search, font_color='white', background_color=(20, 100, 100))
            menu_genes.add.button('Clear Search', clear_gene_search, font_color='white', background_color=(70, 70, 70))
            menu_genes.add.button('Reset Genes', reset_gene_toggles, font_color='white', background_color=(150, 40, 40))
            menu_genes.add.vertical_margin(20)

            for i, gene_id in enumerate(GENES):
                gene_label = GENE_LABELS.get(gene_id, gene_id)
                if gene_id in active_gene_mission_candidates:
                    gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                        gene_label, True, kwargs=gene_id, toggleswitch_id=gene_id,
                        background_color="gold", font_color="black"
                    )
                else:
                    gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                        gene_label, True, kwargs=gene_id, toggleswitch_id=gene_id
                    )
                if _YIELD_ON_WEB and (i + 1) % 8 == 0:
                    await asyncio.sleep(0)
            apply_gene_search('')

        menu_genes.add.vertical_margin(20)
        menu_genes.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_genes.add.vertical_margin(20)


        # MENU RESULTS
        # menu_results = pygame_menu.Menu(
        #     height=720,
        #     onclose=pygame_menu.events.BACK,
        #     theme=mytheme,
        #     title='History of Past Simulations',
        #     width=1280
        # )
        # menu_results.add.vertical_margin(20)
        # try:
        #     res_path = get_resource_path('code/player_history/results')
        #     res = load_file(res_path)

        #     menu_results.add.label(res)
        # except FileNotFoundError:
        #     menu_results.add.label('You have to make at least one simulation to see results.')


        
        

        # MENU SUB (Production Flux)
        menu_production_flux = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Production Flux',
            width=1280
        )

        menu_production_flux.add.vertical_margin(40)
        menu_production_flux.add.label(
            "Select the product fluxes you want to measure after each simulation.\nThis does not change the Objective; it only tracks the selected exchange fluxes in New Results.",
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color="white",
            font_size=26
        )
        menu_production_flux.add.vertical_margin(20)

        production_flux_widgets = {}

        def clear_production_fluxes(*_args, **_kwargs):
            for widget in production_flux_widgets.values():
                widget.set_value(False)

        if PRODUCTION_FLUX_OPTIONS:
            for option in PRODUCTION_FLUX_OPTIONS:
                production_flux_widgets[option['id']] = menu_production_flux.add.toggle_switch(
                    option['label'],
                    False,
                    toggleswitch_id=option['id'],
                    state_text=('Off', 'On'),
                    state_text_font_size=20,
                    font_size=24,
                    state_color=('grey', 'gold'),
                    state_text_font_color=('black', 'black')
                )
                menu_production_flux.add.vertical_margin(10)
        else:
            menu_production_flux.add.label(
                'No curated production fluxes are available for this model.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24
            )

        menu_production_flux.add.vertical_margin(20)
        menu_production_flux.add.button(
            'Clear Production Fluxes',
            clear_production_fluxes,
            font_color='white',
            background_color=(150, 40, 40)
        )
        menu_production_flux.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_production_flux.add.vertical_margin(20)


        # MENU SUB OBJECTIVE
        menu_objective = pygame_menu.Menu(
            height=720,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Objective',
            width=1280
        )

        objective_ids = list(self.model_context.get('objective_ids') or list(REACTIONS_v0.index))
        objective_options = list(self.model_context.get('objective_options') or [])
        objective_labels = {
            str(option.get('id')): str(option.get('label') or option.get('id'))
            for option in objective_options
            if option.get('id') is not None
        }
        objective_text_input = None
        if self.model_context.get('objective_ui_mode') == 'text':
            menu_objective.add.label(
                'Large-model mode: enter an exact reaction id. The complete iMM904 reaction catalogue is validated before the solver runs.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24,
            )
            menu_objective.add.vertical_margin(10)
            # pygame-menu 4.4.3 recomputes variable-length underline geometry
            # whenever the TextInput cursor blinks.  With a full-width underline
            # this repeatedly invalidates the menu surface and causes the entire
            # submenu to visibly jitter.  iMM904 reaction ids are at most 19
            # characters, so a fixed 24-character field is ample and stable.
            objective_text_input = menu_objective.add.text_input(
                'Objective reaction: ',
                default=str(objective),
                input_underline='_',
                input_underline_len=24,
                maxchar=100,
                maxwidth=24,
                maxwidth_dynamically_update=False,
                textinput_id='objective',
                background_color='white',
                font_color=(20, 0, 150),
            )
        else:
            objectives = []
            default_obj = 0
            for i, reaction_id in enumerate(objective_ids):
                if reaction_id == str(objective):
                    default_obj = i
                objectives.append((
                    objective_labels.get(reaction_id, reaction_id),
                    reaction_id,
                ))
            menu_objective.add.label(
                'Objective reaction:',
                font_size=28,
                font_color=(20, 0, 150),
            )
            menu_objective.add.dropselect(
                title='',
                items=objectives,
                default=default_obj,
                selection_box_height=8,
                selection_box_width=850,
                font_size=20,
                dropselect_id='objective'
            )
        # menu_objective.add.range_slider('Fraction', default=90, range_values=(0,100), increment=1, rangeslider_id='obj_fraction')

        menu_objective.add.vertical_margin(30)
        menu_objective.add.label(
            f"TIP: \nBy default, use {self.model_context['default_objective']} to evaluate predicted growth for {self.model_context['organism_name']}.",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
        menu_objective.add.vertical_margin(20)
        menu_objective.add.label(
            'Production Flux:',
            font_size=30,
            font_color=(20, 0, 150)
        )
        menu_objective.add.button(
            'Select production fluxes to track',
            menu_production_flux,
            font_color='white',
            background_color=(20, 100, 100)
        )
        menu_objective.add.vertical_margin(20)
        menu_objective.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        

        # MENU SUB (Bound Sweep)
        menu_bound_sweep = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Bound Sweep Setup',
            width=1280
        )
        menu_bound_sweep.add.vertical_margin(40)
        menu_bound_sweep.add.label(
            f"Bound Sweep tests one environmental bound at several numeric values ({FLUX_UNIT}).\nUse it when you want to read a trend instead of comparing only two simulations.",
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color="white",
            font_size=26
        )
        menu_bound_sweep.add.vertical_margin(20)
        if is_ecoli:
            sweep_variable_items = [
                ('Ammonium lower bound (EX_nh4_e)', 'EX_nh4_e:lower'),
                ('Carbon dioxide upper bound (EX_co2_e)', 'EX_co2_e:upper'),
                ('Oxygen lower bound (EX_o2_e)', 'EX_o2_e:lower'),
                ('D-Glucose lower bound (EX_glc__D_e)', 'EX_glc__D_e:lower'),
                ('Acetate lower bound (EX_ac_e)', 'EX_ac_e:lower'),
                ('Pyruvate lower bound (EX_pyr_e)', 'EX_pyr_e:lower'),
                ('L-Malate lower bound (EX_mal__L_e)', 'EX_mal__L_e:lower'),
                ('Fumarate lower bound (EX_fum_e)', 'EX_fum_e:lower'),
                ('2-Oxoglutarate lower bound (EX_akg_e)', 'EX_akg_e:lower'),
            ]
            sweep_value_items = [
                ('Ammonium sensitivity: -5, -4, -2, -1', 'ammonium_sensitivity'),
                ('CO2 export capacity: 25, 20, 10, 0', 'co2_export_capacity'),
                ('O2 genotype interaction: -25, -10, -1, 0', 'oxygen_transition'),
                ('Glucose limitation: -1000, -500, -100, -50, -10, 0', 'glucose_limitation'),
                ('Alternative carbon: -20, -10, -5, -1, 0', 'alternative_carbon_limitation'),
                ('PFK redundancy threshold: -30, -10, -5, -2', 'pfk_redundancy_threshold'),
                ('Final oxygen convergence: -30, -10, -5, -2', 'final_oxygen_convergence'),
            ]
        else:
            sweep_variable_items = [('D-Glucose lower bound (EX_glc__D_e)', 'EX_glc__D_e:lower')]
            sweep_value_items = [('Yeast glucose fermentation threshold: -0.5, -1, -2, -10', 'yeast_glucose_fermentation_threshold')]
        menu_bound_sweep.add.dropselect(
            title='Sweep variable: ', items=sweep_variable_items, default=0,
            selection_box_height=4, selection_box_width=520,
            dropselect_id='sweep_variable', background_color='white', font_color=(20, 0, 150)
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.dropselect(
            title='Sweep values: ', items=sweep_value_items, default=0,
            selection_box_height=4, selection_box_width=520,
            dropselect_id='sweep_values', background_color='white', font_color=(20, 0, 150)
        )
        if not is_ecoli:
            menu_bound_sweep.add.toggle_switch(
                'Execute this sweep with the next Run Simulation: ', False,
                toggleswitch_id='execute_sweep', background_color='white', font_color=(20,0,150)
            )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.label(
            "Active-mission note: follow the current scientist briefing before selecting a sweep. Some missions require one curve; advanced missions may require matched curves under different genotypes or base conditions.",
            wordwrap=True,
            padding=(20, 20, 20, 20),
            background_color='white',
            font_size=24
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_bound_sweep.add.vertical_margin(20)


        async def data_fun() -> None:
            """
            Print data of the menu.
            """

            # MENU AFTER SIMULATION RESULTS
            menu_simul = pygame_menu.Menu(
                height=720,
                onclose=self.toggle_menu,
                theme=mytheme,
                title='New Results',
                width=1280,
                menu_id='menu_new_results'
            )

            data_simul = menu.get_input_data()
            data_objective = menu_objective.get_input_data()
            raw_data_genes = menu_genes.get_input_data()
            gene_input_error = None
            if self.model_context.get('gene_ui_mode') == 'text':
                refresh_gene_preview()
                raw_knockouts = yeast_knockout_input.get_value() if yeast_knockout_input is not None else ''
                data_genes, _knockouts, unknown_genes, ambiguous_genes = _parse_gene_knockout_text(
                    raw_knockouts, GENES, GENE_NAMES
                )
                problems = []
                if unknown_genes:
                    problems.append('Unknown gene id/name: ' + ', '.join(unknown_genes))
                if ambiguous_genes:
                    problems.append('Ambiguous common gene name: ' + ', '.join(ambiguous_genes))
                if problems:
                    gene_input_error = '; '.join(problems)
            else:
                data_genes = _build_clean_gene_data(raw_data_genes, GENES)
            environment_input_error = None
            if self.model_context.get('environment_ui_mode') == 'compact_text':
                refresh_environment_preview()
                lower_open_text = compact_environment_inputs[0].get_value() if compact_environment_inputs else ''
                lower_close_text = compact_environment_inputs[1].get_value() if compact_environment_inputs else ''
                upper_open_text = compact_environment_inputs[2].get_value() if compact_environment_inputs else ''
                upper_close_text = compact_environment_inputs[3].get_value() if compact_environment_inputs else ''
                data_reac, environment_errors = build_compact_environment_payload(
                    self.model_context.get('exchanges') or [],
                    lower_open_text=lower_open_text,
                    lower_close_text=lower_close_text,
                    upper_open_text=upper_open_text,
                    upper_close_text=upper_close_text,
                )
                if environment_errors:
                    environment_input_error = '; '.join(environment_errors)
            else:
                data_reac = _build_clean_reaction_data(
                    menu_reactions.get_input_data(),
                    REACTIONS,
                )
            raw_fluxes = menu_production_flux.get_input_data()
            data_fluxes = {reaction_id: bool(raw_fluxes.get(reaction_id, False)) for reaction_id in PRODUCTION_FLUX_REACTION_IDS}
            # Snapshot the sweep controls before yielding to a worker/network request.
            # The menu stays responsive while the solver runs, so later UI edits must
            # not change the protocol of an already-started simulation job.
            bound_sweep_input_data = copy.deepcopy(menu_bound_sweep.get_input_data() or {})



            menu_summary = pygame_menu.Menu(
                height=720,
                center_content=False,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
                title='Simulation Summary',
                width=1280,
                menu_id='menu_simulation_summary'
            )

            simulation_method = _selected_menu_value(data_simul, 'method')
            if objective_text_input is not None:
                objective_name = str(objective_text_input.get_value()).strip()
            else:
                objective_name = str(_selected_menu_value(data_objective, 'objective')).strip()
            objective_input_error = None
            if objective_name not in set(self.model_context.get('all_reaction_ids') or []):
                objective_input_error = f'Unknown objective reaction for {self.model_context["display_name"]}: {objective_name}'

            menu_summary.add.vertical_margin(30)

            _add_summary_section(
                menu_summary,
                'General setup',
                f"Model: {self.model_context['display_name']} ({self.model_id})\n"
                f'Simulation method: {_method_display_name(simulation_method)}\nObjective: {objective_name}'
            )

            _add_summary_section(
                menu_summary,
                'Gene knockouts',
                _build_gene_summary(data_genes, GENE_LABELS)
            )

            _add_summary_section(
                menu_summary,
                'Environmental changes',
                _build_environmental_summary_for_table(data_reac, REACTIONS)
            )

            _add_summary_section(
                menu_summary,
                'Production fluxes to track',
                _build_production_flux_summary_for_options(data_fluxes, PRODUCTION_FLUX_OPTIONS)
            )

            menu_summary.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )


            # Persist a canonical text-objective shape for large models.
            # pygame-menu TextInput values are plain strings whereas the E. coli
            # DropSelect uses nested selector data.  Keeping the written yeast
            # payload explicit avoids depending on widget-internal serialization
            # and is also the shape the future web client can send directly.
            saved_objective_data = (
                {'objective': objective_name}
                if objective_text_input is not None
                else data_objective
            )
            save_simulation_file([data_simul, saved_objective_data, data_genes, data_reac, data_fluxes, {'model_id': self.model_id}])
            animation_text_save('Running')
            try:
                if gene_input_error:
                    raise ValueError(gene_input_error)
                if objective_input_error:
                    raise ValueError(objective_input_error)
                if environment_input_error:
                    raise ValueError(environment_input_error)
                if sys.platform == 'emscripten':
                    self.results = await run_simul_remote_async(BACKEND_URL)
                else:
                    self.results = await asyncio.to_thread(run_simul)
            except Exception as error:
                error_message = f'Simulation error: {error}'
                self.results = (
                    objective_name,
                    error_message,
                    {'selected_ids': [], 'items': [], 'error': error_message},
                    {'reaction_ids': [], 'items': [], 'error': error_message},
                )
                animation_text_save(
                    'Simulation failed safely. Open New Results for details.',
                    time=2500,
                )

            exchange_flux_data = None
            try:
                exchange_flux_data = self.results[3] if len(self.results) > 3 else None
            except Exception:
                exchange_flux_data = None

            compare_runs = capture_compare_run_snapshot(self.results)

            mission36_data = None
            mission36_baseline_preexisting = False
            if (not is_ecoli and '36' in self.player.missions_activated and '36' not in self.player.missions_completed):
                previous_m36 = load_mission36_fermentation_onset() or {}
                mission36_baseline_preexisting = bool(previous_m36.get('baseline_ready'))
                if not bool(bound_sweep_input_data.get('execute_sweep', False)) or not mission36_baseline_preexisting:
                    mission36_data = run_mission36_baseline_check(self.results)

            mission37_data = None
            if (not is_ecoli and '37' in self.player.missions_activated and '37' not in self.player.missions_completed):
                mission37_sweep_requested = bool(
                    bound_sweep_input_data.get('execute_sweep', False)
                )
                if sys.platform == 'emscripten':
                    mission37_data = run_mission37_fermentation_cut_set_check_remote(
                        BACKEND_URL,
                        self.results,
                        sweep_requested=mission37_sweep_requested,
                    )
                else:
                    mission37_data = run_mission37_fermentation_cut_set_check(
                        self.results,
                        sweep_requested=mission37_sweep_requested,
                    )

            mission38_data = None
            if (not is_ecoli and '38' in self.player.missions_activated and '38' not in self.player.missions_completed):
                mission38_sweep_requested = bool(
                    bound_sweep_input_data.get('execute_sweep', False)
                )
                if sys.platform == 'emscripten':
                    mission38_data = run_mission38_background_dependency_check_remote(
                        BACKEND_URL,
                        self.results,
                        sweep_requested=mission38_sweep_requested,
                    )
                else:
                    mission38_data = run_mission38_background_dependency_check(
                        self.results,
                        sweep_requested=mission38_sweep_requested,
                    )

            mission39_data = None
            if (not is_ecoli and '39' in self.player.missions_activated and '39' not in self.player.missions_completed):
                mission39_sweep_requested = bool(
                    bound_sweep_input_data.get('execute_sweep', False)
                )
                if sys.platform == 'emscripten':
                    mission39_data = run_mission39_bypass_rescue_check_remote(
                        BACKEND_URL,
                        self.results,
                        sweep_requested=mission39_sweep_requested,
                    )
                else:
                    mission39_data = run_mission39_bypass_rescue_check(
                        self.results,
                        sweep_requested=mission39_sweep_requested,
                    )

            mission40_data = None
            mission40_sweep_requested = False
            mission40_active = bool(
                not is_ecoli
                and '40' in self.player.missions_activated
                and '40' not in self.player.missions_completed
            )
            mission40_sweep_menu_data = bound_sweep_input_data
            mission40_input_errors = [
                error for error in (gene_input_error, objective_input_error, environment_input_error)
                if error
            ]
            if mission40_active:
                mission40_sweep_explicitly_requested = bool(
                    (mission40_sweep_menu_data or {}).get('execute_sweep', False)
                )
                mission40_sweep_requested = bool(
                    mission40_sweep_explicitly_requested
                    and mission40_should_run_bound_sweep(
                        mission40_sweep_menu_data,
                        simulation_method,
                        objective_name,
                        data_genes,
                        input_errors=mission40_input_errors,
                    )
                )
                if not mission40_sweep_requested:
                    mission40_data = run_mission40_rejected_sweep_attempt(
                        mission40_sweep_menu_data,
                        simulation_method,
                        objective_name,
                        data_genes,
                        input_errors=mission40_input_errors,
                    )

            mission01_data = None
            if is_ecoli and '01' in self.player.missions_activated and '01' not in self.player.missions_completed:
                mission01_data = run_mission01_comparison_check(compare_runs)

            mission02_data = None
            if is_ecoli and '02' in self.player.missions_activated and '02' not in self.player.missions_completed:
                mission02_data = run_mission02_source_trial_check(self.results)

            mission03_data = None
            if is_ecoli and '03' in self.player.missions_activated and '03' not in self.player.missions_completed:
                mission03_data = run_mission03_gene_trial_check(self.results)

            mission04_data = None
            if is_ecoli and '04' in self.player.missions_activated and '04' not in self.player.missions_completed:
                mission04_data = run_mission04_production_trial_check(self.results)

            mission21_data = None
            if is_ecoli and '21' in self.player.missions_activated and '21' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission21_data = run_mission21_comparison_check_remote(BACKEND_URL, self.results)
                else:
                    mission21_data = run_mission21_comparison_check(self.results)

            mission22_data = None
            if is_ecoli and '22' in self.player.missions_activated and '22' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission22_data = run_mission22_comparison_check_remote(BACKEND_URL, self.results)
                else:
                    mission22_data = run_mission22_comparison_check(self.results)

            mission23_data = None

            mission24_data = None

            mission25_data = None
            if is_ecoli and '25' in self.player.missions_activated and '25' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission25_data = run_mission25_context_check_remote(BACKEND_URL, self.results)
                else:
                    mission25_data = run_mission25_context_check(self.results)

            mission27_data = None
            if is_ecoli and '27' in self.player.missions_activated and '27' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission27_data = run_mission27_rescue_check_remote(BACKEND_URL, self.results)
                else:
                    mission27_data = run_mission27_rescue_check(self.results)

            mission28_data = None
            if is_ecoli and '28' in self.player.missions_activated and '28' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission28_data = run_mission28_dependency_check_remote(BACKEND_URL, self.results)
                else:
                    mission28_data = run_mission28_dependency_check(self.results)

            mission29_data = None
            if is_ecoli and '29' in self.player.missions_activated and '29' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission29_data = run_mission29_redundancy_check_remote(BACKEND_URL, self.results)
                else:
                    mission29_data = run_mission29_redundancy_check(self.results)

            mission31_data = None
            if is_ecoli and '31' in self.player.missions_activated and '31' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission31_data = run_mission31_environmental_suppression_check_remote(
                        BACKEND_URL, self.results
                    )
                else:
                    mission31_data = run_mission31_environmental_suppression_check(self.results)


            mission32_data = None
            if is_ecoli and '32' in self.player.missions_activated and '32' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission32_data = run_mission32_respiratory_cut_set_check_remote(
                        BACKEND_URL, self.results
                    )
                else:
                    mission32_data = run_mission32_respiratory_cut_set_check(self.results)

            mission33_data = None
            if is_ecoli and '33' in self.player.missions_activated and '33' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission33_data = run_mission33_reference_adjustment_check_remote(
                        BACKEND_URL, self.results
                    )
                else:
                    mission33_data = run_mission33_reference_adjustment_check(self.results)


            mission34_data = None
            if is_ecoli and '34' in self.player.missions_activated and '34' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission34_data = run_mission34_shared_subunit_check_remote(
                        BACKEND_URL, self.results
                    )
                else:
                    mission34_data = run_mission34_shared_subunit_check(self.results)

            mission35_data = None
            if is_ecoli and '35' in self.player.missions_activated and '35' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission35_data = run_mission35_final_certification_check_remote(
                        BACKEND_URL, self.results
                    )
                else:
                    mission35_data = run_mission35_final_certification_check(self.results)

            mission30_data = None
            bound_sweep_data = None
            mission26_data = None
            mission35_sweep_requested = bool(
                '35' in self.player.missions_activated
                and '35' not in self.player.missions_completed
                and mission35_should_run_bound_sweep(
                    bound_sweep_input_data, simulation_method, objective_name, data_genes,
                )
            )
            mission36_sweep_menu_data = bound_sweep_input_data
            mission36_input_errors = [
                error for error in (gene_input_error, objective_input_error, environment_input_error)
                if error
            ]
            mission36_sweep_explicitly_requested = bool(
                not is_ecoli
                and '36' in self.player.missions_activated
                and '36' not in self.player.missions_completed
                and bool((mission36_sweep_menu_data or {}).get('execute_sweep', False))
            )
            mission36_sweep_requested = bool(
                mission36_sweep_explicitly_requested
                and mission36_should_run_bound_sweep(
                    mission36_sweep_menu_data, simulation_method, objective_name,
                    data_genes, baseline_preexisting=mission36_baseline_preexisting,
                    input_errors=mission36_input_errors,
                )
            )
            if (
                mission36_sweep_explicitly_requested
                and mission36_baseline_preexisting
                and not mission36_sweep_requested
            ):
                mission36_data = run_mission36_rejected_sweep_attempt(
                    mission36_sweep_menu_data,
                    simulation_method,
                    objective_name,
                    data_genes,
                    baseline_preexisting=True,
                    input_errors=mission36_input_errors,
                )
            bound_sweep_mission_active = (
                ('23' in self.player.missions_activated and '23' not in self.player.missions_completed)
                or ('24' in self.player.missions_activated and '24' not in self.player.missions_completed)
                or ('26' in self.player.missions_activated and '26' not in self.player.missions_completed)
                or ('30' in self.player.missions_activated and '30' not in self.player.missions_completed)
                or mission35_sweep_requested
                or mission36_sweep_requested
                or mission40_sweep_requested
            )
            if bound_sweep_mission_active:
                if sys.platform == 'emscripten':
                    bound_sweep_data = await run_bound_sweep_remote_async(
                        BACKEND_URL, bound_sweep_input_data, model_id=self.model_id
                    )
                else:
                    bound_sweep_data = await asyncio.to_thread(
                        run_bound_sweep, bound_sweep_input_data, model_id=self.model_id
                    )

                if is_ecoli and '23' in self.player.missions_activated and '23' not in self.player.missions_completed:
                    if sys.platform == 'emscripten':
                        mission23_data = run_mission23_sensitivity_check_remote(
                            BACKEND_URL, bound_sweep_data
                        )
                    else:
                        mission23_data = run_mission23_sensitivity_check(bound_sweep_data)
                if is_ecoli and '24' in self.player.missions_activated and '24' not in self.player.missions_completed:
                    if sys.platform == 'emscripten':
                        mission24_data = run_mission24_export_capacity_check_remote(
                            BACKEND_URL, bound_sweep_data
                        )
                    else:
                        mission24_data = run_mission24_export_capacity_check(bound_sweep_data)
                if is_ecoli and '26' in self.player.missions_activated and '26' not in self.player.missions_completed:
                    if sys.platform == 'emscripten':
                        mission26_data = run_mission26_interaction_curve_check_remote(
                            BACKEND_URL, bound_sweep_data
                        )
                    else:
                        mission26_data = run_mission26_interaction_curve_check(bound_sweep_data)
                if is_ecoli and '30' in self.player.missions_activated and '30' not in self.player.missions_completed:
                    if sys.platform == 'emscripten':
                        mission30_data = run_mission30_redundancy_threshold_check_remote(
                            BACKEND_URL, bound_sweep_data
                        )
                    else:
                        mission30_data = run_mission30_redundancy_threshold_check(bound_sweep_data)
                if mission35_sweep_requested:
                    if sys.platform == 'emscripten':
                        mission35_data = run_mission35_oxygen_curve_check_remote(
                            BACKEND_URL, bound_sweep_data
                        )
                    else:
                        mission35_data = run_mission35_oxygen_curve_check(bound_sweep_data)
                if mission36_sweep_requested:
                    mission36_data = run_mission36_curve_check(bound_sweep_data)
                if mission40_sweep_requested:
                    mission40_data = run_mission40_curve_check(bound_sweep_data)

            menu_compare_runs = pygame_menu.Menu(
                height=720,
                center_content=False,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
                title='Compare Runs',
                width=1280,
                menu_id='menu_compare_runs'
            )
            menu_compare_runs.add.vertical_margin(20)
            menu_compare_runs.add.label(
                build_compare_runs_report_text(compare_runs),
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24
            )
            menu_compare_runs.add.vertical_margin(20)
            menu_compare_runs.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )

            menu_exchange_report = pygame_menu.Menu(
                height=720,
                center_content=False,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
                title='Exchange Flux Report',
                width=1280,
                menu_id='menu_exchange_flux_report'
            )
            menu_exchange_report.add.vertical_margin(20)
            menu_exchange_report.add.label(
                _build_exchange_flux_report_text(exchange_flux_data),
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24
            )
            menu_exchange_report.add.vertical_margin(20)
            menu_exchange_report.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )


            menu_bound_sweep_report = pygame_menu.Menu(
                height=720,
                center_content=False,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
                title='Bound Sweep Report',
                width=1280,
                menu_id='menu_bound_sweep_report'
            )
            menu_bound_sweep_report.add.vertical_margin(20)
            menu_bound_sweep_report.add.label(
                _build_bound_sweep_report_text(bound_sweep_data),
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22
            )
            menu_bound_sweep_report.add.vertical_margin(20)
            menu_bound_sweep_report.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )

            mission07_data = None
            if is_ecoli and '07' in self.player.missions_activated and '07' not in self.player.missions_completed:
                mission07_data = run_mission07_objective_check(self.results)

            mission08_data = None
            if is_ecoli and '08' in self.player.missions_activated and '08' not in self.player.missions_completed:
                mission08_data = run_mission08_constraint_check(self.results)

            mission09_data = None
            if is_ecoli and '09' in self.player.missions_activated and '09' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission09_data = run_mission09_design_check_remote(BACKEND_URL, self.results)
                else:
                    mission09_data = run_mission09_design_check(self.results)

            mission10_data = None
            if is_ecoli and '10' in self.player.missions_activated and '10' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission10_data = run_mission10_robust_design_check_remote(BACKEND_URL, self.results)
                else:
                    mission10_data = run_mission10_robust_design_check(self.results)

            mission11_data = None
            if is_ecoli and '11' in self.player.missions_activated and '11' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission11_data = run_mission11_flux_fingerprint_check_remote(BACKEND_URL, self.results)
                else:
                    mission11_data = run_mission11_flux_fingerprint_check(self.results)

            mission12_data = None
            if is_ecoli and '12' in self.player.missions_activated and '12' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission12_data = run_mission12_byproduct_check_remote(BACKEND_URL, self.results)
                else:
                    mission12_data = run_mission12_byproduct_check(self.results)

            mission13_data = None
            if is_ecoli and '13' in self.player.missions_activated and '13' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission13_data = run_mission13_method_check_remote(BACKEND_URL, self.results)
                else:
                    mission13_data = run_mission13_method_check(self.results)

            mission14_data = None
            if is_ecoli and '14' in self.player.missions_activated and '14' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission14_data = run_mission14_reduction_check_remote(BACKEND_URL, self.results)
                else:
                    mission14_data = run_mission14_reduction_check(self.results)

            mission15_data = None
            if is_ecoli and '15' in self.player.missions_activated and '15' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission15_data = run_mission15_diagnostic_report_check_remote(BACKEND_URL, self.results)
                else:
                    mission15_data = run_mission15_diagnostic_report_check(self.results)

            mission16_data = None
            if is_ecoli and '16' in self.player.missions_activated and '16' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission16_data = run_mission16_medium_report_check_remote(BACKEND_URL, self.results)
                else:
                    mission16_data = run_mission16_medium_report_check(self.results)

            mission17_data = None
            if is_ecoli and '17' in self.player.missions_activated and '17' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission17_data = run_mission17_essential_medium_check_remote(BACKEND_URL, self.results)
                else:
                    mission17_data = run_mission17_essential_medium_check(self.results)

            mission18_data = None
            if is_ecoli and '18' in self.player.missions_activated and '18' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission18_data = run_mission18_export_bottleneck_check_remote(BACKEND_URL, self.results)
                else:
                    mission18_data = run_mission18_export_bottleneck_check(self.results)

            mission19_data = None
            if is_ecoli and '19' in self.player.missions_activated and '19' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission19_data = run_mission19_perturbation_check_remote(BACKEND_URL, self.results)
                else:
                    mission19_data = run_mission19_perturbation_check(self.results)

            mission20_data = None
            if is_ecoli and '20' in self.player.missions_activated and '20' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission20_data = run_mission20_robustness_report_check_remote(BACKEND_URL, self.results)
                else:
                    mission20_data = run_mission20_robustness_report_check(self.results)

            mission05_data = None
            if is_ecoli and '05' in self.player.missions_activated and '05' not in self.player.missions_completed:
                mission05_data = run_mission05_production_trial_check(self.results)

            challenge_data = None
            if is_ecoli and '06' in self.player.missions_activated and '06' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    challenge_data = run_challenge_score_remote(BACKEND_URL, self.results)
                else:
                    challenge_data = run_challenge_score(self.results)

            self.player.results.insert(0,self.results)
            try:
                menu.remove_widget('new_results')
                menu.remove_widget('menu_new_results')
            except:
                # print('teste2')
                pass
            
            menu_simul.add.label("Results:")
            menu_simul.add.vertical_margin(50)  # Adds margin
            
            menu.add.button('New Results', action=menu_simul, font_color = 'white', background_color=(0,150,50), button_id='new_results')
            result_display_text = _build_simulation_results_text(self.results)
            # Error messages for large-model validation can be longer than
            # one screen line.  Word wrapping keeps failures readable instead
            # of clipping them beyond the right edge of the 1280px results menu.
            menu_simul.add.label(
                result_display_text,
                label_id='results',
                wordwrap=True,
                padding=(20, 20, 20, 20),
            )
            save_results(result_display_text)
            save_file(self.player.get_save_data())
            menu_simul.add.vertical_margin(50, margin_id='nr_margin')
            menu_simul.add.button(
                'Simulation Summary',
                menu_summary,
                font_color='white',
                background_color=(20, 100, 100),
                button_id='simulation_summary'
            )
            menu_simul.add.vertical_margin(10)
            menu_simul.add.button(
                'Exchange Flux Report',
                menu_exchange_report,
                font_color='white',
                background_color=(20, 100, 100),
                button_id='exchange_flux_report'
            )
            menu_simul.add.vertical_margin(10)
            menu_simul.add.button(
                'Compare Runs',
                menu_compare_runs,
                font_color='white',
                background_color=(20, 100, 100),
                button_id='compare_runs'
            )

            if bound_sweep_data is not None:
                menu_simul.add.vertical_margin(10)
                menu_simul.add.button(
                    'Bound Sweep Report',
                    menu_bound_sweep_report,
                    font_color='white',
                    background_color=(20, 100, 100),
                    button_id='bound_sweep_report'
                )
            menu_simul.add.vertical_margin(20)

            if mission36_data is not None:
                menu_simul.add.label(
                    build_mission36_fermentation_report_text(mission36_data),
                    wordwrap=True, padding=(20,20,20,20), background_color='white',
                    font_size=22, label_id='mission36_fermentation_onset_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission37_data is not None:
                menu_simul.add.label(
                    build_mission37_fermentation_cut_set_report_text(mission37_data),
                    wordwrap=True, padding=(20,20,20,20), background_color='white',
                    font_size=22, label_id='mission37_fermentation_cut_set_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission38_data is not None:
                menu_simul.add.label(
                    build_mission38_background_dependency_report_text(mission38_data),
                    wordwrap=True, padding=(20,20,20,20), background_color='white',
                    font_size=22, label_id='mission38_background_dependency_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission39_data is not None:
                menu_simul.add.label(
                    build_mission39_bypass_rescue_report_text(mission39_data),
                    wordwrap=True, padding=(20,20,20,20), background_color='white',
                    font_size=22, label_id='mission39_bypass_rescue_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission40_data is not None:
                menu_simul.add.label(
                    build_mission40_final_certification_report_text(mission40_data),
                    wordwrap=True, padding=(20,20,20,20), background_color='white',
                    font_size=22, label_id='mission40_final_certification_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission01_data is not None:
                menu_simul.add.label(
                    _build_mission01_text(mission01_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission01_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission02_data is not None:
                menu_simul.add.label(
                    build_mission02_evidence_report_text(mission02_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission02_source_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission03_data is not None:
                menu_simul.add.label(
                    build_mission03_evidence_report_text(mission03_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission03_gene_screen_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission21_data is not None:
                menu_simul.add.label(
                    _build_mission21_text(mission21_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission21_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission22_data is not None:
                menu_simul.add.label(
                    _build_mission22_text(mission22_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission22_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission23_data is not None:
                menu_simul.add.label(
                    _build_mission23_text(mission23_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission23_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission24_data is not None:
                menu_simul.add.label(
                    _build_mission24_text(mission24_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission24_comparison_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission25_data is not None:
                menu_simul.add.label(
                    _build_mission25_text(mission25_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission25_comparison_check'
                )
                menu_simul.add.vertical_margin(20)


            if mission26_data is not None:
                menu_simul.add.label(
                    _build_mission26_text(mission26_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission26_bound_sweep_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission27_data is not None:
                menu_simul.add.label(
                    _build_mission27_text(mission27_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission27_rescue_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission28_data is not None:
                menu_simul.add.label(
                    _build_mission28_text(mission28_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission28_dependency_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission29_data is not None:
                menu_simul.add.label(
                    _build_mission29_text(mission29_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission29_redundancy_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission30_data is not None:
                menu_simul.add.label(
                    _build_mission30_text(mission30_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission30_redundancy_threshold_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission31_data is not None:
                menu_simul.add.label(
                    _build_mission31_text(mission31_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission31_environmental_suppression_check'
                )
                menu_simul.add.vertical_margin(20)


            if mission32_data is not None:
                menu_simul.add.label(
                    _build_mission32_text(mission32_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission32_respiratory_cut_set_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission33_data is not None:
                menu_simul.add.label(
                    _build_mission33_text(mission33_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission33_reference_adjustment_check'
                )
                menu_simul.add.vertical_margin(20)


            if mission34_data is not None:
                menu_simul.add.label(
                    _build_mission34_text(mission34_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission34_shared_subunit_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission35_data is not None:
                menu_simul.add.label(
                    _build_mission35_text(mission35_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission35_final_certification'
                )
                menu_simul.add.vertical_margin(20)

            if mission07_data is not None:
                menu_simul.add.label(
                    _build_mission07_text(mission07_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission07_objective_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission08_data is not None:
                menu_simul.add.label(
                    _build_mission08_text(mission08_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission08_constraint_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission09_data is not None:
                menu_simul.add.label(
                    _build_mission09_text(mission09_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission09_design_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission10_data is not None:
                menu_simul.add.label(
                    _build_mission10_text(mission10_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission10_robust_design_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission11_data is not None:
                menu_simul.add.label(
                    _build_mission11_text(mission11_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission11_flux_fingerprint_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission12_data is not None:
                menu_simul.add.label(
                    _build_mission12_text(mission12_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission12_byproduct_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission13_data is not None:
                menu_simul.add.label(
                    _build_mission13_text(mission13_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission13_method_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission14_data is not None:
                menu_simul.add.label(
                    _build_mission14_text(mission14_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission14_reduction_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission15_data is not None:
                menu_simul.add.label(
                    _build_mission15_text(mission15_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission15_diagnostic_report_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission16_data is not None:
                menu_simul.add.label(
                    _build_mission16_text(mission16_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission16_medium_report_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission17_data is not None:
                menu_simul.add.label(
                    _build_mission17_text(mission17_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission17_essential_medium_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission18_data is not None:
                menu_simul.add.label(
                    _build_mission18_text(mission18_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission18_export_bottleneck_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission19_data is not None:
                menu_simul.add.label(
                    _build_mission19_text(mission19_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission19_perturbation_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission20_data is not None:
                menu_simul.add.label(
                    _build_mission20_text(mission20_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission20_robustness_report_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission04_data is not None:
                menu_simul.add.label(
                    _build_mission04_text(mission04_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission04_production_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission05_data is not None:
                menu_simul.add.label(
                    _build_mission05_text(mission05_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission05_production_check'
                )
                menu_simul.add.vertical_margin(20)

            if challenge_data is not None:
                menu_simul.add.label(
                    _build_challenge_text(challenge_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission06_challenge'
                )
                menu_simul.add.vertical_margin(20)

            mission19_viable_perturbation = (
                mission19_data is not None
                and mission19_data.get('current_run_recorded')
                and (mission19_data.get('current_biomass_flux') or 0.0) > MISSION07_FLUX_TOLERANCE
            )
            visible_biomass = _visible_biomass_flux(self.results)
            no_predicted_growth = (
                self.results[1] == 'Status: INFEASIBLE'
                or (visible_biomass is not None and visible_biomass <= MISSION07_FLUX_TOLERANCE)
                or (
                    visible_biomass is None
                    and self.results[0] == MISSION07_BIOMASS_OBJECTIVE
                    and self.results[1] in (0.0, -0.0)
                )
            )
            if no_predicted_growth and not mission19_viable_perturbation:
                menu_simul.add.image(ecoli_rip, scale=(0.5, 0.5), image_id='ecolidead')
                menu_simul.add.vertical_margin(50, margin_id='deadmargin')
            else:
                try:
                    menu_simul.remove_widget('ecolidead')
                except:
                    pass
                try:
                    menu_simul.remove_widget('deadmargin')
                except:
                    pass
            menu_simul.add.button('Close', pygame_menu.events.BACK, background_color=(70, 70, 70), button_id='nr_close')


        # def restore_data() -> None:
        #     """
        #     """
        #     menu.reset_value()
        #     menu_objective.reset_value()
        #     menu_genes.reset_value()
        #     menu_reactions.reset_value()


        menu.add.label(f"Model: {self.model_context['display_name']} | {self.model_context['organism_name']}", font_size=24, font_color=(20, 0, 150))
        menu.add.label('TIP: See Book "How to Simulate"', font_size = 20)
        menu.add.vertical_margin(20)
        menu.add.label('Change options: ', font_size = 40)
        menu.add.vertical_margin(20)

        method_items = []
        for method_token in self.model_context['supported_methods']:
            if method_token == 'lMOMA':
                method_items.append((LMOMA_DISPLAY_NAME, 'lmoma'))
            else:
                method_items.append((method_token, method_token.lower()))
        menu.add.dropselect(title='Simulation Method ',
                            items=method_items,
                            default=0,
                            selection_box_height=5, dropselect_id='method', background_color="white", font_color=(20,0,150))
        menu.add.button('Objective', menu_objective, font_color = (20,0,150), background_color="white")
        menu.add.button('Production Flux', menu_production_flux, font_color = (20,0,150), background_color="white")
        menu.add.button('Genes', menu_genes, font_color = (20,0,150), background_color="white")
        menu.add.button('Environmental Conditions', menu_reactions, font_color = (20,0,150), background_color="white")
        if is_ecoli or self.model_id == 'yeast_iMM904':
            menu.add.button('Bound Sweep Setup', menu_bound_sweep, font_color = (20,0,150), background_color="white")
        # menu.add.button('Environmental Conditions', menu_reactions_backup, font_color = (20,0,150), background_color="white")
        menu.add.vertical_margin(50)  # Adds margin
        # menu.add.button('Restore Data', restore_data, background_color=(100,0,0))
        # menu.add.vertical_margin(20)  # Adds margin

        simulation_running = False
        simulation_status_label = menu.add.label(
            '',
            font_size=22,
            font_color=(20, 0, 150),
            label_id='simulation_status',
        )
        menu.add.vertical_margin(8)

        def _simulation_task_finished(task):
            nonlocal simulation_running
            simulation_running = False
            try:
                task.result()
            except Exception:
                simulation_status_label.set_title('Simulation failed safely. Please try again.')
                animation_text_save('Simulation failed safely.', time=1800)
            else:
                simulation_status_label.set_title('Simulation ready. Open New Results.')

        def start_simulation():
            nonlocal simulation_running
            if simulation_running:
                animation_text_save('Simulation already running.', time=1200)
                return

            simulation_running = True
            simulation_status_label.set_title('Running simulation...')
            task = asyncio.create_task(data_fun())
            task.add_done_callback(_simulation_task_finished)

        menu.add.button('Run Simulation', action=start_simulation, font_color = 'white', background_color=(20,100,100))
        menu.add.vertical_margin(20)  # Adds margin
        # last_results = menu.add.button('Results Log', action=menu_results, font_color = 'black', background_color="grey")
        # menu.add.vertical_margin(50)  # Adds margin

        def check_escape():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] and menu.is_enabled() and not simulation_running:
                menu.close()

        await run_menu(menu, self.display_surface, on_update=check_escape)




    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback


    async def update(self):
        self.input()
        await self.setup()

