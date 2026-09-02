import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'

class SettingsBackToSpawnpointTests(unittest.TestCase):
    def test_settings_places_spawn_button_between_volume_and_how_to_play(self):
        source = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        volume = source.index("menu.add.range_slider('Volume'")
        spawn = source.index("menu.add.button('Back to Spawnpoint'")
        how_to = source.index("menu.add.button('How to Play'")
        self.assertLess(volume, spawn)
        self.assertLess(spawn, how_to)

    def test_player_captures_constructor_start_before_saved_state_restore(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        capture = source.index('self.spawnpoint = pygame.math.Vector2(pos)')
        restore = source.index('self._apply_player_state(self.player_state)')
        self.assertLess(capture, restore)

    def test_spawn_return_updates_position_hitbox_and_interaction_state(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        method = source[source.index('def return_to_spawnpoint'):source.index('def get_campaign_context')]
        for token in (
            'self.pos.update(self.spawnpoint.x, self.spawnpoint.y)',
            'self.rect.center = (round(self.pos.x), round(self.pos.y))',
            'self.hitbox.center = self.rect.center',
            'self.direction.update(0, 0)',
            "self.status = 'down_idle'",
            'self.update_interaction_area()',
            'self.get_target_pos()',
        ):
            self.assertIn(token, method)

    def test_spawn_button_persists_and_closes_settings_without_resetting_campaign(self):
        source = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        method = source[source.index('def back_to_spawnpoint'):source.index('async def setup')]
        self.assertIn('self.player.return_to_spawnpoint()', method)
        self.assertIn('save_file(self.player.get_save_data())', method)
        self.assertIn('self.toggle_menu()', method)
        self.assertIn('menu.disable()', method)
        for forbidden in ('missions_completed.clear', 'missions_activated.clear', 'clear_web_persistent_storage', 'DEFAULT_INVENTORY_2'):
            self.assertNotIn(forbidden, method)

    def test_map_still_has_single_canonical_start_object(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        player_layer = next(layer for layer in root.findall('objectgroup') if layer.get('name') == 'Player')
        starts = [obj for obj in player_layer.findall('object') if obj.get('name') == 'Start']
        self.assertEqual(len(starts), 1)
        self.assertIsNotNone(starts[0].get('x'))
        self.assertIsNotNone(starts[0].get('y'))

    def test_controls_document_non_destructive_spawn_return(self):
        source = (CODE / 'controls_content.py').read_text(encoding='utf-8')
        self.assertIn('Back to Spawnpoint', source)
        self.assertIn('without resetting progress', source)

    def test_how_to_play_documents_spawn_return_without_progress_reset(self):
        source = (ROOT / 'data' / 'books' / 'How to Play.md').read_text(encoding='utf-8')
        self.assertIn('Back to Spawnpoint', source)
        self.assertIn('does not reset missions, score, hints', source)

if __name__ == '__main__':
    unittest.main()
