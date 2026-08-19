import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIN_MENU_PATH = ROOT / 'code' / 'skin_menu.py'
LEVEL_PATH = ROOT / 'code' / 'level.py'


class InventoryMenuSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skin_source = SKIN_MENU_PATH.read_text(encoding='utf-8')
        cls.level_source = LEVEL_PATH.read_text(encoding='utf-8')
        cls.skin_tree = ast.parse(cls.skin_source)
        cls.level_tree = ast.parse(cls.level_source)

    def _class_method(self, class_name, method_name):
        for node in self.skin_tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name == method_name:
                        return child
        self.fail(f'Method {class_name}.{method_name} not found')

    def _level_method(self, method_name):
        for node in self.level_tree.body:
            if isinstance(node, ast.ClassDef) and node.name == 'Level':
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name == method_name:
                        return child
        self.fail(f'Level.{method_name} not found')

    def test_key_art_assets_exist(self):
        required = [
            ROOT / 'graphics' / 'keys' / 'Key 3' / 'key3_bronze.png',
            ROOT / 'graphics' / 'keys' / 'Key 3' / 'key3_silver.png',
            ROOT / 'graphics' / 'keys' / 'Key 3' / 'key3_gold.png',
            ROOT / 'graphics' / 'keys' / 'Key 3' / 'key3_grey.png',
        ]
        for path in required:
            self.assertTrue(path.is_file(), f'Missing key art asset: {path}')

    def test_menu_title_changed_to_inventory(self):
        self.assertIn("'Inventory'", self.skin_source)

    def test_key_lock_supports_e(self):
        init_method = self._class_method('SkinSelectionMenu', '__init__')
        init_source = ast.get_source_segment(self.skin_source, init_method)
        self.assertIn('pygame.K_e', init_source)

    def test_key_icons_loaded_from_graphics_keys(self):
        load_method = self._class_method('SkinSelectionMenu', '_load_key_icons')
        load_source = ast.get_source_segment(self.skin_source, load_method)
        self.assertIn('graphics/keys/Key 3/key3_bronze.png', load_source)
        self.assertIn('graphics/keys/Key 3/key3_silver.png', load_source)
        self.assertIn('graphics/keys/Key 3/key3_gold.png', load_source)
        self.assertIn('graphics/keys/Key 3/key3_grey.png', load_source)

    def test_update_closes_with_e_or_escape_and_c_is_removed(self):
        update_method = self._class_method('SkinSelectionMenu', 'update')
        update_source = ast.get_source_segment(self.skin_source, update_method)
        self.assertIn('_pressed_once(pygame.K_E'.lower(), update_source.lower())
        self.assertNotIn('pygame.K_c', update_source)
        self.assertIn('_pressed_once(pygame.K_ESCAPE'.lower(), update_source.lower())

    def test_score_summary_uses_hint_system_total_and_max(self):
        score_method = self._class_method('SkinSelectionMenu', '_score_summary')
        score_source = ast.get_source_segment(self.skin_source, score_method)
        self.assertIn('self.player.hint_system.get_total_score()', score_source)
        self.assertIn('self.player.hint_system.get_max_score(40)', score_source)

    def test_draw_contains_keys_score_and_skin_sections(self):
        draw_method = self._class_method('SkinSelectionMenu', 'draw')
        draw_source = ast.get_source_segment(self.skin_source, draw_method)
        for token in ("'KEYS'", "'SCORE'", "'SKIN'", "'E / Esc close"):
            self.assertIn(token, draw_source)

    def test_draw_uses_grey_icon_when_key_count_zero(self):
        row_method = self._class_method('SkinSelectionMenu', '_draw_key_row')
        row_source = ast.get_source_segment(self.skin_source, row_method)
        self.assertIn("icon_key = key_type if count > 0 else 'grey'", row_source)

    def test_level_shortcut_handles_e_only(self):
        shortcut_method = self._level_method('handle_skin_menu_shortcut')
        shortcut_source = ast.get_source_segment(self.level_source, shortcut_method)
        self.assertIn('pygame.K_e', shortcut_source)
        self.assertNotIn('pygame.K_c', shortcut_source)
        self.assertIn('self.skin_menu.open()', shortcut_source)
        self.assertNotIn('pygame.K_c', self.skin_source)


if __name__ == '__main__':
    unittest.main()
