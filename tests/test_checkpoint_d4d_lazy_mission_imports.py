import ast
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVEL_PATH = ROOT / 'code' / 'level.py'

TALKS = [
    ('1', 'mission01', 'Mission01'), ('2', 'mission03', 'Mission03'),
    ('3', 'mission06', 'Mission06'), ('7', 'mission07', 'Mission07'),
    ('11', 'mission11', 'Mission11'), ('16', 'mission16', 'Mission16'),
    ('21', 'mission21', 'Mission21'), ('23', 'mission23', 'Mission23'),
    ('25', 'mission25', 'Mission25'), ('27', 'mission27', 'Mission27'),
    ('29', 'mission29', 'Mission29'), ('32', 'mission32', 'Mission32'),
    ('35', 'mission35', 'Mission35'), ('36', 'mission36', 'Mission36'),
    ('37', 'mission37', 'Mission37'), ('38', 'mission38', 'Mission38'),
    ('39', 'mission39', 'Mission39'), ('40', 'mission40', 'Mission40'),
]


def _tree():
    return ast.parse(LEVEL_PATH.read_text())


def _level_class():
    return next(node for node in _tree().body if isinstance(node, ast.ClassDef) and node.name == 'Level')


def _method(name):
    return next(
        node for node in _level_class().body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _compile_method(name):
    node = _method(name)
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, str(LEVEL_PATH), 'exec'), namespace)
    return namespace[name]


class TestCheckpointD4DLazyMissionImports(unittest.TestCase):
    def test_no_mission_modules_are_imported_at_level_module_scope(self):
        top_level_imports = [
            node for node in _tree().body
            if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('mission')
        ]
        self.assertEqual(top_level_imports, [])

    def test_each_controller_import_is_inside_its_toggle(self):
        for suffix, module_name, class_name in TALKS:
            method = _method(f'toggle_talk_{suffix}')
            imports = [
                node for node in ast.walk(method)
                if isinstance(node, ast.ImportFrom) and node.module == module_name
            ]
            self.assertEqual(len(imports), 1, f'{module_name} should have one lazy import')
            self.assertEqual([alias.name for alias in imports[0].names], [class_name])

    def test_each_lazy_import_lives_inside_first_open_guard(self):
        for suffix, module_name, _ in TALKS:
            method = _method(f'toggle_talk_{suffix}')
            guards = [node for node in method.body if isinstance(node, ast.If)]
            self.assertEqual(len(guards), 1)
            guard = guards[0]
            # EASY.2B may add a mode branch inside the first-open guard, but
            # Normal mission modules must still stay below that outer guard.
            imports = [
                node for node in ast.walk(guard)
                if isinstance(node, ast.ImportFrom) and node.module == module_name
            ]
            self.assertEqual(len(imports), 1, f'{module_name} import escaped lazy guard')

    def test_import_precedes_controller_construction(self):
        for suffix, module_name, class_name in TALKS:
            guard = next(node for node in _method(f'toggle_talk_{suffix}').body if isinstance(node, ast.If))
            imports = [
                node for node in ast.walk(guard)
                if isinstance(node, ast.ImportFrom) and node.module == module_name
            ]
            assignments = [
                node for node in ast.walk(guard)
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == class_name
            ]
            self.assertEqual(len(imports), 1)
            self.assertEqual(len(assignments), 1)
            self.assertLess(imports[0].lineno, assignments[0].lineno)

    def test_old_eager_mission02_import_is_removed(self):
        source = LEVEL_PATH.read_text()
        self.assertNotIn('from mission02 import Mission02', source)

    def test_first_open_imports_and_constructs_requested_controller(self):
        suffix, module_name, class_name = ('29', 'mission29', 'Mission29')
        created = []

        class StubMission:
            def __init__(self, callback, player):
                created.append((callback, player))

        stub_module = types.ModuleType(module_name)
        setattr(stub_module, class_name, StubMission)
        previous = sys.modules.get(module_name)
        sys.modules[module_name] = stub_module
        try:
            method = _compile_method(f'toggle_talk_{suffix}')
            obj = types.SimpleNamespace(talk_29=None, talk_29_active=False, player=object())
            obj.toggle_talk_29 = types.MethodType(method, obj)
            obj.toggle_talk_29()
            self.assertTrue(obj.talk_29_active)
            self.assertIsInstance(obj.talk_29, StubMission)
            self.assertEqual(len(created), 1)
        finally:
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous

    def test_reopen_reuses_instance_without_needing_module_again(self):
        suffix, module_name, class_name = ('36', 'mission36', 'Mission36')

        class StubMission:
            def __init__(self, callback, player):
                self.callback = callback
                self.player = player

        stub_module = types.ModuleType(module_name)
        setattr(stub_module, class_name, StubMission)
        previous = sys.modules.get(module_name)
        sys.modules[module_name] = stub_module
        try:
            method = _compile_method(f'toggle_talk_{suffix}')
            obj = types.SimpleNamespace(talk_36=None, talk_36_active=False, player=object())
            obj.toggle_talk_36 = types.MethodType(method, obj)
            obj.toggle_talk_36()
            first = obj.talk_36
            obj.toggle_talk_36()  # close

            # If the local import were executed on reopen this would now fail.
            sys.modules.pop(module_name, None)
            obj.toggle_talk_36()
            self.assertTrue(obj.talk_36_active)
            self.assertIs(obj.talk_36, first)
        finally:
            if previous is not None:
                sys.modules[module_name] = previous
            else:
                sys.modules.pop(module_name, None)

    def test_all_18_controller_factories_remain_present(self):
        source = LEVEL_PATH.read_text()
        for suffix, _, class_name in TALKS:
            self.assertIn(
                f'self.talk_{suffix} = {class_name}(self.toggle_talk_{suffix}, self.player)',
                source,
            )


if __name__ == '__main__':
    unittest.main()
