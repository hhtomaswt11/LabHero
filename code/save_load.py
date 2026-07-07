import json
import os
import sys

from utils import *

_IS_WEB = sys.platform == 'emscripten'
_MEMSTORE = {}


def _memkey(filename):
    return os.path.basename(filename)


def save_file(data):
    if _IS_WEB:
        _MEMSTORE['data'] = data
        return
    with open(get_save_path('data.txt'), 'w') as test_file:
        json.dump(data, test_file)


def load_file(filename):
    if _IS_WEB:
        key = _memkey(filename)
        if key in _MEMSTORE:
            return _MEMSTORE[key]
    with open(f'{filename}.txt') as test_file:
        data = json.load(test_file)
        return data


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

