import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
TMX = ROOT / 'data' / 'map_lb.tmx'


def _csv_values(layer):
    text = layer.find('data').text or ''
    return [int(value.strip()) for value in text.replace('\n', '').split(',') if value.strip()]


class CheckpointD2CStaticHouseBottomTests(unittest.TestCase):
    def setUp(self):
        self.level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.level_tree = ast.parse(self.level_source)

    def test_current_house_bottom_layers_account_for_1409_static_tiles(self):
        root = ET.parse(TMX).getroot()
        layers = {layer.get('name'): layer for layer in root.findall('layer')}
        counts = {
            name: sum(1 for gid in _csv_values(layers[name]) if (gid & 0x1FFFFFFF) != 0)
            for name in ('HouseFloor', 'HouseFurnitureBottom')
        }
        self.assertEqual(1189, counts['HouseFloor'])
        self.assertEqual(220, counts['HouseFurnitureBottom'])
        self.assertEqual(1409, sum(counts.values()))

    def test_setup_keeps_exact_pytmx_surfaces_but_not_1409_generic_sprites(self):
        setup = next(
            node for node in ast.walk(self.level_tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'setup'
        )
        block = ast.get_source_segment(self.level_source, setup)

        self.assertIn("for layer in ['HouseFloor', 'HouseFurnitureBottom']", block)
        self.assertIn('surf.get_rect(topleft = (x * TILE_SIZE, y * TILE_SIZE))', block)
        self.assertIn('house_bottom_tiles.append((rect.centery, house_bottom_order, surf, rect))', block)
        self.assertIn('self.all_sprites.set_house_bottom_tiles(house_bottom_tiles)', block)
        self.assertNotRegex(
            block,
            r"Generic\([^\n]*LAYERS\[['\"]house bottom['\"]\]",
        )

    def test_pre_sort_is_equivalent_to_previous_stable_y_sort(self):
        # Old CameraGroup sorted same-z Sprite objects by rect.centery and relied
        # on stable insertion order for ties. D.2C makes that insertion order
        # explicit, which must yield exactly the same sequence.
        sample = [
            ('floor-a', 500, 0),
            ('floor-b', 300, 1),
            ('floor-c', 500, 2),
            ('furniture-a', 300, 3),
            ('furniture-b', 700, 4),
        ]
        old = sorted(sample, key=lambda item: item[1])
        new = sorted(sample, key=lambda item: (item[1], item[2]))
        self.assertEqual(old, new)

    def test_camera_uses_bisect_and_viewport_culling_for_static_layer(self):
        camera = next(
            node for node in self.level_tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'CameraGroup'
        )
        set_layer = next(
            node for node in camera.body
            if isinstance(node, ast.FunctionDef) and node.name == 'set_house_bottom_tiles'
        )
        draw_layer = next(
            node for node in camera.body
            if isinstance(node, ast.FunctionDef) and node.name == '_draw_house_bottom'
        )
        set_block = ast.get_source_segment(self.level_source, set_layer)
        draw_block = ast.get_source_segment(self.level_source, draw_layer)

        self.assertIn('sorted(tiles, key=lambda item: (item[0], item[1]))', set_block)
        self.assertIn('bisect_left(', draw_block)
        self.assertIn('bisect_right(', draw_block)
        self.assertIn('rect.colliderect(view_rect)', draw_block)
        self.assertIn('range(start, stop)', draw_block)
        loops = [node for node in ast.walk(draw_layer) if isinstance(node, ast.For)]
        self.assertEqual(1, len(loops))
        self.assertIn('range(start, stop)', ast.get_source_segment(self.level_source, loops[0]))

    def test_static_layer_is_inserted_at_same_house_bottom_z_position(self):
        custom_draw = next(
            node for node in ast.walk(self.level_tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'custom_draw'
        )
        block = ast.get_source_segment(self.level_source, custom_draw)

        self.assertIn("sprite.z > LAYERS['house bottom']", block)
        self.assertIn('self._draw_house_bottom(view_rect)', block)
        # D.1's one global Sprite sort and viewport culling remain intact.
        self.assertEqual(1, block.count('sorted('))
        self.assertIn('sprite.rect.colliderect(view_rect)', block)

    def test_no_other_runtime_code_creates_house_bottom_sprites(self):
        offenders = []
        pattern = re.compile(r"Generic\([\s\S]{0,220}?LAYERS\[['\"]house bottom['\"]\]")
        for path in CODE.glob('*.py'):
            source = path.read_text(encoding='utf-8')
            if pattern.search(source):
                offenders.append(path.name)
        self.assertEqual([], offenders)


if __name__ == '__main__':
    unittest.main()
