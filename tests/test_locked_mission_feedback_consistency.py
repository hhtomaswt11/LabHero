import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


class LockedMissionFeedbackConsistencyTests(unittest.TestCase):
    def _source(self, name):
        return (CODE / name).read_text(encoding="utf-8")

    def test_normal_yeast_npcs_use_transient_lock_feedback(self):
        previous = {"36": "35", "37": "36", "38": "37", "39": "38", "40": "39"}
        for mission_id, requirement in previous.items():
            with self.subTest(mission=mission_id):
                source = self._source(f"mission{mission_id}.py")
                self.assertIn(
                    f"animation_text_save('Complete Mission {requirement} first!', time=2500)",
                    source,
                )
                self.assertIn("self.toggle_menu()", source)
                tree = ast.parse(source)
                self.assertIsNotNone(tree)

    def test_normal_yeast_locked_branch_no_longer_renders_locked_dialogue(self):
        for mission_id in ("36", "37", "38", "39", "40"):
            with self.subTest(mission=mission_id):
                source = self._source(f"mission{mission_id}.py")
                self.assertNotIn("self.menu_message(locked, buttons=False)", source)

    def test_easy_locked_feedback_uses_same_transient_overlay(self):
        source = self._source("easy_mission_npc.py")
        self.assertIn("from functions import animation_text_save", source)
        self.assertIn("animation_text_save(f'Complete Mission {requirement} first!', time=2500)", source)
        self.assertNotIn("self.menu_message(locked, buttons=False)", source)
        self.assertIn("self.toggle_menu()", source)


if __name__ == "__main__":
    unittest.main()
