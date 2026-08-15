import ast
import re
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
GROUND = ROOT / 'graphics' / 'world' / 'ground_lb.png'


class CheckpointD2BOpaqueGroundTests(unittest.TestCase):
    def setUp(self):
        self.level_source = (CODE / 'level.py').read_text(encoding='utf-8')

    def test_ground_asset_is_still_fully_opaque(self):
        # D.2B is safe only while the pre-rendered ground has no meaningful
        # transparency. If that changes in a future map export, this test must
        # fail before convert() can silently discard visual information.
        with Image.open(GROUND) as image:
            self.assertEqual((5120, 3904), image.size)
            self.assertIn('A', image.getbands())
            self.assertEqual((255, 255), image.getchannel('A').getextrema())

    def test_pre_rendered_ground_uses_display_format_without_per_pixel_alpha(self):
        tree = ast.parse(self.level_source)
        setup = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'setup'
        )
        block = ast.get_source_segment(self.level_source, setup)

        self.assertIn("surf_path = get_resource_path('graphics/world/ground_lb.png')", block)
        self.assertIn('pygame.image.load(surf_path).convert()', block)
        self.assertNotIn('pygame.image.load(surf_path).convert_alpha()', block)

    def test_ground_stays_draw_only_at_ground_z_layer(self):
        tree = ast.parse(self.level_source)
        setup = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'setup'
        )
        block = ast.get_source_segment(self.level_source, setup)

        ground = re.search(
            r"Generic\(\s*pos\s*=\s*\(0,0\),\s*"
            r"surf\s*=\s*pygame\.image\.load\(surf_path\)\.convert\(\),\s*"
            r"groups\s*=\s*self\.all_sprites,\s*"
            r"z\s*=\s*LAYERS\['ground'\]\s*\)",
            block,
        )
        self.assertIsNotNone(ground)
        self.assertNotIn('dynamic_sprites', ground.group(0))


if __name__ == '__main__':
    unittest.main()
