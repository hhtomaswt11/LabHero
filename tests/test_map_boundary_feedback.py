import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


class MapBoundaryFeedbackTests(unittest.TestCase):
    def test_neutral_message_is_shared_by_world_and_egg_boundaries(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn("You can't go any further this way.", source)
        self.assertIn("if getattr(obj, 'name', None) in {'EggGate', 'EggGate_2'}:", source)
        self.assertIn('gate.is_map_boundary = True', source)

    def test_map_boundary_layer_remains_separate_from_collision(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        width = int(root.get('width'))

        def occupied(name):
            layer = next(
                item for item in root.findall('layer')
                if item.get('name') == name
            )
            values = [
                int(value)
                for value in layer.find('data').text.replace('\n', '').split(',')
                if value.strip()
            ]
            return {(index % width, index // width) for index, value in enumerate(values) if value}

        boundary = occupied('MapBoundary')
        collision = occupied('Collision')
        self.assertTrue(boundary)
        self.assertFalse(boundary & collision)

    def test_easter_gate_helper_tiles_are_not_left_as_permanent_boundaries(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        width = int(root.get('width'))
        layer = next(
            item for item in root.findall('layer')
            if item.get('name') == 'MapBoundary'
        )
        values = [
            int(value)
            for value in layer.find('data').text.replace('\n', '').split(',')
            if value.strip()
        ]
        for x, y in ((12, 23), (13, 23), (14, 23), (13, 35), (14, 35), (15, 35)):
            self.assertEqual(values[y * width + x], 0)


if __name__ == '__main__':
    unittest.main()
