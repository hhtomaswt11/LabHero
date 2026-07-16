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

            lower_bound_value = -1000 if lower_bound_open else 0
            upper_bound_value = 1000 if upper_bound_open else 0

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


def _build_simulation_results_text(results):
    try:
        objective_name = results[0]
        objective_result = results[1]
    except Exception:
        return str(results)

    text = (
        'Objective flux:\n'
        f'{objective_name}: {objective_result}'
    )

    production_text = ''
    try:
        production_text = _build_production_fluxes_text(results[2])
    except Exception:
        production_text = ''

    if production_text:
        text += '\n\n' + production_text

    return text





def _build_mission07_text(objective_data):
    if not objective_data:
        return ''

    if objective_data.get('error') and objective_data.get('objective_result') in (None, 'None'):
        return f"Mission 07 Objective Check\nError: {objective_data.get('error')}"

    target_product = objective_data.get('target_product')
    selected_objective = objective_data.get('selected_objective')
    objective_result = objective_data.get('objective_result')

    objective_status = (
        f'The selected objective is targeting {target_product} production.'
        if objective_data.get('objective_correct')
        else f'The selected objective is not targeting {target_product} production yet.'
    )
    environment_status = (
        'Environmental conditions unchanged.'
        if not objective_data.get('environment_changed')
        else 'Environmental conditions changed. This first objective mission should keep the environment unchanged.'
    )
    knockout_status = (
        'No gene knockouts.'
        if not objective_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This first objective mission should keep all genes active.'
    )
    final_status = (
        'Objective test completed. Return to Dr. Nova and deliver the results.'
        if objective_data.get('ready_to_deliver')
        else 'Not ready yet. Keep testing objectives while leaving genes and environment unchanged.'
    )

    matched_objective = ''
    if objective_data.get('objective_correct'):
        matched_objective = f"\nMatched objective: {objective_data.get('target_objective')}"

    return (
        'Mission 07 Objective Check\n\n'
        f"Target product: {target_product}\n"
        f"Selected objective: {selected_objective}\n"
        f"Objective flux: {objective_result}"
        f"{matched_objective}\n\n"
        f"{objective_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n\n"
        f"{final_status}"
    )


def _build_mission08_text(objective_data):
    if not objective_data:
        return ''

    if objective_data.get('error') and objective_data.get('objective_result') in (None, 'None'):
        return f"Mission 08 Constraint Check\nError: {objective_data.get('error')}"

    objective_status = (
        'The objective is targeting the requested product.'
        if objective_data.get('objective_correct')
        else 'The selected objective is not targeting the requested product yet.'
    )
    oxygen_status = (
        'A fermentation-compatible oxygen constraint was detected.'
        if objective_data.get('oxygen_lower_bound_closed')
        else 'The environment is still aerobic. Think about oxygen uptake.'
    )
    environment_status = (
        'No unnecessary environmental changes.'
        if not objective_data.get('unexpected_environment_changes')
        else 'Too many environmental changes. Keep the constraint simple.'
    )
    knockout_status = (
        'No gene knockouts.'
        if not objective_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This mission does not need knockouts.'
    )
    final_status = (
        'Constrained production setup found. Return to Dr. Nova and deliver the results.'
        if objective_data.get('ready_to_deliver')
        else 'Not ready yet. Use the objective and environment menus to keep testing.'
    )

    return (
        'Mission 08 Constraint Check\n\n'
        f"Target product: {objective_data.get('target_product')}\n"
        f"Selected objective: {objective_data.get('selected_objective')}\n"
        f"Objective flux: {objective_data.get('objective_result')}\n\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n\n"
        f"{final_status}"
    )


def _build_mission09_text(design_data):
    if not design_data:
        return ''

    if design_data.get('error') and design_data.get('objective_result') in (None, 'None'):
        return f"Mission 09 Design Check\nError: {design_data.get('error')}"

    objective_status = (
        'Objective: product target found.'
        if design_data.get('objective_correct')
        else 'Objective: not targeting the requested product yet.'
    )
    oxygen_status = (
        'Environment: fermentation-compatible oxygen constraint detected.'
        if design_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Think about uptake of oxygen.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not design_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )

    knocked_out_genes = design_data.get('knocked_out_genes') or []
    if not knocked_out_genes:
        knockout_status = 'Knockout: none selected yet. Test exactly one candidate gene.'
    elif len(knocked_out_genes) > 1:
        knockout_status = 'Knockout: too many genes disabled. Use exactly one candidate.'
    elif design_data.get('target_gene_found'):
        knockout_status = 'Knockout: single productive candidate found.'
    else:
        knockout_status = 'Knockout: single candidate tested, but production is not improved enough yet.'

    production_change = float(design_data.get('production_change', 0.0))
    production_prefix = '+' if production_change > 0 else ''
    production_status = (
        'Production: improvement target reached.'
        if design_data.get('production_improved')
        else f"Production: improvement is still below {float(design_data.get('minimum_production_change', 0.0)):.0f}."
    )
    growth_status = (
        'Growth: viable.'
        if design_data.get('growth_ok')
        else f"Growth: too low. Keep it above {float(design_data.get('minimum_growth', 0.0)):.1f}."
    )
    final_status = (
        'Integrated design ready. Return to Dr. Nova and deliver the results.'
        if design_data.get('ready_to_deliver')
        else 'Not ready yet. Keep iterating with objective, environment and one knockout.'
    )

    return (
        'Mission 09 Design Check\n\n'
        f"Target product: {design_data.get('target_product')}\n"
        f"Selected objective: {design_data.get('selected_objective')}\n"
        f"Objective flux: {design_data.get('objective_result')}\n\n"
        f"Baseline production: {float(design_data.get('baseline_production', 0.0)):.3f}\n"
        f"Current production: {float(design_data.get('current_production', 0.0)):.3f}\n"
        f"Production change: {production_prefix}{production_change:.3f}\n"
        f"Current growth: {float(design_data.get('current_growth', 0.0)):.3f}\n\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{production_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )



def _build_mission10_text(design_data):
    if not design_data:
        return ''

    if design_data.get('error') and design_data.get('objective_result') in (None, 'None'):
        return f"Mission 10 Robust Design Check\nError: {design_data.get('error')}"

    objective_status = (
        'Objective: product target found.'
        if design_data.get('objective_correct')
        else 'Objective: not targeting the requested product yet.'
    )
    oxygen_status = (
        'Environment: fermentation-compatible oxygen constraint detected.'
        if design_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Think about oxygen uptake.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not design_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )

    knocked_out_genes = design_data.get('knocked_out_genes') or []
    if not knocked_out_genes:
        knockout_status = 'Knockout pair: none selected yet. Test two candidate genes.'
    elif not design_data.get('exactly_two_knockouts'):
        knockout_status = f"Knockout pair: {len(knocked_out_genes)} selected. Use exactly two candidates."
    elif design_data.get('target_pair_found'):
        knockout_status = 'Knockout pair: robust two-gene design found.'
    elif not design_data.get('only_candidate_knockouts'):
        knockout_status = 'Knockout pair: use only genes from the candidate list.'
    else:
        knockout_status = 'Knockout pair: two candidates tested, but this pair is not robust enough.'

    selected_fluxes = design_data.get('selected_fluxes') or []
    required_fluxes = design_data.get('required_tracked_fluxes') or []
    tracking_status = (
        'Evidence: target and competing product fluxes are being tracked.'
        if design_data.get('tracking_ready')
        else 'Evidence: incomplete. Use Production Flux to track the target and a competing fermentation product.'
    )

    production_change = float(design_data.get('production_change', 0.0))
    production_prefix = '+' if production_change > 0 else ''
    production_status = (
        'Production: improvement target reached.'
        if design_data.get('production_improved')
        else f"Production: improvement is still below {float(design_data.get('minimum_production_change', 0.0)):.0f}."
    )
    growth_status = (
        'Growth: viable.'
        if design_data.get('growth_ok')
        else f"Growth: too low. Keep it above {float(design_data.get('minimum_growth', 0.0)):.1f}."
    )
    final_status = (
        'Robust design ready. Return to Dr. Nova and deliver the results.'
        if design_data.get('ready_to_deliver')
        else 'Not ready yet. Keep iterating with objective, environment, tracking and the knockout pair.'
    )

    return (
        'Mission 10 Robust Design Check\n\n'
        f"Target product: {design_data.get('target_product')}\n"
        f"Selected objective: {design_data.get('selected_objective')}\n"
        f"Objective flux: {design_data.get('objective_result')}\n\n"
        f"Baseline production: {float(design_data.get('baseline_production', 0.0)):.3f}\n"
        f"Current production: {float(design_data.get('current_production', 0.0)):.3f}\n"
        f"Production change: {production_prefix}{production_change:.3f}\n"
        f"Current growth: {float(design_data.get('current_growth', 0.0)):.3f}\n\n"
        f"Tracked fluxes: {', '.join(selected_fluxes) if selected_fluxes else 'none'}\n"
        f"Required evidence count: {len(required_fluxes)} product fluxes\n\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{tracking_status}\n"
        f"{knockout_status}\n"
        f"{production_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )



def _build_mission11_text(fingerprint_data):
    if not fingerprint_data:
        return ''

    if fingerprint_data.get('error') and fingerprint_data.get('objective_result') in (None, 'None'):
        return f"Mission 11 Flux Fingerprint Check\nError: {fingerprint_data.get('error')}"

    method_status = (
        'Method: standard FBA baseline.'
        if fingerprint_data.get('method_correct')
        else 'Method: use FBA for this first diagnostic baseline.'
    )
    objective_status = (
        'Objective: biomass objective kept as the growth baseline.'
        if fingerprint_data.get('objective_correct')
        else 'Objective: keep the biomass objective for this diagnostic profile.'
    )
    oxygen_status = (
        'Environment: respiration-limited constraint detected.'
        if fingerprint_data.get('oxygen_lower_bound_closed')
        else 'Environment: respiration is not limited yet. Think about oxygen availability.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not fingerprint_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not fingerprint_data.get('knocked_out_genes')
        else 'Gene knockouts detected. This diagnostic mission should keep the strain unchanged.'
    )

    selected_fluxes = fingerprint_data.get('selected_fluxes') or []
    missing_fluxes = fingerprint_data.get('missing_fluxes') or []
    positive_fluxes = fingerprint_data.get('positive_fluxes') or []
    flux_values = fingerprint_data.get('tracked_flux_values') or {}

    tracking_status = (
        'Production Flux: full fingerprint panel selected.'
        if fingerprint_data.get('tracking_ready')
        else 'Production Flux: incomplete panel. Select all requested fingerprint products.'
    )
    positive_status = (
        'Fingerprint: informative secretion profile detected.'
        if fingerprint_data.get('positive_products_ready')
        else f"Fingerprint: fewer than {fingerprint_data.get('minimum_positive_products')} products show secretion."
    )
    growth_status = (
        'Growth: viable.'
        if fingerprint_data.get('growth_ok')
        else f"Growth: too low. Keep it above {float(fingerprint_data.get('minimum_growth', 0.0)):.1f}."
    )
    final_status = (
        'Flux fingerprint ready. Return to Dr. Almeida and deliver the results.'
        if fingerprint_data.get('ready_to_deliver')
        else 'Not ready yet. Keep refining the setup and production-flux evidence.'
    )

    flux_lines = []
    for reaction_id in selected_fluxes:
        value = flux_values.get(reaction_id)
        if value is None:
            flux_lines.append(f'- {reaction_id}: not measured')
        else:
            flux_lines.append(f'- {reaction_id}: {float(value):.3f}')
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    missing_text = ', '.join(missing_fluxes) if missing_fluxes else 'none'
    positive_text = ', '.join(positive_fluxes) if positive_fluxes else 'none'
    dominant_product = fingerprint_data.get('dominant_product') or 'not available'

    return (
        'Mission 11 Flux Fingerprint Check\n\n'
        f"Context: {fingerprint_data.get('target_context')}\n"
        f"Method: {fingerprint_data.get('method')}\n"
        f"Selected objective: {fingerprint_data.get('selected_objective')}\n"
        f"Growth/objective flux: {fingerprint_data.get('objective_result')}\n\n"
        f"Tracked fluxes:\n{flux_text}\n\n"
        f"Missing fingerprint fluxes: {missing_text}\n"
        f"Products with positive secretion: {positive_text}\n"
        f"Dominant tracked product: {dominant_product}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{tracking_status}\n"
        f"{positive_status}\n"
        f"{growth_status}\n\n"
        f"{final_status}"
    )


def _build_mission12_text(byproduct_data):
    if not byproduct_data:
        return ''

    if byproduct_data.get('error') and byproduct_data.get('objective_result') in (None, 'None'):
        return f"Mission 12 Byproduct Check\nError: {byproduct_data.get('error')}"

    method_status = (
        'Method: standard FBA comparison.'
        if byproduct_data.get('method_correct')
        else 'Method: use FBA for this comparison.'
    )
    objective_status = (
        'Objective: target product is being prioritised.'
        if byproduct_data.get('objective_correct')
        else 'Objective: not prioritising the requested product yet.'
    )
    oxygen_status = (
        'Environment: respiration-limited constraint detected.'
        if byproduct_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Think about product formation under limited respiration.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not byproduct_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not byproduct_data.get('knocked_out_genes')
        else 'Gene knockouts detected. Keep the strain unchanged for this diagnostic comparison.'
    )

    target_flux_status = (
        'Evidence: target product flux is being tracked.'
        if byproduct_data.get('target_flux_tracked')
        else 'Evidence: track the target product in Production Flux.'
    )
    competing_status = (
        'Evidence: enough competing byproducts are being tracked.'
        if byproduct_data.get('competing_fluxes_ready')
        else f"Evidence: track at least {byproduct_data.get('minimum_competing_fluxes')} competing byproducts."
    )
    target_production_status = (
        'Target flux: positive production detected.'
        if byproduct_data.get('target_flux_positive')
        else 'Target flux: not enough target production detected yet.'
    )
    final_status = (
        'Byproduct comparison ready. Return to Dr. Almeida and deliver the results.'
        if byproduct_data.get('ready_to_deliver')
        else 'Not ready yet. Keep comparing objective, environment and production-flux evidence.'
    )

    selected_fluxes = byproduct_data.get('selected_fluxes') or []
    selected_competing = byproduct_data.get('selected_competing_fluxes') or []
    flux_values = byproduct_data.get('tracked_flux_values') or {}

    flux_lines = []
    for reaction_id in selected_fluxes:
        value = flux_values.get(reaction_id)
        if value is None:
            flux_lines.append(f'- {reaction_id}: not measured')
        else:
            flux_lines.append(f'- {reaction_id}: {float(value):.3f}')
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    return (
        'Mission 12 Byproduct Check\n\n'
        f"Target product: {byproduct_data.get('target_product')}\n"
        f"Selected objective: {byproduct_data.get('selected_objective')}\n"
        f"Objective flux: {byproduct_data.get('objective_result')}\n\n"
        f"Tracked fluxes:\n{flux_text}\n\n"
        f"Selected competing byproducts: {', '.join(selected_competing) if selected_competing else 'none'}\n"
        f"Target product flux: {float(byproduct_data.get('target_flux', 0.0)):.3f}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{target_flux_status}\n"
        f"{competing_status}\n"
        f"{target_production_status}\n\n"
        f"{final_status}"
    )


def _build_mission13_text(method_data):
    if not method_data:
        return ''

    if method_data.get('error') and method_data.get('objective_result') in (None, 'None'):
        return f"Mission 13 Method Check\nError: {method_data.get('error')}"

    if method_data.get('method_correct'):
        method_status = 'Method: pFBA selected for parsimonious flux analysis.'
    elif method_data.get('baseline_method_selected'):
        method_status = 'Method: this is the FBA baseline. Switch to pFBA for this mission.'
    else:
        method_status = 'Method: choose pFBA for the method-comparison step.'

    objective_status = (
        'Objective: target product is being prioritised.'
        if method_data.get('objective_correct')
        else 'Objective: not prioritising the requested product yet.'
    )
    oxygen_status = (
        'Environment: respiration-limited constraint detected.'
        if method_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Keep the comparison under the same product-forming constraint.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not method_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )
    knockout_status = (
        'Gene knockouts: none.'
        if not method_data.get('knocked_out_genes')
        else 'Gene knockouts detected. Keep the strain unchanged for this method comparison.'
    )
    target_flux_status = (
        'Evidence: target product flux is being tracked.'
        if method_data.get('target_flux_tracked')
        else 'Evidence: track the target product in Production Flux.'
    )
    competing_status = (
        'Evidence: enough competing byproducts are being tracked.'
        if method_data.get('competing_fluxes_ready')
        else f"Evidence: track at least {method_data.get('minimum_competing_fluxes')} competing byproducts."
    )
    target_production_status = (
        'Target flux: positive production detected.'
        if method_data.get('target_flux_positive')
        else 'Target flux: not enough target production detected yet.'
    )
    baseline_status = (
        f"Previous FBA baseline loaded: {float(method_data.get('previous_fba_target_flux', 0.0)):.3f}"
        if method_data.get('baseline_available') and method_data.get('previous_fba_target_flux') is not None
        else 'Previous FBA baseline: not loaded. Use the current pFBA evidence.'
    )

    selected_fluxes = method_data.get('selected_fluxes') or []
    selected_competing = method_data.get('selected_competing_fluxes') or []
    flux_values = method_data.get('tracked_flux_values') or {}

    flux_lines = []
    for reaction_id in selected_fluxes:
        value = flux_values.get(reaction_id)
        if value is None:
            flux_lines.append(f'- {reaction_id}: not measured')
        else:
            flux_lines.append(f'- {reaction_id}: {float(value):.3f}')
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    difference = method_data.get('target_flux_difference_from_fba')
    difference_text = 'not available'
    if difference is not None:
        prefix = '+' if float(difference) > 0 else ''
        difference_text = f'{prefix}{float(difference):.3f}'

    final_status = (
        'pFBA method comparison ready. Return to Dr. Almeida and deliver the results.'
        if method_data.get('ready_to_deliver')
        else 'Not ready yet. Keep comparing method, objective, environment and flux evidence.'
    )

    return (
        'Mission 13 Method Check\n\n'
        f"Target product: {method_data.get('target_product')}\n"
        f"Selected method: {method_data.get('method')}\n"
        f"Selected objective: {method_data.get('selected_objective')}\n"
        f"Objective flux: {method_data.get('objective_result')}\n\n"
        f"Tracked fluxes:\n{flux_text}\n\n"
        f"Selected competing byproducts: {', '.join(selected_competing) if selected_competing else 'none'}\n"
        f"pFBA target flux: {float(method_data.get('target_flux', 0.0)):.3f}\n"
        f"{baseline_status}\n"
        f"Difference from previous FBA target flux: {difference_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_status}\n"
        f"{target_flux_status}\n"
        f"{competing_status}\n"
        f"{target_production_status}\n\n"
        f"{final_status}"
    )



def _build_mission14_text(reduction_data):
    if not reduction_data:
        return ''

    if reduction_data.get('error') and reduction_data.get('objective_result') in (None, 'None'):
        return f"Mission 14 Reduction Check\nError: {reduction_data.get('error')}"

    method_status = (
        'Method: pFBA selected for reduction analysis.'
        if reduction_data.get('method_correct')
        else 'Method: use pFBA for this reduction analysis.'
    )
    objective_status = (
        'Objective: target product is being prioritised.'
        if reduction_data.get('objective_correct')
        else 'Objective: not prioritising the requested target product yet.'
    )
    oxygen_status = (
        'Environment: respiration-limited constraint detected.'
        if reduction_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Keep the same product-forming constraint.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not reduction_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )
    knockout_count_status = (
        'Knockouts: exactly one candidate gene is disabled.'
        if reduction_data.get('exact_one_knockout')
        else 'Knockouts: use exactly one candidate gene.'
    )
    knockout_effect_status = (
        'Knockout effect: unwanted byproduct route reduced.'
        if reduction_data.get('target_gene_found')
        else 'Knockout effect: keep testing candidates to reduce the unwanted byproduct.'
    )
    evidence_status = (
        'Evidence: target and unwanted product fluxes are being tracked.'
        if reduction_data.get('required_fluxes_ready')
        else 'Evidence: track both the target and unwanted product fluxes.'
    )
    target_flux_status = (
        'Target flux: positive target production detected.'
        if reduction_data.get('target_flux_positive')
        else 'Target flux: target product is not high enough yet.'
    )
    unwanted_flux_status = (
        'Byproduct flux: unwanted product is sufficiently reduced.'
        if reduction_data.get('unwanted_flux_reduced')
        else 'Byproduct flux: unwanted product is still too high.'
    )

    selected_fluxes = reduction_data.get('selected_fluxes') or []
    flux_values = reduction_data.get('tracked_flux_values') or {}
    flux_lines = []
    for reaction_id in selected_fluxes:
        value = flux_values.get(reaction_id)
        if value is None:
            flux_lines.append(f'- {reaction_id}: not measured')
        else:
            flux_lines.append(f'- {reaction_id}: {float(value):.3f}')
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    previous_unwanted = reduction_data.get('previous_unwanted_flux')
    previous_text = 'not loaded'
    if previous_unwanted is not None:
        previous_text = f"{float(previous_unwanted):.3f}"

    change = reduction_data.get('unwanted_flux_change_from_previous')
    change_text = 'not available'
    if change is not None:
        prefix = '+' if float(change) > 0 else ''
        change_text = f'{prefix}{float(change):.3f}'

    knocked_out = reduction_data.get('knocked_out_genes') or []
    knocked_out_text = ', '.join(knocked_out) if knocked_out else 'none'

    final_status = (
        'Reduction design ready. Return to Dr. Almeida and deliver the results.'
        if reduction_data.get('ready_to_deliver')
        else 'Not ready yet. Keep testing the knockout, method, environment and flux evidence.'
    )

    return (
        'Mission 14 Reduction Check\n\n'
        f"Target product: {reduction_data.get('target_product')}\n"
        f"Unwanted byproduct: {reduction_data.get('unwanted_product')}\n"
        f"Selected method: {reduction_data.get('method')}\n"
        f"Selected objective: {reduction_data.get('selected_objective')}\n"
        f"Objective flux: {reduction_data.get('objective_result')}\n"
        f"Knockout selected: {knocked_out_text}\n\n"
        f"Tracked fluxes:\n{flux_text}\n\n"
        f"Target flux: {float(reduction_data.get('target_flux', 0.0)):.3f}\n"
        f"Current unwanted flux: {float(reduction_data.get('current_unwanted_flux', 0.0)):.3f}\n"
        f"Previous unwanted flux: {previous_text}\n"
        f"Change from previous diagnostic run: {change_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_count_status}\n"
        f"{knockout_effect_status}\n"
        f"{evidence_status}\n"
        f"{target_flux_status}\n"
        f"{unwanted_flux_status}\n\n"
        f"{final_status}"
    )



def _build_mission15_text(report_data):
    if not report_data:
        return ''

    if report_data.get('error') and report_data.get('objective_result') in (None, 'None'):
        return f"Mission 15 Diagnostic Report\nError: {report_data.get('error')}"

    method_status = (
        'Method: pFBA selected for the final diagnostic report.'
        if report_data.get('method_correct')
        else 'Method: use pFBA for this final report.'
    )
    objective_status = (
        'Objective: target product is being prioritised.'
        if report_data.get('objective_correct')
        else 'Objective: not prioritising the requested target product yet.'
    )
    oxygen_status = (
        'Environment: respiration-limited constraint detected.'
        if report_data.get('oxygen_lower_bound_closed')
        else 'Environment: still aerobic. Keep the product-forming constraint.'
    )
    environment_status = (
        'Extra constraints: none.'
        if not report_data.get('unexpected_environment_changes')
        else 'Extra constraints: too many environmental changes. Keep only the key constraint.'
    )
    knockout_count_status = (
        'Knockouts: exactly one candidate gene is disabled.'
        if report_data.get('exact_one_knockout')
        else 'Knockouts: use exactly one candidate gene.'
    )
    knockout_effect_status = (
        'Knockout effect: byproduct profile is controlled.'
        if report_data.get('target_gene_found')
        else 'Knockout effect: keep testing candidates to control the byproduct profile.'
    )
    evidence_status = (
        'Evidence: full production-flux panel is being tracked.'
        if report_data.get('required_fluxes_ready')
        else 'Evidence: track the full production-flux panel.'
    )
    target_flux_status = (
        'Target flux: positive target production detected.'
        if report_data.get('target_flux_positive')
        else 'Target flux: target product is not high enough yet.'
    )
    unwanted_flux_status = (
        'Byproduct control: unwanted product remains low.'
        if report_data.get('unwanted_flux_reduced')
        else 'Byproduct control: unwanted product is still too high.'
    )
    dominance_status = (
        'Profile verdict: target product dominates the tracked byproduct profile.'
        if report_data.get('target_dominates_byproducts')
        else 'Profile verdict: target product does not dominate the tracked byproducts yet.'
    )

    selected_fluxes = report_data.get('selected_fluxes') or []
    flux_values = report_data.get('tracked_flux_values') or {}
    flux_lines = []
    for reaction_id in selected_fluxes:
        value = flux_values.get(reaction_id)
        if value is None:
            flux_lines.append(f'- {reaction_id}: not measured')
        else:
            flux_lines.append(f'- {reaction_id}: {float(value):.3f}')
    flux_text = '\n'.join(flux_lines) if flux_lines else 'none'

    previous_target = report_data.get('previous_target_flux')
    previous_target_text = 'not loaded'
    if previous_target is not None:
        previous_target_text = f"{float(previous_target):.3f}"

    previous_unwanted = report_data.get('previous_unwanted_flux')
    previous_unwanted_text = 'not loaded'
    if previous_unwanted is not None:
        previous_unwanted_text = f"{float(previous_unwanted):.3f}"

    target_change = report_data.get('target_flux_change_from_previous')
    target_change_text = 'not available'
    if target_change is not None:
        prefix = '+' if float(target_change) > 0 else ''
        target_change_text = f'{prefix}{float(target_change):.3f}'

    unwanted_change = report_data.get('unwanted_flux_change_from_previous')
    unwanted_change_text = 'not available'
    if unwanted_change is not None:
        prefix = '+' if float(unwanted_change) > 0 else ''
        unwanted_change_text = f'{prefix}{float(unwanted_change):.3f}'

    knocked_out = report_data.get('knocked_out_genes') or []
    knocked_out_text = ', '.join(knocked_out) if knocked_out else 'none'

    final_status = (
        'Final diagnostic report ready. Return to Dr. Almeida and deliver the results.'
        if report_data.get('ready_to_deliver')
        else 'Not ready yet. Refine method, environment, knockout choice and flux evidence.'
    )

    return (
        'Mission 15 Diagnostic Report\n\n'
        f"Target product: {report_data.get('target_product')}\n"
        f"Selected method: {report_data.get('method')}\n"
        f"Selected objective: {report_data.get('selected_objective')}\n"
        f"Objective flux: {report_data.get('objective_result')}\n"
        f"Knockout selected: {knocked_out_text}\n\n"
        f"Tracked fluxes:\n{flux_text}\n\n"
        f"Target flux: {float(report_data.get('target_flux', 0.0)):.3f}\n"
        f"Current unwanted flux: {float(report_data.get('current_unwanted_flux', 0.0)):.3f}\n"
        f"Highest tracked byproduct flux: {float(report_data.get('highest_byproduct_flux', 0.0)):.3f}\n"
        f"Previous target flux: {previous_target_text}\n"
        f"Target change from previous design: {target_change_text}\n"
        f"Previous unwanted flux: {previous_unwanted_text}\n"
        f"Unwanted change from previous design: {unwanted_change_text}\n\n"
        f"{method_status}\n"
        f"{objective_status}\n"
        f"{oxygen_status}\n"
        f"{environment_status}\n"
        f"{knockout_count_status}\n"
        f"{knockout_effect_status}\n"
        f"{evidence_status}\n"
        f"{target_flux_status}\n"
        f"{unwanted_flux_status}\n"
        f"{dominance_status}\n\n"
        f"{final_status}"
    )


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
    if not production_data:
        return ''

    if production_data.get('error'):
        return f"Mission 04 Production Check\nError: {production_data.get('error')}"

    environment_note = (
        'Environmental conditions were changed. For Mission 04, keep them unchanged.'
        if production_data.get('environment_changed')
        else 'Environmental conditions unchanged.'
    )
    status = (
        'Production improved. This knockout looks promising.'
        if production_data.get('improved')
        else 'No improvement yet. Try a different candidate knockout.'
    )
    change = float(production_data.get('production_change', 0))
    change_prefix = '+' if change > 0 else ''

    return (
        'Mission 04 Production Check\n\n'
        f"Target product: {production_data.get('product_name')} ({production_data.get('production_objective')})\n"
        f"Baseline {production_data.get('product_name')} flux: {float(production_data.get('baseline_production', 0)):.3f}\n"
        f"Current {production_data.get('product_name')} flux: {float(production_data.get('current_production', 0)):.3f}\n"
        f"Production change: {change_prefix}{change:.3f}\n"
        f"Current growth: {float(production_data.get('current_growth', 0)):.3f}\n\n"
        f"{environment_note}\n"
        f"{status}"
    )


def _build_mission05_text(production_data):
    if not production_data:
        return ''

    if production_data.get('error'):
        return f"Mission 05 Production Check\nError: {production_data.get('error')}"

    oxygen_note = (
        f"O2 lower bound closed ({production_data.get('oxygen_reaction')}): yes."
        if production_data.get('oxygen_disabled')
        else f"O2 is still available. Close the lower bound of {production_data.get('oxygen_reaction')}."
    )
    status = (
        'Lactate production improved. This combination looks promising.'
        if production_data.get('oxygen_disabled') and production_data.get('improved')
        else 'Not enough yet. Combine anaerobiosis with the right knockout.'
    )
    change = float(production_data.get('production_change', 0))
    change_prefix = '+' if change > 0 else ''

    return (
        'Mission 05 Production Check\n\n'
        f"Target product: {production_data.get('product_name')} ({production_data.get('production_objective')})\n"
        f"Anaerobic baseline flux: {float(production_data.get('baseline_production', 0)):.3f}\n"
        f"Current {production_data.get('product_name')} flux: {float(production_data.get('current_production', 0)):.3f}\n"
        f"Production change: {change_prefix}{change:.3f}\n"
        f"Current growth: {float(production_data.get('current_growth', 0)):.3f}\n\n"
        f"{oxygen_note}\n"
        f"{status}"
    )


def _build_challenge_text(challenge_data):
    if not challenge_data:
        return ''

    if challenge_data.get('error'):
        return f"Mission 06 Challenge\nError: {challenge_data.get('error')}"

    status = 'You win!' if challenge_data.get('win') else 'You need a better balance between growth and ethanol production.'
    return (
        'Mission 06 Challenge\n\n'
        f"Growth ({challenge_data.get('growth_objective')}): {float(challenge_data.get('growth', 0)):.3f}\n"
        f"Ethanol production flux ({challenge_data.get('production_objective')}): {float(challenge_data.get('production', 0)):.3f}\n"
        f"Your score: {float(challenge_data.get('score', 0)):.3f}\n"
        f"Villain score: {float(challenge_data.get('villain_score', 0)):.3f}\n\n"
        f"{status}"
    )

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
        'Carbon source: glucose blocked and pyruvate uptake detected.'
        if report_data.get('glucose_uptake_blocked') and report_data.get('pyruvate_uptake_detected')
        else 'Carbon source: verify glucose removal and pyruvate uptake in the Medium Report.'
    )
    bottleneck_status = (
        'Export stress: acetate export bottleneck detected.'
        if report_data.get('acetate_export_blocked')
        else 'Export stress: acetate export is not constrained enough yet.'
    )
    essential_status = (
        'Essential uptake: required nutrient uptake evidence detected.'
        if report_data.get('essential_uptake_ready')
        else 'Essential uptake: Medium Report is missing required nutrient evidence.'
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
        f"Medium uptake evidence:\n{medium_text}\n"
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
        menu_reactions.add.label("TIP for Mission 02:\nThe lower bound tells the cell if it can reverse the reaction and do it the opposite way (e.g., taking in nutrients).\nThe upper bound tells it how fast or how much of the reaction can happen in the forward direction (e.g., producing metabolites).",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
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
            menu_reactions.add.toggle_switch('Lower Bound',default_lb_bool, onchange=None, state_text=('Closed', 'Open'), state_text_font_size=20, font_size = 24, state_color=('grey','gold'), state_text_font_color=('black', 'black')) #, kwargs=txt, toggleswitch_id=txt)
            menu_reactions.add.toggle_switch('Upper Bound',default_ub_bool, onchange=None, state_text=('Closed', 'Open'), state_text_font_size=20, font_size = 24, state_color=('grey','gold'), state_text_font_color=('black', 'black')) #, kwargs=txt, toggleswitch_id=txt)
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
        menu_genes.add.label("TIP for Mission 03, Mission 04 and Mission 05: \nSome genes are essential for survival. Others can redirect metabolism toward useful products. Try one highlighted gene knockout at a time.",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
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

        genes_03 = ['b1241','b3115','b3736','b2975','b1524','b2278','b2926','b2297','b0728','b3919']
        genes_04 = MISSION04_CANDIDATE_GENES
        genes_05 = MISSION05_CANDIDATE_GENES
        genes_09 = MISSION09_CANDIDATE_GENES
        genes_10 = MISSION10_CANDIDATE_GENES

        for i, gene_id in enumerate(GENES):
            gene_label = GENE_LABELS.get(gene_id, gene_id)

            if gene_id in genes_03 or gene_id in genes_04 or gene_id in genes_05 or gene_id in genes_09 or gene_id in genes_10:
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
                mission11_data = run_mission11_flux_fingerprint_check(self.results)

            mission12_data = None
            if '12' in self.player.missions_activated and '12' not in self.player.missions_completed:
                mission12_data = run_mission12_byproduct_check(self.results)

            mission13_data = None
            if '13' in self.player.missions_activated and '13' not in self.player.missions_completed:
                mission13_data = run_mission13_method_check(self.results)

            mission14_data = None
            if '14' in self.player.missions_activated and '14' not in self.player.missions_completed:
                mission14_data = run_mission14_reduction_check(self.results)

            mission15_data = None
            if '15' in self.player.missions_activated and '15' not in self.player.missions_completed:
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

            mission04_data = None
            if '04' in self.player.missions_activated and '04' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission04_data = run_mission04_production_check_remote(BACKEND_URL)
                else:
                    mission04_data = run_mission04_production_check()

            mission05_data = None
            if '05' in self.player.missions_activated and '05' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission05_data = run_mission05_production_check_remote(BACKEND_URL)
                else:
                    mission05_data = run_mission05_production_check()

            challenge_data = None
            if '06' in self.player.missions_activated and '06' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    challenge_data = run_challenge_score_remote(BACKEND_URL)
                else:
                    challenge_data = run_challenge_score()

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
            if (self.results[1] == 'Status: INFEASIBLE' or self.results[1] == 0.0 or self.results[1] == -0.0) and not mission19_viable_perturbation:
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

