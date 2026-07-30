import asyncio
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


_YIELD_ON_WEB = sys.platform == 'emscripten'


def _selected_menu_value(data, key):
    value = data.get(key)

    try:
        return value[0][0]
    except Exception:
        return str(value)


def _format_gene(gene_id):
    return GENE_LABELS.get(gene_id, gene_id)


def _format_reaction_menu_label(reaction_name, reaction_id):
    return f"{reaction_name} ({reaction_id})"


def _normalise_gene_search_text(value):
    """Normalise gene search text so b1241, 1241, adhE or adh e all match."""
    return ''.join(
        char.lower()
        for char in str(value)
        if char.isalnum()
    )


def _gene_matches_search(gene_id, search_text):
    query = _normalise_gene_search_text(search_text)
    if not query:
        return True

    gene_name = GENE_NAMES.get(gene_id, '')
    gene_label = GENE_LABELS.get(gene_id, gene_id)
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


def _build_clean_gene_data(raw_gene_data):
    """Keep only real model genes, ignoring UI-only widgets like the search box."""
    return {
        gene_id: bool(raw_gene_data.get(gene_id, True))
        for gene_id in GENES
    }


def _build_gene_summary(genes):
    knocked_out_genes = [
        gene_id for gene_id, is_active in genes.items()
        if not is_active
    ]

    if not knocked_out_genes:
        return 'No gene knockouts.'

    return '\n'.join(
        f'- {_format_gene(gene_id)}'
        for gene_id in knocked_out_genes
    )


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
                f'Lower Bound {"Open" if lower_bound_open else "Closed"} ({lower_bound_value}), '
                f'Upper Bound {"Open" if upper_bound_open else "Closed"} ({upper_bound_value})'
            )

    if not changed_conditions:
        return 'No environmental changes.'

    return '\n'.join(changed_conditions)



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
            lines.append(f"- {label}: {float(item.get('production_flux', 0.0)):.3f}")

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
        status = f'consumed / uptake {uptake_flux:.3f}'
    elif secretion_flux > 0.001:
        status = f'secreted / export {secretion_flux:.3f}'
    else:
        status = 'no exchange detected'

    return f'- {label}: {raw_flux:.3f} -> {status}'


def _build_exchange_flux_report_text(exchange_fluxes):
    if not exchange_fluxes:
        return 'Exchange Flux Report\n\nRun a simulation first to generate exchange-flux evidence.'

    if exchange_fluxes.get('error'):
        return f"Exchange Flux Report\n\nError: {exchange_fluxes.get('error')}"

    items_by_id = _exchange_items_by_id(exchange_fluxes)

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
        'Exchange reactions connect the cell to the medium.',
        'Negative flux means uptake/consumption. Positive flux means secretion/export.',
        '',
    ]

    for title, reaction_ids in sections:
        measured_ids = [reaction_id for reaction_id in reaction_ids if reaction_id in items_by_id]
        if not measured_ids:
            continue
        lines.append(f'{title}:')
        for reaction_id in measured_ids:
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

    if sweep_data.get('error'):
        return f"Bound Sweep Report\n\nError: {sweep_data.get('error')}"

    reaction_id = sweep_data.get('reaction_id')
    reaction_name = sweep_data.get('reaction_name') or reaction_id
    bound_label = sweep_data.get('bound_label') or sweep_data.get('bound')
    tracked_fluxes = sweep_data.get('tracked_fluxes') or []
    rows = sweep_data.get('rows') or []

    if reaction_id == 'EX_o2_e':
        uptake_label = 'O2 uptake'
    elif reaction_id == 'EX_glc__D_e':
        uptake_label = 'Glucose uptake'
    else:
        uptake_label = 'Tested uptake'

    lines = [
        'Bound Sweep Report',
        '',
        f'Variable tested: {reaction_name} ({reaction_id}) {bound_label}',
        f"Method: {sweep_data.get('method')} | Objective: {sweep_data.get('objective')}",
        'A sweep runs the same setup several times while changing only this bound.',
        '',
        'Rows:',
        f'LB value | growth | {uptake_label} | tracked products',
    ]

    for row in rows:
        values = row.get('tracked_flux_values') or {}
        product_parts = []
        for flux_id in tracked_fluxes:
            label = PRODUCTION_FLUX_NAMES.get(flux_id, flux_id)
            product_parts.append(f"{label}: {_format_sweep_number(values.get(flux_id, 0.0))}")
        product_text = '; '.join(product_parts) if product_parts else 'none'
        tested_uptake = row.get('tested_reaction_uptake')
        if tested_uptake is None:
            tested_uptake = row.get('oxygen_uptake')
        status_note = ' infeasible' if row.get('status') == 'infeasible' else ''
        lines.append(
            f"{_format_sweep_number(row.get('bound_value'))} | "
            f"{_format_sweep_number(row.get('growth_value'))}{status_note} | "
            f"{_format_sweep_number(tested_uptake)} | "
            f"{product_text}"
        )

    if len(rows) >= 2:
        first = rows[0]
        last = rows[-1]
        try:
            growth_drop = float(first.get('growth_value', 0.0)) - float(last.get('growth_value', 0.0))
            first_uptake = first.get('tested_reaction_uptake', first.get('oxygen_uptake', 0.0))
            last_uptake = last.get('tested_reaction_uptake', last.get('oxygen_uptake', 0.0))
            uptake_drop = float(first_uptake or 0.0) - float(last_uptake or 0.0)
            lines.extend([
                '',
                'Trend summary:',
                f"- Growth change from first to last point: {_format_sweep_number(growth_drop)} drop",
                f"- {uptake_label} change from first to last point: {_format_sweep_number(uptake_drop)} drop",
            ])
        except Exception:
            pass

    if reaction_id == 'EX_glc__D_e':
        guide_lines = [
            '- Lower bound closer to 0 means less glucose can be consumed.',
            '- When carbon intake becomes limiting, growth and secretion should fall together.',
            '- Do not read only the final row: identify the trend and the collapse zone.'
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
    if not report_data:
        return 'Mission 26 Oxygen Sweep Check\n\nRun a Bound Sweep to generate the mission report.'

    if report_data.get('error') and not report_data.get('sweep_data'):
        return f"Mission 26 Oxygen Sweep Check\nError: {report_data.get('error')}"

    clean_status = (
        'Base setup: clean sensitivity setup detected.'
        if report_data.get('clean_base_setup')
        else 'Base setup: keep FBA, biomass objective, no knockouts and unchanged environment.'
    )
    sweep_status = (
        'Sweep variable: oxygen lower-bound sweep selected.'
        if report_data.get('oxygen_sweep_selected')
        else 'Sweep variable: select the oxygen lower bound in Bound Sweep Setup.'
    )
    points_status = (
        'Sweep points: all required values returned valid results.'
        if report_data.get('all_points_valid')
        else 'Sweep points: not enough valid points were returned.'
    )
    growth_status = (
        'Growth trend: growth decreases as oxygen becomes limited.'
        if report_data.get('growth_decreased')
        else 'Growth trend: the drop is not clear enough yet.'
    )
    oxygen_status = (
        'Oxygen trend: oxygen uptake decreases across the sweep.'
        if report_data.get('oxygen_uptake_decreased')
        else 'Oxygen trend: uptake did not decrease clearly.'
    )
    profile_status = (
        'Product profile: enough tracked products/byproducts changed.'
        if report_data.get('profile_changed')
        else 'Product profile: not enough tracked products/byproducts changed yet.'
    )
    final_status = (
        'Oxygen sensitivity sweep ready. Return to Dr. Luna and deliver it.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Open the Bound Sweep Report and inspect the trend.'
    )

    changed_fluxes = report_data.get('changed_fluxes') or []
    changed_text = ', '.join(changed_fluxes) if changed_fluxes else 'none'

    return (
        'Mission 26 Oxygen Sweep Check\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Variable: {report_data.get('sweep_reaction')} {report_data.get('sweep_bound')} bound\n"
        f"Values tested: {', '.join(str(v).rstrip('0').rstrip('.') for v in report_data.get('sweep_values') or [])}\n"
        f"Valid points: {report_data.get('valid_point_count')}\n\n"
        f"Growth trend:\n"
        f"- First point growth: {_format_sweep_number(report_data.get('first_growth'))}\n"
        f"- Last point growth: {_format_sweep_number(report_data.get('last_growth'))}\n"
        f"- Growth drop: {_format_sweep_number(report_data.get('growth_drop'))}\n"
        f"- Required minimum drop: {_format_sweep_number(report_data.get('minimum_growth_drop'))}\n\n"
        f"Oxygen trend:\n"
        f"- First point O2 uptake: {_format_sweep_number(report_data.get('first_oxygen_uptake'))}\n"
        f"- Last point O2 uptake: {_format_sweep_number(report_data.get('last_oxygen_uptake'))}\n"
        f"- O2 uptake drop: {_format_sweep_number(report_data.get('oxygen_uptake_drop'))}\n\n"
        f"Changed tracked fluxes: {changed_text}\n"
        f"Changed flux count: {report_data.get('changed_flux_count', 0)} / {report_data.get('minimum_changed_fluxes')}\n\n"
        f"{clean_status}\n"
        f"{sweep_status}\n"
        f"{points_status}\n"
        f"{growth_status}\n"
        f"{oxygen_status}\n"
        f"{profile_status}\n\n"
        f"{final_status}"
    )

def _visible_biomass_flux(results):
    """Read predicted biomass from the same visible simulation solution."""
    try:
        production_data = results[2]
        if isinstance(production_data, dict):
            value = production_data.get('biomass_raw')
            if value is not None:
                return max(float(value), 0.0)
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
    heading = 'Primary objective flux' if method_name == 'pFBA' else 'Objective flux'
    text = (
        f'{heading}:\n'
        f'{objective_name}: {objective_result}'
    )

    if method_name == 'pFBA':
        total_flux = diagnostics.get('total_absolute_flux')
        active_count = diagnostics.get('active_reaction_count')
        text += '\n\npFBA secondary criterion:'
        if total_flux is not None:
            text += f'\nTotal absolute flux: {_clean_report_number(total_flux):.3f}'
        else:
            text += '\nTotal absolute flux: not available'
        if active_count is not None:
            text += f'\nActive reactions: {int(active_count)}'
        text += '\nThe secondary value is not the selected primary objective flux.'

    biomass_flux = _visible_biomass_flux(results)
    if objective_name != MISSION07_BIOMASS_OBJECTIVE and biomass_flux is not None:
        biomass_flux = _clean_report_number(biomass_flux)
        text += f'\n\nPredicted biomass flux: {biomass_flux:.3f}'
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
    if not report_data:
        return 'Mission 27 Glucose Sweep Check\n\nRun a Bound Sweep to generate the mission report.'

    if report_data.get('error') and not report_data.get('sweep_data'):
        return f"Mission 27 Glucose Sweep Check\nError: {report_data.get('error')}"

    clean_status = (
        'Base setup: clean sensitivity setup detected.'
        if report_data.get('clean_base_setup')
        else 'Base setup: keep FBA, biomass objective, no knockouts and unchanged environment.'
    )
    sweep_status = (
        'Sweep variable: glucose lower-bound sweep selected.'
        if report_data.get('glucose_sweep_selected')
        else 'Sweep variable: select the D-Glucose lower bound in Bound Sweep Setup.'
    )
    tracking_status = (
        'Production Flux: full product/byproduct panel selected by the player.'
        if report_data.get('tracking_ready')
        else 'Production Flux: select the full product/byproduct panel before running the sweep.'
    )
    points_status = (
        'Sweep points: all required glucose-limitation points returned results.'
        if report_data.get('all_points_returned')
        else 'Sweep points: the glucose sweep is missing result points.'
    )
    growth_status = (
        'Growth trend: growth falls strongly as glucose becomes limiting.'
        if report_data.get('growth_decreased')
        else 'Growth trend: the drop is not strong enough for a carbon-limitation experiment.'
    )
    collapse_status = (
        'Collapse zone: final point shows severe/no growth.'
        if report_data.get('final_growth_low')
        else 'Collapse zone: the final point does not show strong enough limitation.'
    )
    gradual_status = (
        'Trend shape: several decreasing steps detected, not just one isolated change.'
        if report_data.get('trend_is_gradual')
        else 'Trend shape: look for a progressive decrease across several rows.'
    )
    uptake_status = (
        'Glucose uptake: uptake decreases across the sweep.'
        if report_data.get('glucose_uptake_decreased')
        else 'Glucose uptake: the tested uptake did not decrease enough.'
    )
    profile_status = (
        'Product profile: secretion profile decreases with carbon limitation.'
        if report_data.get('profile_decreased')
        else 'Product profile: not enough tracked products/byproducts decreased.'
    )
    final_status = (
        'Glucose limitation sweep ready. Return to Dr. Luna and deliver it.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Use the Bound Sweep Report to identify the glucose-limitation trend.'
    )

    decreased_fluxes = report_data.get('decreased_fluxes') or []
    decreased_text = ', '.join(decreased_fluxes) if decreased_fluxes else 'none'

    return (
        'Mission 27 Glucose Sweep Check\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Variable: {report_data.get('sweep_reaction')} {report_data.get('sweep_bound')} bound\n"
        f"Values tested: {', '.join(str(v).rstrip('0').rstrip('.') for v in report_data.get('sweep_values') or [])}\n"
        f"Result points: {report_data.get('result_point_count')} / {report_data.get('minimum_result_points')}\n"
        f"Decreasing growth steps: {report_data.get('decreasing_steps')} / {report_data.get('minimum_decreasing_steps')}\n\n"
        f"Growth trend:\n"
        f"- First point growth: {_format_sweep_number(report_data.get('first_growth'))}\n"
        f"- Last point growth: {_format_sweep_number(report_data.get('last_growth'))}\n"
        f"- Growth drop: {_format_sweep_number(report_data.get('growth_drop'))}\n"
        f"- Required minimum drop: {_format_sweep_number(report_data.get('minimum_growth_drop'))}\n"
        f"- Final growth must be <= {_format_sweep_number(report_data.get('maximum_final_growth'))}\n\n"
        f"Glucose uptake trend:\n"
        f"- First point glucose uptake: {_format_sweep_number(report_data.get('first_glucose_uptake'))}\n"
        f"- Last point glucose uptake: {_format_sweep_number(report_data.get('last_glucose_uptake'))}\n"
        f"- Glucose uptake drop: {_format_sweep_number(report_data.get('glucose_uptake_drop'))}\n"
        f"- Required minimum uptake drop: {_format_sweep_number(report_data.get('minimum_uptake_drop'))}\n\n"
        f"Decreased tracked fluxes: {decreased_text}\n"
        f"Decreased flux count: {report_data.get('decreased_flux_count', 0)} / {report_data.get('minimum_changed_fluxes')}\n\n"
        f"{clean_status}\n"
        f"{sweep_status}\n"
        f"{tracking_status}\n"
        f"{points_status}\n"
        f"{growth_status}\n"
        f"{collapse_status}\n"
        f"{gradual_status}\n"
        f"{uptake_status}\n"
        f"{profile_status}\n\n"
        f"{final_status}"
    )



def _build_mission28_text(report_data):
    if not report_data:
        return 'Mission 28 Carbon Source Sweep Check\n\nRun a Bound Sweep to generate the mission report.'

    if report_data.get('error') and not report_data.get('sweep_data'):
        return f"Mission 28 Carbon Source Sweep Check\nError: {report_data.get('error')}"

    base_status = (
        'Base medium: glucose uptake blocked, with no unrelated medium changes.'
        if report_data.get('base_medium_ready')
        else 'Base medium: close only glucose uptake before the sweep.'
    )
    sweep_status = (
        'Sweep variable: candidate alternative carbon-source lower bound selected.'
        if report_data.get('candidate_sweep_selected')
        else 'Sweep variable: choose one candidate carbon-source lower bound in Bound Sweep Setup.'
    )
    tracking_status = (
        'Production Flux: full product/byproduct panel selected.'
        if report_data.get('tracking_ready')
        else 'Production Flux: select the full product/byproduct panel before running the sweep.'
    )
    points_status = (
        'Sweep points: all required source-availability points returned results.'
        if report_data.get('all_points_returned')
        else 'Sweep points: missing result points.'
    )
    source_status = (
        'Source uptake: selected source is consumed and decreases across the sweep.'
        if report_data.get('source_consumed') and report_data.get('source_uptake_decreased')
        else 'Source uptake: the selected source is not showing a clear uptake trend.'
    )
    growth_status = (
        'Growth trend: viable at high source availability, then drops strongly.'
        if report_data.get('first_growth_viable') and report_data.get('growth_decreased')
        else 'Growth trend: the source does not show enough rescue/limitation yet.'
    )
    collapse_status = (
        'Collapse zone: final point shows severe/no growth.'
        if report_data.get('final_growth_low')
        else 'Collapse zone: final point should show severe/no growth.'
    )
    profile_status = (
        'Product profile: enough tracked products/byproducts changed.'
        if report_data.get('profile_changed')
        else 'Product profile: not enough tracked products/byproducts changed.'
    )
    final_status = (
        'Alternative carbon-source sweep ready. Return to Dr. Luna and deliver it.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Use the Bound Sweep Report to identify a stronger carbon-source trend.'
    )

    selected_source = report_data.get('selected_source') or 'none'
    changed_fluxes = report_data.get('changed_fluxes') or []
    changed_text = ', '.join(changed_fluxes) if changed_fluxes else 'none'
    unexpected = report_data.get('unexpected_environment_changes') or []
    unexpected_text = ', '.join(unexpected) if unexpected else 'none'

    return (
        'Mission 28 Carbon Source Sweep Check\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Blocked carbon source: {report_data.get('blocked_carbon_source')}\n"
        f"Selected sweep source: {selected_source}\n"
        f"Candidate sources: {', '.join(report_data.get('candidate_carbon_sources') or [])}\n"
        f"Values tested: {', '.join(str(v).rstrip('0').rstrip('.') for v in report_data.get('sweep_values') or [])}\n"
        f"Unexpected medium changes: {unexpected_text}\n"
        f"Result points: {report_data.get('result_point_count')} / {report_data.get('minimum_result_points')}\n"
        f"Decreasing growth steps: {report_data.get('decreasing_steps')} / {report_data.get('minimum_decreasing_steps')}\n\n"
        f"Growth trend:\n"
        f"- First point growth: {_format_sweep_number(report_data.get('first_growth'))}\n"
        f"- Minimum first growth: {_format_sweep_number(report_data.get('minimum_first_growth'))}\n"
        f"- Last point growth: {_format_sweep_number(report_data.get('last_growth'))}\n"
        f"- Final growth must be <= {_format_sweep_number(report_data.get('maximum_final_growth'))}\n"
        f"- Growth drop: {_format_sweep_number(report_data.get('growth_drop'))}\n"
        f"- Required growth drop: {_format_sweep_number(report_data.get('minimum_growth_drop'))}\n\n"
        f"Source uptake trend:\n"
        f"- First source uptake: {_format_sweep_number(report_data.get('first_source_uptake'))}\n"
        f"- Last source uptake: {_format_sweep_number(report_data.get('last_source_uptake'))}\n"
        f"- Source uptake drop: {_format_sweep_number(report_data.get('source_uptake_drop'))}\n"
        f"- Required uptake drop: {_format_sweep_number(report_data.get('minimum_source_uptake_drop'))}\n\n"
        f"Changed tracked fluxes: {changed_text}\n"
        f"Changed flux count: {report_data.get('changed_flux_count', 0)} / {report_data.get('minimum_changed_fluxes')}\n\n"
        f"{base_status}\n"
        f"{sweep_status}\n"
        f"{tracking_status}\n"
        f"{points_status}\n"
        f"{source_status}\n"
        f"{growth_status}\n"
        f"{collapse_status}\n"
        f"{profile_status}\n\n"
        f"{final_status}"
    )

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
    if not report_data:
        return ''

    if report_data.get('error') and report_data.get('objective_result') in (None, 'None'):
        return f"Mission 16 Medium Report\nError: {report_data.get('error')}"

    method_status = (
        'Method: FBA medium baseline selected.'
        if report_data.get('method_correct')
        else 'Method: use FBA for this first medium-engineering baseline.'
    )
    objective_status = (
        'Objective: biomass objective used to test growth rescue.'
        if report_data.get('objective_correct')
        else 'Objective: use the biomass objective to test whether growth is rescued.'
    )
    glucose_status = (
        'Original carbon source: glucose uptake is blocked.'
        if report_data.get('glucose_lower_bound_closed') and report_data.get('glucose_uptake_blocked')
        else 'Original carbon source: still available. Remove glucose uptake first.'
    )
    environment_status = (
        'Extra medium changes: none.'
        if not report_data.get('unexpected_environment_changes')
        else 'Extra medium changes: too many changes. Keep only glucose removal and one candidate source.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not report_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This is a medium challenge, not a knockout challenge.'
    )

    selected_sources = report_data.get('selected_alternative_sources') or []
    if not selected_sources:
        source_status = 'Alternative source: none selected yet. Open one candidate carbon source.'
    elif len(selected_sources) > 1:
        source_status = 'Alternative source: too many candidates opened. Test one source at a time.'
    elif report_data.get('source_uptake_detected'):
        source_status = f"Alternative source: {selected_sources[0]} is being consumed."
    else:
        source_status = f"Alternative source: {selected_sources[0]} is selected but uptake is not strong enough yet."

    growth_status = (
        'Growth: rescue detected.'
        if report_data.get('growth_ok')
        else f"Growth: still too low. Keep it above {float(report_data.get('minimum_growth', 0.0)):.1f}."
    )

    uptake_fluxes = report_data.get('medium_uptake_fluxes') or {}
    candidate_sources = report_data.get('candidate_carbon_sources') or []
    medium_lines = []
    for reaction_id in [report_data.get('blocked_carbon_source')] + candidate_sources:
        if not reaction_id:
            continue
        medium_lines.append(f"- {reaction_id}: uptake {float(uptake_fluxes.get(reaction_id, 0.0)):.3f}")
    medium_text = '\n'.join(medium_lines) if medium_lines else 'No medium fluxes available.'

    final_status = (
        'Alternative carbon rescue ready. Return to Dr. Rio and deliver the report.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Keep testing candidate sources and check the Medium Report.'
    )

    return (
        'Mission 16 Medium Report\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Selected objective: {report_data.get('selected_objective')}\n"
        f"Growth/objective flux: {report_data.get('objective_result')}\n"
        f"Selected alternative source(s): {', '.join(selected_sources) if selected_sources else 'none'}\n\n"
        f"Medium uptake evidence:\n{medium_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{glucose_status}\n"
        f"{source_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )



def _build_mission17_text(report_data):
    if not report_data:
        return ''

    if report_data.get('error') and report_data.get('objective_result') in (None, 'None'):
        return f"Mission 17 Essential Medium Check\nError: {report_data.get('error')}"

    method_status = (
        'Method: FBA selected for nutrient essentiality testing.'
        if report_data.get('method_correct')
        else 'Method: use FBA for this nutrient-essentiality test.'
    )
    objective_status = (
        'Objective: biomass objective used to test growth dependence.'
        if report_data.get('objective_correct')
        else 'Objective: use the biomass objective to test whether growth is affected.'
    )
    nutrient_status = (
        f"Medium component removed: {report_data.get('target_nutrient_name')} ({report_data.get('target_nutrient')})."
        if report_data.get('target_nutrient_closed')
        else 'Medium component: the expected essential nutrient has not been isolated yet.'
    )
    candidate_count_status = (
        'Candidate test: exactly one nutrient was removed.'
        if report_data.get('exactly_one_candidate_closed')
        else 'Candidate test: remove exactly one candidate nutrient at a time.'
    )
    environment_status = (
        'Extra medium changes: none.'
        if not report_data.get('unexpected_environment_changes')
        else 'Extra medium changes: too many changes. Keep only one nutrient removal.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not report_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This is a medium-essentiality challenge.'
    )
    growth_status = (
        'Growth response: growth collapsed after nutrient removal.'
        if report_data.get('growth_collapsed')
        else f"Growth response: still above the collapse threshold ({float(report_data.get('maximum_growth_after_removal', 0.0)):.1f})."
    )

    uptake_fluxes = report_data.get('medium_uptake_fluxes') or {}
    candidate_nutrients = report_data.get('candidate_nutrients') or []
    medium_lines = []
    for reaction_id in candidate_nutrients:
        medium_lines.append(f"- {reaction_id}: uptake {float(uptake_fluxes.get(reaction_id, 0.0)):.3f}")
    medium_text = '\n'.join(medium_lines) if medium_lines else 'No medium fluxes available.'

    closed = report_data.get('closed_candidate_nutrients') or []
    final_status = (
        'Essential medium component identified. Return to Dr. Rio and deliver the report.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Test one candidate nutrient at a time and check the growth response.'
    )

    return (
        'Mission 17 Essential Medium Check\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Selected objective: {report_data.get('selected_objective')}\n"
        f"Growth/objective flux: {report_data.get('objective_result')}\n"
        f"Closed candidate nutrient(s): {', '.join(closed) if closed else 'none'}\n\n"
        f"Medium uptake evidence:\n{medium_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{candidate_count_status}\n"
        f"{nutrient_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )




def _build_mission18_text(report_data):
    if not report_data:
        return ''

    if report_data.get('error') and report_data.get('objective_result') in (None, 'None'):
        return f"Mission 18 Export Bottleneck Check\nError: {report_data.get('error')}"

    method_status = (
        'Method: FBA selected for export-bottleneck testing.'
        if report_data.get('method_correct')
        else 'Method: use FBA for this export-bottleneck test.'
    )
    objective_status = (
        'Objective: biomass objective used to test viability.'
        if report_data.get('objective_correct')
        else 'Objective: use the biomass objective to test whether the design remains viable.'
    )
    carbon_status = (
        'Carbon source: glucose uptake blocked and pyruvate uptake detected.'
        if report_data.get('glucose_uptake_blocked') and report_data.get('pyruvate_uptake_detected')
        else 'Carbon source: remove glucose uptake and confirm pyruvate uptake.'
    )
    bottleneck_status = (
        f"Export bottleneck: {report_data.get('export_bottleneck_name')} export is constrained."
        if report_data.get('acetate_export_blocked')
        else f"Export bottleneck: {report_data.get('export_bottleneck_name')} can still be secreted. Check the upper bound."
    )
    environment_status = (
        'Extra medium changes: none.'
        if not report_data.get('unexpected_environment_changes')
        else 'Extra medium changes: too many changes. Keep only the carbon-source swap and export bottleneck.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not report_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This mission is about exchange bounds, not genes.'
    )
    tracking_status = (
        'Evidence: required product/byproduct fluxes are being tracked.'
        if report_data.get('tracking_ready')
        else 'Evidence: track acetate and the competing fermentation products.'
    )
    growth_status = (
        'Growth: viable under the bottleneck design.'
        if report_data.get('growth_ok')
        else f"Growth: below the viability threshold ({float(report_data.get('minimum_growth', 0.0)):.1f})."
    )

    uptake_fluxes = report_data.get('medium_uptake_fluxes') or {}
    tracked_values = report_data.get('tracked_flux_values') or {}

    medium_lines = []
    for reaction_id in [
        report_data.get('blocked_carbon_source'),
        report_data.get('alternative_carbon_source'),
        report_data.get('export_bottleneck'),
    ]:
        if reaction_id:
            medium_lines.append(f"- {reaction_id}: uptake {float(uptake_fluxes.get(reaction_id, 0.0)):.3f}")
    medium_text = '\n'.join(medium_lines) if medium_lines else 'No medium fluxes available.'

    production_lines = []
    for reaction_id in report_data.get('required_tracked_fluxes') or []:
        production_lines.append(f"- {reaction_id}: production {float(tracked_values.get(reaction_id, 0.0)):.3f}")
    production_text = '\n'.join(production_lines) if production_lines else 'No production fluxes selected.'

    missing = report_data.get('missing_required_fluxes') or []
    final_status = (
        'Export bottleneck diagnosed. Return to Dr. Rio and deliver the report.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Check the medium setup, export bound and flux evidence.'
    )

    return (
        'Mission 18 Export Bottleneck Check\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Selected objective: {report_data.get('selected_objective')}\n"
        f"Growth/objective flux: {report_data.get('objective_result')}\n"
        f"Export bottleneck target: {report_data.get('export_bottleneck')}\n"
        f"Missing tracked fluxes: {', '.join(missing) if missing else 'none'}\n\n"
        f"Medium uptake evidence:\n{medium_text}\n\n"
        f"Production/export evidence:\n{production_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{carbon_status}\n"
        f"{bottleneck_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{tracking_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )

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
    if not report_data:
        return 'Mission 19 Perturbation Check\n\nRun a simulation to generate a perturbation report.'

    if report_data.get('error'):
        return f"Mission 19 Perturbation Check\nError: {report_data.get('error')}"

    method_status = (
        'Method: lMOMA selected for perturbation-response analysis.'
        if report_data.get('method_correct')
        else 'Method: use lMOMA to study the response after a knockout.'
    )
    objective_status = (
        'Objective: biomass objective selected for viability.'
        if report_data.get('objective_correct')
        else 'Objective: use the biomass objective to evaluate mutant viability.'
    )
    environment_status = (
        'Environment: unchanged.'
        if not report_data.get('environment_changed')
        else 'Environment: changed. Keep the medium unchanged for this perturbation test.'
    )
    knockout_status = (
        f"Knockout: useful perturbation found ({report_data.get('target_gene')} / {report_data.get('target_gene_name')})."
        if report_data.get('target_gene_found')
        else 'Knockout: test one candidate gene at a time.'
    )
    evidence_status = (
        'Evidence: required pathway product fluxes are being tracked.'
        if report_data.get('tracking_ready')
        else 'Evidence: incomplete. Track the required pathway products.'
    )
    growth_status = (
        'Growth: mutant response remains viable.'
        if report_data.get('growth_ok')
        else 'Growth: mutant response is not viable enough yet.'
    )

    flux_lines = []
    tracked_values = report_data.get('tracked_flux_values') or {}
    for reaction_id in report_data.get('required_tracked_fluxes') or []:
        flux_lines.append(f"- {reaction_id}: {float(tracked_values.get(reaction_id, 0.0)):.3f}")
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    missing = report_data.get('missing_required_fluxes') or []
    missing_text = ', '.join(missing) if missing else 'none'

    final_status = (
        'Perturbation report ready. Return to Dr. Rio and deliver the results.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Keep testing method, knockout choice and flux evidence.'
    )

    knocked_out = ', '.join(report_data.get('knocked_out_genes') or []) or 'none'

    return (
        'Mission 19 Perturbation Check\n\n'
        f"Target method: {report_data.get('target_method')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Objective: {report_data.get('selected_objective')}\n"
        f"Objective result shown by method: {report_data.get('objective_result')}\n"
        f"Biomass flux used for viability: {report_data.get('biomass_flux')}\n"
        f"Growth measure: {report_data.get('growth_measure')}\n\n"
        f"Candidate genes: {', '.join(report_data.get('candidate_genes') or [])}\n"
        f"Knocked-out genes: {knocked_out}\n\n"
        f"Tracked pathway fluxes:\n{flux_text}\n"
        f"Missing evidence: {missing_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{evidence_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )



def _build_mission20_text(report_data):
    if not report_data:
        return 'Mission 20 Robustness Report\n\nRun a simulation to generate a final medium report.'

    if report_data.get('error') and report_data.get('objective_result') in (None, 'None'):
        return f"Mission 20 Robustness Report\nError: {report_data.get('error')}"

    method_status = (
        'Method: pFBA selected for a parsimonious robustness report.'
        if report_data.get('method_correct')
        else 'Method: use pFBA for the final robustness report.'
    )
    objective_status = (
        'Objective: biomass objective selected for viability.'
        if report_data.get('objective_correct')
        else 'Objective: use the biomass objective to evaluate growth viability.'
    )
    carbon_status = (
        'Carbon source: glucose blocked and pyruvate uptake detected in the Exchange Flux Report.'
        if report_data.get('glucose_uptake_blocked') and report_data.get('pyruvate_uptake_detected')
        else 'Carbon source: verify glucose removal and pyruvate uptake in the Exchange Flux Report.'
    )
    bottleneck_status = (
        'Export stress: acetate export bottleneck detected.'
        if report_data.get('acetate_export_blocked')
        else 'Export stress: acetate export is not constrained enough yet.'
    )
    essential_status = (
        'Essential uptake: required nutrient uptake evidence detected.'
        if report_data.get('essential_uptake_ready')
        else 'Essential uptake: Exchange Flux Report is missing required nutrient evidence.'
    )
    environment_status = (
        'Extra medium changes: none.'
        if not report_data.get('unexpected_environment_changes')
        else 'Extra medium changes: too many changes. Keep the final stress design controlled.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not report_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This final Rio report keeps the strain unchanged.'
    )
    evidence_status = (
        'Production evidence: full byproduct panel tracked.'
        if report_data.get('tracking_ready')
        else 'Production evidence: incomplete. Track the full byproduct panel.'
    )
    growth_status = (
        'Growth: design remains viable under the modified medium.'
        if report_data.get('growth_ok')
        else f"Growth: below the robustness threshold ({float(report_data.get('minimum_growth', 0.0)):.1f})."
    )

    uptake_fluxes = report_data.get('medium_uptake_fluxes') or {}
    uptake_ids = [
        report_data.get('blocked_carbon_source'),
        report_data.get('alternative_carbon_source'),
    ] + list(report_data.get('required_essential_uptakes') or []) + ['EX_o2_e']
    medium_lines = []
    for reaction_id in uptake_ids:
        if not reaction_id:
            continue
        medium_lines.append(f"- {reaction_id}: uptake {float(uptake_fluxes.get(reaction_id, 0.0)):.3f}")
    medium_text = '\n'.join(medium_lines) if medium_lines else 'No medium uptake evidence available.'

    tracked_values = report_data.get('tracked_flux_values') or {}
    flux_lines = []
    for reaction_id in report_data.get('required_tracked_fluxes') or []:
        flux_lines.append(f"- {reaction_id}: production {float(tracked_values.get(reaction_id, 0.0)):.3f}")
    flux_text = '\n'.join(flux_lines) if flux_lines else 'No production fluxes tracked.'

    missing_fluxes = report_data.get('missing_required_fluxes') or []
    missing_fluxes_text = ', '.join(missing_fluxes) if missing_fluxes else 'none'
    missing_uptakes = report_data.get('missing_essential_uptakes') or []
    missing_uptakes_text = ', '.join(missing_uptakes) if missing_uptakes else 'none'

    final_status = (
        'Final medium robustness report ready. Return to Dr. Rio and deliver the results.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Refine method, medium changes, exchange stress and flux evidence.'
    )

    knocked_out = ', '.join(report_data.get('knocked_out_genes') or []) or 'none'

    return (
        'Mission 20 Robustness Report\n\n'
        f"Context: {report_data.get('target_context')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Selected objective: {report_data.get('selected_objective')}\n"
        f"Growth/objective result: {report_data.get('objective_result')}\n"
        f"Knocked-out genes: {knocked_out}\n\n"
        f"Exchange Flux Report evidence:\n{medium_text}\n"
        f"Missing essential uptake evidence: {missing_uptakes_text}\n\n"
        f"Production/byproduct evidence:\n{flux_text}\n"
        f"Missing production evidence: {missing_fluxes_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{carbon_status}\n"
        f"{bottleneck_status}\n"
        f"{essential_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{evidence_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )



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

    def fmt(value):
        return 'not available' if value is None else f'{_clean_report_number(value):.3f}'

    return (
        'Mission 01 Anaerobic Growth\n\n'
        f"Method: {compare_data.get('target_method')}\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Oxygen exchange: {compare_data.get('oxygen_reaction')}\n\n"
        f"Growth comparison:\n"
        f"- Aerobic baseline: {fmt(compare_data.get('baseline_growth'))}\n"
        f"- Anaerobic growth: {fmt(compare_data.get('anaerobic_growth'))}\n"
        f"- Growth decrease: {fmt(compare_data.get('growth_drop'))}\n\n"
        f"Oxygen uptake magnitude:\n"
        f"- Aerobic baseline: {fmt(compare_data.get('baseline_oxygen_uptake'))}\n"
        f"- Anaerobic run: {fmt(compare_data.get('anaerobic_oxygen_uptake'))}\n"
        f"  (Uptake is shown as a positive magnitude; raw EX_o2_e flux is negative when oxygen is consumed.)\n\n"
        f"{baseline_status}\n"
        f"{anaerobic_status}\n"
        f"{viability_status}\n"
        f"{growth_status}\n"
        f"{oxygen_status}\n\n"
        f"FBA interpretation: the mission validates growth and oxygen evidence, not one unique byproduct profile; alternative optimal flux distributions may exist.\n\n"
        f"{final_status}"
    )


def _build_mission21_text(compare_data):
    if not compare_data:
        return 'Mission 21 Controlled Comparison\n\nRun two simulations to generate a comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 21 Controlled Comparison\n\n{compare_data.get('error')}"

    baseline_status = (
        'Baseline run: normal growth setup found.'
        if compare_data.get('baseline_run_found')
        else 'Baseline run: missing. Run FBA with biomass objective, no knockouts and unchanged environment.'
    )
    anaerobic_status = (
        'Modified run: oxygen-limited setup found.'
        if compare_data.get('oxygen_limited_run_found')
        else 'Modified run: missing. Run the same setup but close the lower bound of oxygen.'
    )
    growth_status = (
        'Comparison: growth decreases under oxygen limitation.'
        if compare_data.get('growth_decreased')
        else 'Comparison: growth difference is not clear enough yet.'
    )
    oxygen_status = (
        'Oxygen evidence: oxygen uptake decreased in the modified run.'
        if compare_data.get('oxygen_uptake_decreased')
        else 'Oxygen evidence: use Compare Runs / Exchange Flux Report to inspect oxygen uptake.'
    )

    final_status = (
        'Controlled comparison ready. Return to Dr. Vega and deliver the report.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Run the baseline first, then the oxygen-limited setup.'
    )

    baseline_growth = compare_data.get('baseline_growth')
    oxygen_growth = compare_data.get('oxygen_limited_growth')
    growth_drop = compare_data.get('growth_drop')
    baseline_o2 = compare_data.get('baseline_oxygen_uptake')
    oxygen_o2 = compare_data.get('oxygen_limited_oxygen_uptake')

    def fmt(value):
        return 'not available' if value is None else f'{float(value):.3f}'

    return (
        'Mission 21 Controlled Comparison\n\n'
        f"Target: aerobic baseline vs oxygen-limited growth\n"
        f"Method: {compare_data.get('target_method')}\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Oxygen reaction: {compare_data.get('oxygen_reaction')}\n\n"
        f"Growth comparison:\n"
        f"- Baseline growth: {fmt(baseline_growth)}\n"
        f"- Oxygen-limited growth: {fmt(oxygen_growth)}\n"
        f"- Growth drop: {fmt(growth_drop)}\n\n"
        f"Oxygen uptake evidence:\n"
        f"- Baseline oxygen uptake: {fmt(baseline_o2)}\n"
        f"- Oxygen-limited oxygen uptake: {fmt(oxygen_o2)}\n\n"
        f"{baseline_status}\n"
        f"{anaerobic_status}\n"
        f"{growth_status}\n"
        f"{oxygen_status}\n\n"
        f"{final_status}"
    )


def _build_mission22_text(compare_data):
    if not compare_data:
        return 'Mission 22 Knockout Comparison\n\nRun two simulations to generate a comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 22 Knockout Comparison\n\n{compare_data.get('error')}"

    baseline_status = (
        'Baseline run: normal strain found.'
        if compare_data.get('baseline_run_found')
        else 'Baseline run: missing. Run FBA with biomass objective, no knockouts, unchanged environment and ethanol tracked.'
    )
    knockout_status = (
        f"Knockout run: {compare_data.get('target_gene')} / {compare_data.get('target_gene_name')} found."
        if compare_data.get('knockout_run_found')
        else f"Knockout run: missing. Turn off only {compare_data.get('target_gene')} and keep the environment unchanged."
    )
    tracking_status = (
        f"Evidence: {compare_data.get('target_flux')} was tracked in both runs."
        if compare_data.get('target_flux_tracked')
        else f"Evidence: track {compare_data.get('target_flux')} in Production Flux for both runs."
    )
    production_status = (
        'Comparison: target product increased after the knockout.'
        if compare_data.get('production_increased')
        else 'Comparison: product increase is not clear enough yet.'
    )
    growth_status = (
        'Growth: both runs remain viable.'
        if compare_data.get('growth_ok')
        else 'Growth: one of the runs is not viable enough.'
    )
    final_status = (
        'Knockout comparison ready. Return to Dr. Vega and deliver the report.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Run the baseline first, then the knockout setup.'
    )

    baseline_growth = compare_data.get('baseline_growth')
    knockout_growth = compare_data.get('knockout_growth')
    baseline_flux = compare_data.get('baseline_product_flux')
    knockout_flux = compare_data.get('knockout_product_flux')
    production_increase = compare_data.get('production_increase')

    def fmt(value):
        return 'not available' if value is None else f'{float(value):.3f}'

    return (
        'Mission 22 Knockout Comparison\n\n'
        f"Target: normal strain vs production knockout\n"
        f"Method: {compare_data.get('target_method')}\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Target product: {compare_data.get('target_product')} ({compare_data.get('target_flux')})\n"
        f"Target gene: {compare_data.get('target_gene')} / {compare_data.get('target_gene_name')}\n\n"
        f"Growth comparison:\n"
        f"- Baseline growth: {fmt(baseline_growth)}\n"
        f"- Knockout growth: {fmt(knockout_growth)}\n\n"
        f"Production comparison:\n"
        f"- Baseline product flux: {fmt(baseline_flux)}\n"
        f"- Knockout product flux: {fmt(knockout_flux)}\n"
        f"- Production increase: {fmt(production_increase)}\n\n"
        f"{baseline_status}\n"
        f"{knockout_status}\n"
        f"{tracking_status}\n"
        f"{production_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )


def _build_mission23_text(compare_data):
    if not compare_data:
        return 'Mission 23 Objective Comparison\n\nRun two simulations to generate a comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 23 Objective Comparison\n\n{compare_data.get('error')}"

    growth_run_status = (
        'Run with biomass objective found.'
        if compare_data.get('growth_objective_run_found')
        else 'Missing growth-objective run. Use FBA, biomass objective, no knockouts and unchanged environment.'
    )
    product_run_status = (
        'Run with product objective found.'
        if compare_data.get('product_objective_run_found')
        else f"Missing product-objective run. Use {compare_data.get('target_objective')} as the objective."
    )
    objective_status = (
        'Objective change detected: growth objective vs product objective.'
        if compare_data.get('objective_changed')
        else 'Objective change not detected yet. The two runs must use different objectives.'
    )
    tracking_status = (
        f"Evidence: {compare_data.get('target_flux')} was tracked in both runs."
        if compare_data.get('target_flux_tracked')
        else f"Evidence: track {compare_data.get('target_flux')} in Production Flux for both runs."
    )
    production_status = (
        'Comparison: target product increased when the product objective was used.'
        if compare_data.get('production_increased')
        else 'Comparison: product increase is not clear enough yet.'
    )
    final_status = (
        'Objective comparison ready. Return to Dr. Vega and deliver the report.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Compare the growth objective with the ethanol objective.'
    )

    growth_objective_value = compare_data.get('growth_objective_value')
    product_objective_value = compare_data.get('product_objective_value')
    baseline_flux = compare_data.get('baseline_product_flux')
    product_flux = compare_data.get('product_objective_flux')
    production_increase = compare_data.get('production_increase')

    def fmt(value):
        return 'not available' if value is None else f'{float(value):.3f}'

    return (
        'Mission 23 Objective Comparison\n\n'
        f"Target: growth objective vs ethanol objective\n"
        f"Method: {compare_data.get('target_method')}\n"
        f"Growth objective: {compare_data.get('baseline_objective')}\n"
        f"Product objective: {compare_data.get('target_objective')}\n"
        f"Target product: {compare_data.get('target_product')} ({compare_data.get('target_flux')})\n\n"
        f"Objective values:\n"
        f"- Biomass objective run: {fmt(growth_objective_value)}\n"
        f"- Product objective run: {fmt(product_objective_value)}\n\n"
        f"Production comparison:\n"
        f"- Product flux with biomass objective: {fmt(baseline_flux)}\n"
        f"- Product flux with product objective: {fmt(product_flux)}\n"
        f"- Production increase: {fmt(production_increase)}\n\n"
        f"{growth_run_status}\n"
        f"{product_run_status}\n"
        f"{objective_status}\n"
        f"{tracking_status}\n"
        f"{production_status}\n\n"
        f"{final_status}"
    )


def _build_mission24_text(compare_data):
    if not compare_data:
        return 'Mission 24 Method Comparison\n\nRun two simulations to generate a comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 24 Method Comparison\n\n{compare_data.get('error')}"

    fba_status = (
        'FBA run found.'
        if compare_data.get('fba_run_found')
        else 'Missing FBA run. Use FBA with biomass objective, no knockouts and unchanged environment.'
    )
    pfba_status = (
        'pFBA run found.'
        if compare_data.get('pfba_run_found')
        else 'Missing pFBA run. Use pFBA with the same objective, genes and environment.'
    )
    method_status = (
        'Method change detected: FBA vs pFBA.'
        if compare_data.get('method_changed')
        else 'Method change not detected yet. The two runs must use different methods.'
    )
    setup_status = (
        'Controlled setup: objective, genes and environment stayed the same.'
        if compare_data.get('same_objective') and compare_data.get('same_clean_setup')
        else 'Controlled setup: keep objective, genes and environment unchanged in both runs.'
    )
    tracking_status = (
        'Evidence: full production-flux panel was tracked in both runs.'
        if compare_data.get('tracking_ready')
        else 'Evidence: track the full production-flux panel in both runs.'
    )
    final_status = (
        'Method comparison ready. Return to Dr. Vega and deliver the report.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Compare FBA with pFBA while keeping the setup controlled.'
    )

    def fmt(value):
        return 'not available' if value is None else f'{float(value):.3f}'

    required_fluxes = compare_data.get('required_tracked_fluxes') or []
    fba_values = compare_data.get('fba_tracked_flux_values') or {}
    pfba_values = compare_data.get('pfba_tracked_flux_values') or {}
    differences = compare_data.get('tracked_flux_differences') or {}

    flux_lines = []
    for reaction_id in required_fluxes:
        label = PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)
        flux_lines.append(
            f"- {label}: FBA {fmt(fba_values.get(reaction_id))} -> pFBA {fmt(pfba_values.get(reaction_id))} "
            f"({fmt(differences.get(reaction_id))})"
        )
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    return (
        'Mission 24 Method Comparison\n\n'
        f"Target: FBA vs pFBA using the same growth setup\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Methods: {compare_data.get('baseline_method')} -> {compare_data.get('target_method')}\n\n"
        f"Objective values:\n"
        f"- FBA objective value: {fmt(compare_data.get('fba_objective_value'))}\n"
        f"- pFBA objective value: {fmt(compare_data.get('pfba_objective_value'))}\n\n"
        f"Tracked production-flux panel:\n{flux_text}\n\n"
        f"{fba_status}\n"
        f"{pfba_status}\n"
        f"{method_status}\n"
        f"{setup_status}\n"
        f"{tracking_status}\n\n"
        f"{final_status}"
    )


def _build_mission25_text(compare_data):
    if not compare_data:
        return 'Mission 25 Final Controlled Report\n\nRun two simulations to generate the final comparison.'

    if compare_data.get('error') and not compare_data.get('run_a'):
        return f"Mission 25 Final Controlled Report\n\n{compare_data.get('error')}"

    baseline_status = (
        'Run A baseline found.'
        if compare_data.get('baseline_run_found')
        else 'Missing Run A. Use FBA, biomass objective, no knockouts and unchanged environment.'
    )
    oxygen_status = (
        'Run B oxygen-limited setup found.'
        if compare_data.get('oxygen_limited_run_found')
        else f"Missing Run B. Close only the lower bound of {compare_data.get('oxygen_reaction')}."
    )
    tracking_status = (
        'Evidence: full production-flux panel was tracked in both runs.'
        if compare_data.get('tracking_ready')
        else 'Evidence: track the full production-flux panel in both runs.'
    )
    growth_status = (
        'Growth comparison: oxygen limitation reduced growth clearly.'
        if compare_data.get('growth_decreased')
        else 'Growth comparison: growth drop is not clear enough yet.'
    )
    profile_status = (
        'Production profile: tracked products changed after oxygen limitation.'
        if compare_data.get('production_profile_changed')
        else 'Production profile: not enough tracked products changed yet.'
    )
    final_status = (
        'Final controlled report ready. Return to Dr. Vega and deliver the report.'
        if compare_data.get('ready_to_deliver')
        else 'Not ready yet. Keep the comparison controlled and check Compare Runs.'
    )

    def fmt(value):
        return 'not available' if value is None else f'{float(value):.3f}'

    required_fluxes = compare_data.get('required_tracked_fluxes') or []
    baseline_values = compare_data.get('baseline_tracked_flux_values') or {}
    oxygen_values = compare_data.get('oxygen_limited_tracked_flux_values') or {}
    differences = compare_data.get('tracked_flux_differences') or {}

    flux_lines = []
    for reaction_id in required_fluxes:
        label = PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)
        flux_lines.append(
            f"- {label}: baseline {fmt(baseline_values.get(reaction_id))} -> oxygen-limited {fmt(oxygen_values.get(reaction_id))} "
            f"({fmt(differences.get(reaction_id))})"
        )
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    changed_fluxes = compare_data.get('changed_fluxes') or []
    changed_text = ', '.join(changed_fluxes) if changed_fluxes else 'none'

    return (
        'Mission 25 Final Controlled Report\n\n'
        f"Target: aerobic baseline vs oxygen-limited medium\n"
        f"Method: {compare_data.get('target_method')}\n"
        f"Objective: {compare_data.get('growth_objective')}\n"
        f"Controlled variable: oxygen uptake ({compare_data.get('oxygen_reaction')})\n\n"
        f"Growth comparison:\n"
        f"- Baseline growth: {fmt(compare_data.get('baseline_growth'))}\n"
        f"- Oxygen-limited growth: {fmt(compare_data.get('oxygen_limited_growth'))}\n"
        f"- Growth drop: {fmt(compare_data.get('growth_drop'))}\n\n"
        f"Oxygen uptake comparison:\n"
        f"- Baseline oxygen uptake: {fmt(compare_data.get('baseline_oxygen_uptake'))}\n"
        f"- Oxygen-limited oxygen uptake: {fmt(compare_data.get('oxygen_limited_oxygen_uptake'))}\n\n"
        f"Tracked production-flux profile:\n{flux_text}\n\n"
        f"Changed tracked fluxes: {changed_text}\n"
        f"Changed flux count: {compare_data.get('changed_flux_count', 0)} / {compare_data.get('minimum_changed_fluxes')}\n\n"
        f"{baseline_status}\n"
        f"{oxygen_status}\n"
        f"{tracking_status}\n"
        f"{growth_status}\n"
        f"{profile_status}\n\n"
        f"{final_status}"
    )


class Window:
    def __init__(self, toggle_menu, player) -> None:

        # general setup
        self.player = player
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        # font_path = get_resource_path('font/LycheeSoda.ttf')
        # font2_path = get_resource_path('font/NotoColorEmoji-Regular.ttf')
        # self.font = pygame.font.Font(font_path,30)
        self.results = ''

        # self.index = 0
        self.timer = Timer(200)



    async def setup(self):

        ecoli_rip = get_resource_path('graphics/environment/ecoli_rip.jpg')
        
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Simulation Menu',
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
        if '02' in self.player.missions_activated and '02' not in self.player.missions_completed:
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
        # Reactions (Range slider) // pode-se alterar as bounds para text inputs de forma a alterar para 0,0 (com range slider não é possível)
        for i in range(len(REACTIONS.name)):
            reaction_label = _format_reaction_menu_label(REACTIONS.name.iloc[i], REACTIONS.index[i])
            menu_reactions.add.label(reaction_label, wordwrap=True)
            if REACTIONS.lb.iloc[i] != 0:
                default_lb_bool = True
            else:
                default_lb_bool = False
            if REACTIONS.ub.iloc[i] != 0:
                default_ub_bool = True
            else:
                default_ub_bool = False
            menu_reactions.add.toggle_switch(
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
            menu_reactions.add.toggle_switch(
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
            # menu_reactions.add.range_slider('Lower Bound', REACTIONS.lb[i], (-1000,0), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]+'lb') #, rangeslider_id=OPTIONS['Reactions'][i])
            # menu_reactions.add.range_slider('Upper Bound', REACTIONS.ub[i], (0, 1000), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]+'ub') #, rangeslider_id=OPTIONS['Reactions'][i])

            menu_reactions.add.vertical_margin(30)

            if _YIELD_ON_WEB and (i + 1) % 4 == 0:
                await asyncio.sleep(0)
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
        ]
        for mission_id, candidates in gene_mission_candidates:
            if mission_id in self.player.missions_activated and mission_id not in self.player.missions_completed:
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
                if _gene_matches_search(gene_id, current_search):
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
            """Reactivate every gene and restore the genes page to its default state."""
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
        menu_genes.add.button(
            'Search / Refresh',
            apply_gene_search,
            font_color='white',
            background_color=(20, 100, 100)
        )
        menu_genes.add.button(
            'Clear Search',
            clear_gene_search,
            font_color='white',
            background_color=(70, 70, 70)
        )
        menu_genes.add.button(
            'Reset Genes',
            reset_gene_toggles,
            font_color='white',
            background_color=(150, 40, 40)
        )
        menu_genes.add.vertical_margin(20)

        for i, gene_id in enumerate(GENES):
            gene_label = GENE_LABELS.get(gene_id, gene_id)

            if gene_id in active_gene_mission_candidates:
                gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                    gene_label,
                    True,
                    kwargs=gene_id,
                    toggleswitch_id=gene_id,
                    background_color="gold",
                    font_color="black"
                )
            else:
                gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                    gene_label,
                    True,
                    kwargs=gene_id,
                    toggleswitch_id=gene_id
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

        objectives = []
        default_obj = 0
        # print(str(objective))
        
        for i in range(len(REACTIONS_v0)):
            if REACTIONS_v0.index[i] == str(objective):
                default_obj = i
            objectives.append((REACTIONS_v0.index[i], REACTIONS_v0.index[i]))
        
        menu_objective.add.dropselect(title='Objective: ',
                                   items=objectives,
                                   default=default_obj,
                                   selection_box_height=8,
                                   selection_box_width=500,
                                   dropselect_id='objective')
        # menu_objective.add.range_slider('Fraction', default=90, range_values=(0,100), increment=1, rangeslider_id='obj_fraction')

        menu_objective.add.vertical_margin(30)
        menu_objective.add.label("TIP: \nBy default, you want \"Biomass” to be set as the objective because you want to see if E. Coli can grow or even survive in the environment you create.",
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
            "Bound Sweep tests one environmental bound at several numeric values.\nUse it when you want to read a trend instead of comparing only two simulations.",
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color="white",
            font_size=26
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.dropselect(
            title='Sweep variable: ',
            items=[
                ('Oxygen lower bound (EX_o2_e)', 'EX_o2_e:lower'),
                ('D-Glucose lower bound (EX_glc__D_e)', 'EX_glc__D_e:lower'),
                ('Acetate lower bound (EX_ac_e)', 'EX_ac_e:lower'),
                ('Pyruvate lower bound (EX_pyr_e)', 'EX_pyr_e:lower'),
                ('L-Malate lower bound (EX_mal__L_e)', 'EX_mal__L_e:lower'),
                ('Fumarate lower bound (EX_fum_e)', 'EX_fum_e:lower'),
                ('2-Oxoglutarate lower bound (EX_akg_e)', 'EX_akg_e:lower'),
                # Future Dr. Luna missions can add nutrient sweeps here.
            ],
            default=0,
            selection_box_height=4,
            selection_box_width=520,
            dropselect_id='sweep_variable',
            background_color='white',
            font_color=(20, 0, 150)
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.dropselect(
            title='Sweep values: ',
            items=[
                ('O2 transition: -20, -10, -5, 0', 'oxygen_transition'),
                ('Glucose limitation: -1000, -500, -100, -50, -10, 0', 'glucose_limitation'),
                ('Alternative carbon: -20, -10, -5, -1, 0', 'alternative_carbon_limitation'),
                # Future presets can be added here without changing the report UI.
            ],
            default=0,
            selection_box_height=4,
            selection_box_width=520,
            dropselect_id='sweep_values',
            background_color='white',
            font_color=(20, 0, 150)
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.label(
            "Dr. Luna note: follow the active mission setup first, then select the requested sweep. Some missions need a clean base setup; harder missions may ask for one controlled medium change before the sweep.",
            wordwrap=True,
            padding=(20, 20, 20, 20),
            background_color='white',
            font_size=24
        )
        menu_bound_sweep.add.vertical_margin(20)
        menu_bound_sweep.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_bound_sweep.add.vertical_margin(20)


        def data_fun() -> None:
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
            data_genes = _build_clean_gene_data(raw_data_genes)
            data_reac = menu_reactions.get_input_data()
            data_fluxes = _build_clean_production_flux_data(menu_production_flux.get_input_data())



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
            objective_name = _selected_menu_value(data_objective, 'objective')

            menu_summary.add.vertical_margin(30)

            _add_summary_section(
                menu_summary,
                'General setup',
                f'Simulation method: {simulation_method}\nObjective: {objective_name}'
            )

            _add_summary_section(
                menu_summary,
                'Gene knockouts',
                _build_gene_summary(data_genes)
            )

            _add_summary_section(
                menu_summary,
                'Environmental changes',
                _build_environmental_summary(data_reac)
            )

            _add_summary_section(
                menu_summary,
                'Production fluxes to track',
                _build_production_flux_summary(data_fluxes)
            )

            menu_summary.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )


            save_simulation_file([data_simul, data_objective, data_genes, data_reac, data_fluxes])
            animation_text_save('Running')
            if sys.platform == 'emscripten':
                self.results = run_simul_remote(BACKEND_URL)
            else:
                self.results = run_simul()

            exchange_flux_data = None
            try:
                exchange_flux_data = self.results[3] if len(self.results) > 3 else None
            except Exception:
                exchange_flux_data = None

            compare_runs = capture_compare_run_snapshot(self.results)

            mission01_data = None
            if '01' in self.player.missions_activated and '01' not in self.player.missions_completed:
                mission01_data = run_mission01_comparison_check(compare_runs)

            mission02_data = None
            if '02' in self.player.missions_activated and '02' not in self.player.missions_completed:
                mission02_data = run_mission02_source_trial_check(self.results)

            mission03_data = None
            if '03' in self.player.missions_activated and '03' not in self.player.missions_completed:
                mission03_data = run_mission03_gene_trial_check(self.results)

            mission04_data = None
            if '04' in self.player.missions_activated and '04' not in self.player.missions_completed:
                mission04_data = run_mission04_production_trial_check(self.results)

            mission21_data = None
            if '21' in self.player.missions_activated and '21' not in self.player.missions_completed:
                mission21_data = run_mission21_comparison_check(compare_runs)

            mission22_data = None
            if '22' in self.player.missions_activated and '22' not in self.player.missions_completed:
                mission22_data = run_mission22_comparison_check(compare_runs)

            mission23_data = None
            if '23' in self.player.missions_activated and '23' not in self.player.missions_completed:
                mission23_data = run_mission23_comparison_check(compare_runs)

            mission24_data = None
            if '24' in self.player.missions_activated and '24' not in self.player.missions_completed:
                mission24_data = run_mission24_comparison_check(compare_runs)

            mission25_data = None
            if '25' in self.player.missions_activated and '25' not in self.player.missions_completed:
                mission25_data = run_mission25_comparison_check(compare_runs)


            bound_sweep_data = None
            mission26_data = None
            mission27_data = None
            mission28_data = None
            luna_sweep_active = (
                ('26' in self.player.missions_activated and '26' not in self.player.missions_completed)
                or ('27' in self.player.missions_activated and '27' not in self.player.missions_completed)
                or ('28' in self.player.missions_activated and '28' not in self.player.missions_completed)
            )
            if luna_sweep_active:
                if sys.platform == 'emscripten':
                    bound_sweep_data = {
                        'error': 'Bound Sweep is not available in this web build yet.'
                    }
                else:
                    bound_sweep_data = run_bound_sweep(menu_bound_sweep.get_input_data())

                if '26' in self.player.missions_activated and '26' not in self.player.missions_completed:
                    mission26_data = run_mission26_bound_sweep_check(bound_sweep_data)
                if '27' in self.player.missions_activated and '27' not in self.player.missions_completed:
                    mission27_data = run_mission27_bound_sweep_check(bound_sweep_data)
                if '28' in self.player.missions_activated and '28' not in self.player.missions_completed:
                    mission28_data = run_mission28_bound_sweep_check(bound_sweep_data)

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
            if '07' in self.player.missions_activated and '07' not in self.player.missions_completed:
                mission07_data = run_mission07_objective_check(self.results)

            mission08_data = None
            if '08' in self.player.missions_activated and '08' not in self.player.missions_completed:
                mission08_data = run_mission08_constraint_check(self.results)

            mission09_data = None
            if '09' in self.player.missions_activated and '09' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission09_data = run_mission09_design_check_remote(BACKEND_URL, self.results)
                else:
                    mission09_data = run_mission09_design_check(self.results)

            mission10_data = None
            if '10' in self.player.missions_activated and '10' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission10_data = run_mission10_robust_design_check_remote(BACKEND_URL, self.results)
                else:
                    mission10_data = run_mission10_robust_design_check(self.results)

            mission11_data = None
            if '11' in self.player.missions_activated and '11' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission11_data = run_mission11_flux_fingerprint_check_remote(BACKEND_URL, self.results)
                else:
                    mission11_data = run_mission11_flux_fingerprint_check(self.results)

            mission12_data = None
            if '12' in self.player.missions_activated and '12' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission12_data = run_mission12_byproduct_check_remote(BACKEND_URL, self.results)
                else:
                    mission12_data = run_mission12_byproduct_check(self.results)

            mission13_data = None
            if '13' in self.player.missions_activated and '13' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission13_data = run_mission13_method_check_remote(BACKEND_URL, self.results)
                else:
                    mission13_data = run_mission13_method_check(self.results)

            mission14_data = None
            if '14' in self.player.missions_activated and '14' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission14_data = run_mission14_reduction_check_remote(BACKEND_URL, self.results)
                else:
                    mission14_data = run_mission14_reduction_check(self.results)

            mission15_data = None
            if '15' in self.player.missions_activated and '15' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission15_data = run_mission15_diagnostic_report_check_remote(BACKEND_URL, self.results)
                else:
                    mission15_data = run_mission15_diagnostic_report_check(self.results)

            mission16_data = None
            if '16' in self.player.missions_activated and '16' not in self.player.missions_completed:
                mission16_data = run_mission16_medium_report_check(self.results)

            mission17_data = None
            if '17' in self.player.missions_activated and '17' not in self.player.missions_completed:
                mission17_data = run_mission17_essential_medium_check(self.results)

            mission18_data = None
            if '18' in self.player.missions_activated and '18' not in self.player.missions_completed:
                mission18_data = run_mission18_export_bottleneck_check(self.results)

            mission19_data = None
            if '19' in self.player.missions_activated and '19' not in self.player.missions_completed:
                mission19_data = run_mission19_perturbation_check(self.results)

            mission20_data = None
            if '20' in self.player.missions_activated and '20' not in self.player.missions_completed:
                mission20_data = run_mission20_robustness_report_check(self.results)

            mission05_data = None
            if '05' in self.player.missions_activated and '05' not in self.player.missions_completed:
                mission05_data = run_mission05_production_trial_check(self.results)

            challenge_data = None
            if '06' in self.player.missions_activated and '06' not in self.player.missions_completed:
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
            menu_simul.add.label(result_display_text, label_id='results')
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
                    label_id='mission27_bound_sweep_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission28_data is not None:
                menu_simul.add.label(
                    _build_mission28_text(mission28_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission28_bound_sweep_check'
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
                and mission19_data.get('method_correct')
                and mission19_data.get('growth_ok')
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


        menu.add.label('TIP: See Book "How to Simulate"', font_size = 20)
        menu.add.vertical_margin(20)
        menu.add.label('Change options: ', font_size = 40)
        menu.add.vertical_margin(20)

        menu.add.dropselect(title='Simulation Method ',
                            items=[('FBA', 'fba'),
                                   ('pFBA', 'pfba'),
                                #    ('MOMA', 'moma'),
                                   ('lMOMA', 'lmoma'),
                                   ('ROOM','room')],
                                   default=0,
                                   selection_box_height=5, dropselect_id='method', background_color="white", font_color=(20,0,150))
        menu.add.button('Objective', menu_objective, font_color = (20,0,150), background_color="white")
        menu.add.button('Production Flux', menu_production_flux, font_color = (20,0,150), background_color="white")
        menu.add.button('Genes', menu_genes, font_color = (20,0,150), background_color="white")
        menu.add.button('Environmental Conditions', menu_reactions, font_color = (20,0,150), background_color="white")
        menu.add.button('Bound Sweep Setup', menu_bound_sweep, font_color = (20,0,150), background_color="white")
        # menu.add.button('Environmental Conditions', menu_reactions_backup, font_color = (20,0,150), background_color="white")
        menu.add.vertical_margin(50)  # Adds margin
        # menu.add.button('Restore Data', restore_data, background_color=(100,0,0))
        # menu.add.vertical_margin(20)  # Adds margin

        menu.add.button('Run Simulation', action=data_fun, font_color = 'white', background_color=(20,100,100))
        menu.add.vertical_margin(20)  # Adds margin
        # last_results = menu.add.button('Results Log', action=menu_results, font_color = 'black', background_color="grey")
        # menu.add.vertical_margin(50)  # Adds margin

        def check_escape():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] and menu.is_enabled():
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

