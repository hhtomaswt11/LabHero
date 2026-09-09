import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, 'code')
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from campaign import CampaignContext
from quest_tracker import (
    MISSION_RESEARCHERS,
    MISSION_TITLES,
    build_quest_tracker_snapshot,
    get_active_npc_interaction,
)


class FakePlayer:
    def __init__(self, mode='normal', activated=None, completed=None):
        self.campaign_mode = mode
        self.missions_activated = list(activated or [])
        self.missions_completed = list(completed or [])

    def get_campaign_context(self):
        return CampaignContext(self.campaign_mode)


class QuestTrackerSnapshotTests(unittest.TestCase):
    def test_metadata_covers_all_normal_missions(self):
        expected = {f'{number:02d}' for number in range(1, 41)}
        self.assertEqual(set(MISSION_TITLES), expected)
        self.assertEqual(set(MISSION_RESEARCHERS), expected)

    def test_new_normal_campaign_points_to_martinez_without_spoilers(self):
        snapshot = build_quest_tracker_snapshot(FakePlayer())
        self.assertEqual(snapshot['status'], 'available')
        self.assertEqual(snapshot['mission_id'], '01')
        self.assertEqual(snapshot['researcher'], 'Dr. Martinez')
        self.assertIn('first laboratory', snapshot['objective'])
        self.assertEqual(snapshot['completed'], 0)
        self.assertEqual(snapshot['total'], 40)

    def test_active_mission_is_activated_but_not_completed(self):
        player = FakePlayer(activated=['01'], completed=[])
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['status'], 'active')
        self.assertEqual(snapshot['mission_id'], '01')
        self.assertIn('return to Dr. Martinez', snapshot['objective'])

    def test_completed_activation_does_not_remain_current(self):
        player = FakePlayer(activated=['02', '01'], completed=['01'])
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['status'], 'active')
        self.assertEqual(snapshot['mission_id'], '02')

    def test_no_active_mission_points_to_next_normal_researcher(self):
        player = FakePlayer(activated=['01'], completed=['01'])
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['status'], 'available')
        self.assertEqual(snapshot['mission_id'], '02')
        self.assertEqual(snapshot['researcher'], 'Dr. Martinez')
        self.assertIn('begin Mission 02', snapshot['objective'])

    def test_easy_mode_skips_non_route_missions(self):
        player = FakePlayer(
            mode='easy',
            activated=['01'],
            completed=['01'],
        )
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['mission_id'], '03')
        self.assertEqual(snapshot['researcher'], 'Dr. Silva')
        self.assertEqual(snapshot['total'], 11)

    def test_easy_active_mission_uses_easy_route(self):
        player = FakePlayer(
            mode='easy',
            activated=['03', '01'],
            completed=['01'],
        )
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['status'], 'active')
        self.assertEqual(snapshot['mission_id'], '03')
        self.assertEqual(snapshot['researcher'], 'Dr. Silva')


    def test_active_npc_points_to_registration_npc_before_campaign_starts(self):
        player = FakePlayer()
        player.name_confirmed = False
        self.assertEqual(get_active_npc_interaction(player), 'Alves')

    def test_active_npc_points_to_next_mission_npc(self):
        player = FakePlayer(activated=['01'], completed=['01'])
        player.name_confirmed = True
        self.assertEqual(get_active_npc_interaction(player), 'Mission01')

    def test_active_mission_does_not_pull_player_back_to_npc(self):
        player = FakePlayer(activated=['01'], completed=[])
        player.name_confirmed = True
        self.assertIsNone(get_active_npc_interaction(player))

    def test_easy_active_npc_uses_curated_route(self):
        player = FakePlayer(mode='easy', activated=['01'], completed=['01'])
        player.name_confirmed = True
        self.assertEqual(get_active_npc_interaction(player), 'Mission02')

    def test_completed_campaign_has_no_next_researcher(self):
        context = CampaignContext('easy')
        player = FakePlayer(
            mode='easy',
            activated=list(context.mission_sequence),
            completed=list(context.mission_sequence),
        )
        snapshot = build_quest_tracker_snapshot(player)
        self.assertEqual(snapshot['status'], 'complete')
        self.assertIsNone(snapshot['mission_id'])
        self.assertEqual(snapshot['completed'], 11)
        self.assertEqual(snapshot['total'], 11)

    def test_tracker_text_does_not_contain_answer_language(self):
        player = FakePlayer(activated=['25'], completed=[f'{i:02d}' for i in range(1, 25)])
        snapshot = build_quest_tracker_snapshot(player)
        text = ' '.join(str(value) for value in snapshot.values()).lower()
        for forbidden in ('correct answer', 'expected answer', 'knockout b', 'flux ='):
            self.assertNotIn(forbidden, text)


class QuestTrackerIntegrationSourceTests(unittest.TestCase):
    def test_level_integrates_q_tracker_as_modal(self):
        with open(os.path.join(CODE, 'level.py'), encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn('QuestTrackerOverlay', source)
        self.assertIn('pygame.K_q', source)
        self.assertIn('self.quest_tracker_active', source)
        self.assertIn('self.quest_tracker.draw_hint(', source)

    def test_controls_document_q_shortcut(self):
        with open(os.path.join(CODE, 'controls_content.py'), encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn('Quest Tracker', source)
        self.assertIn('Press Q during exploration', source)


if __name__ == '__main__':
    unittest.main()
