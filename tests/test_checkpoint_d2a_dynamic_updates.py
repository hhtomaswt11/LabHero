import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


class CheckpointD2ADynamicUpdateTests(unittest.TestCase):
    def setUp(self):
        self.level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.sprites_source = (CODE / 'sprites.py').read_text(encoding='utf-8')

    def test_level_updates_only_dedicated_dynamic_group_during_gameplay(self):
        tree = ast.parse(self.level_source)
        run = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run'
        )
        block = ast.get_source_segment(self.level_source, run)

        self.assertIn('self.dynamic_sprites = pygame.sprite.Group()', self.level_source)
        self.assertIn('self.dynamic_sprites.update(dt)', block)
        self.assertNotIn('self.all_sprites.update(dt)', block)
        self.assertIn('self.plant_collision()', block)

    def test_player_water_and_carter_stay_drawable_and_are_dynamic(self):
        # Every always-active sprite with meaningful per-frame behaviour must
        # remain in all_sprites for rendering and also join dynamic_sprites.
        self.assertRegex(
            self.level_source,
            r"Water\([^\n]*\[self\.all_sprites, self\.dynamic_sprites\]\)",
        )
        self.assertRegex(
            self.level_source,
            r"group\s*=\s*\[self\.all_sprites, self\.dynamic_sprites\]",
        )
        self.assertRegex(
            self.level_source,
            r"CarterRevealSprite\([\s\S]*?groups\s*=\s*\[self\.all_sprites, self\.dynamic_sprites\]",
        )

    def test_transient_particles_are_registered_for_updates_at_both_spawn_sites(self):
        # Particles need update(dt) so their lifetime expires. There are two
        # production sites today: plant harvesting in Level and tree damage.
        level_particles = re.findall(
            r"Particle\([\s\S]*?groups\s*=\s*\[self\.all_sprites, self\.dynamic_sprites\][\s\S]*?\)",
            self.level_source,
        )
        self.assertGreaterEqual(len(level_particles), 1)

        self.assertIn('self.dynamic_sprites = dynamic_sprites', self.sprites_source)
        self.assertRegex(
            self.sprites_source,
            r"Particle\([\s\S]*?groups\s*=\s*\[self\.all_sprites, self\.dynamic_sprites\]",
        )

    def test_tree_receives_dynamic_group_only_to_register_future_particles(self):
        tree = ast.parse(self.sprites_source)
        tree_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'Tree'
        )
        init = next(
            node for node in tree_class.body
            if isinstance(node, ast.FunctionDef) and node.name == '__init__'
        )
        args = [arg.arg for arg in init.args.args]
        self.assertIn('dynamic_sprites', args)

        self.assertRegex(
            self.level_source,
            r"Tree\([\s\S]*?dynamic_sprites\s*=\s*self\.dynamic_sprites",
        )

        # Tree itself has no per-frame behaviour; its historical update is a
        # deliberate no-op and therefore it must not be added to dynamic_sprites.
        update = next(
            node for node in tree_class.body
            if isinstance(node, ast.FunctionDef) and node.name == 'update'
        )
        update_block = ast.get_source_segment(self.sprites_source, update)
        self.assertRegex(update_block, r"def update\(self, dt\):\s*pass")

    def test_static_map_sprite_creation_is_not_added_to_dynamic_group(self):
        setup_tree = ast.parse(self.level_source)
        setup = next(
            node for node in ast.walk(setup_tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'setup'
        )
        block = ast.get_source_segment(self.level_source, setup)

        # House graphics and the large pre-rendered ground remain draw-only.
        self.assertIn("Generic((x* TILE_SIZE, y* TILE_SIZE), surf, self.all_sprites, LAYERS['house bottom'])", block)
        self.assertIn("Generic((x* TILE_SIZE, y* TILE_SIZE), surf, self.all_sprites, LAYERS['main'])", block)
        ground_match = re.search(
            r"Generic\(\s*pos\s*=\s*\(0,0\),[\s\S]*?groups\s*=\s*self\.all_sprites,[\s\S]*?z\s*=\s*LAYERS\['ground'\]",
            block,
        )
        self.assertIsNotNone(ground_match)


if __name__ == '__main__':
    unittest.main()
