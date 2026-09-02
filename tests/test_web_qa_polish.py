import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "code" / "books.py"
BOOK_UI = ROOT / "code" / "book_ui.py"
MENU = ROOT / "code" / "menu_2.py"
PLAYER = ROOT / "code" / "player.py"
SETTINGS = ROOT / "code" / "settings.py"


class WebQaPolishTests(unittest.TestCase):
    def test_library_book_back_disables_standalone_book_menu(self):
        source = BOOKS.read_text(encoding="utf-8")
        self.assertIn("populate_book_menu(menu, book_id, back_action=menu.disable)", source)

    def test_settings_how_to_play_uses_library_content(self):
        source = MENU.read_text(encoding="utf-8")
        self.assertIn("populate_book_menu(menu_how_to_play, 'how_to_play')", source)
        self.assertNotIn("populate_controls_menu(\n            menu_how_to_play", source)

    def test_credits_include_both_developers(self):
        source = MENU.read_text(encoding="utf-8")
        self.assertIn("Game developed by Monica Leiras and Tomas Melo", source)

    def test_music_starts_at_slider_value_15(self):
        settings = SETTINGS.read_text(encoding="utf-8")
        player = PLAYER.read_text(encoding="utf-8")
        menu = MENU.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_MUSIC_VOLUME_PERCENT = 15", settings)
        self.assertIn("DEFAULT_MUSIC_VOLUME_PERCENT / 100.0", player)
        self.assertIn("DEFAULT_MUSIC_VOLUME_PERCENT / 100.0", menu)
        self.assertIn("MUSIC_VOLUME_SCALE", player)

    def test_canonical_book_ui_has_back_control(self):
        source = BOOK_UI.read_text(encoding="utf-8")
        self.assertIn("'Back'", source)
        self.assertIn("back_action", source)


if __name__ == "__main__":
    unittest.main()
