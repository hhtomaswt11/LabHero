import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import HintSystem, TRACKED_HINT_MISSIONS  # noqa: E402


EXPECTED_TRACKED = frozenset(f'{mission:02d}' for mission in range(1, 41))
MISSIONS = tuple(f'{mission:02d}' for mission in range(11, 16))


class P4CMissionHintRolloutTests(unittest.TestCase):
    def test_rollout_tracks_missions_01_through_30(self):
        self.assertEqual(TRACKED_HINT_MISSIONS, EXPECTED_TRACKED)

    def test_mission11_15_use_common_access_helper_with_correct_ids(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('from hint_ui import MissionHintAccess', source)
            self.assertIn(
                f"MissionHintAccess(self.player, '{mission_id}', self.missions_completed, mytheme)",
                source,
            )

    def test_each_mission_preserves_three_progressive_hint_texts(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('Conceptual hint:', source)
            self.assertIn('Experimental hint:', source)
            self.assertIn('Technical hint:', source)

    def test_hint_buttons_use_bronze_silver_gold_cost_labels(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertEqual(source.count("'Optional Hints (Bronze Key if locked)'"), 2, mission_id)
            self.assertEqual(source.count("'Reveal next hint (Silver Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count("'Reveal technical hint (Gold Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count('self.hint_access.request'), 4, mission_id)

    def test_optional_hint_entry_points_pass_correct_source_menus(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('self.hint_access.request, 1, briefing, hint1', source, mission_id)
            self.assertIn('self.hint_access.request, 1, menu, hint1', source, mission_id)

    def test_progressive_buttons_pass_correct_source_and_target_menus(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('self.hint_access.request, 2, hint1, hint2', source, mission_id)
            self.assertIn('self.hint_access.request, 3, hint2, hint3', source, mission_id)

    def test_integrated_mission_score_freezes_from_hint_level(self):
        system = HintSystem()
        system.unlock_hint('13', 1)
        system.unlock_hint('13', 2)
        system.sync_completed_missions(['13'])
        self.assertEqual(system.get_mission_score('13'), 2)

        system.state['mission_hints']['13'] = 3
        system.sync_completed_missions(['13'])
        self.assertEqual(system.get_mission_score('13'), 2)

    def test_final_rollout_also_scores_missions_31_and_35(self):
        system = HintSystem()
        system.sync_completed_missions(['31', '35'])
        self.assertEqual(system.state['mission_scores'], {'31': 5, '35': 5})
        self.assertEqual(system.state['legacy_unscored_missions'], [])

    def test_scientific_methods_remain_present(self):
        for mission_id in MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            tree = ast.parse(source)
            methods = {
                node.name
                for cls in tree.body if isinstance(cls, ast.ClassDef)
                for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            self.assertTrue(any(name.startswith('activate_mission') for name in methods), mission_id)
            self.assertIn('deliver_results', methods, mission_id)


if __name__ == '__main__':
    unittest.main()
