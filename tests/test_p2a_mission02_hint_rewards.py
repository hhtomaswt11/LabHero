import ast
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import HintSystem, TRACKED_HINT_MISSIONS

MISSION02_PATH = CODE / 'mission02.py'
MISSION02_SOURCE = MISSION02_PATH.read_text()


def _load_mission02_info_class(animation_log=None, save_log=None):
    """Compile Mission02_info without importing pygame-dependent mission02.py."""
    tree = ast.parse(MISSION02_SOURCE)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'Mission02_info'
    )
    module = ast.Module(body=[cls], type_ignores=[])
    ast.fix_missing_locations(module)

    animation_log = animation_log if animation_log is not None else []
    save_log = save_log if save_log is not None else []

    def animation_text_save(text, time=1200, fullscreen=False):
        animation_log.append((text, time, fullscreen))

    def save_file(data):
        save_log.append(data)

    namespace = {
        'animation_text_save': animation_text_save,
        'save_file': save_file,
    }
    exec(compile(module, str(MISSION02_PATH), 'exec'), namespace)
    return namespace['Mission02_info'], animation_log, save_log


class FakeMenu:
    def __init__(self):
        self.opened = []
        self.reset_calls = []

    def _open(self, target):
        self.opened.append(target)

    def reset(self, count):
        self.reset_calls.append(count)


class FakePlayer:
    def __init__(self, hint_system=None):
        self.hint_system = hint_system or HintSystem()
        self.reward_state = self.hint_system.state

    def get_save_data(self):
        return ['Player', [], [], [], {}, self.hint_system.to_dict()]


class Mission02HintRewardPilotTests(unittest.TestCase):
    def _info(self, system=None, completed=None):
        cls, animations, saves = _load_mission02_info_class()
        obj = cls.__new__(cls)
        obj.player = FakePlayer(system or HintSystem())
        obj.missions_completed = list(completed or [])
        return obj, animations, saves

    def test_mission02_remains_tracked_after_p4b(self):
        self.assertEqual(TRACKED_HINT_MISSIONS, frozenset(f'{mission:02d}' for mission in range(1, 41)))
        self.assertIn('02', TRACKED_HINT_MISSIONS)

    def test_mission02_keeps_original_progressive_hint_content(self):
        self.assertIn('Conceptual hint: a fair experiment changes the factor', MISSION02_SOURCE)
        self.assertIn('Experimental hint: a replacement is not the same as a supplement', MISSION02_SOURCE)
        self.assertIn('Technical hint: use FBA with the biomass objective', MISSION02_SOURCE)

    def test_hint_buttons_route_through_runtime_access_gate(self):
        self.assertIn("'Optional Hints (Bronze Key if locked)'", MISSION02_SOURCE)
        self.assertIn("'Reveal next hint (Silver Key if locked)'", MISSION02_SOURCE)
        self.assertIn("'Reveal technical hint (Gold Key if locked)'", MISSION02_SOURCE)
        # Both top-level Optional Hints entry points plus Hint 2/3 transitions.
        self.assertEqual(MISSION02_SOURCE.count('self._request_hint_access'), 4)

    def test_first_hint_charges_bronze_once_and_reopen_is_free(self):
        obj, animations, saves = self._info()
        source = FakeMenu()
        target = object()

        first = obj._request_hint_access(1, source, target)
        self.assertEqual(first['status'], 'unlocked')
        self.assertEqual(first['charged_key'], 'bronze')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 14)
        self.assertEqual(obj.player.hint_system.get_hint_level('02'), 1)
        self.assertEqual(len(saves), 1)
        self.assertEqual(source.opened, [target])

        second = obj._request_hint_access(1, source, target)
        self.assertEqual(second['status'], 'already_unlocked')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 14)
        self.assertEqual(len(saves), 1)
        self.assertEqual(source.opened, [target, target])
        self.assertTrue(any('1 Bronze Key' in message for message, *_ in animations))

    def test_hints_are_sequential_and_use_bronze_silver_gold(self):
        obj, _, saves = self._info()
        source = FakeMenu()
        target = object()

        blocked = obj._request_hint_access(2, source, target)
        self.assertEqual(blocked['status'], 'previous_hint_locked')
        self.assertEqual(obj.player.hint_system.get_hint_level('02'), 0)

        obj._request_hint_access(1, source, target)
        level2 = obj._request_hint_access(2, source, target)
        level3 = obj._request_hint_access(3, source, target)

        self.assertEqual(level2['charged_key'], 'silver')
        self.assertEqual(level3['charged_key'], 'gold')
        self.assertEqual(obj.player.hint_system.get_hint_level('02'), 3)
        self.assertEqual(obj.player.hint_system.state['keys'], {
            'bronze': 14,
            'silver': 9,
            'gold': 4,
        })
        self.assertEqual(len(saves), 3)

    def test_fallback_requires_confirmation_before_spending_stronger_key(self):
        system = HintSystem()
        system.state['keys']['bronze'] = 0
        obj, _, saves = self._info(system)
        source = FakeMenu()
        target = object()
        confirmation = FakeMenu()

        # Avoid pygame-menu construction in this pygame-free test; the real
        # builder is covered statically below.
        obj._build_fallback_confirmation = lambda *args: confirmation

        offer = obj._request_hint_access(1, source, target)
        self.assertEqual(offer['status'], 'confirmation_required')
        self.assertEqual(offer['key_to_spend'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 10)
        self.assertEqual(len(saves), 0)
        self.assertEqual(source.opened, [confirmation])

        result = obj._confirm_fallback_hint(1, source, confirmation, target)
        self.assertEqual(result['status'], 'unlocked')
        self.assertEqual(result['charged_key'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 9)
        self.assertEqual(system.get_hint_level('02'), 1)
        self.assertEqual(len(saves), 1)
        self.assertEqual(confirmation.reset_calls, [1])
        self.assertEqual(source.opened[-1], target)

    def test_completed_mission_cannot_buy_new_hint(self):
        obj, animations, saves = self._info(completed=['02'])
        source = FakeMenu()
        target = object()

        result = obj._request_hint_access(1, source, target)
        self.assertEqual(result['status'], 'mission_completed')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 15)
        self.assertEqual(obj.player.hint_system.get_hint_level('02'), 0)
        self.assertEqual(saves, [])
        self.assertEqual(source.opened, [])
        self.assertTrue(any('New hints can no longer be unlocked' in msg for msg, *_ in animations))

    def test_fallback_confirmation_is_explicit_and_cancelable(self):
        self.assertIn("No {required} Keys are available.", MISSION02_SOURCE)
        self.assertIn("Use 1 {fallback} Key instead?", MISSION02_SOURCE)
        self.assertIn("'Cancel',", MISSION02_SOURCE)
        self.assertIn('allow_fallback=True', MISSION02_SOURCE)

    def test_each_hint_purchase_persists_immediately(self):
        tree = ast.parse(MISSION02_SOURCE)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Mission02_info')
        methods = {n.name: n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        save_method = ast.get_source_segment(MISSION02_SOURCE, methods['_save_reward_progress'])
        unlock_method = ast.get_source_segment(MISSION02_SOURCE, methods['_unlock_hint_and_open'])
        fallback_method = ast.get_source_segment(MISSION02_SOURCE, methods['_confirm_fallback_hint'])

        self.assertIn('save_file(self.player.get_save_data())', save_method)
        self.assertIn('self._save_reward_progress()', unlock_method)
        self.assertIn('self._save_reward_progress()', fallback_method)

    def test_mission02_completion_score_is_5_3_2_1_and_frozen(self):
        expected = {0: 5, 1: 3, 2: 2, 3: 1}
        for hint_level, score in expected.items():
            with self.subTest(hint_level=hint_level):
                system = HintSystem()
                for level in range(1, hint_level + 1):
                    result = system.unlock_hint('02', level)
                    self.assertEqual(result['status'], 'unlocked')

                finalized = system.sync_completed_missions(['02'])
                self.assertEqual(finalized, {'02': score})
                self.assertEqual(system.get_mission_score('02'), score)

                # A later malformed change cannot alter the frozen result.
                system.state['mission_hints']['02'] = 3
                system.sync_completed_missions(['02'])
                self.assertEqual(system.get_mission_score('02'), score)

    def test_pre_p2a_completed_mission02_remains_legacy_unscored(self):
        system = HintSystem(state=None, legacy_completed=['02'])
        system.sync_completed_missions(['02'])
        self.assertIsNone(system.get_mission_score('02'))
        self.assertIn('02', system.state['legacy_unscored_missions'])


    def test_hint_state_round_trip_reopens_free_then_continues_sequentially(self):
        original = HintSystem()
        first = original.unlock_hint('02', 1)
        self.assertEqual(first['charged_key'], 'bronze')
        exported = original.to_dict()

        restored = HintSystem(exported)
        obj, _, saves = self._info(restored)
        source = FakeMenu()
        target = object()

        reopened = obj._request_hint_access(1, source, target)
        self.assertEqual(reopened['status'], 'already_unlocked')
        self.assertEqual(restored.get_key_count('bronze'), 14)
        self.assertEqual(len(saves), 0)

        second = obj._request_hint_access(2, source, target)
        self.assertEqual(second['status'], 'unlocked')
        self.assertEqual(second['charged_key'], 'silver')
        self.assertEqual(restored.get_hint_level('02'), 2)
        self.assertEqual(restored.get_key_count('silver'), 9)
        self.assertEqual(len(saves), 1)

    def test_no_suitable_key_keeps_hint_locked_and_does_not_save(self):
        system = HintSystem()
        system.state['keys'].update({'bronze': 0, 'silver': 0, 'gold': 0})
        obj, animations, saves = self._info(system)
        source = FakeMenu()
        target = object()

        result = obj._request_hint_access(1, source, target)
        self.assertEqual(result['status'], 'no_key_available')
        self.assertEqual(system.get_hint_level('02'), 0)
        self.assertEqual(saves, [])
        self.assertEqual(source.opened, [])
        self.assertTrue(any('No Bronze, Silver or Gold Key' in msg for msg, *_ in animations))

    def test_final_rollout_tracks_missions_31_and_40(self):
        system = HintSystem()
        system.sync_completed_missions(['31', '40'])
        self.assertEqual(system.state['mission_scores'], {'31': 5, '40': 5})
        self.assertEqual(system.state['legacy_unscored_missions'], [])


if __name__ == '__main__':
    unittest.main()
