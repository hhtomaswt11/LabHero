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
STANDARD_MISSIONS = tuple(f'{mission:02d}' for mission in range(31, 36))
YEAST_FINAL_MISSIONS = tuple(f'{mission:02d}' for mission in range(36, 41))

PRESERVED_HINT_SNIPPETS = {
    '36': 'A configured bound is not automatically active. Compare the realised O2 uptake',
    '37': 'Do not equate the number of knocked-out genes with the number of disabled reactions.',
    '38': 'Compare the same candidate in two backgrounds. A useful background-specific vulnerability',
    '39': 'Think about pathway order. Pyruvate lies before the blocked decarboxylase step',
    '40': 'Compare rows horizontally between the two curves. A qualifying rescue row needs acetaldehyde uptake',
}


class P4EFinalMissionHintRolloutTests(unittest.TestCase):
    def test_all_40_missions_are_tracked(self):
        self.assertEqual(TRACKED_HINT_MISSIONS, EXPECTED_TRACKED)

    def test_mission31_35_use_common_access_helper_and_existing_three_levels(self):
        for mission_id in STANDARD_MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('from hint_ui import MissionHintAccess', source, mission_id)
            self.assertIn(
                f"MissionHintAccess(self.player, '{mission_id}', self.missions_completed, mytheme)",
                source,
                mission_id,
            )
            self.assertEqual(source.count("'Optional Hints (Bronze Key if locked)'"), 2, mission_id)
            self.assertEqual(source.count("'Reveal next hint (Silver Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count("'Reveal technical hint (Gold Key if locked)'"), 1, mission_id)
            self.assertIn('self.hint_access.request, 1, briefing, hint1', source, mission_id)
            self.assertIn('self.hint_access.request, 1, menu, hint1', source, mission_id)
            self.assertIn('self.hint_access.request, 2, hint1, hint2', source, mission_id)
            self.assertIn('self.hint_access.request, 3, hint2, hint3', source, mission_id)

    def test_mission36_40_now_have_three_progressive_levels(self):
        for mission_id in YEAST_FINAL_MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('Conceptual hint:', source, mission_id)
            self.assertIn('Experimental hint:', source, mission_id)
            self.assertIn('Technical hint:', source, mission_id)
            self.assertIn(f"title='Mission {mission_id} Hint 1'", source, mission_id)
            self.assertIn(f"title='Mission {mission_id} Hint 2'", source, mission_id)
            self.assertIn(f"title='Mission {mission_id} Hint 3'", source, mission_id)

    def test_mission36_40_use_bronze_silver_gold_access(self):
        for mission_id in YEAST_FINAL_MISSIONS:
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('from hint_ui import MissionHintAccess', source, mission_id)
            self.assertIn(
                f"MissionHintAccess(self.player, '{mission_id}', self.missions_completed, mytheme)",
                source,
                mission_id,
            )
            # These missions historically had one main-menu Optional Hint entry.
            self.assertEqual(source.count("'Optional Hints (Bronze Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count("'Reveal next hint (Silver Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count("'Reveal technical hint (Gold Key if locked)'"), 1, mission_id)
            self.assertEqual(source.count('self.hint_access.request'), 3, mission_id)
            self.assertIn('self.hint_access.request, 1, menu, hint1', source, mission_id)
            self.assertIn('self.hint_access.request, 2, hint1, hint2', source, mission_id)
            self.assertIn('self.hint_access.request, 3, hint2, hint3', source, mission_id)

    def test_original_mission36_40_hint_content_is_preserved_at_a_progressive_level(self):
        for mission_id, snippet in PRESERVED_HINT_SNIPPETS.items():
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn(snippet, source, mission_id)

    def test_every_mission_now_exposes_conceptual_experimental_and_technical_hint_text(self):
        for mission in range(1, 41):
            mission_id = f'{mission:02d}'
            source = (CODE / f'mission{mission_id}.py').read_text(encoding='utf-8')
            self.assertIn('Conceptual hint:', source, mission_id)
            self.assertIn('Experimental hint:', source, mission_id)
            self.assertIn('Technical hint:', source, mission_id)

    def test_mission40_three_hints_freeze_one_point_score(self):
        system = HintSystem()
        for level in (1, 2, 3):
            result = system.unlock_hint('40', level)
            self.assertEqual(result['status'], 'unlocked')
        system.sync_completed_missions(['40'])
        self.assertEqual(system.get_mission_score('40'), 1)
        system.state['mission_hints']['40'] = 0
        system.sync_completed_missions(['40'])
        self.assertEqual(system.get_mission_score('40'), 1)

    def test_all_40_perfect_missions_total_200(self):
        system = HintSystem()
        system.sync_completed_missions([f'{mission:02d}' for mission in range(1, 41)])
        self.assertEqual(system.get_total_score(), 200)
        self.assertEqual(len(system.state['mission_scores']), 40)
        self.assertEqual(system.state['legacy_unscored_missions'], [])

    def test_legacy_completed_final_mission_remains_unscored_after_rollout(self):
        system = HintSystem(state=None, legacy_completed=['40'])
        system.sync_completed_missions(['40'])
        self.assertIsNone(system.get_mission_score('40'))
        self.assertEqual(system.state['legacy_unscored_missions'], ['40'])

    def test_mission31_40_scientific_lifecycle_methods_remain_present(self):
        for mission in range(31, 41):
            mission_id = f'{mission:02d}'
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
