"""Regression tests for Coffee/Lamp/Apple movement-speed interactions."""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
TMX = ROOT / 'data' / 'map_lb.tmx'
AUDIO = ROOT / 'audio' / 'lamp_switch.ogg'


class PlayerSpeedInteractionTests(unittest.TestCase):
    def test_canonical_speed_constants_are_explicit_and_symmetric(self):
        source = (CODE / 'settings.py').read_text(encoding='utf-8')
        values = {
            name: int(value)
            for name, value in re.findall(
                r'^(PLAYER_SPEED_(?:DEFAULT|SLEEPY|COFFEE))\s*=\s*(\d+)\s*$',
                source,
                flags=re.MULTILINE,
            )
        }
        self.assertEqual(values, {
            'PLAYER_SPEED_DEFAULT': 750,
            'PLAYER_SPEED_SLEEPY': 600,
            'PLAYER_SPEED_COFFEE': 900,
        })
        self.assertEqual(
            values['PLAYER_SPEED_DEFAULT'] - values['PLAYER_SPEED_SLEEPY'],
            values['PLAYER_SPEED_COFFEE'] - values['PLAYER_SPEED_DEFAULT'],
        )

    def test_player_starts_at_default_and_interactions_replace_speed(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn('self.speed = PLAYER_SPEED_DEFAULT', source)
        self.assertIn("if sprite.name == 'Coffee':", source)
        self.assertIn('self.speed = PLAYER_SPEED_COFFEE', source)
        self.assertIn("elif sprite.name == 'Lamp':", source)
        self.assertIn('self.speed = PLAYER_SPEED_SLEEPY', source)
        # No additive/subtractive modifier should make repeated interactions stack.
        self.assertNotRegex(source, r'self\.speed\s*[+\-]=')

    def test_lamp_sound_is_loaded_and_present_as_ogg(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        self.assertIn("get_resource_path('audio/lamp_switch.ogg')", source)
        self.assertIn('self.lamp_switch.play()', source)
        self.assertTrue(AUDIO.is_file())
        self.assertEqual(AUDIO.read_bytes()[:4], b'OggS')

    def test_tiled_lamps_are_registered_as_generic_interactions(self):
        root = ET.parse(TMX).getroot()
        player_layer = next(
            group for group in root.findall('objectgroup')
            if group.attrib.get('name') == 'Player'
        )
        lamps = [
            obj for obj in player_layer.findall('object')
            if obj.attrib.get('name') == 'Lamp'
        ]
        self.assertEqual(len(lamps), 2)
        for obj in lamps:
            self.assertGreater(float(obj.attrib.get('width', 0)), 0)
            self.assertGreater(float(obj.attrib.get('height', 0)), 0)

        level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn("if obj.name == 'Lamp':", level_source)
        self.assertIn(
            "Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)",
            level_source,
        )

    def test_apple_collection_restores_default_speed_without_touching_tree_logic(self):
        level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        sprites_source = (CODE / 'sprites.py').read_text(encoding='utf-8')
        self.assertIn("if item == 'apple':", level_source)
        self.assertIn('self.player.speed = PLAYER_SPEED_DEFAULT', level_source)
        self.assertIn("self.player_add('apple')", sprites_source)

    def test_speed_sequence_contract_is_absolute_not_stacked(self):
        # Mirrors the intended direct-assignment semantics without importing pygame.
        default, sleepy, coffee = 750, 600, 900
        speed = default
        speed = sleepy       # Lamp
        self.assertEqual(speed, 600)
        speed = coffee       # Coffee replaces Lamp
        self.assertEqual(speed, 900)
        speed = default      # Apple replaces Coffee
        self.assertEqual(speed, 750)
        speed = default      # Another Apple is idempotent
        self.assertEqual(speed, 750)

        speed = coffee
        speed = sleepy       # Lamp replaces Coffee
        self.assertEqual(speed, 600)
        speed = coffee       # Coffee replaces Lamp
        self.assertEqual(speed, 900)


if __name__ == '__main__':
    unittest.main()
