import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from campaign import CampaignContext, EASY_MISSIONS
from progression import is_model_unlocked


EXPECTED_EASY = (
    "01", "03", "06", "07", "13", "18",
    "21", "23", "25", "27", "36",
)


class Easy2ACuratedProgressionTests(unittest.TestCase):
    def test_easy_sequence_is_the_reviewed_11_mission_route(self):
        self.assertEqual(EASY_MISSIONS, EXPECTED_EASY)
        ctx = CampaignContext("easy")
        self.assertTrue(ctx.is_configured)
        self.assertEqual(ctx.mission_count, 11)
        self.assertEqual(ctx.first_mission, "01")
        self.assertEqual(ctx.final_mission, "36")
        self.assertEqual(ctx.max_score, 55)

    def test_easy_navigation_skips_normal_only_missions(self):
        ctx = CampaignContext("easy")
        self.assertEqual(ctx.next_mission("01"), "03")
        self.assertEqual(ctx.previous_mission("03"), "01")
        self.assertEqual(ctx.next_mission("07"), "13")
        self.assertEqual(ctx.previous_mission("13"), "07")
        self.assertEqual(ctx.next_mission("27"), "36")

    def test_easy_unlocks_use_actual_easy_predecessor(self):
        ctx = CampaignContext("easy")
        self.assertFalse(ctx.is_mission_unlocked("03", []))
        self.assertTrue(ctx.is_mission_unlocked("03", ["01"]))
        self.assertFalse(ctx.is_mission_unlocked("13", ["12"]))
        self.assertTrue(ctx.is_mission_unlocked("13", ["07"]))
        self.assertFalse(ctx.is_mission_unlocked("36", ["35"]))
        self.assertTrue(ctx.is_mission_unlocked("36", ["27"]))

    def test_skipped_missions_are_not_playable_or_falsely_completed(self):
        ctx = CampaignContext("easy")
        completed = ["01", "03", "06", "07"]
        self.assertFalse(ctx.includes_mission("02"))
        self.assertFalse(ctx.is_mission_unlocked("02", completed))
        self.assertFalse(ctx.is_mission_effectively_completed("02", completed))
        self.assertEqual(
            ctx.completed_missions_in_mode(completed),
            ("01", "03", "06", "07"),
        )

    def test_normal_prerequisites_are_unchanged(self):
        ctx = CampaignContext("normal")
        self.assertFalse(ctx.is_mission_unlocked("13", ["07"]))
        self.assertTrue(ctx.is_mission_unlocked("13", ["12"]))
        self.assertFalse(ctx.is_mission_unlocked("36", ["27"]))
        self.assertTrue(ctx.is_mission_unlocked("36", ["35"]))
        self.assertEqual(ctx.max_score, 200)

    def test_easy_gate06_still_requires_real_mission06(self):
        ctx = CampaignContext("easy")
        self.assertFalse(ctx.should_gate_be_open("06", ["03"]))
        self.assertTrue(ctx.should_gate_be_open("06", ["06"]))

    def test_easy_gate35_maps_to_last_pre_yeast_mission_without_fake_completion(self):
        ctx = CampaignContext("easy")
        self.assertEqual(ctx.progression_milestone_for("35"), "27")
        self.assertFalse(ctx.should_gate_be_open("35", ["25"]))
        self.assertTrue(ctx.should_gate_be_open("35", ["27"]))
        self.assertFalse(ctx.is_mission_effectively_completed("35", ["27"]))

    def test_yeast_model_unlock_uses_campaign_context_only_when_supplied(self):
        easy = CampaignContext("easy")
        normal = CampaignContext("normal")
        self.assertTrue(is_model_unlocked("yeast_iMM904", ["27"], easy))
        self.assertFalse(is_model_unlocked("yeast_iMM904", ["27"], normal))
        self.assertFalse(is_model_unlocked("yeast_iMM904", ["27"]))
        self.assertTrue(is_model_unlocked("yeast_iMM904", ["35"]))

    def test_easy_campaign_completion_is_mission36(self):
        ctx = CampaignContext("easy")
        self.assertFalse(ctx.is_campaign_complete(["27"]))
        self.assertTrue(ctx.is_campaign_complete(["36"]))

    def test_runtime_missions_use_campaign_aware_player_unlocks(self):
        # Mission 01 is the first mission and has no predecessor check.  Every
        # later mission must consult the campaign policy so skipped Easy
        # missions cannot be activated through an NPC chain by accident.
        for number in range(2, 41):
            mission_id = f"{number:02d}"
            source = (ROOT / "code" / f"mission{mission_id}.py").read_text(encoding="utf-8")
            self.assertIn(
                f"self.player.is_mission_unlocked('{mission_id}')",
                source,
                msg=f"Mission {mission_id} still uses only the Normal predecessor.",
            )
            self.assertNotIn(
                f"is_mission{mission_id}_unlocked(self.missions_completed)",
                source,
            )

    def test_level_uses_campaign_context_for_yeast_model_unlock(self):
        source = (ROOT / "code" / "level.py").read_text(encoding="utf-8")
        self.assertIn(
            "is_model_unlocked('yeast_iMM904', self.player.missions_completed, self.campaign_context)",
            source,
        )
        self.assertIn("progression_milestone_for('35')", source)


if __name__ == "__main__":
    unittest.main()
