import ast
import asyncio
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
FUNCTIONS_PATH = CODE / 'functions.py'


class _FakeRect:
    def __init__(self):
        self.inflate_calls = []

    def inflate(self, x, y):
        self.inflate_calls.append((x, y))
        return ('inflated', x, y)


class _FakeSurface:
    def __init__(self, label):
        self.label = label
        self.rect_calls = []

    def get_rect(self, **kwargs):
        self.rect_calls.append(dict(kwargs))
        return _FakeRect()


class _FakeFont:
    def __init__(self, owner, path, size):
        self.owner = owner
        self.path = path
        self.size = size

    def render(self, text, antialias, color):
        self.owner.render_calls.append((self.size, str(text), bool(antialias), color))
        return _FakeSurface(str(text))


class _FakeFontModule:
    def __init__(self, owner):
        self.owner = owner

    def Font(self, path, size):
        self.owner.font_calls.append((path, size))
        return _FakeFont(self.owner, path, size)


class _FakeDisplaySurface:
    def __init__(self):
        self.fill_calls = []
        self.blit_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, rect):
        self.blit_calls.append((surface, rect))


class _FakeDisplay:
    def __init__(self, owner):
        self.owner = owner
        self.surface = _FakeDisplaySurface()
        self.update_calls = 0

    def get_surface(self):
        return self.surface

    def update(self):
        self.update_calls += 1


class _FakeClock:
    def __init__(self, owner):
        self.owner = owner

    def tick(self, fps):
        self.owner.tick_calls.append(fps)
        return 20


class _FakeTime:
    def __init__(self, owner):
        self.owner = owner

    def Clock(self):
        self.owner.clock_calls += 1
        return _FakeClock(self.owner)


class _FakeDraw:
    def __init__(self, owner):
        self.owner = owner

    def rect(self, surface, color, rect, width, border_radius):
        self.owner.draw_calls.append((surface, color, rect, width, border_radius))


class _FakePygame:
    def __init__(self):
        self.font_calls = []
        self.render_calls = []
        self.tick_calls = []
        self.clock_calls = 0
        self.draw_calls = []
        self.font = _FakeFontModule(self)
        self.display = _FakeDisplay(self)
        self.time = _FakeTime(self)
        self.draw = _FakeDraw(self)


def _load_play_animation(fake_pygame):
    source = FUNCTIONS_PATH.read_text(encoding='utf-8')
    tree = ast.parse(source)
    fn = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == '_play_animation'
    )
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        'pygame': fake_pygame,
        'asyncio': asyncio,
        'get_resource_path': lambda value: f'/resource/{value}',
        'SCREEN_WIDTH': 1280,
        'SCREEN_HEIGHT': 720,
    }
    exec(compile(module, str(FUNCTIONS_PATH), 'exec'), namespace)
    return namespace['_play_animation']


class AnimationTextCacheTests(unittest.TestCase):
    def test_normal_animation_builds_text_font_and_surface_once(self):
        fake = _FakePygame()
        play = _load_play_animation(fake)
        asyncio.run(play('Saved!', 60, False))

        # Three 20 ms frames were drawn, but immutable resources were created once.
        self.assertEqual(fake.tick_calls, [60, 60, 60])
        self.assertEqual(fake.font_calls, [('/resource/font/LycheeSoda.ttf', 30)])
        self.assertEqual(fake.render_calls, [(30, 'Saved!', False, 'black')])
        self.assertEqual(fake.display.update_calls, 3)
        self.assertEqual(len(fake.draw_calls), 3)
        self.assertEqual(len(fake.display.surface.blit_calls), 3)

    def test_fullscreen_animation_builds_title_and_text_once_each(self):
        fake = _FakePygame()
        play = _load_play_animation(fake)
        asyncio.run(play('Loading...', 20, True))

        self.assertEqual(fake.font_calls, [
            ('/resource/font/LycheeSoda.ttf', 100),
            ('/resource/font/LycheeSoda.ttf', 30),
        ])
        self.assertEqual(fake.render_calls, [
            (100, 'Lab Hero', False, 'black'),
            (30, 'Loading...', False, 'black'),
        ])
        self.assertEqual(fake.display.surface.fill_calls, ['gold'])
        # fullscreen preserves the old forced 1000 ms duration: 50 * 20 ms frames.
        self.assertEqual(len(fake.tick_calls), 50)
        self.assertEqual(fake.display.update_calls, 50)

    def test_animation_loop_contains_no_font_construction_or_render(self):
        tree = ast.parse(FUNCTIONS_PATH.read_text(encoding='utf-8'))
        fn = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == '_play_animation'
        )
        loop = next(node for node in ast.walk(fn) if isinstance(node, ast.While))
        forbidden = []
        for node in ast.walk(loop):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr in {'Font', 'render', 'get_rect', 'inflate'}:
                forbidden.append((node.func.attr, node.lineno))
        self.assertEqual(forbidden, [])

    def test_text_geometry_is_prepared_before_loop(self):
        tree = ast.parse(FUNCTIONS_PATH.read_text(encoding='utf-8'))
        fn = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == '_play_animation'
        )
        loop = next(node for node in fn.body if isinstance(node, ast.While))
        assignments = {
            target.id: node.lineno
            for node in fn.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for name in ('text_font', 'text_surf', 'text_rect', 'text_backdrop_rect'):
            self.assertIn(name, assignments)
            self.assertLess(assignments[name], loop.lineno)

    def test_loop_keeps_frame_update_timing_and_async_yield(self):
        tree = ast.parse(FUNCTIONS_PATH.read_text(encoding='utf-8'))
        fn = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == '_play_animation'
        )
        loop = next(node for node in ast.walk(fn) if isinstance(node, ast.While))
        attrs = [
            node.func.attr
            for node in ast.walk(loop)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        self.assertIn('update', attrs)
        self.assertIn('tick', attrs)
        self.assertIn('sleep', attrs)

    def test_queue_contract_is_unchanged(self):
        tree = ast.parse(FUNCTIONS_PATH.read_text(encoding='utf-8'))
        fn = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == 'animation_text_save'
        )
        append_calls = [
            node for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'append'
        ]
        self.assertEqual(len(append_calls), 1)
        arg = append_calls[0].args[0]
        self.assertIsInstance(arg, ast.Tuple)
        self.assertEqual([elt.id for elt in arg.elts if isinstance(elt, ast.Name)], ['text', 'time', 'fullscreen'])


if __name__ == '__main__':
    unittest.main()
