import copy
import json
import sys

from save_load import *
from options_values import *


CHALLENGE_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
CHALLENGE_PRODUCTION_OBJECTIVE = 'EX_etoh_e'

MISSION04_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION04_PRODUCT_NAME = 'ethanol'
MISSION04_PRODUCTION_OBJECTIVE = 'EX_etoh_e'
MISSION04_TARGET_GENE = 'b2297'
MISSION04_TARGET_GENE_NAME = 'pta'
MISSION04_CANDIDATE_GENES = ['b0728', 'b1241', 'b2975', 'b2297', 'b0723']

MISSION05_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION05_PRODUCT_NAME = 'lactate'
MISSION05_PRODUCTION_OBJECTIVE = 'EX_lac__D_e'
MISSION05_TARGET_GENE = 'b1241'
MISSION05_TARGET_GENE_NAME = 'adhE'
MISSION05_CANDIDATE_GENES = ['b0903', 'b2297', 'b0723', 'b3115', 'b0728', 'b1241']
MISSION05_OXYGEN_REACTION = 'EX_o2_e'

MISSION07_DEFAULT_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION07_TARGET_PRODUCT = 'ethanol'
MISSION07_TARGET_OBJECTIVE = 'EX_etoh_e'

MISSION08_DEFAULT_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION08_TARGET_PRODUCT = 'lactate'
MISSION08_TARGET_OBJECTIVE = 'EX_lac__D_e'
MISSION08_OXYGEN_REACTION = 'EX_o2_e'

MISSION09_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION09_TARGET_PRODUCT = 'lactate'
MISSION09_TARGET_OBJECTIVE = 'EX_lac__D_e'
MISSION09_OXYGEN_REACTION = 'EX_o2_e'
MISSION09_TARGET_GENE = 'b1241'
MISSION09_TARGET_GENE_NAME = 'adhE'
MISSION09_MIN_GROWTH = 8.0
MISSION09_MIN_PRODUCTION_CHANGE = 100.0
MISSION09_CANDIDATE_GENES = ['b0903', 'b2297', 'b0723', 'b3115', 'b0728', 'b1241']

MISSION10_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION10_TARGET_PRODUCT = 'lactate'
MISSION10_TARGET_OBJECTIVE = 'EX_lac__D_e'
MISSION10_OXYGEN_REACTION = 'EX_o2_e'
MISSION10_TARGET_GENES = ['b1241', 'b2297']
MISSION10_TARGET_GENE_NAMES = {'b1241': 'adhE', 'b2297': 'pta'}
MISSION10_MIN_GROWTH = 5.0
MISSION10_MIN_PRODUCTION_CHANGE = 50.0
MISSION10_CANDIDATE_GENES = ['b0903', 'b2297', 'b0723', 'b3115', 'b0728', 'b1241']
MISSION10_REQUIRED_TRACKED_FLUXES = ['EX_lac__D_e', 'EX_etoh_e']

MISSION11_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION11_TARGET_CONTEXT = 'respiration-limited growth'
MISSION11_OXYGEN_REACTION = 'EX_o2_e'
MISSION11_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION11_MIN_GROWTH = 5.0
MISSION11_MIN_POSITIVE_PRODUCTS = 2

VILLAIN_SCORE = 14500.0


def _normalise_result(result):
    results_str = str(result)
    try:
        if str(results_str.splitlines()[1]) == 'Status: INFEASIBLE':
            return 'Status: INFEASIBLE'
        return round(float(str(results_str.splitlines()[0])[11:]), 3)
    except Exception:
        return results_str


def _numeric_result(value):
    try:
        return max(float(value), 0.0)
    except Exception:
        return 0.0


def _read_simulation_file():
    data_simul = load_file(get_save_path('simulation_file'))
    method, objective, genes, reactions = data_simul[:4]

    method_name = method['method'][0][0]
    objective_name = objective['objective'][0][0]

    return method_name, objective_name, genes, reactions



def _build_default_reactions_data():
    reactions_data = {}
    for i in range(len(REACTIONS.index)):
        reactions_data[f'reaction_{i}_lb'] = REACTIONS.lb.iloc[i] != 0
        reactions_data[f'reaction_{i}_ub'] = REACTIONS.ub.iloc[i] != 0
    return reactions_data


def _build_active_genes_data():
    return {gene_id: True for gene_id in GENES}



def _read_selected_production_fluxes():
    """Read the production fluxes selected by the player in the simulation UI.

    Older save files only have method/objective/genes/reactions, so this stays
    backwards compatible and simply returns an empty selection in that case.
    """
    try:
        data_simul = load_file(get_save_path('simulation_file'))
    except Exception:
        return []

    if not isinstance(data_simul, (list, tuple)) or len(data_simul) < 5:
        return []

    raw_flux_data = data_simul[4] or {}
    if not isinstance(raw_flux_data, dict):
        return []

    return [
        reaction_id
        for reaction_id in PRODUCTION_FLUX_REACTION_IDS
        if bool(raw_flux_data.get(reaction_id, False))
    ]

def _build_anaerobic_reactions_data():
    reactions_data = _build_default_reactions_data()

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
        reactions_data[f'reaction_{oxygen_index}_lb'] = False
    except ValueError:
        pass

    return reactions_data


def _oxygen_lower_bound_closed(reactions):
    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
    except ValueError:
        return False

    reaction_values = list(reactions.values())
    lb_index = oxygen_index * 2
    if lb_index >= len(reaction_values):
        return False

    return not bool(reaction_values[lb_index])


def _mission08_environment_status(reactions):
    """Return whether Mission 08 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION08_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes



def _mission09_environment_status(reactions):
    """Return whether Mission 09 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION09_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes




def _mission10_environment_status(reactions):
    """Return whether Mission 10 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION10_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes


def _mission11_environment_status(reactions):
    """Return whether Mission 11 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION11_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes


def _environment_has_changes(reactions):
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
            return True

    return False


def _knocked_out_genes(genes):
    return [
        gene_id
        for gene_id, is_active in genes.items()
        if not bool(is_active)
    ]


def _build_envconditions_from_reactions(reactions, reactions_original):
    envconditions = {}

    count = 0
    count_2 = 0
    for i, (k, x) in enumerate(reactions.items()):
        if count >= len(REACTIONS.index):
            break

        if count_2 % 2 == 0:
            envconditions[REACTIONS.index[count]] = (
                reactions_original.lb.iloc[count],
                reactions_original.ub.iloc[count]
            )
            if not x:
                envconditions[REACTIONS.index[count]] = (0, envconditions[REACTIONS.index[count]][1])
            else:
                envconditions[REACTIONS.index[count]] = (-1000, envconditions[REACTIONS.index[count]][1])
            count_2 += 1
        else:
            if not x:
                envconditions[REACTIONS.index[count]] = (envconditions[REACTIONS.index[count]][0], 0)
            else:
                envconditions[REACTIONS.index[count]] = (envconditions[REACTIONS.index[count]][0], 1000)
            count_2 += 1
            count += 1

    return envconditions


def _apply_gene_knockouts(envconditions, genes, genes_data):
    for gene_id, is_active in genes.items():
        if not is_active and gene_id in genes_data.index:
            list_react = genes_data.loc[gene_id, 'reactions']
            for react in list_react:
                envconditions[react] = (0, 0)
    return envconditions


def _build_local_constraints(genes, reactions):
    from mewpy.simulation import get_simulator

    simul = get_simulator(model)
    reactions_original = simul.find_reactions('EX')
    envconditions = _build_envconditions_from_reactions(reactions, reactions_original)
    genes_data = simul.find_genes()
    envconditions = _apply_gene_knockouts(envconditions, genes, genes_data)
    return simul, envconditions


def _simulate_local_objective(method_name, objective_name, genes, reactions):
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    return _normalise_result(result)


def _extract_from_mapping(data, key):
    if data is None:
        return None

    if callable(data):
        try:
            data = data()
        except TypeError:
            pass

    if hasattr(data, 'to_dict'):
        try:
            data = data.to_dict()
        except Exception:
            pass

    if isinstance(data, dict):
        if key in data:
            return data[key]
        # Some objects may use reaction objects as keys. Fall back to string ids.
        for candidate_key, value in data.items():
            if str(candidate_key) == key:
                return value
        return None

    if hasattr(data, 'get'):
        try:
            value = data.get(key)
            if value is not None:
                return value
        except Exception:
            pass

    if hasattr(data, 'loc'):
        try:
            return data.loc[key]
        except Exception:
            pass

    try:
        return data[key]
    except Exception:
        return None


def _extract_flux(result, reaction_id):
    """Read one reaction flux from a MEWpy/Cobra-like simulation result."""
    for attr_name in ('fluxes', 'flux_distribution', 'values', 'data'):
        value = _extract_from_mapping(getattr(result, attr_name, None), reaction_id)
        if value is not None:
            return value

    for method_name in ('to_dataframe', 'to_frame'):
        method = getattr(result, method_name, None)
        if not callable(method):
            continue
        try:
            table = method()
        except Exception:
            continue

        if hasattr(table, 'loc'):
            try:
                row = table.loc[reaction_id]
                for column in ('flux', 'Flux', 'value', 'Value'):
                    try:
                        return row[column]
                    except Exception:
                        pass
                try:
                    return float(row)
                except Exception:
                    pass
            except Exception:
                pass

    return _extract_from_mapping(result, reaction_id)


def _as_float_or_none(value):
    try:
        return float(value)
    except Exception:
        return None



def _build_production_flux_data(selected_ids, flux_getter=None, error=None):
    """Build display-ready production flux data for selected exchange reactions."""
    selected_ids = [
        reaction_id
        for reaction_id in selected_ids
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS
    ]

    data = {
        'selected_ids': selected_ids,
        'items': [],
    }

    if error:
        data['error'] = error
        return data

    if not selected_ids:
        return data

    for reaction_id in selected_ids:
        raw_flux = None
        if callable(flux_getter):
            try:
                raw_flux = flux_getter(reaction_id)
            except Exception:
                raw_flux = None

        raw_value = _as_float_or_none(raw_flux)
        item = {
            'reaction_id': reaction_id,
            'product_name': PRODUCTION_FLUX_NAMES.get(reaction_id, reaction_id),
            'label': PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id),
        }

        if raw_value is None:
            item['error'] = 'Flux not available in this simulation result.'
        else:
            # For exchange reactions, positive flux represents secretion/export.
            # A negative value would mean uptake/consumption, not production.
            item['raw_flux'] = round(raw_value, 6)
            item['production_flux'] = round(max(raw_value, 0.0), 3)

        data['items'].append(item)

    return data


def _simulate_local_objective_with_production_fluxes(method_name, objective_name, genes, reactions, selected_fluxes):
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    objective_result = _normalise_result(result)

    if objective_result == 'Status: INFEASIBLE':
        return objective_result, _build_production_flux_data(
            selected_fluxes,
            error='Simulation infeasible. Production fluxes could not be measured.'
        )

    production_fluxes = _build_production_flux_data(
        selected_fluxes,
        flux_getter=lambda reaction_id: _extract_flux(result, reaction_id)
    )
    return objective_result, production_fluxes


def _build_challenge_data(growth, production_flux, error=None):
    growth_value = _numeric_result(growth)
    production_value = _numeric_result(production_flux)
    score = round(growth_value * production_value, 3)

    challenge_data = {
        'mission_id': '06',
        'check_version': 2,
        'growth_objective': CHALLENGE_GROWTH_OBJECTIVE,
        'production_objective': CHALLENGE_PRODUCTION_OBJECTIVE,
        'growth': round(growth_value, 3),
        'production': round(production_value, 3),
        'score': score,
        'villain_score': VILLAIN_SCORE,
        'win': score > VILLAIN_SCORE,
    }
    if error:
        challenge_data['error'] = error
    save_challenge_score(challenge_data)
    return challenge_data



def _simulate_flux_in_biomass_solution(genes, reactions, production_objective, growth_objective):
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = growth_objective
    result = simul.simulate(method='FBA', constraints=constraints)

    growth = _normalise_result(result)
    if growth == 'Status: INFEASIBLE':
        return 0.0, 0.0, 'Status: INFEASIBLE'

    production_flux = _extract_flux(result, production_objective)
    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return growth, 0.0, f'Could not read {production_objective} flux from the FBA solution.'

    return growth, production_value, None


def _build_mission07_data(selected_objective, objective_result, genes, reactions, error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)
    objective_correct = selected_objective == MISSION07_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0

    mission07_data = {
        'mission_id': '07',
        'check_version': 2,
        'default_objective': MISSION07_DEFAULT_OBJECTIVE,
        'target_product': MISSION07_TARGET_PRODUCT,
        'target_objective': MISSION07_TARGET_OBJECTIVE,
        'selected_objective': selected_objective,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'objective_correct': objective_correct,
        'environment_changed': environment_changed,
        'knocked_out_genes': knocked_out_genes,
        'result_valid': result_valid,
        'ready_to_deliver': (
            objective_correct
            and not environment_changed
            and not knocked_out_genes
            and result_valid
        ),
    }
    if error:
        mission07_data['error'] = error
    save_mission07_objective_check(mission07_data)
    return mission07_data


def run_mission07_objective_check(simulation_results=None):
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        error = 'Run the simulation before delivering Mission 07.'

    return _build_mission07_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        error=error,
    )


def _build_mission08_data(selected_objective, objective_result, genes, reactions, error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    objective_correct = selected_objective == MISSION08_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission08_environment_status(reactions)

    mission08_data = {
        'mission_id': '08',
        'check_version': 2,
        'default_objective': MISSION08_DEFAULT_OBJECTIVE,
        'target_product': MISSION08_TARGET_PRODUCT,
        'target_objective': MISSION08_TARGET_OBJECTIVE,
        'oxygen_reaction': MISSION08_OXYGEN_REACTION,
        'selected_objective': selected_objective,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'objective_correct': objective_correct,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'result_valid': result_valid,
        'ready_to_deliver': (
            objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and result_valid
        ),
    }
    if error:
        mission08_data['error'] = error
    save_mission08_constraint_check(mission08_data)
    return mission08_data


def run_mission08_constraint_check(simulation_results=None):
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        error = 'Run the simulation before delivering Mission 08.'

    return _build_mission08_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        error=error,
    )



def _build_mission09_data(
    selected_objective,
    objective_result,
    genes,
    reactions,
    baseline_growth,
    baseline_flux,
    current_growth,
    current_flux,
    flux_error=None,
    objective_error=None,
):
    knocked_out_genes = _knocked_out_genes(genes)
    objective_correct = selected_objective == MISSION09_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission09_environment_status(reactions)

    baseline_value = _numeric_result(baseline_flux)
    current_value = _numeric_result(current_flux)
    growth_value = _numeric_result(current_growth)
    production_change = round(current_value - baseline_value, 3)

    single_knockout = len(knocked_out_genes) == 1
    target_gene_found = single_knockout and knocked_out_genes[0] == MISSION09_TARGET_GENE
    growth_ok = growth_value >= MISSION09_MIN_GROWTH
    production_improved = production_change >= MISSION09_MIN_PRODUCTION_CHANGE

    mission09_data = {
        'mission_id': '09',
        'check_version': 2,
        'target_product': MISSION09_TARGET_PRODUCT,
        'target_objective': MISSION09_TARGET_OBJECTIVE,
        'selected_objective': selected_objective,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'objective_correct': objective_correct,
        'oxygen_reaction': MISSION09_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'single_knockout': single_knockout,
        'target_gene_found': target_gene_found,
        'target_gene': MISSION09_TARGET_GENE,
        'target_gene_name': MISSION09_TARGET_GENE_NAME,
        'candidate_genes': MISSION09_CANDIDATE_GENES,
        'growth_objective': MISSION09_GROWTH_OBJECTIVE,
        'minimum_growth': MISSION09_MIN_GROWTH,
        'minimum_production_change': MISSION09_MIN_PRODUCTION_CHANGE,
        'baseline_growth': round(_numeric_result(baseline_growth), 3),
        'baseline_production': round(baseline_value, 3),
        'current_growth': round(growth_value, 3),
        'current_production': round(current_value, 3),
        'production_change': production_change,
        'growth_ok': growth_ok,
        'production_improved': production_improved,
        'result_valid': result_valid,
        'ready_to_deliver': (
            objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and target_gene_found
            and growth_ok
            and production_improved
            and result_valid
        ),
    }
    error = objective_error or flux_error
    if error:
        mission09_data['error'] = error
    save_mission09_design_check(mission09_data)
    return mission09_data


def run_mission09_design_check(simulation_results=None):
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 09.'

    baseline_growth, baseline_flux, baseline_error = _simulate_flux_in_biomass_solution(
        _build_active_genes_data(),
        _build_anaerobic_reactions_data(),
        MISSION09_TARGET_OBJECTIVE,
        MISSION09_GROWTH_OBJECTIVE,
    )

    current_growth, current_flux, current_error = _simulate_flux_in_biomass_solution(
        genes,
        reactions,
        MISSION09_TARGET_OBJECTIVE,
        MISSION09_GROWTH_OBJECTIVE,
    )

    return _build_mission09_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        flux_error=baseline_error or current_error,
        objective_error=objective_error,
    )




def _build_mission10_data(
    selected_objective,
    objective_result,
    genes,
    reactions,
    baseline_growth,
    baseline_flux,
    current_growth,
    current_flux,
    flux_error=None,
    objective_error=None,
):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()

    objective_correct = selected_objective == MISSION10_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission10_environment_status(reactions)

    baseline_value = _numeric_result(baseline_flux)
    current_value = _numeric_result(current_flux)
    growth_value = _numeric_result(current_growth)
    production_change = round(current_value - baseline_value, 3)

    exactly_two_knockouts = len(knocked_out_genes) == 2
    only_candidate_knockouts = all(gene_id in MISSION10_CANDIDATE_GENES for gene_id in knocked_out_genes)
    target_pair_found = set(knocked_out_genes) == set(MISSION10_TARGET_GENES)
    tracking_ready = all(reaction_id in selected_fluxes for reaction_id in MISSION10_REQUIRED_TRACKED_FLUXES)
    growth_ok = growth_value >= MISSION10_MIN_GROWTH
    production_improved = production_change >= MISSION10_MIN_PRODUCTION_CHANGE

    mission10_data = {
        'mission_id': '10',
        'check_version': 2,
        'target_product': MISSION10_TARGET_PRODUCT,
        'target_objective': MISSION10_TARGET_OBJECTIVE,
        'selected_objective': selected_objective,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'objective_correct': objective_correct,
        'oxygen_reaction': MISSION10_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'exactly_two_knockouts': exactly_two_knockouts,
        'only_candidate_knockouts': only_candidate_knockouts,
        'target_pair_found': target_pair_found,
        'target_genes': MISSION10_TARGET_GENES,
        'target_gene_names': MISSION10_TARGET_GENE_NAMES,
        'candidate_genes': MISSION10_CANDIDATE_GENES,
        'selected_fluxes': selected_fluxes,
        'required_tracked_fluxes': MISSION10_REQUIRED_TRACKED_FLUXES,
        'tracking_ready': tracking_ready,
        'growth_objective': MISSION10_GROWTH_OBJECTIVE,
        'minimum_growth': MISSION10_MIN_GROWTH,
        'minimum_production_change': MISSION10_MIN_PRODUCTION_CHANGE,
        'baseline_growth': round(_numeric_result(baseline_growth), 3),
        'baseline_production': round(baseline_value, 3),
        'current_growth': round(growth_value, 3),
        'current_production': round(current_value, 3),
        'production_change': production_change,
        'growth_ok': growth_ok,
        'production_improved': production_improved,
        'result_valid': result_valid,
        'ready_to_deliver': (
            objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and exactly_two_knockouts
            and only_candidate_knockouts
            and target_pair_found
            and tracking_ready
            and growth_ok
            and production_improved
            and result_valid
        ),
    }
    error = objective_error or flux_error
    if error:
        mission10_data['error'] = error
    save_mission10_robust_design_check(mission10_data)
    return mission10_data



def _production_flux_value_map(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict):
        return values

    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if not reaction_id:
            continue
        try:
            values[reaction_id] = float(item.get('production_flux', 0.0))
        except Exception:
            values[reaction_id] = 0.0
    return values


def _build_mission11_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == 'FBA'
    objective_correct = selected_objective == MISSION11_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission11_environment_status(reactions)

    missing_fluxes = [
        reaction_id
        for reaction_id in MISSION11_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_fluxes

    positive_fluxes = [
        reaction_id
        for reaction_id in MISSION11_REQUIRED_TRACKED_FLUXES
        if flux_values.get(reaction_id, 0.0) > 0.001
    ]
    positive_products_ready = len(positive_fluxes) >= MISSION11_MIN_POSITIVE_PRODUCTS

    dominant_product = None
    if flux_values:
        dominant_product = max(flux_values, key=lambda reaction_id: flux_values.get(reaction_id, 0.0))

    growth_ok = _numeric_result(objective_value) >= MISSION11_MIN_GROWTH

    mission11_data = {
        'mission_id': '11',
        'check_version': 1,
        'target_context': MISSION11_TARGET_CONTEXT,
        'method': method_name,
        'method_correct': method_correct,
        'growth_objective': MISSION11_GROWTH_OBJECTIVE,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION11_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'required_tracked_fluxes': MISSION11_REQUIRED_TRACKED_FLUXES,
        'selected_fluxes': selected_fluxes,
        'missing_fluxes': missing_fluxes,
        'tracking_ready': tracking_ready,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'positive_fluxes': positive_fluxes,
        'minimum_positive_products': MISSION11_MIN_POSITIVE_PRODUCTS,
        'positive_products_ready': positive_products_ready,
        'dominant_product': dominant_product,
        'minimum_growth': MISSION11_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and tracking_ready
            and positive_products_ready
            and growth_ok
            and result_valid
        ),
    }
    if objective_error:
        mission11_data['error'] = objective_error
    save_mission11_flux_fingerprint_check(mission11_data)
    return mission11_data


def run_mission11_flux_fingerprint_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 11.'

    return _build_mission11_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )


def run_mission10_robust_design_check(simulation_results=None):
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 10.'

    baseline_growth, baseline_flux, baseline_error = _simulate_flux_in_biomass_solution(
        _build_active_genes_data(),
        _build_anaerobic_reactions_data(),
        MISSION10_TARGET_OBJECTIVE,
        MISSION10_GROWTH_OBJECTIVE,
    )

    current_growth, current_flux, current_error = _simulate_flux_in_biomass_solution(
        genes,
        reactions,
        MISSION10_TARGET_OBJECTIVE,
        MISSION10_GROWTH_OBJECTIVE,
    )

    return _build_mission10_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        flux_error=baseline_error or current_error,
        objective_error=objective_error,
    )


def _build_mission04_data(baseline_growth, baseline_flux, current_growth, current_flux, environment_changed, error=None):
    baseline_value = _numeric_result(baseline_flux)
    current_value = _numeric_result(current_flux)
    production_change = round(current_value - baseline_value, 3)

    mission04_data = {
        'product_name': MISSION04_PRODUCT_NAME,
        'production_objective': MISSION04_PRODUCTION_OBJECTIVE,
        'growth_objective': MISSION04_GROWTH_OBJECTIVE,
        'target_gene': MISSION04_TARGET_GENE,
        'target_gene_name': MISSION04_TARGET_GENE_NAME,
        'baseline_growth': round(_numeric_result(baseline_growth), 3),
        'baseline_production': round(baseline_value, 3),
        'current_growth': round(_numeric_result(current_growth), 3),
        'current_production': round(current_value, 3),
        'production_change': production_change,
        'environment_changed': environment_changed,
        'improved': current_value > baseline_value,
    }
    if error:
        mission04_data['error'] = error
    save_mission04_production_check(mission04_data)
    return mission04_data


def run_mission04_production_check():
    _method_name, _objective_name, genes, reactions = _read_simulation_file()

    baseline_growth, baseline_flux, baseline_error = _simulate_flux_in_biomass_solution(
        _build_active_genes_data(),
        _build_default_reactions_data(),
        MISSION04_PRODUCTION_OBJECTIVE,
        MISSION04_GROWTH_OBJECTIVE,
    )

    current_growth, current_flux, current_error = _simulate_flux_in_biomass_solution(
        genes,
        reactions,
        MISSION04_PRODUCTION_OBJECTIVE,
        MISSION04_GROWTH_OBJECTIVE,
    )

    error = baseline_error or current_error
    return _build_mission04_data(
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        _environment_has_changes(reactions),
        error=error,
    )



def _build_mission05_data(baseline_growth, baseline_flux, current_growth, current_flux, oxygen_disabled, error=None):
    baseline_value = _numeric_result(baseline_flux)
    current_value = _numeric_result(current_flux)
    production_change = round(current_value - baseline_value, 3)

    mission05_data = {
        'product_name': MISSION05_PRODUCT_NAME,
        'production_objective': MISSION05_PRODUCTION_OBJECTIVE,
        'growth_objective': MISSION05_GROWTH_OBJECTIVE,
        'target_gene': MISSION05_TARGET_GENE,
        'target_gene_name': MISSION05_TARGET_GENE_NAME,
        'oxygen_reaction': MISSION05_OXYGEN_REACTION,
        'baseline_growth': round(_numeric_result(baseline_growth), 3),
        'baseline_production': round(baseline_value, 3),
        'current_growth': round(_numeric_result(current_growth), 3),
        'current_production': round(current_value, 3),
        'production_change': production_change,
        'oxygen_disabled': oxygen_disabled,
        'improved': current_value > baseline_value,
    }
    if error:
        mission05_data['error'] = error
    save_mission05_production_check(mission05_data)
    return mission05_data


def run_mission05_production_check():
    _method_name, _objective_name, genes, reactions = _read_simulation_file()

    baseline_growth, baseline_flux, baseline_error = _simulate_flux_in_biomass_solution(
        _build_active_genes_data(),
        _build_anaerobic_reactions_data(),
        MISSION05_PRODUCTION_OBJECTIVE,
        MISSION05_GROWTH_OBJECTIVE,
    )

    current_growth, current_flux, current_error = _simulate_flux_in_biomass_solution(
        genes,
        reactions,
        MISSION05_PRODUCTION_OBJECTIVE,
        MISSION05_GROWTH_OBJECTIVE,
    )

    error = baseline_error or current_error
    return _build_mission05_data(
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        _oxygen_lower_bound_closed(reactions),
        error=error,
    )


def run_simul():
    method_name, objective_name, genes, reactions = _read_simulation_file()
    selected_fluxes = _read_selected_production_fluxes()
    results, production_fluxes = _simulate_local_objective_with_production_fluxes(
        method_name,
        objective_name,
        genes,
        reactions,
        selected_fluxes,
    )
    return objective_name, results, production_fluxes


def run_challenge_score():
    _method_name, _objective_name, genes, reactions = _read_simulation_file()

    # Mission 06 must evaluate growth and ethanol production in the same
    # metabolic solution. We therefore run one biomass-optimised FBA and read
    # the ethanol exchange flux from that solution, instead of maximising
    # EX_etoh_e separately (which can just hit the 1000 upper bound).
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = CHALLENGE_GROWTH_OBJECTIVE
    result = simul.simulate(method='FBA', constraints=constraints)

    growth = _normalise_result(result)
    if growth == 'Status: INFEASIBLE':
        return _build_challenge_data(0.0, 0.0)

    production_flux = _extract_flux(result, CHALLENGE_PRODUCTION_OBJECTIVE)
    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return _build_challenge_data(
            growth,
            0.0,
            error=f'Could not read {CHALLENGE_PRODUCTION_OBJECTIVE} flux from the FBA solution.'
        )

    return _build_challenge_data(growth, production_value)


def _build_request_payload():
    method_name, objective_name, genes, reactions = _read_simulation_file()

    reactions_original = REACTIONS

    env_conditions = {}
    count = 0
    count_2 = 0
    for i, (k, x) in enumerate(reactions.items()):
        if count >= len(reactions_original.index):
            break

        rid = reactions_original.index[count]
        if count_2 % 2 == 0:
            lb = -1000 if x else 0
            env_conditions[rid] = [lb, reactions_original.ub.iloc[count]]
            count_2 += 1
        else:
            ub = 1000 if x else 0
            env_conditions[rid] = [env_conditions[rid][0], ub]
            count_2 += 1
            count += 1

    gene_knockouts = [k for k, x in genes.items() if not x]

    return {
        'method': method_name,
        'objective': objective_name,
        'gene_knockouts': gene_knockouts,
        'env_conditions': env_conditions,
    }


def _http_post_json(url, payload):
    body = json.dumps(payload)
    if sys.platform == 'emscripten':
        # pygbag's pyodide does not expose `from js import XMLHttpRequest`
        # as a constructable JsProxy (XMLHttpRequest.new is None and the
        # plain JsProxy is not callable), so we instantiate via js.eval.
        # Synchronous XHR lets us stay inside the sync pygame_menu callback
        # at window.py:data_fun — no async bridge needed for the simulate call.
        import js
        xhr = js.eval("new XMLHttpRequest()")
        xhr.open('POST', url, False)
        xhr.setRequestHeader('Content-Type', 'application/json')
        xhr.send(body)
        return json.loads(xhr.responseText)
    import urllib.request
    req = urllib.request.Request(
        url,
        data=body.encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def run_simul_remote(backend_url):
    payload = _build_request_payload()
    selected_fluxes = _read_selected_production_fluxes()
    try:
        response = _http_post_json(backend_url.rstrip('/') + '/simulate', payload)
    except Exception as e:
        return payload['objective'], f'Error: {e}', _build_production_flux_data(
            selected_fluxes,
            error=f'Backend error: {e}'
        )

    if response.get('status') == 'ok':
        fluxes = response.get('fluxes') or {}
        return response['objective'], response['result'], _build_production_flux_data(
            selected_fluxes,
            flux_getter=lambda reaction_id: fluxes.get(reaction_id)
        )
    if response.get('status') == 'infeasible':
        return response['objective'], 'Status: INFEASIBLE', _build_production_flux_data(
            selected_fluxes,
            error='Simulation infeasible. Production fluxes could not be measured.'
        )
    return (
        response.get('objective', payload['objective']),
        f'Error: {response.get("message", "unknown")}',
        _build_production_flux_data(
            selected_fluxes,
            error=response.get('message', 'unknown backend error')
        )
    )



def _build_default_env_conditions_payload():
    env_conditions = {}
    for i in range(len(REACTIONS.index)):
        rid = REACTIONS.index[i]
        lb = -1000 if REACTIONS.lb.iloc[i] != 0 else 0
        ub = 1000 if REACTIONS.ub.iloc[i] != 0 else 0
        env_conditions[rid] = [lb, ub]
    return env_conditions


def _simulate_remote_flux_solution(backend_url, payload, objective):
    request_payload = copy.deepcopy(payload)
    request_payload['method'] = 'FBA'
    request_payload['objective'] = objective
    return _http_post_json(backend_url.rstrip('/') + '/simulate', request_payload)


def _extract_remote_growth_and_flux(response, production_objective):
    if response.get('status') == 'infeasible':
        return 0.0, 0.0, 'Status: INFEASIBLE'

    if response.get('status') != 'ok':
        return 0.0, 0.0, response.get('message', 'unknown backend error')

    growth = response.get('result', 0.0)
    fluxes = response.get('fluxes') or {}
    production_flux = fluxes.get(production_objective)

    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return growth, 0.0, f'Backend did not return {production_objective} flux.'

    return growth, production_value, None


def run_mission04_production_check_remote(backend_url):
    payload = _build_request_payload()

    baseline_payload = copy.deepcopy(payload)
    baseline_payload['objective'] = MISSION04_GROWTH_OBJECTIVE
    baseline_payload['gene_knockouts'] = []
    baseline_payload['env_conditions'] = _build_default_env_conditions_payload()

    current_payload = copy.deepcopy(payload)
    current_payload['objective'] = MISSION04_GROWTH_OBJECTIVE

    try:
        baseline_response = _simulate_remote_flux_solution(backend_url, baseline_payload, MISSION04_GROWTH_OBJECTIVE)
        current_response = _simulate_remote_flux_solution(backend_url, current_payload, MISSION04_GROWTH_OBJECTIVE)
    except Exception as e:
        return _build_mission04_data(0.0, 0.0, 0.0, 0.0, _environment_has_changes(_read_simulation_file()[3]), error=str(e))

    baseline_growth, baseline_flux, baseline_error = _extract_remote_growth_and_flux(
        baseline_response,
        MISSION04_PRODUCTION_OBJECTIVE,
    )
    current_growth, current_flux, current_error = _extract_remote_growth_and_flux(
        current_response,
        MISSION04_PRODUCTION_OBJECTIVE,
    )

    return _build_mission04_data(
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        _environment_has_changes(_read_simulation_file()[3]),
        error=baseline_error or current_error,
    )



def _build_anaerobic_env_conditions_payload():
    env_conditions = _build_default_env_conditions_payload()
    if MISSION05_OXYGEN_REACTION in env_conditions:
        env_conditions[MISSION05_OXYGEN_REACTION][0] = 0
    return env_conditions


def run_mission05_production_check_remote(backend_url):
    payload = _build_request_payload()

    baseline_payload = copy.deepcopy(payload)
    baseline_payload['objective'] = MISSION05_GROWTH_OBJECTIVE
    baseline_payload['gene_knockouts'] = []
    baseline_payload['env_conditions'] = _build_anaerobic_env_conditions_payload()

    current_payload = copy.deepcopy(payload)
    current_payload['objective'] = MISSION05_GROWTH_OBJECTIVE

    try:
        baseline_response = _simulate_remote_flux_solution(backend_url, baseline_payload, MISSION05_GROWTH_OBJECTIVE)
        current_response = _simulate_remote_flux_solution(backend_url, current_payload, MISSION05_GROWTH_OBJECTIVE)
    except Exception as e:
        return _build_mission05_data(0.0, 0.0, 0.0, 0.0, _oxygen_lower_bound_closed(_read_simulation_file()[3]), error=str(e))

    baseline_growth, baseline_flux, baseline_error = _extract_remote_growth_and_flux(
        baseline_response,
        MISSION05_PRODUCTION_OBJECTIVE,
    )
    current_growth, current_flux, current_error = _extract_remote_growth_and_flux(
        current_response,
        MISSION05_PRODUCTION_OBJECTIVE,
    )

    return _build_mission05_data(
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        _oxygen_lower_bound_closed(_read_simulation_file()[3]),
        error=baseline_error or current_error,
    )


def run_mission09_design_check_remote(backend_url, simulation_results=None):
    payload = _build_request_payload()
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 09.'

    baseline_payload = copy.deepcopy(payload)
    baseline_payload['objective'] = MISSION09_GROWTH_OBJECTIVE
    baseline_payload['gene_knockouts'] = []
    baseline_payload['env_conditions'] = _build_anaerobic_env_conditions_payload()

    current_payload = copy.deepcopy(payload)
    current_payload['objective'] = MISSION09_GROWTH_OBJECTIVE

    try:
        baseline_response = _simulate_remote_flux_solution(backend_url, baseline_payload, MISSION09_GROWTH_OBJECTIVE)
        current_response = _simulate_remote_flux_solution(backend_url, current_payload, MISSION09_GROWTH_OBJECTIVE)
    except Exception as e:
        return _build_mission09_data(
            selected_objective,
            objective_result,
            genes,
            reactions,
            0.0,
            0.0,
            0.0,
            0.0,
            flux_error=str(e),
            objective_error=objective_error,
        )

    baseline_growth, baseline_flux, baseline_error = _extract_remote_growth_and_flux(
        baseline_response,
        MISSION09_TARGET_OBJECTIVE,
    )
    current_growth, current_flux, current_error = _extract_remote_growth_and_flux(
        current_response,
        MISSION09_TARGET_OBJECTIVE,
    )

    return _build_mission09_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        flux_error=baseline_error or current_error,
        objective_error=objective_error,
    )



def _simulate_remote_challenge_solution(backend_url, payload):
    request_payload = copy.deepcopy(payload)
    request_payload['method'] = 'FBA'
    request_payload['objective'] = CHALLENGE_GROWTH_OBJECTIVE
    return _http_post_json(backend_url.rstrip('/') + '/simulate', request_payload)


def run_challenge_score_remote(backend_url):
    payload = _build_request_payload()
    try:
        response = _simulate_remote_challenge_solution(backend_url, payload)
    except Exception as e:
        return _build_challenge_data(0.0, 0.0, error=str(e))

    if response.get('status') == 'infeasible':
        return _build_challenge_data(0.0, 0.0)

    if response.get('status') != 'ok':
        return _build_challenge_data(
            0.0,
            0.0,
            error=response.get('message', 'unknown backend error')
        )

    growth = response.get('result', 0.0)
    fluxes = response.get('fluxes') or {}
    production_flux = fluxes.get(CHALLENGE_PRODUCTION_OBJECTIVE)

    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return _build_challenge_data(
            growth,
            0.0,
            error=f'Backend did not return {CHALLENGE_PRODUCTION_OBJECTIVE} flux.'
        )

    return _build_challenge_data(growth, production_value)


if __name__ == '__main__':
     print(run_simul())


def run_mission10_robust_design_check_remote(backend_url, simulation_results=None):
    payload = _build_request_payload()
    _method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 10.'

    baseline_payload = copy.deepcopy(payload)
    baseline_payload['objective'] = MISSION10_GROWTH_OBJECTIVE
    baseline_payload['gene_knockouts'] = []
    baseline_payload['env_conditions'] = _build_anaerobic_env_conditions_payload()

    current_payload = copy.deepcopy(payload)
    current_payload['objective'] = MISSION10_GROWTH_OBJECTIVE

    try:
        baseline_response = _simulate_remote_flux_solution(backend_url, baseline_payload, MISSION10_GROWTH_OBJECTIVE)
        current_response = _simulate_remote_flux_solution(backend_url, current_payload, MISSION10_GROWTH_OBJECTIVE)
    except Exception as e:
        return _build_mission10_data(
            selected_objective,
            objective_result,
            genes,
            reactions,
            0.0,
            0.0,
            0.0,
            0.0,
            flux_error=str(e),
            objective_error=objective_error,
        )

    baseline_growth, baseline_flux, baseline_error = _extract_remote_growth_and_flux(
        baseline_response,
        MISSION10_TARGET_OBJECTIVE,
    )
    current_growth, current_flux, current_error = _extract_remote_growth_and_flux(
        current_response,
        MISSION10_TARGET_OBJECTIVE,
    )

    return _build_mission10_data(
        selected_objective,
        objective_result,
        genes,
        reactions,
        baseline_growth,
        baseline_flux,
        current_growth,
        current_flux,
        flux_error=baseline_error or current_error,
        objective_error=objective_error,
    )
