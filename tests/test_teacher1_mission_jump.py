import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from campaign import CampaignContext, NORMAL_MISSIONS, teacher_interaction_for_mission
from teacher_mode import (
    build_teacher_save_data,
    parse_teacher_argv,
    parse_teacher_query,
    previous_teacher_missions,
    validate_teacher_mission,
)


class Teacher1MissionJumpTests(unittest.TestCase):
    def test_web_query_contract(self):
        self.assertEqual(
            parse_teacher_query("?teacher=1&mission=17"),
            {"mission_id": "17", "source": "web"},
        )
        self.assertEqual(
            parse_teacher_query("?mission=7&teacher=true"),
            {"mission_id": "07", "source": "web"},
        )
        self.assertIsNone(parse_teacher_query("?teacher=0&mission=17"))
        self.assertIsNone(parse_teacher_query("?teacher=1&mission=41"))
        self.assertIsNone(parse_teacher_query("?teacher=1"))

    def test_desktop_cli_contract(self):
        self.assertEqual(
            parse_teacher_argv(["--teacher", "--mission", "17"]),
            {"mission_id": "17", "source": "desktop"},
        )
        self.assertEqual(
            parse_teacher_argv(["--teacher", "--mission=7"]),
            {"mission_id": "07", "source": "desktop"},
        )
        self.assertIsNone(parse_teacher_argv(["--mission", "17"]))
        self.assertIsNone(parse_teacher_argv(["--teacher", "--mission", "0"]))

    def test_teacher_mission_range_is_exactly_01_to_40(self):
        self.assertEqual(validate_teacher_mission("1"), "01")
        self.assertEqual(validate_teacher_mission("40"), "40")
        self.assertIsNone(validate_teacher_mission("00"))
        self.assertIsNone(validate_teacher_mission("41"))

    def test_previous_missions_stop_before_target(self):
        self.assertEqual(previous_teacher_missions("01"), ())
        self.assertEqual(previous_teacher_missions("03"), ("01", "02"))
        self.assertEqual(previous_teacher_missions("40")[-1], "39")

    def test_teacher_payload_is_isolated_campaign_state(self):
        data = build_teacher_save_data("17")
        self.assertEqual(len(data), 6)
        self.assertEqual(data[0], "Teacher Preview")
        self.assertEqual(data[4]["campaign_mode"], "teacher")
        self.assertTrue(data[4]["name_confirmed"])
        self.assertTrue(data[4]["final_results_seen"])
        self.assertIn("16", data[3])
        self.assertNotIn("17", data[3])
        self.assertIn("16", data[2])
        self.assertNotIn("17", data[2])
        self.assertIn("16", data[5]["legacy_unscored_missions"])

    def test_teacher_campaign_bypasses_all_gates_and_unlocks_target(self):
        context = CampaignContext("teacher")
        self.assertTrue(context.should_gate_be_open("06", []))
        self.assertTrue(context.should_gate_be_open("35", []))
        self.assertTrue(context.is_mission_unlocked("01", []))
        self.assertTrue(context.is_mission_unlocked("40", []))

    def test_teacher_interaction_metadata_covers_all_missions(self):
        missing = [mid for mid in NORMAL_MISSIONS if teacher_interaction_for_mission(mid) is None]
        self.assertEqual(missing, [])
        self.assertEqual(teacher_interaction_for_mission("17"), "Mission16")
        self.assertEqual(teacher_interaction_for_mission("36"), "Vale")
        self.assertEqual(teacher_interaction_for_mission("40"), "Mortis")

    def test_teacher_launcher_is_lazy(self):
        source = (CODE / "teacher_mission_launcher.py").read_text(encoding="utf-8")
        self.assertIn("importlib.import_module", source)
        self.assertNotIn("from mission17 import", source)
        self.assertIn('f"mission{self.mission_id}"', source)

    def test_game_boot_uses_teacher_namespace_and_fresh_payload(self):
        source = (ROOT / "LabHero.py").read_text(encoding="utf-8")
        self.assertIn("get_teacher_request()", source)
        self.assertIn("set_save_namespace('teacher')", source)
        self.assertIn("clear_active_persistent_storage()", source)
        self.assertIn("build_teacher_save_data(mission_id)", source)
        self.assertIn("teacher_target_mission=mission_id", source)

    def test_level_opens_target_and_supports_t_shortcut(self):
        source = (CODE / "level.py").read_text(encoding="utf-8")
        self.assertIn("teacher_target_mission=None", source)
        self.assertIn("TeacherMissionLauncher", source)
        self.assertIn("pygame.K_t", source)
        self.assertIn("self.teacher_launch_pending = True", source)

    def test_teacher_mode_never_shows_student_final_results(self):
        source = (CODE / "level.py").read_text(encoding="utf-8")
        self.assertIn("self.campaign_context.mode != 'teacher'", source)

    def test_save_namespace_keeps_normal_web_prefix_unchanged(self):
        save_source = (CODE / "save_load.py").read_text(encoding="utf-8")
        utils_source = (CODE / "utils.py").read_text(encoding="utf-8")
        self.assertIn("_WEB_STORAGE_PREFIX = 'labhero:v1:'", save_source)
        self.assertIn("labhero:{namespace}:v1:", save_source)
        self.assertIn("def set_save_namespace", utils_source)
        self.assertIn("if namespace:", utils_source)


if __name__ == "__main__":
    unittest.main()
