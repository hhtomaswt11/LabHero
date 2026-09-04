import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import (
    CAMPAIGN_INITIAL_KEYS,
    GOLDEN_EGG_GOLD_REWARD_BY_CAMPAIGN,
    HintSystem,
    INITIAL_KEYS,
    golden_egg_gold_reward_for_campaign,
    initial_keys_for_campaign,
)


class EasyHintKeyBudgetTests(unittest.TestCase):
    def test_normal_budget_remains_historic_15_10_5(self):
        expected = {'bronze': 15, 'silver': 10, 'gold': 5}
        self.assertEqual(initial_keys_for_campaign('normal'), expected)
        self.assertEqual(INITIAL_KEYS, expected)
        self.assertEqual(CAMPAIGN_INITIAL_KEYS['normal'], expected)

    def test_easy_budget_is_8_5_2(self):
        self.assertEqual(
            initial_keys_for_campaign('easy'),
            {'bronze': 8, 'silver': 5, 'gold': 2},
        )

    def test_budget_function_returns_fresh_copy(self):
        first = initial_keys_for_campaign('easy')
        first['bronze'] = 999
        self.assertEqual(initial_keys_for_campaign('easy')['bronze'], 8)

    def test_unknown_legacy_mode_falls_back_to_normal_budget(self):
        self.assertEqual(initial_keys_for_campaign('teacher'), INITIAL_KEYS)
        self.assertEqual(initial_keys_for_campaign('unknown'), INITIAL_KEYS)

    def test_setting_campaign_budget_does_not_rewrite_progress(self):
        system = HintSystem()
        system.state['mission_hints']['03'] = 2
        system.state['mission_scores']['03'] = 2
        system.state['mission_wrong_answers']['03'] = 1
        before = copy.deepcopy(system.state)

        system.set_campaign_initial_keys('easy')

        self.assertEqual(system.state['keys'], {'bronze': 8, 'silver': 5, 'gold': 2})
        for key in ('mission_hints', 'mission_scores', 'mission_wrong_answers'):
            self.assertEqual(system.state[key], before[key])

    def test_golden_egg_reward_is_route_specific(self):
        self.assertEqual(GOLDEN_EGG_GOLD_REWARD_BY_CAMPAIGN['normal'], 3)
        self.assertEqual(GOLDEN_EGG_GOLD_REWARD_BY_CAMPAIGN['easy'], 1)
        self.assertEqual(golden_egg_gold_reward_for_campaign('normal'), 3)
        self.assertEqual(golden_egg_gold_reward_for_campaign('easy'), 1)
        self.assertEqual(golden_egg_gold_reward_for_campaign('legacy'), 3)

    def test_registration_applies_budget_only_at_campaign_lock_in(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        registration = source[source.index('def register_student_campaign'):source.index('def register_student_name')]
        self.assertIn('self.campaign_mode = mode', registration)
        self.assertIn('self.hint_system.set_campaign_initial_keys(mode)', registration)
        self.assertIn('self.name_confirmed = True', registration)
        self.assertLess(
            registration.index('self.hint_system.set_campaign_initial_keys(mode)'),
            registration.index('self.name_confirmed = True'),
        )


if __name__ == '__main__':
    unittest.main()
