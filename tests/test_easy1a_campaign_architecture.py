import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from campaign import (
    CampaignContext,
    NORMAL_MISSIONS,
    EASY_MISSIONS,
    normalize_campaign_mode,
)


class Easy1ACampaignArchitectureTests(unittest.TestCase):
    def test_normal_contains_all_40_missions(self):
        ctx = CampaignContext("normal")
        self.assertEqual(len(NORMAL_MISSIONS), 40)
        self.assertEqual(ctx.mission_count, 40)
        self.assertEqual(ctx.first_mission, "01")
        self.assertEqual(ctx.final_mission, "40")
        self.assertEqual(ctx.max_score, 200)

    def test_normal_sequence_navigation(self):
        ctx = CampaignContext("normal")
        self.assertIsNone(ctx.previous_mission("01"))
        self.assertEqual(ctx.next_mission("01"), "02")
        self.assertEqual(ctx.previous_mission("Mission 20"), "19")
        self.assertEqual(ctx.next_mission(39), "40")
        self.assertIsNone(ctx.next_mission("40"))

    def test_easy_is_configured_by_easy2(self):
        self.assertIsNotNone(EASY_MISSIONS)
        ctx = CampaignContext("easy")
        self.assertTrue(ctx.is_configured)
        self.assertEqual(ctx.mission_count, 11)
        self.assertEqual(ctx.max_score, 55)
        self.assertEqual(ctx.first_mission, "01")
        self.assertEqual(ctx.final_mission, "36")

    def test_teacher_uses_full_sequence_but_bypasses_gates(self):
        ctx = CampaignContext("teacher")
        self.assertEqual(ctx.mission_count, 40)
        self.assertTrue(ctx.should_gate_be_open("35", []))

    def test_normal_gate_semantics_are_unchanged(self):
        ctx = CampaignContext("normal")
        self.assertFalse(ctx.should_gate_be_open("06", ["01", "02"]))
        self.assertTrue(ctx.should_gate_be_open(6, ["06"]))
        self.assertTrue(ctx.should_gate_be_open("Mission35", ["35"]))

    def test_campaign_completion_uses_mode_final_mission(self):
        ctx = CampaignContext("normal")
        self.assertFalse(ctx.is_campaign_complete(["01", "39"]))
        self.assertTrue(ctx.is_campaign_complete(["40"]))

    def test_completed_missions_are_filtered_to_mode_sequence(self):
        ctx = CampaignContext("normal")
        self.assertEqual(ctx.completed_missions_in_mode(["02", "99", "01"]), ("01", "02"))

    def test_mode_normalizer_is_safe_for_historic_or_bad_values(self):
        self.assertEqual(normalize_campaign_mode(None), "normal")
        self.assertEqual(normalize_campaign_mode(" NORMAL "), "normal")
        self.assertEqual(normalize_campaign_mode("easy"), "easy")
        self.assertEqual(normalize_campaign_mode("unexpected"), "normal")

    def test_default_player_state_persists_normal_mode(self):
        source = (ROOT / "code" / "settings.py").read_text(encoding="utf-8")
        self.assertIn("'campaign_mode': 'normal'", source)

    def test_player_serializes_campaign_mode_without_save_schema_change(self):
        source = (ROOT / "code" / "player.py").read_text(encoding="utf-8")
        self.assertIn("'campaign_mode': self.campaign_mode", source)
        self.assertIn("self.campaign_mode = normalize_campaign_mode", source)
        self.assertIn("return [\n            self.player_name,", source)

    def test_level_restores_context_before_gates(self):
        source = (ROOT / "code" / "level.py").read_text(encoding="utf-8")
        restore = "self.campaign_context = CampaignContext(mode=self.player.campaign_mode)"
        gates = "self._setup_progression_gates(tmx_data)"
        self.assertIn(restore, source)
        self.assertLess(source.index(restore), source.index(gates))


if __name__ == "__main__":
    unittest.main()
