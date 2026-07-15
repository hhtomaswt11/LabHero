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

