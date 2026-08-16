import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

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


class _FakeSurface:
    def __init__(self, size, label='base'):
        self._size = tuple(size)
        self.label = label
        self.convert_calls = 0

    def convert(self):
        self.convert_calls += 1
        return self

    def get_size(self):
        return self._size


class _FakePygame:
    def __init__(self, loaded_size=(150, 150)):
        self.load_calls = 0
        self.scale_calls = 0
        self.loaded_size = tuple(loaded_size)
        self.last_loaded = None
        self.image = SimpleNamespace(load=self._load)
        self.transform = SimpleNamespace(smoothscale=self._smoothscale)

    def _load(self, path):
        self.load_calls += 1
        self.last_loaded = _FakeSurface(self.loaded_size, label=str(path))
        return self.last_loaded

    def _smoothscale(self, image, size):
        self.scale_calls += 1
        return _FakeSurface(tuple(size), label=f'scaled:{image.label}')


class DialoguePortraitCacheTests(unittest.TestCase):
    def setUp(self):
        utils.clear_dialogue_portrait_cache()
        self._old_pygame = sys.modules.get('pygame')

    def tearDown(self):
        utils.clear_dialogue_portrait_cache()
        if self._old_pygame is None:
            sys.modules.pop('pygame', None)
        else:
            sys.modules['pygame'] = self._old_pygame

    def test_same_portrait_is_loaded_and_converted_only_once(self):
        fake = _FakePygame((150, 150))
        sys.modules['pygame'] = fake

        first = utils.get_dialogue_portrait('/tmp/scientist.jpg')
        second = utils.get_dialogue_portrait('/tmp/scientist.jpg')

        self.assertIs(first, second)
        self.assertEqual(fake.load_calls, 1)
        self.assertEqual(fake.last_loaded.convert_calls, 1)
        self.assertEqual(fake.scale_calls, 0)

    def test_scaled_variant_is_reused_without_reloading_or_rescaling(self):
        fake = _FakePygame((100, 100))
        sys.modules['pygame'] = fake

        first = utils.get_dialogue_portrait('/tmp/scientist.jpg', (150, 150))
        second = utils.get_dialogue_portrait('/tmp/scientist.jpg', (150, 150))
        base = utils.get_dialogue_portrait('/tmp/scientist.jpg')

        self.assertIs(first, second)
        self.assertEqual(first.get_size(), (150, 150))
        self.assertEqual(base.get_size(), (100, 100))
        self.assertEqual(fake.load_calls, 1)
        self.assertEqual(fake.last_loaded.convert_calls, 1)
        self.assertEqual(fake.scale_calls, 1)

    def test_current_size_request_reuses_base_surface(self):
        fake = _FakePygame((150, 150))
        sys.modules['pygame'] = fake

        base = utils.get_dialogue_portrait('/tmp/scientist.jpg')
        sized = utils.get_dialogue_portrait('/tmp/scientist.jpg', (150, 150))

        self.assertIs(base, sized)
        self.assertEqual(fake.load_calls, 1)
        self.assertEqual(fake.scale_calls, 0)

    def test_dialogue_renderers_no_longer_load_or_scale_portraits_per_frame(self):
        for filename in DIALOGUE_RENDER_FILES:
            source = (CODE / filename).read_text(encoding='utf-8')
            with self.subTest(filename=filename):
                self.assertNotIn('pygame.image.load(', source)
                self.assertNotIn('pygame.transform.smoothscale(', source)
                self.assertIn('get_dialogue_portrait(', source)

    def test_all_referenced_dialogue_portraits_exist(self):
        for filename in DIALOGUE_RENDER_FILES:
            source = (CODE / filename).read_text(encoding='utf-8')
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Name) or node.func.id != 'get_resource_path':
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                rel = node.args[0].value
                if isinstance(rel, str) and rel.startswith('graphics/dialogues/'):
                    with self.subTest(filename=filename, portrait=rel):
                        self.assertTrue((ROOT / rel).is_file())

    def test_utils_keeps_pygame_as_a_lazy_dependency(self):
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
