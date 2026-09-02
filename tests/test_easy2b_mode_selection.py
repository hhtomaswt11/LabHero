import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from campaign import (
    CampaignContext,
    EASY_INTERACTION_MISSIONS,
    NORMAL_INTERACTION_MISSIONS,
    STUDENT_CAMPAIGN_MODES,
)


class Easy2BModeSelectionTests(unittest.TestCase):
    def test_only_normal_and_easy_are_student_selectable(self):
        self.assertEqual(STUDENT_CAMPAIGN_MODES, ('normal', 'easy'))
        self.assertNotIn('teacher', STUDENT_CAMPAIGN_MODES)

    def test_easy_interactions_route_to_curated_missions(self):
        ctx = CampaignContext('easy')
        expected = {
            'Mission01': '01', 'Mission02': '03', 'Mission03': '06',
            'Mission07': '07', 'Mission11': '13', 'Mission16': '18',
            'Mission21': '21', 'Mission23': '23', 'Mission25': '25',
            'Mission27': '27', 'Vale': '36',
        }
        self.assertEqual(EASY_INTERACTION_MISSIONS, expected)
        for interaction, mission_id in expected.items():
            self.assertEqual(ctx.mission_for_interaction(interaction), mission_id)
            self.assertTrue(ctx.interaction_is_available(interaction))

    def test_easy_excludes_late_normal_only_entry_points(self):
        ctx = CampaignContext('easy')
        for interaction in ('Mission29', 'Mission32', 'Final', 'Voss', 'Umbra', 'Morbus', 'Mortis'):
            self.assertIsNone(ctx.mission_for_interaction(interaction))
            self.assertFalse(ctx.interaction_is_available(interaction))

    def test_normal_interaction_contract_is_unchanged(self):
        ctx = CampaignContext('normal')
        self.assertEqual(ctx.mission_for_interaction('Mission11'), '11')
        self.assertEqual(ctx.mission_for_interaction('Mission16'), '16')
        self.assertEqual(ctx.mission_for_interaction('Final'), '35')
        self.assertEqual(ctx.mission_for_interaction('Mortis'), '40')
        self.assertEqual(len(NORMAL_INTERACTION_MISSIONS), 18)

    def test_registration_ui_collects_name_then_mode_and_confirms_atomically(self):
        source = (CODE / 'student_registration.py').read_text(encoding='utf-8')
        self.assertIn('Choose Campaign Mode', source)
        self.assertIn('Normal - full 40-mission campaign', source)
        self.assertIn('Easy - curated 11-mission classroom route', source)
        self.assertIn('Confirm Campaign', source)
        self.assertIn('register_student_campaign(candidate["name"], candidate["mode"])', source)
        self.assertIn('campaign_changed_callback', source)
        self.assertLess(source.index('Confirm Student'), source.index('Choose Campaign Mode'))
        self.assertLess(source.index('Choose Campaign Mode'), source.index('Confirm Campaign'))

    def test_player_locks_name_and_mode_together_before_progress(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn('def register_student_campaign(self, value, campaign_mode):', source)
        self.assertIn('if self.name_confirmed or self.missions_activated or self.missions_completed:', source)
        self.assertIn('self.campaign_mode = mode', source)
        self.assertIn('self.name_confirmed = True', source)
        self.assertIn('interaction_is_available(interaction_name)', source)
        self.assertIn('not part of your Easy campaign route', source)

    def test_level_refreshes_gate_context_after_mode_choice(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn('self.refresh_campaign_context,', source)
        self.assertIn('def refresh_campaign_context(self):', source)
        self.assertIn('gate.campaign_context = self.campaign_context', source)
        self.assertIn('gate.sync_with_progression()', source)

    def test_easy_npcs_open_only_the_selected_single_missions(self):
        level = (CODE / 'level.py').read_text(encoding='utf-8')
        expected_ids = ('01', '03', '06', '07', '13', '18', '21', '23', '25', '27', '36')
        for mission_id in expected_ids:
            self.assertIn(f"EasyMissionNPC(", level)
            self.assertIn(f"self.player, '{mission_id}')", level)
        easy_npc = (CODE / 'easy_mission_npc.py').read_text(encoding='utf-8')
        for mission_id in expected_ids:
            self.assertIn(f"'{mission_id}': {{", easy_npc)
        self.assertIn("from mission13 import Mission13_info", easy_npc)
        self.assertIn("from mission18 import Mission18_info", easy_npc)

    def test_normal_controllers_remain_available(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        for module_class in (
            'from mission01 import Mission01',
            'from mission03 import Mission03',
            'from mission06 import Mission06',
            'from mission07 import Mission07',
            'from mission11 import Mission11',
            'from mission16 import Mission16',
            'from mission21 import Mission21',
            'from mission23 import Mission23',
            'from mission25 import Mission25',
            'from mission27 import Mission27',
            'from mission36 import Mission36',
        ):
            self.assertIn(module_class, source)

    def test_m13_briefing_is_self_contained_in_easy_but_preserves_normal_copy(self):
        source = (CODE / 'mission13.py').read_text(encoding='utf-8')
        self.assertIn("self.player.campaign_mode == 'easy'", source)
        self.assertIn('Use an anaerobic succinate-optimisation setup', source)
        self.assertIn('from Mission 12', source)

    def test_settings_displays_locked_campaign_mode(self):
        source = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        self.assertIn("Mode: {self.player.campaign_mode.title()}", source)


if __name__ == '__main__':
    unittest.main()
