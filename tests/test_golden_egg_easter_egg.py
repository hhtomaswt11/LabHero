import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from campaign import CampaignContext
from hint_system import HintSystem


class GoldenEggEasterEggTests(unittest.TestCase):
    def test_map_contains_unique_golden_egg_on_player_layer(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        player_layer = next(
            layer for layer in root.findall('objectgroup')
            if layer.get('name') == 'Player'
        )
        eggs = [
            obj for obj in player_layer.findall('object')
            if obj.get('name') == 'GoldenEgg'
        ]
        self.assertEqual(len(eggs), 1)
        self.assertEqual(eggs[0].get('width'), '80')
        self.assertEqual(eggs[0].get('height'), '80')

    def test_map_contains_egg_gate_at_mission35_milestone(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        gate_layer = next(
            layer for layer in root.findall('objectgroup')
            if layer.get('name') == 'ProgressionGates'
        )
        gates = [
            obj for obj in gate_layer.findall('object')
            if obj.get('name') == 'EggGate'
        ]
        self.assertEqual(len(gates), 1)
        properties = {
            prop.get('name'): prop.get('value')
            for prop in gates[0].findall('./properties/property')
        }
        self.assertEqual(properties.get('unlock_after'), '35')

    def test_gate35_policy_is_normal_m35_easy_m27_teacher_open(self):
        normal = CampaignContext('normal')
        easy = CampaignContext('easy')
        teacher = CampaignContext('teacher')

        self.assertFalse(normal.should_gate_be_open('35', ['34']))
        self.assertTrue(normal.should_gate_be_open('35', ['35']))

        self.assertFalse(easy.should_gate_be_open('35', ['25']))
        self.assertTrue(easy.should_gate_be_open('35', ['27']))

        self.assertTrue(teacher.should_gate_be_open('35', []))

    def test_hint_system_can_award_three_gold_keys_without_touching_scores(self):
        hints = HintSystem()
        before_scores = hints.to_dict()['mission_scores']
        before_hints = hints.to_dict()['mission_hints']
        self.assertEqual(hints.get_key_count('gold'), 5)

        updated = hints.award_keys('gold', 3)

        self.assertEqual(updated, 8)
        self.assertEqual(hints.get_key_count('gold'), 8)
        self.assertEqual(hints.to_dict()['mission_scores'], before_scores)
        self.assertEqual(hints.to_dict()['mission_hints'], before_hints)

    def test_award_keys_rejects_invalid_or_non_positive_rewards(self):
        hints = HintSystem()
        for value in (0, -1, True, 'bad'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    hints.award_keys('gold', value)
        with self.assertRaises(ValueError):
            hints.award_keys('platinum', 3)

    def test_player_state_persists_golden_egg_collected(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn(
            "self.player_state.get('golden_egg_collected', False)",
            source,
        )
        self.assertIn(
            "'golden_egg_collected': bool(self.golden_egg_collected)",
            source,
        )

    def test_collection_is_idempotent_awards_and_saves_immediately(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn('def collect_golden_egg(self):', source)
        self.assertIn('if self.golden_egg_collected:', source)
        self.assertIn("self.hint_system.award_keys('gold', 3)", source)
        self.assertIn('save_file(self.get_save_data())', source)
        self.assertIn(
            'Golden Egg discovered! You found 3 Gold Keys.',
            source,
        )

    def test_level_spawns_only_uncollected_egg_and_nearby_interaction(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn("if obj.name == 'GoldenEgg':", source)
        self.assertIn(
            "and not getattr(self.player, 'golden_egg_collected', False)",
            source,
        )
        self.assertIn('GoldenEgg(', source)
        self.assertIn("'GoldenEgg',", source)
        self.assertIn('interaction_padding = 32', source)

    def test_enter_interaction_collects_and_removes_interaction_sprite(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn("elif interaction_name == 'GoldenEgg':", source)
        self.assertIn('if self.collect_golden_egg():', source)
        self.assertIn('collided_interaction_sprite[0].kill()', source)


if __name__ == '__main__':
    unittest.main()
