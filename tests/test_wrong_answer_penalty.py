import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import (  # noqa: E402
    HintSystem,
    MAX_MISSION_SCORE,
    MIN_MISSION_SCORE,
    REWARD_STATE_VERSION,
    WRONG_ANSWER_PENALTY,
    normalize_reward_state,
)


WRITTEN_ANSWER_MISSIONS = (
    "02", "03", "04", "05",
    *tuple(f"{number:02d}" for number in range(9, 41)),
)


class WrongAnswerPenaltySystemTests(unittest.TestCase):
    def test_fresh_state_tracks_no_wrong_answers(self):
        system = HintSystem()
        self.assertEqual(REWARD_STATE_VERSION, 2)
        self.assertEqual(system.state["mission_wrong_answers"], {})
        self.assertEqual(system.get_wrong_answer_count("10"), 0)
        self.assertEqual(system.get_current_mission_score("10"), 5)

    def test_each_wrong_submission_costs_one_point_and_clamps_at_zero(self):
        system = HintSystem()

        expected = [4, 3, 2, 1, 0, 0]
        for current_score in expected:
            result = system.record_wrong_answer("10")
            self.assertEqual(result["applied"], WRONG_ANSWER_PENALTY)
            self.assertEqual(result["current_score"], current_score)

        self.assertEqual(system.get_wrong_answer_count("10"), 6)
        self.assertEqual(system.get_current_mission_score("10"), MIN_MISSION_SCORE)

    def test_hint_and_wrong_answer_penalties_are_cumulative(self):
        system = HintSystem()
        system.record_wrong_answer("12")       # 5 -> 4
        system.unlock_hint("12", 1)            # hint base becomes 3; wrong answer => 2
        self.assertEqual(system.get_current_mission_score("12"), 2)

        system.record_wrong_answer("12")       # 2 -> 1
        self.assertEqual(system.get_current_mission_score("12"), 1)

        system.unlock_hint("12", 2)            # hint base 2 minus two wrong => 0
        self.assertEqual(system.get_current_mission_score("12"), 0)

    def test_completion_freezes_penalized_score(self):
        system = HintSystem()
        system.record_wrong_answer("34")
        self.assertEqual(system.finalize_mission_score("34"), 4)
        self.assertEqual(system.get_mission_score("34"), 4)

        # Completed scores are immutable; accidental later calls cannot charge
        # the same completed mission again.
        result = system.record_wrong_answer("34")
        self.assertEqual(result["applied"], 0)
        self.assertTrue(result["finalized"])
        self.assertEqual(system.get_mission_score("34"), 4)

    def test_zero_point_completed_mission_is_valid_and_persistent(self):
        system = HintSystem()
        for _ in range(7):
            system.record_wrong_answer("39")
        self.assertEqual(system.finalize_mission_score("39"), 0)

        reloaded = HintSystem(system.to_dict())
        self.assertEqual(reloaded.get_mission_score("39"), 0)
        self.assertEqual(reloaded.get_wrong_answer_count("39"), 7)

    def test_old_reward_state_migrates_without_inventing_penalties(self):
        old_state = {
            "version": 1,
            "keys": {"bronze": 14, "silver": 10, "gold": 5},
            "mission_hints": {"02": 1},
            "mission_scores": {"02": 3},
            "legacy_unscored_missions": [],
        }
        migrated = normalize_reward_state(old_state)
        self.assertEqual(migrated["version"], REWARD_STATE_VERSION)
        self.assertEqual(migrated["mission_scores"], {"02": 3})
        self.assertEqual(migrated["mission_wrong_answers"], {})

    def test_version_two_accepts_new_intermediate_and_zero_scores(self):
        state = normalize_reward_state({
            "version": 2,
            "mission_scores": {"02": 4, "03": 0, "04": 5},
            "mission_wrong_answers": {"02": 1, "03": 8},
        })
        self.assertEqual(state["mission_scores"], {"02": 4, "03": 0, "04": 5})
        self.assertEqual(state["mission_wrong_answers"], {"02": 1, "03": 8})

    def test_maximum_score_contract_is_unchanged(self):
        system = HintSystem()
        self.assertEqual(MAX_MISSION_SCORE, 5)
        self.assertEqual(system.get_max_score(40), 200)
        self.assertEqual(system.get_max_score(11), 55)


class WrongAnswerPenaltyIntegrationContractTests(unittest.TestCase):
    def test_every_written_answer_mission_calls_shared_penalty_helper(self):
        for mission_id in WRITTEN_ANSWER_MISSIONS:
            source = (CODE / f"mission{mission_id}.py").read_text(encoding="utf-8")
            self.assertIn(
                "from answer_penalty import penalize_wrong_answer",
                source,
                mission_id,
            )
            self.assertIn(
                f"penalize_wrong_answer(self.player, '{mission_id}')",
                source,
                mission_id,
            )

    def test_non_answer_missions_do_not_get_guessing_penalty(self):
        for mission_id in ("01", "06", "07", "08"):
            source = (CODE / f"mission{mission_id}.py").read_text(encoding="utf-8")
            self.assertNotIn("penalize_wrong_answer(", source, mission_id)

    def test_penalty_happens_only_after_evidence_guards_in_each_written_mission(self):
        for mission_id in WRITTEN_ANSWER_MISSIONS:
            source = (CODE / f"mission{mission_id}.py").read_text(encoding="utf-8")
            penalty_pos = source.index(
                f"penalize_wrong_answer(self.player, '{mission_id}')"
            )
            deliver_pos = source.index("def deliver_results")
            self.assertGreater(penalty_pos, deliver_pos, mission_id)

            # The penalty helper must not be used by activation/evidence guards.
            prefix = source[deliver_pos:penalty_pos]
            self.assertTrue(
                "evidence" in prefix.lower()
                or "ready_to_deliver" in prefix
                or "screen_complete" in prefix
                or "relationship_supported" in prefix,
                mission_id,
            )

    def test_onboarding_explicitly_warns_about_wrong_answer_penalty(self):
        registration = (CODE / "student_registration.py").read_text(encoding="utf-8")
        dialogues = (CODE / "dialogues.py").read_text(encoding="utf-8")
        for source in (registration, dialogues):
            self.assertIn("WRONG_ANSWER_PENALTY", source)
            self.assertIn("incorrect final-answer submission", source.lower())
            self.assertIn("typo", source.lower())


if __name__ == "__main__":
    unittest.main()
