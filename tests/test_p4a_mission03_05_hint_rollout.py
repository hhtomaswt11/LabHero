import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import HintSystem, TRACKED_HINT_MISSIONS  # noqa: E402


class FakeMenu:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.opened = []
        self.reset_calls = []
        self.labels = []
        self.buttons = []
        self.add = types.SimpleNamespace(
            vertical_margin=lambda *args, **kwargs: None,
            label=self._add_label,
            button=self._add_button,
        )

    def _add_label(self, text, *args, **kwargs):
        self.labels.append((text, args, kwargs))

    def _add_button(self, text, *args, **kwargs):
        self.buttons.append((text, args, kwargs))

    def _open(self, target):
        self.opened.append(target)

    def reset(self, *args):
        self.reset_calls.append(args)


class FakePlayer:
    def __init__(self, system=None):
        self.hint_system = system or HintSystem()
        self.reward_state = self.hint_system.state
        self.saved_payloads = []

    def get_save_data(self):
        payload = ['Player', [], [], [], {}, self.hint_system.to_dict()]
        self.saved_payloads.append(payload)
        return payload


def load_hint_ui():
    animations = []
    saves = []

    fake_pygame_menu = types.ModuleType('pygame_menu')
    fake_pygame_menu.Menu = FakeMenu
    fake_pygame_menu.events = types.SimpleNamespace(BACK='BACK')
    fake_pygame_menu.locals = types.SimpleNamespace(ALIGN_CENTER='CENTER')

    fake_functions = types.ModuleType('functions')
    fake_functions.animation_text_save = lambda message, time=0: animations.append((message, time))

    fake_save_load = types.ModuleType('save_load')
    fake_save_load.save_file = lambda payload: saves.append(payload)

    previous = {name: sys.modules.get(name) for name in ('pygame_menu', 'functions', 'save_load')}
    sys.modules['pygame_menu'] = fake_pygame_menu
    sys.modules['functions'] = fake_functions
    sys.modules['save_load'] = fake_save_load
    try:
        spec = importlib.util.spec_from_file_location('hint_ui_p4a_test', CODE / 'hint_ui.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old

    return module.MissionHintAccess, animations, saves


class P4AMissionHintRolloutTests(unittest.TestCase):
    def test_rollout_now_tracks_missions_01_through_30(self):
        self.assertEqual(
            TRACKED_HINT_MISSIONS,
            frozenset(f'{mission:02d}' for mission in range(1, 41)),
        )

    def test_mission03_05_use_common_access_helper_with_correct_ids(self):
        for mission_id in ('03', '04', '05'):
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('from hint_ui import MissionHintAccess', source)
            self.assertIn(
                f"MissionHintAccess(self.player, '{mission_id}', self.missions_completed, mytheme)",
                source,
            )
            self.assertEqual(source.count('self.hint_access.request'), 4)

    def test_mission03_05_keep_existing_three_hint_content(self):
        expected = {
            '03': (
                'Conceptual hint: the impact of a knockout needs a viable all-genes-active reference.',
                'Experimental hint: isolate one genetic perturbation at a time.',
                'Technical hint: use FBA with the biomass objective and the unchanged default medium.',
            ),
            '04': (
                'Conceptual hint:',
                'Experimental hint:',
                'Technical hint:',
            ),
            '05': (
                'Conceptual hint:',
                'Experimental hint:',
                'Technical hint:',
            ),
        }
        for mission_id, snippets in expected.items():
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            for snippet in snippets:
                self.assertIn(snippet, source)

    def test_all_four_entry_points_show_key_costs(self):
        for mission_id in ('03', '04', '05'):
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertEqual(source.count("'Optional Hints (Bronze Key if locked)'"), 2)
            self.assertEqual(source.count("'Reveal next hint (Silver Key if locked)'"), 1)
            self.assertEqual(source.count("'Reveal technical hint (Gold Key if locked)'"), 1)

    def test_common_helper_charges_preferred_key_and_saves(self):
        Access, animations, saves = load_hint_ui()
        system = HintSystem()
        player = FakePlayer(system)
        source = FakeMenu()
        target = object()
        access = Access(player, '03', [], object())

        result = access.request(1, source, target)

        self.assertEqual(result['status'], 'unlocked')
        self.assertEqual(result['charged_key'], 'bronze')
        self.assertEqual(system.get_key_count('bronze'), 14)
        self.assertEqual(system.get_hint_level('03'), 1)
        self.assertEqual(source.opened, [target])
        self.assertEqual(len(saves), 1)
        self.assertTrue(any('Mission 03 Hint 1 unlocked' in msg for msg, _ in animations))

    def test_common_helper_reopening_is_free(self):
        Access, _animations, saves = load_hint_ui()
        system = HintSystem()
        player = FakePlayer(system)
        access = Access(player, '04', [], object())
        first_source = FakeMenu()
        second_source = FakeMenu()
        target = object()

        access.request(1, first_source, target)
        bronze_after_first = system.get_key_count('bronze')
        save_count = len(saves)
        result = access.request(1, second_source, target)

        self.assertEqual(result['status'], 'already_unlocked')
        self.assertEqual(system.get_key_count('bronze'), bronze_after_first)
        self.assertEqual(len(saves), save_count)
        self.assertEqual(second_source.opened, [target])

    def test_common_helper_fallback_requires_explicit_confirmation(self):
        Access, _animations, saves = load_hint_ui()
        system = HintSystem()
        system.state['keys']['bronze'] = 0
        player = FakePlayer(system)
        access = Access(player, '05', [], object())
        source = FakeMenu()
        target = object()

        offer = access.request(1, source, target)

        self.assertEqual(offer['status'], 'confirmation_required')
        self.assertEqual(offer['key_to_spend'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 10)
        self.assertEqual(system.get_hint_level('05'), 0)
        self.assertEqual(len(saves), 0)
        self.assertEqual(len(source.opened), 1)
        confirmation = source.opened[0]
        use_button = next(button for button in confirmation.buttons if button[0].startswith('Use 1 Silver'))
        callback = use_button[1][0]
        callback_args = use_button[1][1:]
        callback(*callback_args)

        self.assertEqual(system.get_key_count('silver'), 9)
        self.assertEqual(system.get_hint_level('05'), 1)
        self.assertEqual(len(saves), 1)

    def test_completed_integrated_mission_score_freezes_from_hint_level(self):
        system = HintSystem()
        system.unlock_hint('03', 1)
        system.unlock_hint('03', 2)
        system.sync_completed_missions(['03'])
        self.assertEqual(system.get_mission_score('03'), 2)
        system.state['mission_hints']['03'] = 3
        system.sync_completed_missions(['03'])
        self.assertEqual(system.get_mission_score('03'), 2)

    def test_final_rollout_also_scores_missions_31_and_35(self):
        system = HintSystem()
        system.sync_completed_missions(['31', '35'])
        self.assertEqual(system.state['mission_scores'], {'31': 5, '35': 5})
        self.assertEqual(system.state['legacy_unscored_missions'], [])

    def test_c_inventory_shortcut_is_completely_removed(self):
        skin_source = (CODE / 'skin_menu.py').read_text(encoding='utf-8')
        level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertNotIn('pygame.K_c', skin_source)
        self.assertNotIn('pygame.K_c', level_source)
        self.assertIn('pygame.K_e', skin_source)
        self.assertIn('pygame.K_e', level_source)


if __name__ == '__main__':
    unittest.main()
