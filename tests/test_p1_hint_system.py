import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from hint_system import (
    HintSystem,
    INITIAL_KEYS,
    SCORE_BY_HINT_LEVEL,
    TRACKED_HINT_MISSIONS,
    create_reward_state,
    normalize_mission_id,
    normalize_reward_state,
)


class TestP1HintSystem(unittest.TestCase):
    def test_fresh_state_uses_15_10_5_and_no_progress(self):
        system = HintSystem()
        self.assertEqual(system.state['keys'], {'bronze': 15, 'silver': 10, 'gold': 5})
        self.assertEqual(system.state['mission_hints'], {})
        self.assertEqual(system.state['mission_scores'], {})
        self.assertEqual(system.state['legacy_unscored_missions'], [])

    def test_mission_ids_are_canonical(self):
        self.assertEqual(normalize_mission_id(1), '01')
        self.assertEqual(normalize_mission_id('01'), '01')
        self.assertEqual(normalize_mission_id(' 9 '), '09')
        self.assertEqual(normalize_mission_id(40), '40')
        with self.assertRaises(ValueError):
            normalize_mission_id(0)
        with self.assertRaises(ValueError):
            normalize_mission_id('abc')

    def test_hint_levels_charge_bronze_then_silver_then_gold(self):
        system = HintSystem()
        first = system.unlock_hint(2, 1)
        second = system.unlock_hint(2, 2)
        third = system.unlock_hint(2, 3)

        self.assertEqual(first['charged_key'], 'bronze')
        self.assertEqual(second['charged_key'], 'silver')
        self.assertEqual(third['charged_key'], 'gold')
        self.assertEqual(system.get_hint_level('02'), 3)
        self.assertEqual(system.state['keys'], {'bronze': 14, 'silver': 9, 'gold': 4})

    def test_unlocks_must_be_sequential(self):
        system = HintSystem()
        result = system.unlock_hint('17', 2)
        self.assertEqual(result['status'], 'previous_hint_locked')
        self.assertEqual(system.get_hint_level('17'), 0)
        self.assertEqual(system.state['keys'], INITIAL_KEYS)

    def test_reopening_an_unlocked_hint_is_free(self):
        system = HintSystem()
        system.unlock_hint('15', 1)
        before = copy.deepcopy(system.state['keys'])

        reopened = system.unlock_hint('15', 1)

        self.assertEqual(reopened['status'], 'already_unlocked')
        self.assertIsNone(reopened['charged_key'])
        self.assertEqual(system.state['keys'], before)

    def test_bronze_fallback_requires_confirmation_before_spending_silver(self):
        state = create_reward_state()
        state['keys']['bronze'] = 0
        system = HintSystem(state)

        offer = system.get_unlock_offer('03', 1)
        attempt = system.unlock_hint('03', 1)

        self.assertEqual(offer['status'], 'confirmation_required')
        self.assertEqual(offer['key_to_spend'], 'silver')
        self.assertTrue(offer['fallback'])
        self.assertEqual(attempt['status'], 'confirmation_required')
        self.assertEqual(system.get_hint_level('03'), 0)
        self.assertEqual(system.get_key_count('silver'), 10)

        confirmed = system.unlock_hint('03', 1, allow_fallback=True)
        self.assertEqual(confirmed['status'], 'unlocked')
        self.assertEqual(confirmed['charged_key'], 'silver')
        self.assertEqual(system.get_key_count('silver'), 9)

    def test_bronze_fallback_uses_gold_when_bronze_and_silver_are_empty(self):
        state = create_reward_state()
        state['keys']['bronze'] = 0
        state['keys']['silver'] = 0
        system = HintSystem(state)

        offer = system.get_unlock_offer('04', 1)
        self.assertEqual(offer['status'], 'confirmation_required')
        self.assertEqual(offer['key_to_spend'], 'gold')

        result = system.unlock_hint('04', 1, allow_fallback=True)
        self.assertEqual(result['charged_key'], 'gold')
        self.assertEqual(system.get_key_count('gold'), 4)

    def test_silver_fallback_can_use_gold_but_never_bronze(self):
        state = create_reward_state()
        state['mission_hints']['05'] = 1
        state['keys']['silver'] = 0
        state['keys']['gold'] = 1
        system = HintSystem(state)

        offer = system.get_unlock_offer('05', 2)
        self.assertEqual(offer['key_to_spend'], 'gold')

        # Even an abundant bronze balance is irrelevant to Hint 2.
        self.assertEqual(system.get_key_count('bronze'), 15)
        result = system.unlock_hint('05', 2, allow_fallback=True)
        self.assertEqual(result['charged_key'], 'gold')

    def test_gold_hint_has_no_downward_fallback(self):
        state = create_reward_state()
        state['mission_hints']['06'] = 2
        state['keys']['gold'] = 0
        state['keys']['bronze'] = 99
        state['keys']['silver'] = 99
        system = HintSystem(state)

        offer = system.get_unlock_offer('06', 3)
        self.assertEqual(offer['status'], 'no_key_available')
        self.assertIsNone(system.find_fallback_key(3))
        self.assertFalse(system.can_unlock_hint('06', 3))
        self.assertEqual(system.get_hint_level('06'), 2)

    def test_completed_mission_cannot_buy_a_new_hint(self):
        system = HintSystem()
        result = system.unlock_hint('07', 1, mission_completed=True)
        self.assertEqual(result['status'], 'mission_completed')
        self.assertEqual(system.get_key_count('bronze'), 15)
        self.assertEqual(system.get_hint_level('07'), 0)

    def test_already_unlocked_hint_remains_reviewable_after_completion(self):
        system = HintSystem()
        system.unlock_hint('08', 1)
        before = system.get_key_count('bronze')

        result = system.unlock_hint('08', 1, mission_completed=True)
        self.assertEqual(result['status'], 'already_unlocked')
        self.assertEqual(system.get_key_count('bronze'), before)

    def test_score_mapping_is_exact(self):
        system = HintSystem()
        self.assertEqual(
            [system.score_for_hint_level(level) for level in range(4)],
            [5, 3, 2, 1],
        )
        self.assertEqual(SCORE_BY_HINT_LEVEL, {0: 5, 1: 3, 2: 2, 3: 1})

    def test_score_is_frozen_when_mission_finishes(self):
        system = HintSystem()
        system.unlock_hint('12', 1)
        self.assertEqual(system.finalize_mission_score('12'), 3)

        # Even if malformed/external code later changes hint state, a completed
        # score is immutable.
        system.state['mission_hints']['12'] = 3
        self.assertEqual(system.finalize_mission_score('12'), 3)
        self.assertEqual(system.get_mission_score('12'), 3)

    def test_completed_missions_finalize_only_once_and_total_is_derived(self):
        system = HintSystem()
        system.unlock_hint('01', 1)  # 3 points
        system.unlock_hint('02', 1)
        system.unlock_hint('02', 2)  # 2 points

        system.finalize_completed_missions(['01', '02'])
        self.assertEqual(system.get_total_score(), 5)
        self.assertEqual(system.get_max_score(), 200)

        system.finalize_completed_missions(['01', '02'])
        self.assertEqual(system.get_total_score(), 5)

    def test_rollout_tracks_first_thirty_missions_after_p4d(self):
        self.assertEqual(TRACKED_HINT_MISSIONS, frozenset(f'{mission:02d}' for mission in range(1, 41)))

    def test_final_rollout_scores_current_missions_31_and_32(self):
        system = HintSystem()
        system.sync_completed_missions(['31', '32'])

        self.assertEqual(system.state['legacy_unscored_missions'], [])
        self.assertEqual(system.state['mission_scores'], {'31': 5, '32': 5})

    def test_rollout_sync_scores_only_explicitly_tracked_missions(self):
        system = HintSystem()
        system.unlock_hint('02', 1)
        system.sync_completed_missions(['01', '02'], tracked_missions={'02'})

        self.assertEqual(system.get_mission_score('02'), 3)
        self.assertIsNone(system.get_mission_score('01'))
        self.assertIn('01', system.state['legacy_unscored_missions'])

    def test_legacy_completed_missions_are_not_scored_retroactively(self):
        system = HintSystem(state=None, legacy_completed=['01', '2', 24])
        self.assertEqual(
            system.state['legacy_unscored_missions'],
            ['01', '02', '24'],
        )
        system.finalize_completed_missions(['01', '02', '24', '25'])

        self.assertIsNone(system.get_mission_score('01'))
        self.assertIsNone(system.get_mission_score('24'))
        self.assertEqual(system.get_mission_score('25'), 5)
        self.assertEqual(system.get_total_score(), 5)

    def test_normalization_repairs_malformed_state_without_negative_keys(self):
        raw = {
            'keys': {'bronze': -3, 'silver': '7', 'gold': 'bad'},
            'mission_hints': {'1': 2, '02': 9, 'bad': 1, '03': 0},
            'mission_scores': {'1': 3, '2': 4, '03': 5},
            'legacy_unscored_missions': ['01', '03', 'bad', '03'],
        }
        state = normalize_reward_state(raw)

        self.assertEqual(state['keys'], {'bronze': 0, 'silver': 7, 'gold': 5})
        self.assertEqual(state['mission_hints'], {'01': 2})
        self.assertEqual(state['mission_scores'], {'01': 3, '03': 5})
        self.assertEqual(state['legacy_unscored_missions'], [])

    def test_to_dict_does_not_expose_mutable_internal_state(self):
        system = HintSystem()
        exported = system.to_dict()
        exported['keys']['bronze'] = 0
        exported['mission_hints']['01'] = 3

        self.assertEqual(system.get_key_count('bronze'), 15)
        self.assertEqual(system.get_hint_level('01'), 0)


if __name__ == '__main__':
    unittest.main()
