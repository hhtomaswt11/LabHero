import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from campaign import CampaignContext, normalize_mission_id


class Game1AProgressionGateTests(unittest.TestCase):
    def test_mission_id_normalization(self):
        self.assertEqual(normalize_mission_id(6), "06")
        self.assertEqual(normalize_mission_id("06"), "06")
        self.assertEqual(normalize_mission_id("Mission35"), "35")

    def test_normal_gate_closed_before_mission(self):
        self.assertFalse(CampaignContext("normal").should_gate_be_open("06", ["01", "05"]))

    def test_normal_gate_opens_after_mission(self):
        self.assertTrue(CampaignContext("normal").should_gate_be_open("06", ["01", "06"]))
        self.assertTrue(CampaignContext("normal").should_gate_be_open(35, ["35"]))

    def test_teacher_bypasses_gates(self):
        self.assertTrue(CampaignContext("teacher").should_gate_be_open("35", []))

    def test_easy_uses_curated_progression_milestones(self):
        ctx = CampaignContext("easy")
        self.assertFalse(ctx.should_gate_be_open("06", ["03"]))
        self.assertTrue(ctx.should_gate_be_open("06", ["06"]))
        self.assertFalse(ctx.should_gate_be_open("35", ["25"]))
        self.assertTrue(ctx.should_gate_be_open("35", ["27"]))

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            CampaignContext("invalid")

    def test_level_contract_is_optional_and_uses_unlock_after(self):
        src = (ROOT / "code/level.py").read_text(encoding="utf-8")
        self.assertIn("_optional_tmx_layer(tmx_data, 'ProgressionGates')", src)
        self.assertIn("properties.get('unlock_after')", src)
        self.assertIn("self._setup_progression_gates(tmx_data)", src)

    def test_gates_created_after_player_loop(self):
        src = (ROOT / "code/level.py").read_text(encoding="utf-8")
        self.assertLess(
            src.index("for obj in tmx_data.get_layer_by_name('Player')"),
            src.index("self._setup_progression_gates(tmx_data)")
        )

    def test_gate_is_drawn_collidable_and_dynamic(self):
        src = (ROOT / "code/level.py").read_text(encoding="utf-8")
        for group in ("self.all_sprites", "self.dynamic_sprites",
                      "self.collision_sprites", "self.progression_gate_sprites"):
            self.assertIn(group, src)

    def test_gate_kill_removes_draw_and_collision_membership(self):
        src = (ROOT / "code/sprites.py").read_text(encoding="utf-8")
        self.assertIn("class ProgressionGate", src)
        self.assertIn("self.hitbox = self.rect.copy()", src)
        self.assertIn("self.kill()", src)


if __name__ == "__main__":
    unittest.main()
