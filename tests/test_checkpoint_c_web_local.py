import re
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _png_size(path: Path):
    with path.open('rb') as handle:
        signature = handle.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise AssertionError(f'{path} is not a PNG file')
        length = struct.unpack('>I', handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b'IHDR' or length < 8:
            raise AssertionError(f'{path} has no valid IHDR chunk')
        return struct.unpack('>II', handle.read(8))


class CheckpointCWebLocalTests(unittest.TestCase):
    def test_final_tmx_and_ground_raster_have_identical_dimensions(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        pixel_size = (
            int(root.get('width')) * int(root.get('tilewidth')),
            int(root.get('height')) * int(root.get('tileheight')),
        )
        self.assertEqual((80, 61), (int(root.get('width')), int(root.get('height'))))
        self.assertEqual((5120, 3904), pixel_size)
        self.assertEqual(pixel_size, _png_size(ROOT / 'graphics' / 'world' / 'ground_lb.png'))

    def test_every_tile_layer_matches_the_final_map_grid(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        expected = (root.get('width'), root.get('height'))
        mismatches = [
            (layer.get('name'), layer.get('width'), layer.get('height'))
            for layer in root.findall('layer')
            if (layer.get('width'), layer.get('height')) != expected
        ]
        self.assertEqual([], mismatches)

    def test_critical_gameplay_objects_remain_unique_and_inside_map(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        width = int(root.get('width')) * int(root.get('tilewidth'))
        height = int(root.get('height')) * int(root.get('tileheight'))
        player_group = next(group for group in root.findall('objectgroup') if group.get('name') == 'Player')
        objects = list(player_group.findall('object'))

        critical = (
            'Start', 'Desk', 'Mission01', 'Mission02', 'Mission03',
            'Mission07', 'Mission11', 'Mission16', 'Mission21', 'Mission23',
            'Mission25', 'Mission27', 'Mission29', 'Mission32', 'Final',
            'Vale', 'Voss', 'Umbra', 'Morbus', 'Mortis', 'YeastSimulator',
        )
        for name in critical:
            matches = [obj for obj in objects if obj.get('name') == name]
            self.assertEqual(1, len(matches), name)
            obj = matches[0]
            x = float(obj.get('x', 0.0))
            y = float(obj.get('y', 0.0))
            obj_width = float(obj.get('width', 0.0))
            obj_height = float(obj.get('height', 0.0))
            self.assertGreaterEqual(x, 0.0, name)
            self.assertGreaterEqual(y, 0.0, name)
            self.assertLessEqual(x + obj_width, width, name)
            self.assertLessEqual(y + obj_height, height, name)

    def test_browser_uses_same_origin_api_and_nginx_strips_api_prefix(self):
        settings = (ROOT / 'code' / 'settings.py').read_text(encoding='utf-8')
        nginx = (ROOT / 'deploy' / 'nginx.conf').read_text(encoding='utf-8')
        self.assertRegex(settings, r"(?m)^BACKEND_URL\s*=\s*['\"]\/api['\"]")
        self.assertIn('location /api/', nginx)
        self.assertIn('proxy_pass http://backend:8000/;', nginx)

    def test_local_compose_exposes_one_frontend_for_game_and_api(self):
        compose = (ROOT / 'deploy' / 'docker-compose.yml').read_text(encoding='utf-8')
        self.assertRegex(compose, r'(?m)^\s*backend:\s*$')
        self.assertRegex(compose, r'(?m)^\s*frontend:\s*$')
        self.assertIn('"80:80"', compose)
        self.assertIn('depends_on:', compose)
        self.assertIn('- backend', compose)

    def test_local_smoke_script_checks_health_and_frontend(self):
        script = (ROOT / 'deploy' / 'local_smoke.sh').read_text(encoding='utf-8')
        self.assertIn('docker compose up -d --build', script)
        self.assertIn('http://localhost/api/health', script)
        self.assertIn('http://localhost/', script)


if __name__ == '__main__':
    unittest.main()
