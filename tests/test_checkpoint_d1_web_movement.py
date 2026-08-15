import ast
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


def _load_substep_function():
    """Execute only the pure movement helper without importing pygame."""
    source = (CODE / 'player.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == '_movement_substep_plan'
    )
    helper.decorator_list = []
    module = ast.Module(body=[helper], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {'ceil': math.ceil, 'MAX_COLLISION_STEP': 16.0}
    exec(compile(module, str(CODE / 'player.py'), 'exec'), namespace)
    return namespace['_movement_substep_plan']


class CheckpointD1WebMovementTests(unittest.TestCase):
    def test_low_fps_distances_are_split_into_safe_collision_steps(self):
        plan = _load_substep_function()

        # speed=750 px/s: representative movement distances at 60, 10 and 5 FPS.
        for distance in (12.5, 75.0, 150.0, -75.0, -150.0):
            steps, step = plan(distance)
            self.assertGreaterEqual(steps, 1)
            self.assertLessEqual(abs(step), 16.0)
            self.assertAlmostEqual(distance, steps * step, places=9)

        self.assertEqual((0, 0.0), plan(0.0))
        self.assertEqual(1, plan(12.5)[0])      # normal 60 FPS keeps one check
        self.assertEqual(5, plan(75.0)[0])      # 10 FPS frame
        self.assertEqual(10, plan(150.0)[0])    # 5 FPS frame

    def test_player_move_checks_collision_inside_each_axis_substep(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        move = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'move'
        )
        block = ast.get_source_segment(source, move)

        self.assertIn('_movement_substep_plan(horizontal_distance)', block)
        self.assertIn('_movement_substep_plan(vertical_distance)', block)
        self.assertRegex(
            block,
            r'for _ in range\(horizontal_steps\):[\s\S]*?self\.collision\([\'\"]horizontal[\'\"]\)',
        )
        self.assertRegex(
            block,
            r'for _ in range\(vertical_steps\):[\s\S]*?self\.collision\([\'\"]vertical[\'\"]\)',
        )

    def test_camera_draw_order_is_equivalent_but_sorted_only_once(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        custom_draw = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'custom_draw'
        )
        block = ast.get_source_segment(source, custom_draw)

        self.assertIn('key=lambda sprite: (sprite.z, sprite.rect.centery)', block)
        self.assertIn('sprite.rect.colliderect(view_rect)', block)
        self.assertEqual(1, block.count('sorted('))
        self.assertNotIn('for layer in LAYERS.values()', block)

        # For the project's numeric z layers, one (z, y) sort is exactly the
        # same ordering as the previous layer-loop + per-layer y sort.
        sample = [
            ('a', 7, 300), ('b', 1, 900), ('c', 7, 100),
            ('d', 1, 50), ('e', 10, 20), ('f', 7, 100),
        ]
        old_order = []
        for layer in range(11):
            old_order.extend(sorted((s for s in sample if s[1] == layer), key=lambda s: s[2]))
        new_order = sorted(sample, key=lambda s: (s[1], s[2]))
        self.assertEqual(old_order, new_order)

    def test_checkpoint_d1_does_not_change_mission_sources(self):
        # Structural guard: this checkpoint belongs only to movement/rendering.
        player_source = (CODE / 'player.py').read_text(encoding='utf-8')
        level_source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn('MAX_COLLISION_STEP = 16.0', player_source)
        self.assertIn('view_rect = pygame.Rect(', level_source)


if __name__ == '__main__':
    unittest.main()
