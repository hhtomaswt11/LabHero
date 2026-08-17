import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
INTRO_PATH = CODE / 'intro.py'


class _FakeRect:
    def __init__(self, center=None):
        self.center = center


class _FakeSurface:
    def __init__(self, label):
        self.label = label
        self.get_rect_calls = []

    def get_rect(self, **kwargs):
        self.get_rect_calls.append(dict(kwargs))
        return _FakeRect(center=kwargs.get('center'))


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
        self.blit_calls.append((surface.label, rect.center))


class _FakeDisplay:
    def __init__(self):
        self.surface = _FakeDisplaySurface()

    def get_surface(self):
        return self.surface


class _FakePygame:
    def __init__(self):
        self.font_calls = []
        self.render_calls = []
        self.font = _FakeFontModule(self)
        self.display = _FakeDisplay()


class _FakePanel:
    def __init__(self):
        self.update_calls = 0

    async def update(self):
        self.update_calls += 1


class _FakeButton:
    created = []

    def __init__(self, x, y, width, height, surface, text, callback, **kwargs):
        self.args = (x, y, width, height, surface, text, callback)
        self.kwargs = kwargs
        self.process_calls = 0
        type(self).created.append(self)

    def process(self):
        self.process_calls += 1


def _load_intro(platform):
    source = INTRO_PATH.read_text(encoding='utf-8')
    tree = ast.parse(source)
    intro_cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'Intro'
    )
    module = ast.Module(body=[intro_cls], type_ignores=[])
    ast.fix_missing_locations(module)

    fake_pygame = _FakePygame()
    _FakeButton.created = []
    namespace = {
        'pygame': fake_pygame,
        'sys': types.SimpleNamespace(platform=platform),
        'SCREEN_WIDTH': 1280,
        'SCREEN_HEIGHT': 720,
        'get_resource_path': lambda value: f'/resource/{value}',
        'Tutorial': _FakePanel,
        'Story': _FakePanel,
        'Button': _FakeButton,
    }
    exec(compile(module, str(INTRO_PATH), 'exec'), namespace)
    return namespace['Intro'], fake_pygame


class IntroStaticSurfaceCacheTests(unittest.TestCase):
    def test_run_contains_no_font_render_or_text_geometry_work(self):
        tree = ast.parse(INTRO_PATH.read_text(encoding='utf-8'))
        intro_cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Intro')
        run = next(node for node in intro_cls.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
        forbidden = []
        for node in ast.walk(run):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr in {'Font', 'render', 'get_rect'}:
                forbidden.append((node.func.attr, node.lineno))
        self.assertEqual(forbidden, [])

    def test_desktop_static_labels_are_rendered_once_during_init(self):
        Intro, fake = _load_intro('linux')
        intro = Intro()
        self.assertEqual(fake.font_calls, [
            ('/resource/font/LycheeSoda.ttf', 130),
            ('/resource/font/LycheeSoda.ttf', 30),
        ])
        self.assertEqual(fake.render_calls, [
            (130, 'Lab Hero', False, 'black'),
            (30, 'press ENTER to continue', False, 'red'),
            (30, 'or press SPACE to new game', False, (60, 150, 140)),
        ])
        self.assertIsNotNone(intro.text2)

    def test_web_static_labels_are_rendered_once_during_init(self):
        Intro, fake = _load_intro('emscripten')
        intro = Intro()
        self.assertEqual(fake.render_calls, [
            (130, 'Lab Hero', False, 'black'),
            (30, 'press ENTER to play', False, 'red'),
        ])
        self.assertIsNone(intro.text2)
        self.assertIsNone(intro.text_rect2)

    def test_repeated_desktop_frames_reuse_cached_surfaces(self):
        Intro, fake = _load_intro('linux')
        intro = Intro()
        font_count = len(fake.font_calls)
        render_count = len(fake.render_calls)
        intro.run()
        intro.run()
        self.assertEqual(len(fake.font_calls), font_count)
        self.assertEqual(len(fake.render_calls), render_count)
        self.assertEqual(fake.display.surface.fill_calls, ['gold', 'gold'])
        self.assertEqual(len(fake.display.surface.blit_calls), 6)

    def test_repeated_web_frames_reuse_cached_surfaces(self):
        Intro, fake = _load_intro('emscripten')
        intro = Intro()
        render_count = len(fake.render_calls)
        intro.run()
        intro.run()
        self.assertEqual(len(fake.render_calls), render_count)
        self.assertEqual(len(fake.display.surface.blit_calls), 4)

    def test_cached_geometry_preserves_original_positions(self):
        Intro, _ = _load_intro('linux')
        intro = Intro()
        self.assertEqual(intro.title_rect.center, (640, 260))
        self.assertEqual(intro.text_rect.center, (640, 360))
        self.assertEqual(intro.text_rect2.center, (640, 400))

    def test_buttons_are_still_created_and_processed_each_frame(self):
        Intro, _ = _load_intro('linux')
        intro = Intro()
        intro.run()
        intro.run()
        self.assertEqual(len(_FakeButton.created), 4)
        self.assertEqual([button.args[5] for button in _FakeButton.created], [
            'Controls', 'Story', 'Controls', 'Story'
        ])
        self.assertTrue(all(button.process_calls == 1 for button in _FakeButton.created))


if __name__ == '__main__':
    unittest.main()
