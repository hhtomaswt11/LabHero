import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from campaign import EASY_MISSIONS, NORMAL_MISSIONS, teacher_interaction_for_mission
from hint_system import initial_keys_for_campaign
from teacher_mode import (
    build_teacher_save_data,
    parse_teacher_argv,
    parse_teacher_web_request,
    previous_teacher_missions,
    teacher_missions_for_mode,
    validate_teacher_mission,
)


class TeacherMissionJumpTests(unittest.TestCase):
    def test_web_teacher_entry_requires_protected_path_and_defaults_to_normal(self):
        self.assertEqual(
            parse_teacher_web_request('/teacher/', '?mission=17'),
            {'mission_id': '17', 'campaign_mode': 'normal', 'source': 'web'},
        )
        self.assertIsNone(parse_teacher_web_request('/', '?teacher=1&mission=17'))
        self.assertIsNone(parse_teacher_web_request('/teacher/', '?mission=41'))

    def test_web_easy_preview_uses_canonical_easy_ids(self):
        self.assertEqual(
            parse_teacher_web_request('/teacher/', '?mission=25&mode=easy'),
            {'mission_id': '25', 'campaign_mode': 'easy', 'source': 'web'},
        )
        self.assertIsNone(
            parse_teacher_web_request('/teacher/', '?mission=17&mode=easy')
        )

    def test_desktop_cli_supports_normal_and_easy(self):
        self.assertEqual(
            parse_teacher_argv(['--teacher', '--mission', '17']),
            {'mission_id': '17', 'campaign_mode': 'normal', 'source': 'desktop'},
        )
        self.assertEqual(
            parse_teacher_argv(['--teacher', '--mission=25', '--mode', 'easy']),
            {'mission_id': '25', 'campaign_mode': 'easy', 'source': 'desktop'},
        )
        self.assertIsNone(parse_teacher_argv(['--mission', '17']))
        self.assertIsNone(parse_teacher_argv(['--teacher', '--mission', '17', '--mode', 'easy']))

    def test_normal_teacher_range_is_exactly_01_to_40(self):
        self.assertEqual(teacher_missions_for_mode('normal'), NORMAL_MISSIONS)
        self.assertEqual(validate_teacher_mission('1', 'normal'), '01')
        self.assertEqual(validate_teacher_mission('40', 'normal'), '40')
        self.assertIsNone(validate_teacher_mission('00', 'normal'))
        self.assertIsNone(validate_teacher_mission('41', 'normal'))

    def test_easy_uses_same_canonical_ids_so_no_number_mapping_is_required(self):
        self.assertEqual(teacher_missions_for_mode('easy'), EASY_MISSIONS)
        self.assertTrue(set(EASY_MISSIONS).issubset(set(NORMAL_MISSIONS)))
        for mission_id in EASY_MISSIONS:
            self.assertEqual(validate_teacher_mission(mission_id, 'easy'), mission_id)
        self.assertIsNone(validate_teacher_mission('02', 'easy'))

    def test_previous_teacher_missions_follow_selected_route(self):
        self.assertEqual(previous_teacher_missions('01', 'normal'), ())
        self.assertEqual(previous_teacher_missions('03', 'normal'), ('01', '02'))
        self.assertEqual(previous_teacher_missions('40', 'normal')[-1], '39')
        self.assertEqual(
            previous_teacher_missions('25', 'easy'),
            ('01', '03', '06', '07', '13', '18', '21', '23'),
        )

    def test_normal_teacher_payload_is_isolated_and_uses_normal_context(self):
        data = build_teacher_save_data('17', 'normal')
        self.assertEqual(len(data), 6)
        self.assertEqual(data[0], 'Teacher Preview')
        self.assertEqual(data[4]['campaign_mode'], 'normal')
        self.assertTrue(data[4]['name_confirmed'])
        self.assertTrue(data[4]['final_results_seen'])
        self.assertIn('16', data[3])
        self.assertNotIn('17', data[3])
        self.assertIn('16', data[2])
        self.assertNotIn('17', data[2])
        self.assertIn('16', data[5]['legacy_unscored_missions'])
        self.assertEqual(data[5]['keys'], initial_keys_for_campaign('normal'))

    def test_easy_teacher_payload_marks_only_easy_predecessors(self):
        data = build_teacher_save_data('25', 'easy')
        expected = {'01', '03', '06', '07', '13', '18', '21', '23'}
        self.assertEqual(data[4]['campaign_mode'], 'easy')
        self.assertEqual(set(data[3]), expected)
        self.assertEqual(set(data[2]), expected)
        self.assertNotIn('02', data[3])
        self.assertNotIn('25', data[3])
        self.assertEqual(data[5]['keys'], initial_keys_for_campaign('easy'))

    def test_teacher_interaction_metadata_covers_all_normal_missions(self):
        missing = [
            mission_id for mission_id in NORMAL_MISSIONS
            if teacher_interaction_for_mission(mission_id) is None
        ]
        self.assertEqual(missing, [])
        self.assertEqual(teacher_interaction_for_mission('17'), 'Mission16')
        self.assertEqual(teacher_interaction_for_mission('36'), 'Vale')
        self.assertEqual(teacher_interaction_for_mission('40'), 'Mortis')

    def test_teacher_launcher_remains_lazy(self):
        source = (CODE / 'teacher_mission_launcher.py').read_text(encoding='utf-8')
        self.assertIn('importlib.import_module', source)
        self.assertNotIn('from mission17 import', source)
        self.assertIn('f"mission{self.mission_id}"', source)

    def test_game_boot_uses_separate_teacher_namespace_and_fresh_route_payload(self):
        source = (ROOT / 'LabHero.py').read_text(encoding='utf-8')
        self.assertIn('get_teacher_request()', source)
        self.assertIn("set_save_namespace('teacher')", source)
        self.assertIn('clear_active_persistent_storage()', source)
        self.assertIn('build_teacher_save_data(mission_id, campaign_mode)', source)
        self.assertIn('teacher_target_mission=mission_id', source)
        self.assertIn('teacher_preview=True', source)
        self.assertIn('set_save_namespace(None)', source)

    def test_level_opens_target_supports_t_banner_and_suppresses_student_results(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn('teacher_target_mission=None, teacher_preview=False', source)
        self.assertIn('TeacherMissionLauncher', source)
        self.assertIn('pygame.K_t', source)
        self.assertIn('self.teacher_launch_pending = True', source)
        self.assertIn('not self.teacher_preview', source)
        self.assertIn('TEACHER PREVIEW - {mode} - MISSION {target}', source)
        self.assertIn('Student save is isolated. T reopens target; M can change mission.', source)

    def test_settings_offer_teacher_switch_and_clean_exit_to_title(self):
        source = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        self.assertIn("getattr(self.player, 'teacher_preview', False)", source)
        self.assertIn("menu.add.button('Change Teacher Mission', teacher_switch)", source)
        self.assertIn("'Switch to Normal Mission'", source)
        self.assertIn("'Switch to Easy Mission'", source)
        self.assertIn('self.player.teacher_switch_request = request', source)
        self.assertIn("menu.add.button('Exit Teacher Preview', back_to_title)", source)
        self.assertIn('self.player.restart_to_intro = True', source)


if __name__ == '__main__':
    unittest.main()
