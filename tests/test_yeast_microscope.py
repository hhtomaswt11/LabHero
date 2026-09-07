"""Regression tests for Golden Lab yeast microscope interactions."""
from __future__ import annotations

import struct
import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TMX = ROOT / 'data' / 'map_lb.tmx'
PLAYER = ROOT / 'code' / 'player.py'
LEVEL = ROOT / 'code' / 'level.py'
VIEWER = ROOT / 'code' / 'yeast_microscope.py'
ASSET = ROOT / 'graphics' / 'environment' / 'Yeast.png'


def png_size(path: Path) -> tuple[int, int]:
    with path.open('rb') as handle:
        signature = handle.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise AssertionError(f'{path} is not a PNG')
        length = struct.unpack('>I', handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b'IHDR' or length < 8:
            raise AssertionError(f'{path} has no valid PNG IHDR')
        width, height = struct.unpack('>II', handle.read(8))
        return width, height


class YeastMicroscopeTests(unittest.TestCase):
    def test_viewer_builds_and_draws_in_real_pygame(self):
        # A separate process avoids pygame stubs used by source-only tests.
        script = """
import asyncio, sys
sys.path.insert(0, 'code')
import pygame
import yeast_microscope
pygame.init()
surface = pygame.display.set_mode((1280, 720))
async def draw_once(menu, target):
    menu.draw(target)
yeast_microscope.run_menu = draw_once
asyncio.run(yeast_microscope.YeastMicroscope(lambda: None).setup())
pygame.quit()
"""
        environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                                env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_yeast_asset_is_present_and_matches_microscope_canvas(self):
        self.assertTrue(ASSET.is_file())
        self.assertEqual(png_size(ASSET), (500, 500))

    def test_tiled_has_five_explicit_yeast_interaction_rectangles(self):
        root = ET.parse(TMX).getroot()
        player_layer = next(
            group for group in root.findall('objectgroup')
            if group.attrib.get('name') == 'Player'
        )
        yeast = [
            obj for obj in player_layer.findall('object')
            if obj.attrib.get('name') == 'Yeast'
        ]
        self.assertEqual(len(yeast), 5)
        for obj in yeast:
            self.assertGreater(float(obj.attrib.get('width', 0)), 0)
            self.assertGreater(float(obj.attrib.get('height', 0)), 0)

    def test_yeast_and_ecoli_interaction_rectangles_are_not_duplicates(self):
        root = ET.parse(TMX).getroot()
        player_layer = next(
            group for group in root.findall('objectgroup')
            if group.attrib.get('name') == 'Player'
        )

        def rects(name):
            return {
                (
                    obj.attrib.get('x'), obj.attrib.get('y'),
                    obj.attrib.get('width'), obj.attrib.get('height'),
                )
                for obj in player_layer.findall('object')
                if obj.attrib.get('name') == name
            }

        self.assertTrue(rects('Yeast').isdisjoint(rects('Ecoli')))

    def test_level_builds_and_updates_yeast_microscope_modal(self):
        source = LEVEL.read_text(encoding='utf-8')
        self.assertIn('from yeast_microscope import YeastMicroscope', source)
        self.assertIn("if obj.name == 'Yeast':", source)
        self.assertIn('yeast_microscope = self.see_yeast', source)
        self.assertIn('self.yeast_microscope = YeastMicroscope(self.see_yeast)', source)
        self.assertIn('self.yeast_microscope_active', source)
        self.assertIn('await self.yeast_microscope.update()', source)

    def test_player_routes_yeast_interaction_to_dedicated_callback(self):
        source = PLAYER.read_text(encoding='utf-8')
        self.assertIn('yeast_microscope=None', source)
        self.assertIn('self.yeast_microscope = yeast_microscope', source)
        self.assertIn("collided_interaction_sprite[0].name == 'Yeast'", source)
        self.assertIn('self.yeast_microscope()', source)

    def test_viewer_uses_yeast_asset_and_scientific_label(self):
        source = VIEWER.read_text(encoding='utf-8')
        self.assertIn("graphics/environment/Yeast.png", source)
        self.assertIn("title='S. cerevisiae'", source)
        self.assertIn("'S. cerevisiae'", source)


if __name__ == '__main__':
    unittest.main()
