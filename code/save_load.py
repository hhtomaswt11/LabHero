import json
import os
import sys
import copy

from utils import *
from settings import DEFAULT_PLAYER_STATE
from hint_system import create_reward_state, normalize_reward_state

_IS_WEB = sys.platform == 'emscripten'
_MEMSTORE = {}

# Browser persistence is namespaced so LabHero never clears unrelated
# localStorage data belonging to the same university origin.  _MEMSTORE remains
# as a hot in-session cache and as a graceful fallback if browser storage is
# unavailable (privacy mode/quota/browser policy).
_WEB_STORAGE_PREFIX = 'labhero:v1:'
_WEB_STORAGE_WARNING_EMITTED = False


def _browser_local_storage():
    """Return the browser localStorage object on the Pygbag runtime, or None.

    Pygbag exposes browser globals through ``platform.window``.  That is the
    runtime's documented persistence path.  A ``js`` fallback is kept only for
    compatibility with alternate Emscripten/Pyodide environments.
    """
    if not _IS_WEB:
        return None

    try:
        from platform import window
        return window.localStorage
    except Exception:
        pass

    try:
        import js
        window = getattr(js, 'window', js)
        return window.localStorage
    except Exception:
        return None


def _web_storage_key(mem_key):
    return f'{_WEB_STORAGE_PREFIX}{mem_key}'


def _warn_web_storage_once(operation, error):
    global _WEB_STORAGE_WARNING_EMITTED
    if _WEB_STORAGE_WARNING_EMITTED:
        return
    _WEB_STORAGE_WARNING_EMITTED = True
    print(
        f'[LabHero save] Browser localStorage {operation} failed; '
        f'using in-memory fallback for this session: {error}',
        flush=True,
    )


def _web_store_set(mem_key, data):
    """Write JSON-serialisable data to RAM and durable browser storage."""
    _MEMSTORE[mem_key] = copy.deepcopy(data)
    storage = _browser_local_storage()
    if storage is None:
        return
    try:
        storage.setItem(_web_storage_key(mem_key), json.dumps(data))
    except Exception as exc:
        _warn_web_storage_once('write', exc)


def _web_store_get(mem_key):
    """Read from RAM first, then hydrate RAM from localStorage after reload."""
    if mem_key in _MEMSTORE:
        return copy.deepcopy(_MEMSTORE[mem_key])

    storage = _browser_local_storage()
    if storage is None:
        return None
    try:
        raw = storage.getItem(_web_storage_key(mem_key))
        if raw is None:
            return None
        data = json.loads(str(raw))
        _MEMSTORE[mem_key] = copy.deepcopy(data)
        return data
    except Exception as exc:
        _warn_web_storage_once('read', exc)
        return None


def _web_store_delete(mem_key):
    """Delete one artifact from both the session cache and localStorage."""
    _MEMSTORE.pop(mem_key, None)
    storage = _browser_local_storage()
    if storage is None:
        return
    try:
        storage.removeItem(_web_storage_key(mem_key))
    except Exception as exc:
        _warn_web_storage_once('delete', exc)


def clear_web_persistent_storage():
    """Erase only LabHero browser saves/artifacts (used by explicit New Game)."""
    _MEMSTORE.clear()
    storage = _browser_local_storage()
    if storage is None:
        return
    try:
        keys_to_remove = []
        for index in range(int(storage.length)):
            key = storage.key(index)
            if key is not None and str(key).startswith(_WEB_STORAGE_PREFIX):
                keys_to_remove.append(str(key))
        for key in keys_to_remove:
            storage.removeItem(key)
    except Exception as exc:
        _warn_web_storage_once('clear', exc)


def get_web_storage_status():
    """Small diagnostics payload used by tests/manual browser validation."""
    storage = _browser_local_storage()
    return {
        'is_web': bool(_IS_WEB),
        'local_storage_available': storage is not None,
        'cached_keys': sorted(_MEMSTORE),
        'namespace': _WEB_STORAGE_PREFIX,
    }


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
        _web_store_delete(mem_key)
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
            existing = _web_store_get('data')
        else:
            with open(get_save_path('data.txt')) as test_file:
                existing = json.load(test_file)

        if isinstance(existing, list) and len(existing) >= 5 and isinstance(existing[4], dict):
            return existing[4]
    except Exception:
        pass
    return _default_player_state()


def _read_existing_reward_state():
    """Return reward_state from the current save, when available.

    This protects the new reward data if any older code path still calls
    save_file with a pre-P.1 payload.
    """
    try:
        if _IS_WEB:
            existing = _web_store_get('data')
        else:
            with open(get_save_path('data.txt')) as test_file:
                existing = json.load(test_file)

        if isinstance(existing, list) and len(existing) >= 6 and isinstance(existing[5], dict):
            return existing[5]
    except Exception:
        pass
    return None


def normalize_save_data(data, reward_state_fallback=None):
    """Normalize save data to the current schema.

    Current schema:
    [player_name, results, missions_activated, missions_completed,
     player_state, reward_state]

    Saves predating P.1 may have only 4 or 5 fields. Their existing completed
    missions are marked as legacy-unscored because historic hint usage cannot
    be reconstructed honestly.
    """
    if not isinstance(data, list):
        return data

    normalized = list(data)

    while len(normalized) < 4:
        normalized.append([])

    if len(normalized) < 5 or not isinstance(normalized[4], dict):
        normalized = normalized[:4] + [_read_existing_player_state()]
    else:
        normalized = normalized[:5] + normalized[5:]

    completed = normalized[3] if isinstance(normalized[3], list) else []

    if len(normalized) < 6 or not isinstance(normalized[5], dict):
        if isinstance(reward_state_fallback, dict):
            reward_state = normalize_reward_state(reward_state_fallback)
        else:
            reward_state = create_reward_state(legacy_completed=completed)
        normalized = normalized[:5] + [reward_state]
    else:
        normalized[5] = normalize_reward_state(normalized[5])

    return normalized[:6]


def save_file(data):
    # All current runtime calls use Player.get_save_data() (6 fields).  The
    # fallback keeps reward progress safe if an older 4/5-field caller survives.
    reward_fallback = None
    if isinstance(data, list) and (len(data) < 6 or not isinstance(data[5], dict)):
        reward_fallback = _read_existing_reward_state()

    data = normalize_save_data(data, reward_state_fallback=reward_fallback)
    if _IS_WEB:
        _web_store_set('data', data)
        return
    with open(get_save_path('data.txt'), 'w') as test_file:
        json.dump(data, test_file)

def load_file(filename):
    if _IS_WEB:
        key = _memkey(filename)
        stored = _web_store_get(key)
        if stored is not None:
            return normalize_save_data(stored)
    with open(f'{filename}.txt') as test_file:
        data = json.load(test_file)
        return normalize_save_data(data)


def save_simulation_file(data):
    if _IS_WEB:
        _web_store_set('simulation_file', data)
        return
    with open(get_save_path('simulation_file.txt'), 'w') as test_file:
        json.dump(data, test_file)


def clear_memstore():
    """Clear only the in-session cache; durable browser data is preserved."""
    if _IS_WEB:
        _MEMSTORE.clear()


def save_results(data):
    if _IS_WEB:
        old = _web_store_get('results')
        try:
            combined = data + '\n' + '\n' + old if old else data
        except Exception:
            combined = data
        _web_store_set('results', combined)
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
        _web_store_set('challenge_score', data)
        return
    with open(get_save_path('challenge_score.txt'), 'w') as score_file:
        json.dump(data, score_file)


def load_challenge_score():
    if _IS_WEB:
        return _web_store_get('challenge_score')
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
        _web_store_set('mission03_gene_screen_check', data)
        return
    with open(get_save_path('mission03_gene_screen_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission03_gene_screen_check():
    if _IS_WEB:
        return _web_store_get('mission03_gene_screen_check')
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
        _web_store_set('mission04_production_check', data)
        return
    with open(get_save_path('mission04_production_check.txt'), 'w') as production_file:
        json.dump(data, production_file)


def load_mission04_production_check():
    if _IS_WEB:
        return _web_store_get('mission04_production_check')
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
        _web_store_set('mission05_production_check', data)
        return
    with open(get_save_path('mission05_production_check.txt'), 'w') as production_file:
        json.dump(data, production_file)


def load_mission05_production_check():
    if _IS_WEB:
        return _web_store_get('mission05_production_check')
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
        _web_store_set('mission07_objective_check', data)
        return
    with open(get_save_path('mission07_objective_check.txt'), 'w') as objective_file:
        json.dump(data, objective_file)


def load_mission07_objective_check():
    if _IS_WEB:
        return _web_store_get('mission07_objective_check')
    try:
        with open(get_save_path('mission07_objective_check.txt')) as objective_file:
            return json.load(objective_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission08_constraint_check(data):
    if _IS_WEB:
        _web_store_set('mission08_constraint_check', data)
        return
    with open(get_save_path('mission08_constraint_check.txt'), 'w') as objective_file:
        json.dump(data, objective_file)


def load_mission08_constraint_check():
    if _IS_WEB:
        return _web_store_get('mission08_constraint_check')
    try:
        with open(get_save_path('mission08_constraint_check.txt')) as objective_file:
            return json.load(objective_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None

def save_mission09_design_check(data):
    if _IS_WEB:
        _web_store_set('mission09_design_check', data)
        return
    with open(get_save_path('mission09_design_check.txt'), 'w') as design_file:
        json.dump(data, design_file)


def load_mission09_design_check():
    if _IS_WEB:
        return _web_store_get('mission09_design_check')
    try:
        with open(get_save_path('mission09_design_check.txt')) as design_file:
            return json.load(design_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission10_robust_design_check(data):
    if _IS_WEB:
        _web_store_set('mission10_robust_design_check', data)
        return
    with open(get_save_path('mission10_robust_design_check.txt'), 'w') as design_file:
        json.dump(data, design_file)


def load_mission10_robust_design_check():
    if _IS_WEB:
        return _web_store_get('mission10_robust_design_check')
    try:
        with open(get_save_path('mission10_robust_design_check.txt')) as design_file:
            return json.load(design_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission11_flux_fingerprint_check(data):
    if _IS_WEB:
        _web_store_set('mission11_flux_fingerprint_check', data)
        return
    with open(get_save_path('mission11_flux_fingerprint_check.txt'), 'w') as fingerprint_file:
        json.dump(data, fingerprint_file)


def load_mission11_flux_fingerprint_check():
    if _IS_WEB:
        return _web_store_get('mission11_flux_fingerprint_check')
    try:
        with open(get_save_path('mission11_flux_fingerprint_check.txt')) as fingerprint_file:
            return json.load(fingerprint_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission12_byproduct_check(data):
    if _IS_WEB:
        _web_store_set('mission12_byproduct_check', data)
        return
    with open(get_save_path('mission12_byproduct_check.txt'), 'w') as byproduct_file:
        json.dump(data, byproduct_file)


def load_mission12_byproduct_check():
    if _IS_WEB:
        return _web_store_get('mission12_byproduct_check')
    try:
        with open(get_save_path('mission12_byproduct_check.txt')) as byproduct_file:
            return json.load(byproduct_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission13_method_check(data):
    if _IS_WEB:
        _web_store_set('mission13_method_check', data)
        return
    with open(get_save_path('mission13_method_check.txt'), 'w') as method_file:
        json.dump(data, method_file)


def load_mission13_method_check():
    if _IS_WEB:
        return _web_store_get('mission13_method_check')
    try:
        with open(get_save_path('mission13_method_check.txt')) as method_file:
            return json.load(method_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None



def save_mission14_reduction_check(data):
    if _IS_WEB:
        _web_store_set('mission14_reduction_check', data)
        return
    with open(get_save_path('mission14_reduction_check.txt'), 'w') as reduction_file:
        json.dump(data, reduction_file)


def load_mission14_reduction_check():
    if _IS_WEB:
        return _web_store_get('mission14_reduction_check')
    try:
        with open(get_save_path('mission14_reduction_check.txt')) as reduction_file:
            return json.load(reduction_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission15_diagnostic_report_check(data):
    if _IS_WEB:
        _web_store_set('mission15_diagnostic_report_check', data)
        return
    with open(get_save_path('mission15_diagnostic_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission15_diagnostic_report_check():
    if _IS_WEB:
        return _web_store_get('mission15_diagnostic_report_check')
    try:
        with open(get_save_path('mission15_diagnostic_report_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None



def save_mission16_medium_report_check(data):
    if _IS_WEB:
        _web_store_set('mission16_medium_report_check', data)
        return
    with open(get_save_path('mission16_medium_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission16_medium_report_check():
    if _IS_WEB:
        return _web_store_get('mission16_medium_report_check')
    try:
        with open(get_save_path('mission16_medium_report_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission17_essential_medium_check(data):
    if _IS_WEB:
        _web_store_set('mission17_essential_medium_check', data)
        return
    with open(get_save_path('mission17_essential_medium_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission17_essential_medium_check():
    if _IS_WEB:
        return _web_store_get('mission17_essential_medium_check')
    try:
        with open(get_save_path('mission17_essential_medium_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission18_export_bottleneck_check(data):
    if _IS_WEB:
        _web_store_set('mission18_export_bottleneck_check', data)
        return
    with open(get_save_path('mission18_export_bottleneck_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission18_export_bottleneck_check():
    if _IS_WEB:
        return _web_store_get('mission18_export_bottleneck_check')
    try:
        with open(get_save_path('mission18_export_bottleneck_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_mission19_perturbation_check(data):
    if _IS_WEB:
        _web_store_set('mission19_perturbation_check', data)
        return
    with open(get_save_path('mission19_perturbation_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission19_perturbation_check():
    if _IS_WEB:
        return _web_store_get('mission19_perturbation_check')
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
        _web_store_set('mission20_robustness_report_check', data)
        return
    with open(get_save_path('mission20_robustness_report_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission20_robustness_report_check():
    if _IS_WEB:
        return _web_store_get('mission20_robustness_report_check')
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
        _web_store_set('mission02_source_comparison_check', data)
        return
    with open(get_save_path('mission02_source_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission02_source_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission02_source_comparison_check')
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
        _web_store_set('mission01_comparison_check', data)
        return
    with open(get_save_path('mission01_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission01_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission01_comparison_check')
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
        _web_store_set('compare_runs', data)
        return
    with open(get_save_path('compare_runs.txt'), 'w') as compare_file:
        json.dump(data, compare_file)


def load_compare_runs():
    if _IS_WEB:
        return _web_store_get('compare_runs')
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
        _web_store_set('mission21_comparison_check', data)
        return
    with open(get_save_path('mission21_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission21_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission21_comparison_check')
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
        _web_store_set('mission22_comparison_check', data)
        return
    with open(get_save_path('mission22_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission22_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission22_comparison_check')
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
        _web_store_set('mission23_comparison_check', data)
        return
    with open(get_save_path('mission23_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission23_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission23_comparison_check')
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
        _web_store_set('mission24_comparison_check', data)
        return
    with open(get_save_path('mission24_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission24_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission24_comparison_check')
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
        _web_store_set('mission25_comparison_check', data)
        return
    with open(get_save_path('mission25_comparison_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission25_comparison_check():
    if _IS_WEB:
        return _web_store_get('mission25_comparison_check')
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
        _web_store_set('bound_sweep', data)
        return
    with open(get_save_path('bound_sweep.txt'), 'w') as sweep_file:
        json.dump(data, sweep_file)


def load_bound_sweep():
    if _IS_WEB:
        return _web_store_get('bound_sweep')
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
        _web_store_set('mission26_bound_sweep_check', data)
        return
    with open(get_save_path('mission26_bound_sweep_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission26_bound_sweep_check():
    if _IS_WEB:
        return _web_store_get('mission26_bound_sweep_check')
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
        _web_store_set('mission27_rescue_check', data)
        return
    with open(get_save_path('mission27_rescue_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission27_rescue_check():
    if _IS_WEB:
        return _web_store_get('mission27_rescue_check')
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
        _web_store_set('mission28_dependency_check', data)
        return
    with open(get_save_path('mission28_dependency_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission28_dependency_check():
    if _IS_WEB:
        return _web_store_get('mission28_dependency_check')
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
        _web_store_set('mission29_redundancy_check', data)
        return
    with open(get_save_path('mission29_redundancy_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission29_redundancy_check():
    if _IS_WEB:
        return _web_store_get('mission29_redundancy_check')
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
        _web_store_set('mission30_redundancy_threshold_check', data)
        return
    with open(get_save_path('mission30_redundancy_threshold_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission30_redundancy_threshold_check():
    if _IS_WEB:
        return _web_store_get('mission30_redundancy_threshold_check')
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
        _web_store_set('mission31_environmental_suppression_check', data)
        return
    with open(get_save_path('mission31_environmental_suppression_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission31_environmental_suppression_check():
    if _IS_WEB:
        return _web_store_get('mission31_environmental_suppression_check')
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
        _web_store_set('mission32_respiratory_cut_set_check', data)
        return
    with open(get_save_path('mission32_respiratory_cut_set_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission32_respiratory_cut_set_check():
    if _IS_WEB:
        return _web_store_get('mission32_respiratory_cut_set_check')
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


def save_mission33_reference_adjustment_check(data):
    if _IS_WEB:
        _web_store_set('mission33_reference_adjustment_check', data)
        return
    with open(get_save_path('mission33_reference_adjustment_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission33_reference_adjustment_check():
    if _IS_WEB:
        return _web_store_get('mission33_reference_adjustment_check')
    try:
        with open(get_save_path('mission33_reference_adjustment_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission33_reference_adjustment_check():
    _delete_save_artifact(
        'mission33_reference_adjustment_check',
        'mission33_reference_adjustment_check.txt',
    )


def save_mission34_shared_subunit_check(data):
    if _IS_WEB:
        _web_store_set('mission34_shared_subunit_check', data)
        return
    with open(get_save_path('mission34_shared_subunit_check.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission34_shared_subunit_check():
    if _IS_WEB:
        return _web_store_get('mission34_shared_subunit_check')
    try:
        with open(get_save_path('mission34_shared_subunit_check.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission34_shared_subunit_check():
    _delete_save_artifact(
        'mission34_shared_subunit_check',
        'mission34_shared_subunit_check.txt',
    )


def save_mission35_final_certification(data):
    """Persist the complete Mission 35 dossier as JSON-serialisable evidence."""
    if _IS_WEB:
        _web_store_set('mission35_final_certification', data)
        return
    with open(get_save_path('mission35_final_certification.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission35_final_certification():
    if _IS_WEB:
        return _web_store_get('mission35_final_certification')
    try:
        with open(get_save_path('mission35_final_certification.txt')) as report_file:
            return json.load(report_file)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def clear_mission35_final_certification():
    _delete_save_artifact(
        'mission35_final_certification',
        'mission35_final_certification.txt',
    )


def save_mission36_fermentation_onset(data):
    if _IS_WEB:
        _web_store_set('mission36_fermentation_onset', data)
        return
    with open(get_save_path('mission36_fermentation_onset.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission36_fermentation_onset():
    if _IS_WEB:
        return _web_store_get('mission36_fermentation_onset')
    try:
        with open(get_save_path('mission36_fermentation_onset.txt')) as report_file:
            return json.load(report_file)
    except (FileNotFoundError, Exception):
        return None


def clear_mission36_fermentation_onset():
    _delete_save_artifact('mission36_fermentation_onset', 'mission36_fermentation_onset.txt')


def save_mission37_fermentation_cut_set(data):
    """Persist Mission 37 visible yeast cut-set evidence."""
    if _IS_WEB:
        _web_store_set('mission37_fermentation_cut_set', data)
        return
    with open(get_save_path('mission37_fermentation_cut_set.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission37_fermentation_cut_set():
    if _IS_WEB:
        return _web_store_get('mission37_fermentation_cut_set')
    try:
        with open(get_save_path('mission37_fermentation_cut_set.txt')) as report_file:
            return json.load(report_file)
    except (FileNotFoundError, Exception):
        return None


def clear_mission37_fermentation_cut_set():
    _delete_save_artifact(
        'mission37_fermentation_cut_set',
        'mission37_fermentation_cut_set.txt',
    )


def save_mission38_background_dependency(data):
    """Persist Mission 38 visible yeast background-dependency evidence."""
    if _IS_WEB:
        _web_store_set('mission38_background_dependency', data)
        return
    with open(get_save_path('mission38_background_dependency.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission38_background_dependency():
    if _IS_WEB:
        return _web_store_get('mission38_background_dependency')
    try:
        with open(get_save_path('mission38_background_dependency.txt')) as report_file:
            return json.load(report_file)
    except (FileNotFoundError, Exception):
        return None


def clear_mission38_background_dependency():
    _delete_save_artifact(
        'mission38_background_dependency',
        'mission38_background_dependency.txt',
    )


def save_mission39_bypass_rescue(data):
    """Persist Mission 39 visible yeast bypass-rescue evidence."""
    if _IS_WEB:
        _web_store_set('mission39_bypass_rescue', data)
        return
    with open(get_save_path('mission39_bypass_rescue.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission39_bypass_rescue():
    if _IS_WEB:
        return _web_store_get('mission39_bypass_rescue')
    try:
        with open(get_save_path('mission39_bypass_rescue.txt')) as report_file:
            return json.load(report_file)
    except (FileNotFoundError, Exception):
        return None


def clear_mission39_bypass_rescue():
    _delete_save_artifact(
        'mission39_bypass_rescue',
        'mission39_bypass_rescue.txt',
    )


def save_mission40_final_certification(data):
    """Persist Mission 40 visible final matched-curve evidence."""
    if _IS_WEB:
        _web_store_set('mission40_final_certification', data)
        return
    with open(get_save_path('mission40_final_certification.txt'), 'w') as report_file:
        json.dump(data, report_file)


def load_mission40_final_certification():
    if _IS_WEB:
        return _web_store_get('mission40_final_certification')
    try:
        with open(get_save_path('mission40_final_certification.txt')) as report_file:
            return json.load(report_file)
    except (FileNotFoundError, Exception):
        return None


def clear_mission40_final_certification():
    _delete_save_artifact(
        'mission40_final_certification',
        'mission40_final_certification.txt',
    )
