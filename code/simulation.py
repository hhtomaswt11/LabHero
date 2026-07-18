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

MISSION12_METHOD = 'FBA'
MISSION12_TARGET_PRODUCT = 'succinate'
MISSION12_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION12_OXYGEN_REACTION = 'EX_o2_e'
MISSION12_REQUIRED_TRACKED_FLUXES = ['EX_succ_e']
MISSION12_COMPETING_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION12_MIN_COMPETING_FLUXES = 2
MISSION12_MIN_TARGET_FLUX = 1.0

MISSION13_BASELINE_METHOD = 'FBA'
MISSION13_TARGET_METHOD = 'pFBA'
MISSION13_TARGET_PRODUCT = 'succinate'
MISSION13_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION13_OXYGEN_REACTION = 'EX_o2_e'
MISSION13_REQUIRED_TRACKED_FLUXES = ['EX_succ_e']
MISSION13_COMPETING_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION13_MIN_COMPETING_FLUXES = 3
MISSION13_MIN_TARGET_FLUX = 1.0

MISSION14_TARGET_METHOD = 'pFBA'
MISSION14_TARGET_PRODUCT = 'succinate'
MISSION14_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION14_UNWANTED_PRODUCT = 'ethanol'
MISSION14_UNWANTED_FLUX = 'EX_etoh_e'
MISSION14_OXYGEN_REACTION = 'EX_o2_e'
MISSION14_TARGET_GENE = 'b1241'
MISSION14_TARGET_GENE_NAME = 'adhE'
MISSION14_CANDIDATE_GENES = ['b0903', 'b2297', 'b0728', 'b3115', 'b0118', 'b1241']
MISSION14_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_etoh_e']
MISSION14_MIN_TARGET_FLUX = 1.0
MISSION14_MAX_UNWANTED_FLUX = 1.0

MISSION15_TARGET_METHOD = 'pFBA'
MISSION15_TARGET_PRODUCT = 'succinate'
MISSION15_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION15_OXYGEN_REACTION = 'EX_o2_e'
MISSION15_TARGET_GENE = 'b1241'
MISSION15_TARGET_GENE_NAME = 'adhE'
MISSION15_CANDIDATE_GENES = ['b0903', 'b2297', 'b0728', 'b3115', 'b0118', 'b1241']
MISSION15_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_etoh_e', 'EX_ac_e', 'EX_for_e', 'EX_lac__D_e']
MISSION15_TARGET_FLUX = 'EX_succ_e'
MISSION15_UNWANTED_FLUX = 'EX_etoh_e'
MISSION15_MIN_TARGET_FLUX = 1.0
MISSION15_MAX_UNWANTED_FLUX = 1.0
MISSION15_MIN_GROWTH = 1.0

MISSION16_METHOD = 'FBA'
MISSION16_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION16_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION16_TARGET_CONTEXT = 'alternative carbon rescue'
MISSION16_CANDIDATE_CARBON_SOURCES = ['EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e']
MISSION16_REQUIRED_MEDIUM_FLUXES = [
    MISSION16_BLOCKED_CARBON_SOURCE,
    'EX_ac_e',
    'EX_pyr_e',
    'EX_mal__L_e',
    'EX_fum_e',
    'EX_akg_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION16_MIN_GROWTH = 5.0
MISSION16_MIN_SOURCE_UPTAKE = 0.001

MISSION17_METHOD = 'FBA'
MISSION17_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION17_TARGET_CONTEXT = 'essential medium component'
MISSION17_TARGET_NUTRIENT = 'EX_pi_e'
MISSION17_TARGET_NUTRIENT_NAME = 'phosphate'
MISSION17_CANDIDATE_NUTRIENTS = ['EX_nh4_e', 'EX_pi_e', 'EX_h2o_e', 'EX_h_e', 'EX_co2_e']
MISSION17_REQUIRED_MEDIUM_FLUXES = [
    'EX_glc__D_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_h2o_e',
    'EX_h_e',
    'EX_co2_e',
    'EX_o2_e',
]
MISSION17_MAX_GROWTH = 1.0
MISSION17_MIN_BASELINE_GROWTH = 5.0

MISSION18_METHOD = 'FBA'
MISSION18_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION18_TARGET_CONTEXT = 'export bottleneck'
MISSION18_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION18_ALTERNATIVE_CARBON_SOURCE = 'EX_pyr_e'
MISSION18_EXPORT_BOTTLENECK = 'EX_ac_e'
MISSION18_EXPORT_BOTTLENECK_NAME = 'acetate'
MISSION18_REQUIRED_MEDIUM_FLUXES = [
    MISSION18_BLOCKED_CARBON_SOURCE,
    MISSION18_ALTERNATIVE_CARBON_SOURCE,
    MISSION18_EXPORT_BOTTLENECK,
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION18_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_succ_e']
MISSION18_MIN_GROWTH = 1.0
MISSION18_MIN_SOURCE_UPTAKE = 0.001
MISSION18_MAX_BLOCKED_EXPORT_FLUX = 0.001

MISSION19_TARGET_METHOD = 'lMOMA'
MISSION19_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION19_TARGET_CONTEXT = 'single-gene perturbation response'
MISSION19_TARGET_GENE = 'b2296'
MISSION19_TARGET_GENE_NAME = 'ackA'
MISSION19_CANDIDATE_GENES = ['b0118', 'b1276', 'b0720', 'b1611', 'b3236', 'b0728', 'b2296']
MISSION19_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION19_MIN_GROWTH = 0.1

MISSION20_TARGET_METHOD = 'pFBA'
MISSION20_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION20_TARGET_CONTEXT = 'final medium robustness report'
MISSION20_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION20_ALTERNATIVE_CARBON_SOURCE = 'EX_pyr_e'
MISSION20_EXPORT_BOTTLENECK = 'EX_ac_e'
MISSION20_EXPORT_BOTTLENECK_NAME = 'acetate'
MISSION20_REQUIRED_ESSENTIAL_UPTAKES = ['EX_nh4_e', 'EX_pi_e']
MISSION20_REQUIRED_MEDIUM_FLUXES = [
    MISSION20_BLOCKED_CARBON_SOURCE,
    MISSION20_ALTERNATIVE_CARBON_SOURCE,
    MISSION20_EXPORT_BOTTLENECK,
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION20_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_succ_e', 'EX_lac__D_e']
MISSION20_MIN_GROWTH = 1.0
MISSION20_MIN_SOURCE_UPTAKE = 0.001
MISSION20_MIN_ESSENTIAL_UPTAKE = 0.001
MISSION20_MAX_BLOCKED_EXPORT_FLUX = 0.001


EXCHANGE_FLUX_REPORT_REACTION_IDS = [
    'EX_glc__D_e',   # D-Glucose
    'EX_fru_e',      # D-Fructose
    'EX_ac_e',       # Acetate
    'EX_pyr_e',      # Pyruvate
    'EX_mal__L_e',   # L-Malate
    'EX_fum_e',      # Fumarate
    'EX_akg_e',      # 2-Oxoglutarate
    'EX_succ_e',     # Succinate
    'EX_etoh_e',     # Ethanol
    'EX_for_e',      # Formate
    'EX_lac__D_e',   # D-lactate
    'EX_nh4_e',      # Ammonia
    'EX_pi_e',       # Phosphate
    'EX_o2_e',       # Oxygen
    'EX_co2_e',      # CO2
    'EX_h2o_e',      # Water
    'EX_h_e',        # Protons
    'EX_gln__L_e',   # L-Glutamine
    'EX_glu__L_e',   # L-Glutamate
]

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


def _mission12_environment_status(reactions):
    """Return whether Mission 12 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION12_OXYGEN_REACTION)
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


def _mission13_environment_status(reactions):
    """Return whether Mission 13 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION13_OXYGEN_REACTION)
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



def _mission14_environment_status(reactions):
    """Return whether Mission 14 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION14_OXYGEN_REACTION)
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



def _mission15_environment_status(reactions):
    """Return whether Mission 15 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION15_OXYGEN_REACTION)
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


def _reaction_display_label(reaction_id):
    try:
        reaction_ids = list(REACTIONS.index)
        reaction_index = reaction_ids.index(reaction_id)
        reaction_name = str(REACTIONS.name.iloc[reaction_index])
        return f'{reaction_name} ({reaction_id})'
    except Exception:
        return reaction_id


def _build_medium_flux_data(reaction_ids=None, flux_getter=None, error=None):
    """Build a compact uptake/exchange report for medium-engineering missions.

    For exchange reactions, negative flux means uptake/consumption and positive
    flux means secretion/export. Production Flux already focuses on exported
    products; this report focuses on what the model is taking from the medium.
    """
    reaction_ids = reaction_ids or EXCHANGE_FLUX_REPORT_REACTION_IDS
    reaction_ids = [reaction_id for reaction_id in reaction_ids if reaction_id in list(REACTIONS.index)]

    data = {
        'reaction_ids': reaction_ids,
        'items': [],
    }

    if error:
        data['error'] = error
        return data

    for reaction_id in reaction_ids:
        raw_flux = None
        if callable(flux_getter):
            try:
                raw_flux = flux_getter(reaction_id)
            except Exception:
                raw_flux = None

        raw_value = _as_float_or_none(raw_flux)
        item = {
            'reaction_id': reaction_id,
            'label': _reaction_display_label(reaction_id),
        }

        if raw_value is None:
            item['error'] = 'Flux not available in this simulation result.'
        else:
            item['raw_flux'] = round(raw_value, 6)
            item['uptake_flux'] = round(max(-raw_value, 0.0), 3)
            item['secretion_flux'] = round(max(raw_value, 0.0), 3)

        data['items'].append(item)

    return data


def _simulate_local_objective_with_production_fluxes(method_name, objective_name, genes, reactions, selected_fluxes):
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    objective_result = _normalise_result(result)

    if objective_result == 'Status: INFEASIBLE':
        return (
            objective_result,
            _build_production_flux_data(
                selected_fluxes,
                error='Simulation infeasible. Production fluxes could not be measured.'
            ),
            _build_medium_flux_data(
                error='Simulation infeasible. Medium fluxes could not be measured.'
            )
        )

    flux_getter = lambda reaction_id: _extract_flux(result, reaction_id)
    production_fluxes = _build_production_flux_data(
        selected_fluxes,
        flux_getter=flux_getter
    )
    medium_fluxes = _build_medium_flux_data(
        flux_getter=flux_getter
    )
    return objective_result, production_fluxes, medium_fluxes




def _simulate_local_reaction_flux(method_name, objective_name, genes, reactions, reaction_id):
    """Run a local simulation and read one reaction flux from its solution.

    For lMOMA/ROOM, the printed objective value may represent the method
    objective instead of the biomass reaction flux. Mission 19 therefore reads
    the biomass reaction flux directly from the solution.
    """
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    raw_flux = _extract_flux(result, reaction_id)
    return _as_float_or_none(raw_flux)

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


def _build_mission12_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION12_METHOD
    objective_correct = selected_objective == MISSION12_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission12_environment_status(reactions)

    target_flux_tracked = MISSION12_TARGET_OBJECTIVE in selected_fluxes
    target_flux = flux_values.get(MISSION12_TARGET_OBJECTIVE, 0.0)
    target_flux_positive = target_flux >= MISSION12_MIN_TARGET_FLUX

    selected_competing_fluxes = [
        reaction_id
        for reaction_id in MISSION12_COMPETING_FLUXES
        if reaction_id in selected_fluxes
    ]
    competing_fluxes_ready = len(selected_competing_fluxes) >= MISSION12_MIN_COMPETING_FLUXES

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION12_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]

    mission12_data = {
        'mission_id': '12',
        'check_version': 1,
        'target_product': MISSION12_TARGET_PRODUCT,
        'target_objective': MISSION12_TARGET_OBJECTIVE,
        'method': method_name,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION12_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION12_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'competing_flux_options': MISSION12_COMPETING_FLUXES,
        'selected_competing_fluxes': selected_competing_fluxes,
        'minimum_competing_fluxes': MISSION12_MIN_COMPETING_FLUXES,
        'target_flux_tracked': target_flux_tracked,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION12_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'competing_fluxes_ready': competing_fluxes_ready,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and target_flux_tracked
            and target_flux_positive
            and competing_fluxes_ready
            and result_valid
        ),
    }
    if objective_error:
        mission12_data['error'] = objective_error
    save_mission12_byproduct_check(mission12_data)
    return mission12_data


def run_mission12_byproduct_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 12.'

    return _build_mission12_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )




def _build_mission13_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION13_TARGET_METHOD
    baseline_method_selected = method_name == MISSION13_BASELINE_METHOD
    objective_correct = selected_objective == MISSION13_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission13_environment_status(reactions)

    target_flux_tracked = MISSION13_TARGET_OBJECTIVE in selected_fluxes
    target_flux = flux_values.get(MISSION13_TARGET_OBJECTIVE, 0.0)
    target_flux_positive = target_flux >= MISSION13_MIN_TARGET_FLUX

    selected_competing_fluxes = [
        reaction_id
        for reaction_id in MISSION13_COMPETING_FLUXES
        if reaction_id in selected_fluxes
    ]
    competing_fluxes_ready = len(selected_competing_fluxes) >= MISSION13_MIN_COMPETING_FLUXES

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION13_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]

    baseline_data = load_mission12_byproduct_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '12'
        and baseline_data.get('check_version') == 1
        and baseline_data.get('ready_to_deliver')
    )
    baseline_target_flux = baseline_data.get('target_flux') if baseline_available else None
    baseline_method = baseline_data.get('method') if baseline_available else None

    flux_difference = None
    try:
        if baseline_target_flux is not None:
            flux_difference = round(float(target_flux) - float(baseline_target_flux), 3)
    except Exception:
        flux_difference = None

    mission13_data = {
        'mission_id': '13',
        'check_version': 1,
        'target_product': MISSION13_TARGET_PRODUCT,
        'target_objective': MISSION13_TARGET_OBJECTIVE,
        'baseline_method': MISSION13_BASELINE_METHOD,
        'target_method': MISSION13_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'baseline_method_selected': baseline_method_selected,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION13_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION13_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'competing_flux_options': MISSION13_COMPETING_FLUXES,
        'selected_competing_fluxes': selected_competing_fluxes,
        'minimum_competing_fluxes': MISSION13_MIN_COMPETING_FLUXES,
        'target_flux_tracked': target_flux_tracked,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION13_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'competing_fluxes_ready': competing_fluxes_ready,
        'baseline_available': baseline_available,
        'previous_baseline_method': baseline_method,
        'previous_fba_target_flux': baseline_target_flux,
        'target_flux_difference_from_fba': flux_difference,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and target_flux_tracked
            and target_flux_positive
            and competing_fluxes_ready
            and result_valid
        ),
    }
    if objective_error:
        mission13_data['error'] = objective_error
    save_mission13_method_check(mission13_data)
    return mission13_data


def run_mission13_method_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 13.'

    return _build_mission13_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )



def _build_mission14_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION14_TARGET_METHOD
    objective_correct = selected_objective == MISSION14_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission14_environment_status(reactions)

    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION14_TARGET_GENE]

    target_flux_tracked = MISSION14_TARGET_OBJECTIVE in selected_fluxes
    unwanted_flux_tracked = MISSION14_UNWANTED_FLUX in selected_fluxes
    required_fluxes_ready = all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION14_REQUIRED_TRACKED_FLUXES
    )

    target_flux = flux_values.get(MISSION14_TARGET_OBJECTIVE, 0.0)
    unwanted_flux = flux_values.get(MISSION14_UNWANTED_FLUX, 0.0)
    target_flux_positive = target_flux >= MISSION14_MIN_TARGET_FLUX
    unwanted_flux_reduced = unwanted_flux <= MISSION14_MAX_UNWANTED_FLUX

    baseline_data = load_mission13_method_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '13'
        and baseline_data.get('check_version') == 1
        and baseline_data.get('ready_to_deliver')
    )
    baseline_unwanted_flux = None
    if baseline_available:
        baseline_values = baseline_data.get('tracked_flux_values') or {}
        baseline_unwanted_flux = baseline_values.get(MISSION14_UNWANTED_FLUX)

    unwanted_flux_change = None
    try:
        if baseline_unwanted_flux is not None:
            unwanted_flux_change = round(float(unwanted_flux) - float(baseline_unwanted_flux), 3)
    except Exception:
        unwanted_flux_change = None

    mission14_data = {
        'mission_id': '14',
        'check_version': 1,
        'target_product': MISSION14_TARGET_PRODUCT,
        'target_objective': MISSION14_TARGET_OBJECTIVE,
        'unwanted_product': MISSION14_UNWANTED_PRODUCT,
        'unwanted_flux': MISSION14_UNWANTED_FLUX,
        'target_method': MISSION14_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION14_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'candidate_genes': MISSION14_CANDIDATE_GENES,
        'target_gene': MISSION14_TARGET_GENE,
        'target_gene_name': MISSION14_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION14_REQUIRED_TRACKED_FLUXES,
        'target_flux_tracked': target_flux_tracked,
        'unwanted_flux_tracked': unwanted_flux_tracked,
        'required_fluxes_ready': required_fluxes_ready,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION14_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'current_unwanted_flux': round(unwanted_flux, 3),
        'maximum_unwanted_flux': MISSION14_MAX_UNWANTED_FLUX,
        'unwanted_flux_reduced': unwanted_flux_reduced,
        'baseline_available': baseline_available,
        'previous_unwanted_flux': baseline_unwanted_flux,
        'unwanted_flux_change_from_previous': unwanted_flux_change,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and exact_one_knockout
            and target_gene_found
            and target_flux_tracked
            and unwanted_flux_tracked
            and required_fluxes_ready
            and target_flux_positive
            and unwanted_flux_reduced
            and result_valid
        ),
    }
    if objective_error:
        mission14_data['error'] = objective_error
    save_mission14_reduction_check(mission14_data)
    return mission14_data


def run_mission14_reduction_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 14.'

    return _build_mission14_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )



def _build_mission15_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION15_TARGET_METHOD
    objective_correct = selected_objective == MISSION15_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission15_environment_status(reactions)

    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION15_TARGET_GENE]

    required_fluxes_ready = all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
    )
    target_flux_tracked = MISSION15_TARGET_FLUX in selected_fluxes
    unwanted_flux_tracked = MISSION15_UNWANTED_FLUX in selected_fluxes

    target_flux = flux_values.get(MISSION15_TARGET_FLUX, 0.0)
    unwanted_flux = flux_values.get(MISSION15_UNWANTED_FLUX, 0.0)
    target_flux_positive = target_flux >= MISSION15_MIN_TARGET_FLUX
    unwanted_flux_reduced = unwanted_flux <= MISSION15_MAX_UNWANTED_FLUX

    byproduct_fluxes = {
        reaction_id: flux_values.get(reaction_id, 0.0)
        for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
        if reaction_id != MISSION15_TARGET_FLUX
    }
    highest_byproduct_flux = max(byproduct_fluxes.values()) if byproduct_fluxes else 0.0
    target_dominates_byproducts = target_flux > highest_byproduct_flux

    baseline_data = load_mission14_reduction_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '14'
        and baseline_data.get('check_version') == 1
        and baseline_data.get('ready_to_deliver')
    )
    baseline_target_flux = None
    baseline_unwanted_flux = None
    if baseline_available:
        baseline_target_flux = baseline_data.get('target_flux')
        baseline_unwanted_flux = baseline_data.get('current_unwanted_flux')

    target_flux_change = None
    unwanted_flux_change = None
    try:
        if baseline_target_flux is not None:
            target_flux_change = round(float(target_flux) - float(baseline_target_flux), 3)
    except Exception:
        target_flux_change = None
    try:
        if baseline_unwanted_flux is not None:
            unwanted_flux_change = round(float(unwanted_flux) - float(baseline_unwanted_flux), 3)
    except Exception:
        unwanted_flux_change = None

    mission15_data = {
        'mission_id': '15',
        'check_version': 1,
        'target_product': MISSION15_TARGET_PRODUCT,
        'target_objective': MISSION15_TARGET_OBJECTIVE,
        'target_method': MISSION15_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION15_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'candidate_genes': MISSION15_CANDIDATE_GENES,
        'target_gene': MISSION15_TARGET_GENE,
        'target_gene_name': MISSION15_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION15_REQUIRED_TRACKED_FLUXES,
        'required_fluxes_ready': required_fluxes_ready,
        'target_flux_tracked': target_flux_tracked,
        'unwanted_flux_tracked': unwanted_flux_tracked,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION15_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'current_unwanted_flux': round(unwanted_flux, 3),
        'maximum_unwanted_flux': MISSION15_MAX_UNWANTED_FLUX,
        'unwanted_flux_reduced': unwanted_flux_reduced,
        'byproduct_fluxes': {reaction_id: round(value, 3) for reaction_id, value in byproduct_fluxes.items()},
        'highest_byproduct_flux': round(highest_byproduct_flux, 3),
        'target_dominates_byproducts': target_dominates_byproducts,
        'baseline_available': baseline_available,
        'previous_target_flux': baseline_target_flux,
        'previous_unwanted_flux': baseline_unwanted_flux,
        'target_flux_change_from_previous': target_flux_change,
        'unwanted_flux_change_from_previous': unwanted_flux_change,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and exact_one_knockout
            and target_gene_found
            and required_fluxes_ready
            and target_flux_tracked
            and unwanted_flux_tracked
            and target_flux_positive
            and unwanted_flux_reduced
            and target_dominates_byproducts
            and result_valid
        ),
    }
    if objective_error:
        mission15_data['error'] = objective_error
    save_mission15_diagnostic_report_check(mission15_data)
    return mission15_data


def run_mission15_diagnostic_report_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 15.'

    return _build_mission15_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )


def _mission16_environment_status(reactions):
    """Evaluate the medium changes required for Mission 16.

    The player must close glucose uptake and open exactly one candidate
    alternative carbon source, without adding unrelated medium changes.
    """
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    selected_sources = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION16_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id in MISSION16_CANDIDATE_CARBON_SOURCES:
            if lower_changed and lower_bound_open:
                selected_sources.append(reaction_id)
            elif lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return glucose_lower_bound_closed, selected_sources, unexpected_changes


def _medium_flux_maps(medium_fluxes):
    raw_fluxes = {}
    uptake_fluxes = {}
    secretion_fluxes = {}

    if not medium_fluxes or medium_fluxes.get('error'):
        return raw_fluxes, uptake_fluxes, secretion_fluxes

    for item in medium_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if not reaction_id or item.get('error'):
            continue
        raw_fluxes[reaction_id] = float(item.get('raw_flux', 0.0))
        uptake_fluxes[reaction_id] = float(item.get('uptake_flux', 0.0))
        secretion_fluxes[reaction_id] = float(item.get('secretion_flux', 0.0))

    return raw_fluxes, uptake_fluxes, secretion_fluxes


def _build_mission16_data(method_name, selected_objective, objective_result, genes, reactions, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    method_correct = method_name == MISSION16_METHOD
    objective_correct = selected_objective == MISSION16_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    growth_value = _numeric_result(objective_value)
    growth_ok = growth_value >= MISSION16_MIN_GROWTH

    glucose_lower_bound_closed, selected_sources, unexpected_environment_changes = _mission16_environment_status(reactions)
    exactly_one_alternative_source = len(selected_sources) == 1
    selected_source = selected_sources[0] if exactly_one_alternative_source else None

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    selected_source_uptake = uptake_fluxes.get(selected_source, 0.0) if selected_source else 0.0
    glucose_uptake = uptake_fluxes.get(MISSION16_BLOCKED_CARBON_SOURCE, 0.0)
    source_uptake_detected = selected_source_uptake >= MISSION16_MIN_SOURCE_UPTAKE
    glucose_uptake_blocked = glucose_uptake <= MISSION16_MIN_SOURCE_UPTAKE

    result_valid = objective_value is not None and objective_value > 0

    mission16_data = {
        'mission_id': '16',
        'check_version': 1,
        'mission_title': 'Alternative Carbon Rescue',
        'target_context': MISSION16_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION16_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION16_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if objective_value is not None else str(objective_result),
        'blocked_carbon_source': MISSION16_BLOCKED_CARBON_SOURCE,
        'candidate_carbon_sources': MISSION16_CANDIDATE_CARBON_SOURCES,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'selected_alternative_sources': selected_sources,
        'selected_source': selected_source,
        'exactly_one_alternative_source': exactly_one_alternative_source,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_raw_fluxes': {reaction_id: round(value, 3) for reaction_id, value in raw_fluxes.items()},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'selected_source_uptake': round(selected_source_uptake, 3),
        'glucose_uptake': round(glucose_uptake, 3),
        'minimum_source_uptake': MISSION16_MIN_SOURCE_UPTAKE,
        'source_uptake_detected': source_uptake_detected,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'minimum_growth': MISSION16_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and exactly_one_alternative_source
            and not unexpected_environment_changes
            and not knocked_out_genes
            and source_uptake_detected
            and growth_ok
            and result_valid
        ),
    }
    if objective_error:
        mission16_data['error'] = objective_error
    save_mission16_medium_report_check(mission16_data)
    return mission16_data


def run_mission16_medium_report_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 16.'

    return _build_mission16_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )



def _mission17_environment_status(reactions):
    """Evaluate the medium perturbation required for Mission 17.

    The player must close exactly one candidate medium component, and the
    intended component is phosphate. This teaches that growth depends on
    essential nutrients, not only on carbon sources or oxygen.
    """
    reaction_values = list(reactions.values())
    closed_candidate_nutrients = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
            if lower_changed and not lower_bound_open:
                closed_candidate_nutrients.append(reaction_id)
            elif lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return closed_candidate_nutrients, unexpected_changes


def _build_mission17_data(method_name, selected_objective, objective_result, genes, reactions, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    method_correct = method_name == MISSION17_METHOD
    objective_correct = selected_objective == MISSION17_GROWTH_OBJECTIVE

    objective_value = _as_float_or_none(objective_result)
    if objective_value is None and str(objective_result) == 'Status: INFEASIBLE':
        growth_value = 0.0
        result_available = True
        infeasible = True
    else:
        growth_value = _numeric_result(objective_value)
        result_available = objective_value is not None
        infeasible = False

    growth_collapsed = result_available and growth_value <= MISSION17_MAX_GROWTH

    closed_candidate_nutrients, unexpected_environment_changes = _mission17_environment_status(reactions)
    exactly_one_candidate_closed = len(closed_candidate_nutrients) == 1
    selected_nutrient = closed_candidate_nutrients[0] if exactly_one_candidate_closed else None
    target_nutrient_closed = selected_nutrient == MISSION17_TARGET_NUTRIENT

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    target_uptake = uptake_fluxes.get(MISSION17_TARGET_NUTRIENT, 0.0)
    target_uptake_blocked = target_nutrient_closed and target_uptake <= 0.001

    mission17_data = {
        'mission_id': '17',
        'check_version': 1,
        'mission_title': 'Essential Medium Component',
        'target_context': MISSION17_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION17_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION17_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'simulation_infeasible': infeasible,
        'target_nutrient': MISSION17_TARGET_NUTRIENT,
        'target_nutrient_name': MISSION17_TARGET_NUTRIENT_NAME,
        'candidate_nutrients': MISSION17_CANDIDATE_NUTRIENTS,
        'closed_candidate_nutrients': closed_candidate_nutrients,
        'selected_nutrient': selected_nutrient,
        'exactly_one_candidate_closed': exactly_one_candidate_closed,
        'target_nutrient_closed': target_nutrient_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_raw_fluxes': {reaction_id: round(value, 3) for reaction_id, value in raw_fluxes.items()},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'target_nutrient_uptake': round(target_uptake, 3),
        'target_uptake_blocked': target_uptake_blocked,
        'maximum_growth_after_removal': MISSION17_MAX_GROWTH,
        'growth_collapsed': growth_collapsed,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and exactly_one_candidate_closed
            and target_nutrient_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and growth_collapsed
            and result_available
        ),
    }
    if objective_error:
        mission17_data['error'] = objective_error
    save_mission17_essential_medium_check(mission17_data)
    return mission17_data


def run_mission17_essential_medium_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 17.'

    return _build_mission17_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )


def _mission18_environment_status(reactions):
    """Evaluate the export-bottleneck setup required for Mission 18.

    The player must remove glucose uptake, open pyruvate uptake and close
    acetate export. This teaches that exchange bounds affect both import and
    export, and that upper bounds can create secretion bottlenecks.
    """
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    pyruvate_lower_bound_open = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION18_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION18_ALTERNATIVE_CARBON_SOURCE:
            pyruvate_lower_bound_open = lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION18_EXPORT_BOTTLENECK:
            acetate_upper_bound_closed = not upper_bound_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_changes,
    )


def _build_mission18_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    production_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION18_METHOD
    objective_correct = selected_objective == MISSION18_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    growth_ok = result_available and growth_value >= MISSION18_MIN_GROWTH

    (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_environment_changes,
    ) = _mission18_environment_status(reactions)

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    glucose_uptake = uptake_fluxes.get(MISSION18_BLOCKED_CARBON_SOURCE, 0.0)
    pyruvate_uptake = uptake_fluxes.get(MISSION18_ALTERNATIVE_CARBON_SOURCE, 0.0)
    acetate_medium_secretion = secretion_fluxes.get(MISSION18_EXPORT_BOTTLENECK, 0.0)
    acetate_production_flux = production_values.get(MISSION18_EXPORT_BOTTLENECK, 0.0)

    glucose_uptake_blocked = glucose_uptake <= MISSION18_MIN_SOURCE_UPTAKE
    pyruvate_uptake_detected = pyruvate_uptake >= MISSION18_MIN_SOURCE_UPTAKE
    acetate_export_blocked = acetate_upper_bound_closed and acetate_production_flux <= MISSION18_MAX_BLOCKED_EXPORT_FLUX

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    mission18_data = {
        'mission_id': '18',
        'check_version': 1,
        'mission_title': 'Export Bottleneck',
        'target_context': MISSION18_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION18_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION18_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'blocked_carbon_source': MISSION18_BLOCKED_CARBON_SOURCE,
        'alternative_carbon_source': MISSION18_ALTERNATIVE_CARBON_SOURCE,
        'export_bottleneck': MISSION18_EXPORT_BOTTLENECK,
        'export_bottleneck_name': MISSION18_EXPORT_BOTTLENECK_NAME,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'pyruvate_lower_bound_open': pyruvate_lower_bound_open,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'glucose_uptake': round(glucose_uptake, 3),
        'pyruvate_uptake': round(pyruvate_uptake, 3),
        'acetate_medium_secretion': round(acetate_medium_secretion, 3),
        'minimum_source_uptake': MISSION18_MIN_SOURCE_UPTAKE,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'pyruvate_uptake_detected': pyruvate_uptake_detected,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in production_values.items()},
        'required_tracked_fluxes': MISSION18_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'acetate_production_flux': round(acetate_production_flux, 3),
        'maximum_blocked_export_flux': MISSION18_MAX_BLOCKED_EXPORT_FLUX,
        'acetate_export_blocked': acetate_export_blocked,
        'minimum_growth': MISSION18_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and pyruvate_lower_bound_open
            and pyruvate_uptake_detected
            and acetate_upper_bound_closed
            and acetate_export_blocked
            and not unexpected_environment_changes
            and not knocked_out_genes
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission18_data['error'] = objective_error
    save_mission18_export_bottleneck_check(mission18_data)
    return mission18_data


def run_mission18_export_bottleneck_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 18.'

    return _build_mission18_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )



def _build_mission19_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, biomass_flux=None, objective_error=None):
    """Evaluate Mission 19: lMOMA response to a single gene perturbation."""
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION19_TARGET_METHOD
    objective_correct = selected_objective == MISSION19_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    biomass_flux_value = _as_float_or_none(biomass_flux)
    result_available = objective_value is not None

    # lMOMA minimises a perturbation-distance objective. The printed objective
    # result can therefore be 0 even when the biomass reaction still carries
    # flux. For viability, use the actual biomass flux from the solution when
    # it is available.
    if biomass_flux_value is not None:
        growth_value = _numeric_result(biomass_flux_value)
        growth_measure = 'biomass flux from lMOMA solution'
    else:
        growth_value = _numeric_result(objective_value)
        growth_measure = 'objective result'

    growth_ok = result_available and growth_value >= MISSION19_MIN_GROWTH

    environment_changed = _environment_has_changes(reactions)
    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION19_TARGET_GENE]

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    mission19_data = {
        'mission_id': '19',
        'check_version': 2,
        'mission_title': 'Perturbation Method Challenge',
        'target_context': MISSION19_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION19_TARGET_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION19_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(_numeric_result(objective_value), 3) if objective_value is not None else str(objective_result),
        'biomass_flux': round(growth_value, 3) if result_available else None,
        'growth_measure': growth_measure,
        'candidate_genes': MISSION19_CANDIDATE_GENES,
        'target_gene': MISSION19_TARGET_GENE,
        'target_gene_name': MISSION19_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'environment_changed': environment_changed,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION19_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'minimum_growth': MISSION19_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and exact_one_knockout
            and target_gene_found
            and not environment_changed
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission19_data['error'] = objective_error
    save_mission19_perturbation_check(mission19_data)
    return mission19_data


def run_mission19_perturbation_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    biomass_flux = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
    except Exception:
        objective_result = None

    try:
        biomass_flux = _simulate_local_reaction_flux(
            method_name,
            selected_objective,
            genes,
            reactions,
            MISSION19_GROWTH_OBJECTIVE,
        )
    except Exception:
        biomass_flux = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 19.'

    return _build_mission19_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        biomass_flux=biomass_flux,
        objective_error=objective_error,
    )


def _mission20_environment_status(reactions):
    """Evaluate the medium/stress setup required for Mission 20."""
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    pyruvate_lower_bound_open = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION20_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION20_ALTERNATIVE_CARBON_SOURCE:
            pyruvate_lower_bound_open = lower_bound_open
            if not lower_changed or not lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION20_EXPORT_BOTTLENECK:
            acetate_upper_bound_closed = not upper_bound_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_changes,
    )


def _build_mission20_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, medium_fluxes=None, objective_error=None):
    """Evaluate Mission 20: final medium robustness report."""
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    production_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION20_TARGET_METHOD
    objective_correct = selected_objective == MISSION20_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    growth_ok = result_available and growth_value >= MISSION20_MIN_GROWTH

    (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_environment_changes,
    ) = _mission20_environment_status(reactions)

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    glucose_uptake = uptake_fluxes.get(MISSION20_BLOCKED_CARBON_SOURCE, 0.0)
    pyruvate_uptake = uptake_fluxes.get(MISSION20_ALTERNATIVE_CARBON_SOURCE, 0.0)
    acetate_medium_secretion = secretion_fluxes.get(MISSION20_EXPORT_BOTTLENECK, 0.0)
    acetate_production_flux = production_values.get(MISSION20_EXPORT_BOTTLENECK, 0.0)

    glucose_uptake_blocked = glucose_uptake <= MISSION20_MIN_SOURCE_UPTAKE
    pyruvate_uptake_detected = pyruvate_uptake >= MISSION20_MIN_SOURCE_UPTAKE
    acetate_export_blocked = acetate_upper_bound_closed and acetate_production_flux <= MISSION20_MAX_BLOCKED_EXPORT_FLUX

    essential_uptake_values = {
        reaction_id: uptake_fluxes.get(reaction_id, 0.0)
        for reaction_id in MISSION20_REQUIRED_ESSENTIAL_UPTAKES
    }
    missing_essential_uptakes = [
        reaction_id
        for reaction_id, value in essential_uptake_values.items()
        if value < MISSION20_MIN_ESSENTIAL_UPTAKE
    ]
    essential_uptake_ready = not missing_essential_uptakes

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    tracked_byproduct_values = {
        reaction_id: round(production_values.get(reaction_id, 0.0), 3)
        for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
    }
    positive_tracked_products = [
        reaction_id
        for reaction_id, value in tracked_byproduct_values.items()
        if value > 0.001
    ]

    mission20_data = {
        'mission_id': '20',
        'check_version': 1,
        'mission_title': 'Final Medium Robustness Report',
        'target_context': MISSION20_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION20_TARGET_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION20_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'blocked_carbon_source': MISSION20_BLOCKED_CARBON_SOURCE,
        'alternative_carbon_source': MISSION20_ALTERNATIVE_CARBON_SOURCE,
        'export_bottleneck': MISSION20_EXPORT_BOTTLENECK,
        'export_bottleneck_name': MISSION20_EXPORT_BOTTLENECK_NAME,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'pyruvate_lower_bound_open': pyruvate_lower_bound_open,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'glucose_uptake': round(glucose_uptake, 3),
        'pyruvate_uptake': round(pyruvate_uptake, 3),
        'acetate_medium_secretion': round(acetate_medium_secretion, 3),
        'essential_uptake_values': {reaction_id: round(value, 3) for reaction_id, value in essential_uptake_values.items()},
        'required_essential_uptakes': MISSION20_REQUIRED_ESSENTIAL_UPTAKES,
        'missing_essential_uptakes': missing_essential_uptakes,
        'essential_uptake_ready': essential_uptake_ready,
        'minimum_source_uptake': MISSION20_MIN_SOURCE_UPTAKE,
        'minimum_essential_uptake': MISSION20_MIN_ESSENTIAL_UPTAKE,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'pyruvate_uptake_detected': pyruvate_uptake_detected,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': tracked_byproduct_values,
        'positive_tracked_products': positive_tracked_products,
        'required_tracked_fluxes': MISSION20_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'acetate_production_flux': round(acetate_production_flux, 3),
        'maximum_blocked_export_flux': MISSION20_MAX_BLOCKED_EXPORT_FLUX,
        'acetate_export_blocked': acetate_export_blocked,
        'minimum_growth': MISSION20_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and pyruvate_lower_bound_open
            and pyruvate_uptake_detected
            and acetate_upper_bound_closed
            and acetate_export_blocked
            and essential_uptake_ready
            and not unexpected_environment_changes
            and not knocked_out_genes
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission20_data['error'] = objective_error
    save_mission20_robustness_report_check(mission20_data)
    return mission20_data


def run_mission20_robustness_report_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 20.'

    return _build_mission20_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
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
    results, production_fluxes, medium_fluxes = _simulate_local_objective_with_production_fluxes(
        method_name,
        objective_name,
        genes,
        reactions,
        selected_fluxes,
    )
    return objective_name, results, production_fluxes, medium_fluxes


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
        ), _build_medium_flux_data(
            error=f'Backend error: {e}'
        )

    if response.get('status') == 'ok':
        fluxes = response.get('fluxes') or {}
        flux_getter = lambda reaction_id: fluxes.get(reaction_id)
        return response['objective'], response['result'], _build_production_flux_data(
            selected_fluxes,
            flux_getter=flux_getter
        ), _build_medium_flux_data(
            flux_getter=flux_getter
        )
    if response.get('status') == 'infeasible':
        return response['objective'], 'Status: INFEASIBLE', _build_production_flux_data(
            selected_fluxes,
            error='Simulation infeasible. Production fluxes could not be measured.'
        ), _build_medium_flux_data(
            error='Simulation infeasible. Medium fluxes could not be measured.'
        )
    return (
        response.get('objective', payload['objective']),
        f'Error: {response.get("message", "unknown")}',
        _build_production_flux_data(
            selected_fluxes,
            error=response.get('message', 'unknown backend error')
        ),
        _build_medium_flux_data(
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
