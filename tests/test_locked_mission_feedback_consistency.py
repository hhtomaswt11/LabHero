import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


class LockedMissionFeedbackConsistencyTests(unittest.TestCase):
    def _source(self, name):
        return (CODE / name).read_text(encoding="utf-8")

    def test_normal_yeast_mission_menus_keep_direct_activation_guard(self):
        # Direct access to a locked mission menu still needs a transient guard.
        # This is separate from talking to the scientist on the map, where the
        # selected final UX is for the scientist to explain why the mission is
        # locked in their normal dialogue panel.
        previous = {"36": "35", "37": "36", "38": "37", "39": "38", "40": "39"}
        for mission_id, requirement in previous.items():
            with self.subTest(mission=mission_id):
                source = self._source(f"mission{mission_id}.py")
                self.assertIn(
                    f"animation_text_save('Complete Mission {requirement} first!', time=2500)",
                    source,
                )
                tree = ast.parse(source)
                self.assertIsNotNone(tree)

    def test_normal_yeast_locked_npc_branch_uses_scientist_dialogue(self):
        for mission_id in ("36", "37", "38", "39", "40"):
            with self.subTest(mission=mission_id):
                source = self._source(f"mission{mission_id}.py")
                self.assertIn("self.menu_message(locked, buttons=False)", source)

    def test_easy_locked_npc_branch_uses_scientist_dialogue(self):
        source = self._source("easy_mission_npc.py")
        self.assertIn("self.menu_message(locked, buttons=False)", source)
        self.assertNotIn("from functions import animation_text_save", source)
        self.assertIn("Complete Mission {requirement} first in your Easy campaign.", source)


if __name__ == "__main__":
    unittest.main()
