import ast
import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


class _FakeTextRect:
    def __init__(self, width, height=20):
        self.width = width
        self.height = height


class _FakeTextSurface:
    def __init__(self, text):
        self.text = text

    def get_rect(self):
        return _FakeTextRect(max(1, len(self.text)) * 8)


class _FakeFont:
    def __init__(self, owner, path, size):
        self.owner = owner
        self.path = path
        self.size = size

    def render(self, text, antialias, color):
        self.owner.render_calls.append((str(text), bool(antialias), color))
        return _FakeTextSurface(str(text))


class _FakeFontModule:
    def __init__(self, owner):
        self.owner = owner

    def Font(self, path, size):
        self.owner.font_calls.append((path, size))
        return _FakeFont(self.owner, path, size)


class _FakeSurface:
    def __init__(self, owner, size):
        self.owner = owner
        self.size = tuple(size)
        self.fill_calls = []
        self.blit_calls = []
        owner.surface_calls.append(self.size)

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, tuple(position)))


class _FakeRect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def collidepoint(self, position):
        px, py = position
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


class _FakeMouse:
    def __init__(self):
        self.position = (0, 0)
        self.left_pressed = False

    def get_pos(self):
        return self.position

    def get_pressed(self, num_buttons=3):
        values = [False] * num_buttons
        values[0] = self.left_pressed
        return tuple(values)


class _FakeScreen:
    def __init__(self):
        self.blit_calls = []

    def blit(self, surface, rect):
        self.blit_calls.append((surface, rect))


class _FakePygame(types.ModuleType):
    def __init__(self):
        super().__init__('pygame')
        self.font_calls = []
        self.render_calls = []
        self.surface_calls = []
        self.mouse = _FakeMouse()
        self.font = _FakeFontModule(self)
        self.Rect = _FakeRect

    def Surface(self, size):
        return _FakeSurface(self, size)


class ButtonVisualCacheTests(unittest.TestCase):
    def setUp(self):
        self.previous_pygame = sys.modules.get('pygame')
        self.fake_pygame = _FakePygame()
        sys.modules['pygame'] = self.fake_pygame
        sys.modules.pop('button', None)
        self.button = importlib.import_module('button')
        self.button.clear_button_resource_cache()

    def tearDown(self):
        sys.modules.pop('button', None)
        if self.previous_pygame is None:
            sys.modules.pop('pygame', None)
        else:
            sys.modules['pygame'] = self.previous_pygame

    def _make_button(self, text='Yes', callback=lambda: None, **kwargs):
        return self.button.Button(
            200, 650, 150, 50, _FakeScreen(), text, callback, **kwargs
        )

    def test_many_identical_buttons_build_font_text_and_state_surfaces_once(self):
        buttons = [self._make_button() for _ in range(50)]
        self.assertEqual(len(self.fake_pygame.font_calls), 1)
        self.assertEqual(len(self.fake_pygame.render_calls), 1)
        self.assertEqual(len(self.fake_pygame.surface_calls), 3)
        self.assertIs(buttons[0].font, buttons[-1].font)
        self.assertIs(buttons[0].buttonSurf, buttons[-1].buttonSurf)
        self.assertIs(buttons[0]._buttonVisuals, buttons[-1]._buttonVisuals)

    def test_different_text_reuses_font_but_builds_separate_visuals(self):
        yes = self._make_button('Yes')
        later = self._make_button('Not now')
        self.assertIs(yes.font, later.font)
        self.assertEqual(len(self.fake_pygame.font_calls), 1)
        self.assertEqual(len(self.fake_pygame.render_calls), 2)
        self.assertEqual(len(self.fake_pygame.surface_calls), 6)
        self.assertIsNot(yes._buttonVisuals, later._buttonVisuals)

    def test_style_variants_do_not_share_incompatible_visuals(self):
        normal = self._make_button('Controls')
        inverted = self._make_button('Controls', bg_color='black', font_color='white')
        self.assertIs(normal.font, inverted.font)
        self.assertEqual(len(self.fake_pygame.font_calls), 1)
        self.assertEqual(len(self.fake_pygame.render_calls), 2)
        self.assertEqual(len(self.fake_pygame.surface_calls), 6)
        self.assertIsNot(normal._buttonVisuals, inverted._buttonVisuals)

    def test_cached_visuals_do_not_share_click_state_between_instances(self):
        calls = []
        self.fake_pygame.mouse.position = (210, 660)
        self.fake_pygame.mouse.left_pressed = True

        first = self._make_button(callback=lambda: calls.append('first'))
        second = self._make_button(callback=lambda: calls.append('second'))
        self.assertIs(first._buttonVisuals, second._buttonVisuals)
        self.assertFalse(first.alreadyPressed)
        self.assertFalse(second.alreadyPressed)

        first.process()
        second.process()
        self.assertEqual(calls, ['first', 'second'])
        self.assertTrue(first.alreadyPressed)
        self.assertTrue(second.alreadyPressed)

    def test_process_preserves_debounce_and_creates_no_new_visual_resources(self):
        calls = []
        button = self._make_button(callback=lambda: calls.append('click'))
        resources_before = (
            len(self.fake_pygame.font_calls),
            len(self.fake_pygame.render_calls),
            len(self.fake_pygame.surface_calls),
        )
        self.fake_pygame.mouse.position = (210, 660)

        self.fake_pygame.mouse.left_pressed = True
        button.process()
        button.process()
        self.assertEqual(calls, ['click'])

        self.fake_pygame.mouse.left_pressed = False
        button.process()
        self.fake_pygame.mouse.left_pressed = True
        button.process()
        self.assertEqual(calls, ['click', 'click'])
        self.assertEqual(resources_before, (
            len(self.fake_pygame.font_calls),
            len(self.fake_pygame.render_calls),
            len(self.fake_pygame.surface_calls),
        ))

    def test_one_press_branch_keeps_existing_per_frame_callback_semantics(self):
        calls = []
        button = self._make_button(callback=lambda: calls.append('click'), onePress=True)
        self.fake_pygame.mouse.position = (210, 660)
        self.fake_pygame.mouse.left_pressed = True
        button.process()
        button.process()
        self.assertEqual(calls, ['click', 'click'])

    def test_dialogue_renderers_still_construct_fresh_buttons(self):
        expected_files = {
            'dialogues.py',
            'mission01.py', 'mission02.py', 'mission03.py', 'mission04.py',
            'mission05.py', 'mission06.py', 'mission07.py', 'mission11.py',
            'mission16.py', 'mission21.py', 'mission23.py', 'mission25.py',
            'mission27.py', 'mission29.py', 'mission32.py', 'mission35.py',
            'mission36.py', 'mission37.py', 'mission38.py', 'mission39.py',
            'mission40.py',
        }
        found = set()
        for filename in expected_files:
            source = (CODE / filename).read_text(encoding='utf-8')
            tree = ast.parse(source)
            menu_functions = [
                node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'menu_message'
            ]
            self.assertTrue(menu_functions, filename)
            button_calls = [
                node for fn in menu_functions for node in ast.walk(fn)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == 'Button'
            ]
            if button_calls:
                found.add(filename)
                self.assertGreaterEqual(len(button_calls), 2, filename)
        self.assertEqual(found, expected_files)

    def test_button_process_does_not_rebuild_fonts_text_or_surfaces(self):
        tree = ast.parse((CODE / 'button.py').read_text(encoding='utf-8'))
        process = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'process'
        )
        forbidden = []
        for node in ast.walk(process):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr in {'Font', 'render', 'Surface', 'fill'}:
                forbidden.append((node.func.attr, node.lineno))
            if isinstance(node.func, ast.Name) and node.func.id == 'Surface':
                forbidden.append(('Surface', node.lineno))
        self.assertEqual(forbidden, [])


if __name__ == '__main__':
    unittest.main()
