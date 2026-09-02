import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTRO = ROOT / "code" / "intro.py"
GAME = ROOT / "LabHero.py"


class TitleNewGameConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intro_source = INTRO.read_text(encoding="utf-8")
        cls.game_source = GAME.read_text(encoding="utf-8")
        cls.game_tree = ast.parse(cls.game_source)

    def test_confirmation_copy_is_cached_and_explicit(self):
        self.assertIn("'Start a new game?'", self.intro_source)
        self.assertIn("'This will erase your current saved progress.'", self.intro_source)
        self.assertIn("'Press SPACE again to confirm.'", self.intro_source)
        self.assertIn("'Press ESC to go back.'", self.intro_source)
        self.assertIn("self.new_game_confirmation_pending = False", self.intro_source)

    def test_confirmation_overlay_suppresses_title_buttons(self):
        marker = "if self.new_game_confirmation_pending:"
        self.assertIn(marker, self.intro_source)
        block = self.intro_source[self.intro_source.index(marker):]
        self.assertIn("pygame.draw.rect", block)
        self.assertIn("self.confirm_title", block)
        self.assertIn("return", block)

    def test_first_space_only_requests_confirmation(self):
        intro_run = next(
            node for node in ast.walk(self.game_tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "intro_run"
        )
        outer_space_branches = []
        for node in ast.walk(intro_run):
            if not isinstance(node, ast.If):
                continue
            test = ast.unparse(node.test)
            if test == "event.key == pygame.K_SPACE":
                outer_space_branches.append(node)

        request_branches = [
            node for node in outer_space_branches
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "request_new_game_confirmation"
                for child in ast.walk(node)
            )
        ]
        self.assertEqual(len(request_branches), 1)
        request_source = ast.get_source_segment(self.game_source, request_branches[0])
        self.assertNotIn("clear_web_persistent_storage", request_source)
        self.assertNotIn("os.remove", request_source)

    def test_save_deletion_exists_only_behind_pending_confirmation(self):
        pending_if = next(
            node for node in ast.walk(self.game_tree)
            if isinstance(node, ast.If)
            and ast.unparse(node.test) == "self.intro.new_game_confirmation_pending"
        )
        pending_source = ast.get_source_segment(self.game_source, pending_if)
        self.assertIn("event.key == pygame.K_ESCAPE", pending_source)
        self.assertIn("event.key == pygame.K_SPACE", pending_source)
        self.assertIn("clear_web_persistent_storage()", pending_source)
        self.assertIn("os.remove(path)", pending_source)
        self.assertIn("Level(copy.deepcopy(DEFAULT_INVENTORY_2))", pending_source)

    def test_keyboard_handling_uses_keydown_not_held_key_state(self):
        self.assertIn("if event.type != pygame.KEYDOWN:", self.game_source)
        self.assertNotIn("pygame.key.get_pressed()[pygame.K_SPACE]", self.game_source)


if __name__ == "__main__":
    unittest.main()
