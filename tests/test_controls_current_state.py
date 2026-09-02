import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "code" / "controls_content.py"
INTRO = ROOT / "code" / "intro.py"
MENU = ROOT / "code" / "menu_2.py"


class ControlsCurrentStateTests(unittest.TestCase):
    def test_current_controls_are_documented(self):
        source = CONTENT.read_text(encoding="utf-8")
        for token in [
            "Press ENTER to continue",
            "Press SPACE to start a New Game",
            "arrow keys or WASD",
            "Press ENTER when close",
            "Press E during exploration to open the Inventory",
            "hint keys",
            "current score",
            "unlocked skins",
            "Left/Right or A/D",
            "E or ESC to close",
            "Press M to open Settings",
        ]:
            self.assertIn(token, source)

    def test_obsolete_or_typo_control_copy_is_gone(self):
        combined = (
            INTRO.read_text(encoding="utf-8")
            + MENU.read_text(encoding="utf-8")
            + CONTENT.read_text(encoding="utf-8")
        )
        self.assertNotIn("left, righ", combined)
        self.assertNotIn("Use arrows (up, down, left, righ)", combined)

    def test_intro_controls_and_settings_reference_use_their_canonical_sources(self):
        intro = INTRO.read_text(encoding="utf-8")
        menu = MENU.read_text(encoding="utf-8")
        self.assertIn("from controls_content import populate_controls_menu", intro)
        self.assertIn("populate_controls_menu(", intro)
        # Settings -> How to Play is intentionally the same scientific/gameplay
        # reference shown by Books -> How to Play.
        self.assertIn("from book_ui import populate_book_menu", menu)
        self.assertIn("populate_book_menu(menu_how_to_play, 'how_to_play')", menu)

    def test_platform_specific_save_copy_is_preserved(self):
        source = CONTENT.read_text(encoding="utf-8")
        self.assertIn("progress is saved automatically", source)
        self.assertIn("Back to Title", source)
        self.assertIn("Save Game and Quit Game", source)


if __name__ == "__main__":
    unittest.main()
