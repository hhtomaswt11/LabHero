import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import INITIAL_KEYS, SCORE_BY_HINT_LEVEL


class AlvesHintKeyOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.dialogue_source = (CODE / "dialogues.py").read_text(encoding="utf-8")
        self.registration_source = (CODE / "student_registration.py").read_text(encoding="utf-8")

    def test_reward_system_still_uses_documented_initial_key_budget(self):
        self.assertEqual(
            INITIAL_KEYS,
            {"bronze": 15, "silver": 10, "gold": 5},
        )

    def test_reward_system_still_uses_documented_hint_score_ladder(self):
        self.assertEqual(
            SCORE_BY_HINT_LEVEL,
            {0: 5, 1: 3, 2: 2, 3: 1},
        )

    def test_initial_registration_guarantees_key_budget_warning(self):
        self.assertIn("Dr. Alves: You start with", self.registration_source)
        self.assertIn("INITIAL_KEYS['bronze']", self.registration_source)
        self.assertIn("INITIAL_KEYS['silver']", self.registration_source)
        self.assertIn("INITIAL_KEYS['gold']", self.registration_source)

    def test_initial_registration_guarantees_limited_key_warning(self):
        self.assertIn(
            "Hint keys are limited. Unlocking a hint spends a key and lowers that mission's score.",
            self.registration_source,
        )

    def test_initial_registration_explains_exact_score_ladder(self):
        for level in range(4):
            self.assertIn(f"SCORE_BY_HINT_LEVEL[{level}]", self.registration_source)
        self.assertIn("points with no hints", self.registration_source)
        self.assertIn("three hint levels", self.registration_source)

    def test_alves_followup_dialogue_repeats_key_warning(self):
        self.assertIn("Hint keys:", self.dialogue_source)
        self.assertIn("INITIAL_KEYS['bronze']", self.dialogue_source)
        self.assertIn("INITIAL_KEYS['silver']", self.dialogue_source)
        self.assertIn("INITIAL_KEYS['gold']", self.dialogue_source)
        self.assertIn(
            "Unlocking a hint spends a key. Keys are limited, so use them carefully.",
            self.dialogue_source,
        )

    def test_alves_followup_dialogue_repeats_score_penalty(self):
        self.assertIn("Hints reduce mission score:", self.dialogue_source)
        for level in range(4):
            self.assertIn(f"SCORE_BY_HINT_LEVEL[{level}]", self.dialogue_source)


if __name__ == "__main__":
    unittest.main()
