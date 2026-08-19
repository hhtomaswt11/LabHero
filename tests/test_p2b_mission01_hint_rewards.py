import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import HintSystem, TRACKED_HINT_MISSIONS

MISSION01_PATH = CODE / 'mission01.py'
MISSION01_SOURCE = MISSION01_PATH.read_text(encoding='utf-8')


def _load_mission01_info_class(animation_log=None, save_log=None):
    """Compile Mission_info without importing pygame-dependent mission01.py."""
    tree = ast.parse(MISSION01_SOURCE)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'Mission_info'
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
    exec(compile(module, str(MISSION01_PATH), 'exec'), namespace)
    return namespace['Mission_info'], animation_log, save_log


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


class Mission01HintRewardIntegrationTests(unittest.TestCase):
    def _info(self, system=None, completed=None):
        cls, animations, saves = _load_mission01_info_class()
        obj = cls.__new__(cls)
        obj.player = FakePlayer(system or HintSystem())
        obj.missions_completed = list(completed or [])
        return obj, animations, saves

    def test_mission01_and_mission02_remain_tracked_in_p4b(self):
        self.assertEqual(TRACKED_HINT_MISSIONS, frozenset(f'{mission:02d}' for mission in range(1, 41)))

    def test_mission01_has_three_progressive_hint_levels(self):
        self.assertIn('Conceptual hint: treat this as a controlled experiment.', MISSION01_SOURCE)
        self.assertIn('Experimental hint: oxygen availability is controlled through the EX_o2_e exchange reaction.', MISSION01_SOURCE)
        self.assertIn('Technical hint: use FBA with the biomass objective and no gene knockouts.', MISSION01_SOURCE)
        self.assertIn("'Reveal next hint (Silver Key if locked)'", MISSION01_SOURCE)
        self.assertIn("'Reveal technical hint (Gold Key if locked)'", MISSION01_SOURCE)
        self.assertEqual(MISSION01_SOURCE.count("'Optional Hints (Bronze Key if locked)'"), 2)
        self.assertEqual(MISSION01_SOURCE.count('self._request_hint_access'), 4)

    def test_briefing_no_longer_gives_technical_hint_for_free(self):
        tree = ast.parse(MISSION01_SOURCE)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Mission_info')
        setup = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'setup')
        setup_source = ast.get_source_segment(MISSION01_SOURCE, setup)

        # EX_o2_e should appear only in paid Hint 2 and Hint 3 inside setup,
        # not in the main mission description/briefing as it did before P.2B.
        self.assertEqual(setup_source.count('EX_o2_e'), 2)
        self.assertNotIn('Then run the same setup again and change only the lower bound of EX_o2_e', setup_source)

    def test_first_hint_charges_bronze_once_and_reopen_is_free(self):
        obj, animations, saves = self._info()
        source = FakeMenu()
        target = object()

        first = obj._request_hint_access(1, source, target)
        self.assertEqual(first['status'], 'unlocked')
        self.assertEqual(first['charged_key'], 'bronze')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 14)
        self.assertEqual(obj.player.hint_system.get_hint_level('01'), 1)
        self.assertEqual(len(saves), 1)
        self.assertEqual(source.opened, [target])

        second = obj._request_hint_access(1, source, target)
        self.assertEqual(second['status'], 'already_unlocked')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 14)
        self.assertEqual(len(saves), 1)
        self.assertEqual(source.opened, [target, target])
        self.assertTrue(any('Mission 01 Hint 1 unlocked with 1 Bronze Key.' in msg for msg, *_ in animations))

    def test_hints_are_sequential_and_charge_bronze_silver_gold(self):
        obj, _, saves = self._info()
        source = FakeMenu()
        target = object()

        blocked = obj._request_hint_access(2, source, target)
        self.assertEqual(blocked['status'], 'previous_hint_locked')
        self.assertEqual(obj.player.hint_system.get_hint_level('01'), 0)

        one = obj._request_hint_access(1, source, target)
        two = obj._request_hint_access(2, source, target)
        three = obj._request_hint_access(3, source, target)

        self.assertEqual(one['charged_key'], 'bronze')
        self.assertEqual(two['charged_key'], 'silver')
        self.assertEqual(three['charged_key'], 'gold')
        self.assertEqual(obj.player.hint_system.get_hint_level('01'), 3)
        self.assertEqual(obj.player.hint_system.state['keys'], {
            'bronze': 14,
            'silver': 9,
            'gold': 4,
        })
        self.assertEqual(len(saves), 3)

    def test_fallback_requires_explicit_confirmation(self):
        system = HintSystem()
        system.state['keys']['bronze'] = 0
        obj, _, saves = self._info(system)
        source = FakeMenu()
        target = object()
        confirmation = FakeMenu()
        obj._build_fallback_confirmation = lambda *args: confirmation

        offer = obj._request_hint_access(1, source, target)
        self.assertEqual(offer['status'], 'confirmation_required')
        self.assertEqual(offer['key_to_spend'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 10)
        self.assertEqual(saves, [])
        self.assertEqual(source.opened, [confirmation])

        result = obj._confirm_fallback_hint(1, source, confirmation, target)
        self.assertEqual(result['status'], 'unlocked')
        self.assertEqual(result['charged_key'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 9)
        self.assertEqual(system.get_hint_level('01'), 1)
        self.assertEqual(len(saves), 1)
        self.assertEqual(confirmation.reset_calls, [1])
        self.assertEqual(source.opened[-1], target)

    def test_fallback_prompt_is_explicit_and_cancelable(self):
        self.assertIn("No {required} Keys are available.", MISSION01_SOURCE)
        self.assertIn("Use 1 {fallback} Key instead?", MISSION01_SOURCE)
        self.assertIn("'Cancel',", MISSION01_SOURCE)
        self.assertIn('allow_fallback=True', MISSION01_SOURCE)

    def test_completed_mission_cannot_buy_new_hint(self):
        obj, animations, saves = self._info(completed=['01'])
        source = FakeMenu()
        target = object()

        result = obj._request_hint_access(1, source, target)
        self.assertEqual(result['status'], 'mission_completed')
        self.assertEqual(obj.player.hint_system.get_key_count('bronze'), 15)
        self.assertEqual(obj.player.hint_system.get_hint_level('01'), 0)
        self.assertEqual(saves, [])
        self.assertEqual(source.opened, [])
        self.assertTrue(any('New hints can no longer be unlocked' in msg for msg, *_ in animations))

    def test_each_hint_purchase_persists_immediately(self):
        tree = ast.parse(MISSION01_SOURCE)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Mission_info')
        methods = {n.name: n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        save_method = ast.get_source_segment(MISSION01_SOURCE, methods['_save_reward_progress'])
        unlock_method = ast.get_source_segment(MISSION01_SOURCE, methods['_unlock_hint_and_open'])
        fallback_method = ast.get_source_segment(MISSION01_SOURCE, methods['_confirm_fallback_hint'])

        self.assertIn('save_file(self.player.get_save_data())', save_method)
        self.assertIn('self._save_reward_progress()', unlock_method)
        self.assertIn('self._save_reward_progress()', fallback_method)

    def test_mission01_completion_score_is_5_3_2_1_and_frozen(self):
        expected = {0: 5, 1: 3, 2: 2, 3: 1}
        for hint_level, score in expected.items():
            with self.subTest(hint_level=hint_level):
                system = HintSystem()
                for level in range(1, hint_level + 1):
                    result = system.unlock_hint('01', level)
                    self.assertEqual(result['status'], 'unlocked')

                finalized = system.sync_completed_missions(['01'])
                self.assertEqual(finalized, {'01': score})
                self.assertEqual(system.get_mission_score('01'), score)

                system.state['mission_hints']['01'] = 3
                system.sync_completed_missions(['01'])
                self.assertEqual(system.get_mission_score('01'), score)

    def test_pre_p2b_completed_mission01_remains_legacy_unscored(self):
        system = HintSystem(state=None, legacy_completed=['01'])
        system.sync_completed_missions(['01'])
        self.assertIsNone(system.get_mission_score('01'))
        self.assertIn('01', system.state['legacy_unscored_missions'])

    def test_hint_state_round_trip_reopens_free_then_continues(self):
        original = HintSystem()
        first = original.unlock_hint('01', 1)
        self.assertEqual(first['charged_key'], 'bronze')

        restored = HintSystem(original.to_dict())
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
        self.assertEqual(restored.get_hint_level('01'), 2)
        self.assertEqual(restored.get_key_count('silver'), 9)
        self.assertEqual(len(saves), 1)

    def test_no_available_key_keeps_hint_locked(self):
        system = HintSystem()
        system.state['keys'].update({'bronze': 0, 'silver': 0, 'gold': 0})
        obj, animations, saves = self._info(system)
        source = FakeMenu()
        target = object()

        result = obj._request_hint_access(1, source, target)
        self.assertEqual(result['status'], 'no_key_available')
        self.assertEqual(system.get_hint_level('01'), 0)
        self.assertEqual(saves, [])
        self.assertEqual(source.opened, [])
        self.assertTrue(any('No Bronze, Silver or Gold Key' in msg for msg, *_ in animations))

    def test_mission01_activation_and_delivery_contracts_are_preserved(self):
        tree = ast.parse(MISSION01_SOURCE)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Mission_info')
        methods = {n.name: ast.get_source_segment(MISSION01_SOURCE, n) for n in cls.body if isinstance(n, ast.FunctionDef)}

        self.assertIn("clear_compare_runs()", methods['activate_mission01'])
        self.assertIn("clear_mission01_comparison_check()", methods['activate_mission01'])
        self.assertIn("load_mission01_comparison_check()", methods['deliver_results'])
        self.assertIn("report_data.get('ready_to_deliver')", methods['deliver_results'])
        self.assertIn("self.missions_completed.insert(0, '01')", methods['deliver_results'])
        self.assertIn("save_file(self.player.get_save_data())", methods['deliver_results'])


if __name__ == '__main__':
    unittest.main()
