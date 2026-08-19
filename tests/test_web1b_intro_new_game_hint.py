import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTRO = ROOT / "code" / "intro.py"

class WebIntroNewGameHintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = INTRO.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_intro_exposes_continue_and_new_game_labels(self):
        self.assertIn("press ENTER to continue", self.source)
        self.assertIn("or press SPACE to new game", self.source)

    def test_intro_no_longer_uses_web_only_play_label(self):
        self.assertNotIn("press ENTER to play", self.source)

    def test_second_label_is_drawn_when_present(self):
        intro_cls = next(n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == "Intro")
        run = next(n for n in intro_cls.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        run_source = ast.get_source_segment(self.source, run)
        self.assertIn("self.display_surface.blit(self.text2, self.text_rect2)", run_source)

if __name__ == "__main__":
    unittest.main()
