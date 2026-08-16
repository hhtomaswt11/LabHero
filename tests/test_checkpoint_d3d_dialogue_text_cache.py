import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import utils


DIALOGUE_RENDER_FILES = [
    'dialogues.py',
    'mission01.py', 'mission02.py', 'mission03.py', 'mission04.py',
    'mission05.py', 'mission06.py', 'mission07.py', 'mission11.py',
    'mission16.py', 'mission21.py', 'mission23.py', 'mission25.py',
    'mission27.py', 'mission29.py', 'mission32.py', 'mission35.py',
    'mission36.py', 'mission37.py', 'mission38.py', 'mission39.py',
    'mission40.py',
]


class _FakeFont:
    def __init__(self, label):
        self.label = label
        self.calls = []

    def render(self, text, antialias, color):
        value = (self.label, str(text), bool(antialias), color, len(self.calls))
        self.calls.append((str(text), bool(antialias), color))
        return value


class DialogueTextCacheTests(unittest.TestCase):
    def setUp(self):
        utils.clear_dialogue_text_cache()

    def tearDown(self):
        utils.clear_dialogue_text_cache()

    def test_same_font_text_and_style_render_only_once(self):
        font = _FakeFont('body')
        first = utils.get_dialogue_text_surface(font, 'Hello')
        second = utils.get_dialogue_text_surface(font, 'Hello')
        self.assertIs(first, second)
        self.assertEqual(font.calls, [('Hello', True, 'black')])

    def test_different_text_or_style_gets_distinct_cached_surface(self):
        font = _FakeFont('body')
        a = utils.get_dialogue_text_surface(font, 'Line A')
        b = utils.get_dialogue_text_surface(font, 'Line B')
        c = utils.get_dialogue_text_surface(font, 'Line A', antialias=False)
        d = utils.get_dialogue_text_surface(font, 'Line A', color='red')
        self.assertEqual(len(font.calls), 4)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)

    def test_same_text_on_different_fonts_is_not_shared(self):
        body = _FakeFont('body')
        name = _FakeFont('name')
        first = utils.get_dialogue_text_surface(body, 'Vale')
        second = utils.get_dialogue_text_surface(name, 'Vale')
        self.assertEqual(len(body.calls), 1)
        self.assertEqual(len(name.calls), 1)
        self.assertNotEqual(first, second)

    def test_clear_cache_forces_a_fresh_render(self):
        font = _FakeFont('body')
        utils.get_dialogue_text_surface(font, 'Hello')
        utils.clear_dialogue_text_cache()
        utils.get_dialogue_text_surface(font, 'Hello')
        self.assertEqual(len(font.calls), 2)

    def test_menu_message_functions_do_not_rasterize_font_text_per_frame(self):
        for filename in DIALOGUE_RENDER_FILES:
            source = (CODE / filename).read_text(encoding='utf-8')
            tree = ast.parse(source)
            menu_functions = [
                node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'menu_message'
            ]
            self.assertTrue(menu_functions, filename)
            for fn in menu_functions:
                render_calls = []
                helper_calls = []
                for node in ast.walk(fn):
                    if not isinstance(node, ast.Call):
                        continue
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'render':
                        render_calls.append(node.lineno)
                    if isinstance(node.func, ast.Name) and node.func.id == 'get_dialogue_text_surface':
                        helper_calls.append(node.lineno)
                with self.subTest(filename=filename):
                    self.assertEqual(render_calls, [])
                    self.assertTrue(helper_calls)

    def test_utils_keeps_text_cache_independent_of_pygame_import(self):
        tree = ast.parse((CODE / 'utils.py').read_text(encoding='utf-8'))
        top_level_imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_level_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level_imports.append(node.module)
        self.assertNotIn('pygame', top_level_imports)


if __name__ == '__main__':
    unittest.main()
