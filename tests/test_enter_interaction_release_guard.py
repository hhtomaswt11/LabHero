import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / 'code' / 'player.py'
LEVEL = ROOT / 'code' / 'level.py'


class EnterInteractionReleaseGuardTests(unittest.TestCase):
    def test_player_starts_enter_interaction_locked(self):
        source = PLAYER.read_text(encoding='utf-8')
        self.assertIn('self.interaction_enter_locked = True', source)

    def test_player_exposes_release_guard(self):
        source = PLAYER.read_text(encoding='utf-8')
        tree = ast.parse(source)
        player = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Player')
        methods = {node.name for node in player.body if isinstance(node, ast.FunctionDef)}
        self.assertIn('block_interaction_until_enter_release', methods)
        self.assertIn('_interaction_enter_pressed_once', methods)

    def test_world_interaction_uses_edge_trigger_not_raw_enter_poll(self):
        source = PLAYER.read_text(encoding='utf-8')
        self.assertIn('if self._interaction_enter_pressed_once(keys):', source)
        self.assertNotIn(
            'if keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]:\n                # timer for tool use',
            source,
        )

    def test_release_gate_handles_return_and_keypad_enter(self):
        source = PLAYER.read_text(encoding='utf-8')
        self.assertIn('keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]', source)
        self.assertIn('self.interaction_enter_locked = False', source)

    def test_level_blocks_enter_when_modal_returns_to_map(self):
        source = LEVEL.read_text(encoding='utf-8')
        self.assertIn('self._map_modal_was_active = False', source)
        self.assertIn('def suppress_enter_after_modal_close(self):', source)
        self.assertIn('self.player.block_interaction_until_enter_release()', source)
        self.assertIn('self.suppress_enter_after_modal_close()', source)

    def test_python_sources_still_parse(self):
        ast.parse(PLAYER.read_text(encoding='utf-8'))
        ast.parse(LEVEL.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
