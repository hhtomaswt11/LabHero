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

VILLAIN_SCORE = 14000.0


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
    method, objective, genes, reactions = data_simul

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


def _build_challenge_data(growth, production_flux, error=None):
    growth_value = _numeric_result(growth)
    production_value = _numeric_result(production_flux)
    score = round(growth_value * production_value, 3)

    challenge_data = {
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
    results = _simulate_local_objective(method_name, objective_name, genes, reactions)
    return objective_name, results


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
    try:
        response = _http_post_json(backend_url.rstrip('/') + '/simulate', payload)
    except Exception as e:
        return payload['objective'], f'Error: {e}'

    if response.get('status') == 'ok':
        return response['objective'], response['result']
    if response.get('status') == 'infeasible':
        return response['objective'], 'Status: INFEASIBLE'
    return response.get('objective', payload['objective']), f'Error: {response.get("message", "unknown")}'



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
