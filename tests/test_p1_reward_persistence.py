import ast
import copy
import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


class _Vector2:
    def __init__(self, *args, **kwargs):
        self.args = args


# settings.py only needs Vector2 at import time.  Keep these persistence tests
# pygame-free so they run in backend/CI environments too.
if 'pygame' not in sys.modules:
    pygame_stub = types.ModuleType('pygame')
    pygame_stub.Vector2 = _Vector2
    sys.modules['pygame'] = pygame_stub

from hint_system import HintSystem, create_reward_state
import save_load


PLAYER_PATH = CODE / 'player.py'
SETTINGS_PATH = CODE / 'settings.py'


class TestP1RewardPersistence(unittest.TestCase):
    def setUp(self):
        self.original_is_web = save_load._IS_WEB
        self.original_memstore = copy.deepcopy(save_load._MEMSTORE)
        save_load._IS_WEB = True
        save_load._MEMSTORE.clear()

    def tearDown(self):
        save_load._IS_WEB = self.original_is_web
        save_load._MEMSTORE.clear()
        save_load._MEMSTORE.update(self.original_memstore)

    def test_old_four_field_save_migrates_to_six_fields(self):
        old = ['Player', [], ['01'], ['01', '02']]
        normalized = save_load.normalize_save_data(old)

        self.assertEqual(len(normalized), 6)
        self.assertIsInstance(normalized[4], dict)
        self.assertEqual(
            normalized[5]['legacy_unscored_missions'],
            ['01', '02'],
        )
        self.assertEqual(normalized[5]['keys'], {'bronze': 15, 'silver': 10, 'gold': 5})

    def test_old_five_field_save_migrates_without_changing_player_state(self):
        player_state = {
            'scene': 'main_map',
            'x': 123.0,
            'y': 456.0,
            'facing': 'left',
            'status': 'left_idle',
            'skin_id': 'alt',
        }
        old = ['Player', [], [], ['03'], player_state]
        normalized = save_load.normalize_save_data(old)

        self.assertEqual(normalized[4], player_state)
        self.assertEqual(normalized[5]['legacy_unscored_missions'], ['03'])

    def test_new_six_field_save_preserves_reward_progress(self):
        reward = create_reward_state()
        reward['keys']['bronze'] = 11
        reward['mission_hints']['02'] = 2
        reward['mission_scores']['01'] = 5
        data = ['Player', [], [], ['01'], {}, reward]

        normalized = save_load.normalize_save_data(data)

        self.assertEqual(normalized[5]['keys']['bronze'], 11)
        self.assertEqual(normalized[5]['mission_hints']['02'], 2)
        self.assertEqual(normalized[5]['mission_scores']['01'], 5)
        self.assertEqual(normalized[5]['legacy_unscored_missions'], [])

    def test_old_shape_save_file_preserves_existing_reward_state(self):
        reward = create_reward_state()
        reward['keys']['bronze'] = 4
        reward['mission_hints']['02'] = 1
        current = ['Player', [], [], [], {}, reward]
        save_load._MEMSTORE['data'] = current

        save_load.save_file(['Player', [], [], [], {}])

        saved = save_load._MEMSTORE['data']
        self.assertEqual(saved[5]['keys']['bronze'], 4)
        self.assertEqual(saved[5]['mission_hints']['02'], 1)

    def test_web_save_and_load_round_trip_sixth_field(self):
        reward = create_reward_state()
        reward['keys']['silver'] = 3
        reward['mission_scores']['02'] = 2
        data = ['Player', ['x'], ['02'], ['02'], {}, reward]

        save_load.save_file(data)
        loaded = save_load.load_file('data')

        self.assertEqual(len(loaded), 6)
        self.assertEqual(loaded[5]['keys']['silver'], 3)
        self.assertEqual(loaded[5]['mission_scores']['02'], 2)

    def test_settings_default_inventory_declares_reward_state(self):
        tree = ast.parse(SETTINGS_PATH.read_text())
        assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'DEFAULT_INVENTORY_2' for t in node.targets)
        )
        self.assertIsInstance(assignment.value, ast.List)
        self.assertEqual(len(assignment.value.elts), 6)
        self.assertIsInstance(assignment.value.elts[5], ast.Call)
        self.assertEqual(assignment.value.elts[5].func.id, 'create_reward_state')

    def test_player_unpacks_reward_state_and_owns_hint_system(self):
        source = PLAYER_PATH.read_text()
        self.assertIn('reward_state', source)
        self.assertIn('self.hint_system = HintSystem(reward_state)', source)
        self.assertIn('self.reward_state = self.hint_system.state', source)

    def test_player_old_save_path_marks_existing_completed_as_legacy(self):
        tree = ast.parse(PLAYER_PATH.read_text())
        player = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Player')
        method = next(
            n for n in player.body
            if isinstance(n, ast.FunctionDef) and n.name == '_unpack_save_data'
        )
        source = ast.get_source_segment(PLAYER_PATH.read_text(), method)
        self.assertIn(
            'create_reward_state(legacy_completed=missions_completed)',
            source,
        )

    def test_get_save_data_finalizes_scores_and_returns_six_fields(self):
        tree = ast.parse(PLAYER_PATH.read_text())
        player = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Player')
        method = next(
            n for n in player.body
            if isinstance(n, ast.FunctionDef) and n.name == 'get_save_data'
        )

        # Compile only this pygame-independent method.
        module = ast.Module(body=[method], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {}
        exec(compile(module, str(PLAYER_PATH), 'exec'), namespace)
        get_save_data = namespace['get_save_data']

        class StubHintSystem:
            def __init__(self):
                self.state = create_reward_state()
                self.completed_seen = None

            def sync_completed_missions(self, completed):
                self.completed_seen = list(completed)
                self.state['mission_scores']['02'] = 3

            def to_dict(self):
                return copy.deepcopy(self.state)

        obj = types.SimpleNamespace(
            player_name='Player',
            results=[],
            missions_activated=['02'],
            missions_completed=['02'],
            hint_system=StubHintSystem(),
        )
        obj.get_player_state = lambda: {'scene': 'main_map'}

        payload = get_save_data(obj)

        self.assertEqual(obj.hint_system.completed_seen, ['02'])
        self.assertEqual(len(payload), 6)
        self.assertEqual(payload[5]['mission_scores']['02'], 3)
        self.assertIs(obj.reward_state, obj.hint_system.state)

    def test_total_score_is_not_stored_as_a_separate_save_field(self):
        reward = create_reward_state()
        system = HintSystem(reward)
        system.finalize_completed_missions(['01'])
        exported = system.to_dict()

        self.assertNotIn('total_score', exported)
        self.assertEqual(system.get_total_score(), 5)


if __name__ == '__main__':
    unittest.main()
