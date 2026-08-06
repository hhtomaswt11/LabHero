import json
import os
import sys
import copy

from utils import *
from settings import DEFAULT_PLAYER_STATE

_IS_WEB = sys.platform == 'emscripten'
_MEMSTORE = {}


def _memkey(filename):
    return os.path.basename(filename)


def _default_player_state():
    return copy.deepcopy(DEFAULT_PLAYER_STATE)





def _delete_save_artifact(mem_key, filename):
    """Remove a mission-specific simulation/check artifact.

    Mission delivery checks are stored separately from the main player save.
    When a mission is activated, its old check file must be cleared so the
    player cannot deliver stale results from an earlier attempt/session.
    """
    if _IS_WEB:
        _MEMSTORE.pop(mem_key, None)
        return
    try:
        os.remove(get_save_path(filename))
    except FileNotFoundError:
        pass
    except Exception:
        pass

def _read_existing_player_state():
    """Return the player_state from the current save, when available.

    This keeps backwards compatibility with older calls to save_file that may
    still send the old 4-field save format.
    """
    try:
        if _IS_WEB:
            existing = _MEMSTORE.get('data')
        else:
            with open(get_save_path('data.txt')) as test_file:
                existing = json.load(test_file)

        if isinstance(existing, list) and len(existing) >= 5 and isinstance(existing[4], dict):
            return existing[4]
    except Exception:
        pass
    return _default_player_state()


def normalize_save_data(data):
    """Normalize save data to the current schema.

    Current schema:
    [player_name, results, missions_activated, missions_completed, player_state]

    Older saves only had the first 4 fields. They still load correctly; in that
    case the player_state falls back to the default spawn state.
    """
    if not isinstance(data, list):
        return data

    normalized = list(data)

    while len(normalized) < 4:
        normalized.append([])

    if len(normalized) < 5 or not isinstance(normalized[4], dict):
        normalized = normalized[:4] + [_read_existing_player_state()]

    return normalized


def save_file(data):
    data = normalize_save_data(data)
    if _IS_WEB:
        _MEMSTORE['data'] = data
        return
    with open(get_save_path('data.txt'), 'w') as test_file:
        json.dump(data, test_file)


def load_file(filename):
    if _IS_WEB:
        key = _memkey(filename)
        if key in _MEMSTORE:
            return normalize_save_data(_MEMSTORE[key])
    with open(f'{filename}.txt') as test_file:
        data = json.load(test_file)
        return normalize_save_data(data)


def save_simulation_file(data):
    if _IS_WEB:
        _MEMSTORE['simulation_file'] = data
        return
    with open(get_save_path('simulation_file.txt'), 'w') as test_file:
        json.dump(data, test_file)


def clear_memstore():
    if _IS_WEB:
        _MEMSTORE.clear()


def save_results(data):
    if _IS_WEB:
        old = _MEMSTORE.get('results')
        try:
            _MEMSTORE['results'] = data + '\n' + '\n' + old if old else data
        except Exception:
            _MEMSTORE['results'] = data
        return
    try:
        results = open(get_save_path('results.txt'), 'r')
        old_data = json.load(results)
        data = data + '\n' + '\n' + old_data
        results.close()
    except:
        pass
    with open(get_save_path('results.txt'), 'w') as results_file:
        json.dump(data, results_file)
        results_file.close()


def save_challenge_score(data):
    if _IS_WEB:
        _MEMSTORE['challenge_score'] = data
        return
    with open(get_save_path('challenge_score.txt'), 'w') as score_file:
        json.dump(data, score_file)


def load_challenge_score():
    if _IS_WEB:
        return _MEMSTORE.get('challenge_score')
    try:
        with open(get_save_path('challenge_score.txt')) as score_file:
            return json.load(score_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None




def save_mission03_gene_screen_check(data):
    """Persist Mission 03 baseline and controlled knockout evidence."""
    if _IS_WEB:
        _MEMSTORE['mission03_gene_screen_check'] = data
        return
    with open(get_save_path('mission03_gene_screen_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission03_gene_screen_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission03_gene_screen_check')
    try:
        with open(get_save_path('mission03_gene_screen_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission03_gene_screen_check():
    _delete_save_artifact('mission03_gene_screen_check', 'mission03_gene_screen_check.txt')


def save_mission04_production_check(data):
    if _IS_WEB:
        _MEMSTORE['mission04_production_check'] = data
        return
    with open(get_save_path('mission04_production_check.txt'), 'w') as production_file:
        json.dump(data, production_file)


def load_mission04_production_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission04_production_check')
    try:
        with open(get_save_path('mission04_production_check.txt')) as production_file:
            return json.load(production_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission04_production_check():
    _delete_save_artifact('mission04_production_check', 'mission04_production_check.txt')


def save_mission05_production_check(data):
    if _IS_WEB:
        _MEMSTORE['mission05_production_check'] = data
        return
    with open(get_save_path('mission05_production_check.txt'), 'w') as production_file:
        json.dump(data, production_file)


def load_mission05_production_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission05_production_check')
    try:
        with open(get_save_path('mission05_production_check.txt')) as production_file:
            return json.load(production_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None

def clear_mission05_production_check():
    _delete_save_artifact('mission05_production_check', 'mission05_production_check.txt')


def save_mission07_objective_check(data):
    if _IS_WEB:
        _MEMSTORE['mission07_objective_check'] = data
        return
    with open(get_save_path('mission07_objective_check.txt'), 'w') as objective_file:
        json.dump(data, objective_file)


def load_mission07_objective_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission07_objective_check')
    try:
        with open(get_save_path('mission07_objective_check.txt')) as objective_file:
            return json.load(objective_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission08_constraint_check(data):
    if _IS_WEB:
        _MEMSTORE['mission08_constraint_check'] = data
        return
    with open(get_save_path('mission08_constraint_check.txt'), 'w') as objective_file:
        json.dump(data, objective_file)


def load_mission08_constraint_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission08_constraint_check')
    try:
        with open(get_save_path('mission08_constraint_check.txt')) as objective_file:
            return json.load(objective_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None

def save_mission09_design_check(data):
    if _IS_WEB:
        _MEMSTORE['mission09_design_check'] = data
        return
    with open(get_save_path('mission09_design_check.txt'), 'w') as design_file:
        json.dump(data, design_file)


def load_mission09_design_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission09_design_check')
    try:
        with open(get_save_path('mission09_design_check.txt')) as design_file:
            return json.load(design_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission10_robust_design_check(data):
    if _IS_WEB:
        _MEMSTORE['mission10_robust_design_check'] = data
        return
    with open(get_save_path('mission10_robust_design_check.txt'), 'w') as design_file:
        json.dump(data, design_file)


def load_mission10_robust_design_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission10_robust_design_check')
    try:
        with open(get_save_path('mission10_robust_design_check.txt')) as design_file:
            return json.load(design_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission11_flux_fingerprint_check(data):
    if _IS_WEB:
        _MEMSTORE['mission11_flux_fingerprint_check'] = data
        return
    with open(get_save_path('mission11_flux_fingerprint_check.txt'), 'w') as fingerprint_file:
        json.dump(data, fingerprint_file)


def load_mission11_flux_fingerprint_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission11_flux_fingerprint_check')
    try:
        with open(get_save_path('mission11_flux_fingerprint_check.txt')) as fingerprint_file:
            return json.load(fingerprint_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission12_byproduct_check(data):
    if _IS_WEB:
        _MEMSTORE['mission12_byproduct_check'] = data
        return
    with open(get_save_path('mission12_byproduct_check.txt'), 'w') as byproduct_file:
        json.dump(data, byproduct_file)


def load_mission12_byproduct_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission12_byproduct_check')
    try:
        with open(get_save_path('mission12_byproduct_check.txt')) as byproduct_file:
            return json.load(byproduct_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission13_method_check(data):
    if _IS_WEB:
        _MEMSTORE['mission13_method_check'] = data
        return
    with open(get_save_path('mission13_method_check.txt'), 'w') as method_file:
        json.dump(data, method_file)


def load_mission13_method_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission13_method_check')
    try:
        with open(get_save_path('mission13_method_check.txt')) as method_file:
            return json.load(method_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None



def save_mission14_reduction_check(data):
    if _IS_WEB:
        _MEMSTORE['mission14_reduction_check'] = data
        return
    with open(get_save_path('mission14_reduction_check.txt'), 'w') as reduction_file:
        json.dump(data, reduction_file)


def load_mission14_reduction_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission14_reduction_check')
    try:
        with open(get_save_path('mission14_reduction_check.txt')) as reduction_file:
            return json.load(reduction_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission15_diagnostic_report_check(data):
    if _IS_WEB:
        _MEMSTORE['mission15_diagnostic_report_check'] = data
        return
    with open(get_save_path('mission15_diagnostic_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission15_diagnostic_report_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission15_diagnostic_report_check')
    try:
        with open(get_save_path('mission15_diagnostic_report_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None



def save_mission16_medium_report_check(data):
    if _IS_WEB:
        _MEMSTORE['mission16_medium_report_check'] = data
        return
    with open(get_save_path('mission16_medium_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission16_medium_report_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission16_medium_report_check')
    try:
        with open(get_save_path('mission16_medium_report_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission17_essential_medium_check(data):
    if _IS_WEB:
        _MEMSTORE['mission17_essential_medium_check'] = data
        return
    with open(get_save_path('mission17_essential_medium_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission17_essential_medium_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission17_essential_medium_check')
    try:
        with open(get_save_path('mission17_essential_medium_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission18_export_bottleneck_check(data):
    if _IS_WEB:
        _MEMSTORE['mission18_export_bottleneck_check'] = data
        return
    with open(get_save_path('mission18_export_bottleneck_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission18_export_bottleneck_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission18_export_bottleneck_check')
    try:
        with open(get_save_path('mission18_export_bottleneck_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission19_perturbation_check(data):
    if _IS_WEB:
        _MEMSTORE['mission19_perturbation_check'] = data
        return
    with open(get_save_path('mission19_perturbation_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission19_perturbation_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission19_perturbation_check')
    try:
        with open(get_save_path('mission19_perturbation_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_challenge_score():
    _delete_save_artifact('challenge_score', 'challenge_score.txt')


def clear_mission07_objective_check():
    _delete_save_artifact('mission07_objective_check', 'mission07_objective_check.txt')


def clear_mission08_constraint_check():
    _delete_save_artifact('mission08_constraint_check', 'mission08_constraint_check.txt')


def clear_mission09_design_check():
    _delete_save_artifact('mission09_design_check', 'mission09_design_check.txt')


def clear_mission10_robust_design_check():
    _delete_save_artifact('mission10_robust_design_check', 'mission10_robust_design_check.txt')


def clear_mission11_flux_fingerprint_check():
    _delete_save_artifact('mission11_flux_fingerprint_check', 'mission11_flux_fingerprint_check.txt')


def clear_mission12_byproduct_check():
    _delete_save_artifact('mission12_byproduct_check', 'mission12_byproduct_check.txt')


def clear_mission13_method_check():
    _delete_save_artifact('mission13_method_check', 'mission13_method_check.txt')


def clear_mission14_reduction_check():
    _delete_save_artifact('mission14_reduction_check', 'mission14_reduction_check.txt')


def clear_mission15_diagnostic_report_check():
    _delete_save_artifact('mission15_diagnostic_report_check', 'mission15_diagnostic_report_check.txt')


def clear_mission16_medium_report_check():
    _delete_save_artifact('mission16_medium_report_check', 'mission16_medium_report_check.txt')


def clear_mission17_essential_medium_check():
    _delete_save_artifact('mission17_essential_medium_check', 'mission17_essential_medium_check.txt')



def clear_mission18_export_bottleneck_check():
    _delete_save_artifact('mission18_export_bottleneck_check', 'mission18_export_bottleneck_check.txt')


def clear_mission19_perturbation_check():
    _delete_save_artifact('mission19_perturbation_check', 'mission19_perturbation_check.txt')



def save_mission20_robustness_report_check(data):
    if _IS_WEB:
        _MEMSTORE['mission20_robustness_report_check'] = data
        return
    with open(get_save_path('mission20_robustness_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission20_robustness_report_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission20_robustness_report_check')
    try:
        with open(get_save_path('mission20_robustness_report_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission20_robustness_report_check():
    _delete_save_artifact('mission20_robustness_report_check', 'mission20_robustness_report_check.txt')


def save_mission02_source_comparison_check(data):
    """Persist Mission 02 controlled carbon-source trial evidence."""
    if _IS_WEB:
        _MEMSTORE['mission02_source_comparison_check'] = data
        return
    with open(get_save_path('mission02_source_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission02_source_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission02_source_comparison_check')
    try:
        with open(get_save_path('mission02_source_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission02_source_comparison_check():
    _delete_save_artifact(
        'mission02_source_comparison_check',
        'mission02_source_comparison_check.txt',
    )


def save_mission01_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission01_comparison_check'] = data
        return
    with open(get_save_path('mission01_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission01_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission01_comparison_check')
    try:
        with open(get_save_path('mission01_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission01_comparison_check():
    _delete_save_artifact('mission01_comparison_check', 'mission01_comparison_check.txt')


def save_compare_runs(data):
    """Store the two runs used by the Compare Runs report.

    Schema:
    {
        'run_a': snapshot or None,
        'run_b': snapshot or None,
    }
    """
    if _IS_WEB:
        _MEMSTORE['compare_runs'] = data
        return
    with open(get_save_path('compare_runs.txt'), 'w') as compare_file:
        json.dump(data, compare_file)


def load_compare_runs():
    if _IS_WEB:
        return _MEMSTORE.get('compare_runs')
    try:
        with open(get_save_path('compare_runs.txt')) as compare_file:
            return json.load(compare_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_compare_runs():
    _delete_save_artifact('compare_runs', 'compare_runs.txt')


def save_mission21_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission21_comparison_check'] = data
        return
    with open(get_save_path('mission21_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission21_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission21_comparison_check')
    try:
        with open(get_save_path('mission21_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission21_comparison_check():
    _delete_save_artifact('mission21_comparison_check', 'mission21_comparison_check.txt')




def save_mission22_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission22_comparison_check'] = data
        return
    with open(get_save_path('mission22_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission22_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission22_comparison_check')
    try:
        with open(get_save_path('mission22_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission22_comparison_check():
    _delete_save_artifact('mission22_comparison_check', 'mission22_comparison_check.txt')


def save_mission23_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission23_comparison_check'] = data
        return
    with open(get_save_path('mission23_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission23_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission23_comparison_check')
    try:
        with open(get_save_path('mission23_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission23_comparison_check():
    _delete_save_artifact('mission23_comparison_check', 'mission23_comparison_check.txt')


def save_mission24_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission24_comparison_check'] = data
        return
    with open(get_save_path('mission24_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission24_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission24_comparison_check')
    try:
        with open(get_save_path('mission24_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission24_comparison_check():
    _delete_save_artifact('mission24_comparison_check', 'mission24_comparison_check.txt')


def save_mission25_comparison_check(data):
    if _IS_WEB:
        _MEMSTORE['mission25_comparison_check'] = data
        return
    with open(get_save_path('mission25_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission25_comparison_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission25_comparison_check')
    try:
        with open(get_save_path('mission25_comparison_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission25_comparison_check():
    _delete_save_artifact('mission25_comparison_check', 'mission25_comparison_check.txt')




def save_bound_sweep(data):
    if _IS_WEB:
        _MEMSTORE['bound_sweep'] = data
        return
    with open(get_save_path('bound_sweep.txt'), 'w') as sweep_file:
        json.dump(data, sweep_file)


def load_bound_sweep():
    if _IS_WEB:
        return _MEMSTORE.get('bound_sweep')
    try:
        with open(get_save_path('bound_sweep.txt')) as sweep_file:
            return json.load(sweep_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_bound_sweep():
    _delete_save_artifact('bound_sweep', 'bound_sweep.txt')


def save_mission26_bound_sweep_check(data):
    if _IS_WEB:
        _MEMSTORE['mission26_bound_sweep_check'] = data
        return
    with open(get_save_path('mission26_bound_sweep_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission26_bound_sweep_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission26_bound_sweep_check')
    try:
        with open(get_save_path('mission26_bound_sweep_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission26_bound_sweep_check():
    _delete_save_artifact('mission26_bound_sweep_check', 'mission26_bound_sweep_check.txt')


def save_mission27_rescue_check(data):
    if _IS_WEB:
        _MEMSTORE['mission27_rescue_check'] = data
        return
    with open(get_save_path('mission27_rescue_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission27_rescue_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission27_rescue_check')
    try:
        with open(get_save_path('mission27_rescue_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission27_rescue_check():
    _delete_save_artifact('mission27_rescue_check', 'mission27_rescue_check.txt')


# Backwards-compatible helpers retained for stale imports and old activation
# code. The redesigned Mission 27 no longer stores Bound Sweep evidence.
def save_mission27_bound_sweep_check(data):
    save_mission27_rescue_check(data)


def load_mission27_bound_sweep_check():
    return load_mission27_rescue_check()


def clear_mission27_bound_sweep_check():
    clear_mission27_rescue_check()
    _delete_save_artifact('mission27_bound_sweep_check', 'mission27_bound_sweep_check.txt')



def save_mission28_dependency_check(data):
    if _IS_WEB:
        _MEMSTORE['mission28_dependency_check'] = data
        return
    with open(get_save_path('mission28_dependency_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission28_dependency_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission28_dependency_check')
    try:
        with open(get_save_path('mission28_dependency_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission28_dependency_check():
    _delete_save_artifact('mission28_dependency_check', 'mission28_dependency_check.txt')
    _delete_save_artifact('mission28_bound_sweep_check', 'mission28_bound_sweep_check.txt')


# Backwards-compatible helpers retained for stale imports. Mission 28 no
# longer uses Bound Sweep evidence.
def save_mission28_bound_sweep_check(data):
    save_mission28_dependency_check(data)


def load_mission28_bound_sweep_check():
    return load_mission28_dependency_check()


def clear_mission28_bound_sweep_check():
    clear_mission28_dependency_check()


def save_mission29_redundancy_check(data):
    if _IS_WEB:
        _MEMSTORE['mission29_redundancy_check'] = data
        return
    with open(get_save_path('mission29_redundancy_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission29_redundancy_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission29_redundancy_check')
    try:
        with open(get_save_path('mission29_redundancy_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission29_redundancy_check():
    _delete_save_artifact('mission29_redundancy_check', 'mission29_redundancy_check.txt')


def save_mission30_redundancy_threshold_check(data):
    if _IS_WEB:
        _MEMSTORE['mission30_redundancy_threshold_check'] = data
        return
    with open(get_save_path('mission30_redundancy_threshold_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission30_redundancy_threshold_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission30_redundancy_threshold_check')
    try:
        with open(get_save_path('mission30_redundancy_threshold_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission30_redundancy_threshold_check():
    _delete_save_artifact(
        'mission30_redundancy_threshold_check',
        'mission30_redundancy_threshold_check.txt',
    )


def save_mission31_environmental_suppression_check(data):
    if _IS_WEB:
        _MEMSTORE['mission31_environmental_suppression_check'] = data
        return
    with open(get_save_path('mission31_environmental_suppression_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission31_environmental_suppression_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission31_environmental_suppression_check')
    try:
        with open(get_save_path('mission31_environmental_suppression_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission31_environmental_suppression_check():
    _delete_save_artifact(
        'mission31_environmental_suppression_check',
        'mission31_environmental_suppression_check.txt',
    )


def save_mission32_respiratory_cut_set_check(data):
    if _IS_WEB:
        _MEMSTORE['mission32_respiratory_cut_set_check'] = data
        return
    with open(get_save_path('mission32_respiratory_cut_set_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission32_respiratory_cut_set_check():
    if _IS_WEB:
        return _MEMSTORE.get('mission32_respiratory_cut_set_check')
    try:
        with open(get_save_path('mission32_respiratory_cut_set_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission32_respiratory_cut_set_check():
    _delete_save_artifact(
        'mission32_respiratory_cut_set_check',
        'mission32_respiratory_cut_set_check.txt',
    )
