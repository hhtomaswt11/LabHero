import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVEL_PATH = ROOT / 'code' / 'level.py'

TALKS = [
    ('1', 'Mission01'), ('2', 'Mission03'), ('3', 'Mission06'),
    ('7', 'Mission07'), ('11', 'Mission11'), ('16', 'Mission16'),
    ('21', 'Mission21'), ('23', 'Mission23'), ('25', 'Mission25'),
    ('27', 'Mission27'), ('29', 'Mission29'), ('32', 'Mission32'),
    ('35', 'Mission35'), ('36', 'Mission36'), ('37', 'Mission37'),
    ('38', 'Mission38'), ('39', 'Mission39'), ('40', 'Mission40'),
]


def _level_class_ast():
    tree = ast.parse(LEVEL_PATH.read_text())
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Level')


def _method_ast(name):
    return next(
        node for node in _level_class_ast().body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _compiled_toggle(method_name, mission_class_name):
    node = _method_ast(method_name)

    # D.4D moves mission imports inside the first-open guard.  These lifecycle
    # tests deliberately replace the mission class with a stub, so strip only
    # those local imports from the compiled test copy; the real source is
    # validated separately by the D.4D regression suite.
    class _StripLocalImports(ast.NodeTransformer):
        def visit_ImportFrom(self, import_node):
            if import_node.module and import_node.module.startswith('mission'):
                return ast.Pass()
            return import_node

    node = _StripLocalImports().visit(node)
    ast.fix_missing_locations(node)
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)

    created = []

    class StubMission:
        def __init__(self, callback, player):
            self.callback = callback
            self.player = player
            created.append(self)

    namespace = {mission_class_name: StubMission}
    exec(compile(module, str(LEVEL_PATH), 'exec'), namespace)
    return namespace[method_name], created


class TestCheckpointD4CLazyMissionControllers(unittest.TestCase):
    def test_all_talk_controllers_start_unloaded(self):
        init = _method_ast('__init__')
        assignments = {}
        for node in ast.walk(init):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                assignments[target.attr] = node.value

        for suffix, _ in TALKS:
            value = assignments.get(f'talk_{suffix}')
            self.assertIsNotNone(value, f'talk_{suffix} missing from Level.__init__')
            self.assertIsInstance(value, ast.Constant)
            self.assertIsNone(value.value, f'talk_{suffix} must start unloaded')

    def test_first_open_constructs_only_requested_controller(self):
        method, created = _compiled_toggle('toggle_talk_29', 'Mission29')
        obj = types.SimpleNamespace(talk_29=None, talk_29_active=False, player=object())
        obj.toggle_talk_29 = types.MethodType(method, obj)

        obj.toggle_talk_29()

        self.assertTrue(obj.talk_29_active)
        self.assertEqual(len(created), 1)
        self.assertIs(obj.talk_29, created[0])
        self.assertIs(created[0].player, obj.player)

    def test_close_does_not_reconstruct_controller(self):
        method, created = _compiled_toggle('toggle_talk_36', 'Mission36')
        obj = types.SimpleNamespace(talk_36=None, talk_36_active=False, player=object())
        obj.toggle_talk_36 = types.MethodType(method, obj)
        obj.toggle_talk_36()
        first = obj.talk_36

        obj.toggle_talk_36()

        self.assertFalse(obj.talk_36_active)
        self.assertIs(obj.talk_36, first)
        self.assertEqual(len(created), 1)

    def test_reopen_reuses_same_controller(self):
        method, created = _compiled_toggle('toggle_talk_40', 'Mission40')
        obj = types.SimpleNamespace(talk_40=None, talk_40_active=False, player=object())
        obj.toggle_talk_40 = types.MethodType(method, obj)
        obj.toggle_talk_40()
        first = obj.talk_40
        obj.toggle_talk_40()

        obj.toggle_talk_40()

        self.assertTrue(obj.talk_40_active)
        self.assertIs(obj.talk_40, first)
        self.assertEqual(len(created), 1)

    def test_every_toggle_has_lazy_guard_and_correct_factory(self):
        source = LEVEL_PATH.read_text()
        for suffix, mission_class in TALKS:
            guard = f'if not self.talk_{suffix}_active and self.talk_{suffix} is None:'
            factory = f'self.talk_{suffix} = {mission_class}(self.toggle_talk_{suffix}, self.player)'
            self.assertIn(guard, source)
            self.assertIn(factory, source)

    def test_every_controller_preserves_existing_run_update_path(self):
        source = LEVEL_PATH.read_text()
        for suffix, _ in TALKS:
            self.assertIn(f'elif self.talk_{suffix}_active:', source)
            self.assertIn(f'await self.talk_{suffix}.update()', source)

    def test_player_callbacks_remain_wired_to_level_toggles(self):
        source = LEVEL_PATH.read_text()
        for suffix, _ in TALKS:
            self.assertIn(f'talk_{suffix} = self.toggle_talk_{suffix}', source)

    def test_all_lazy_toggles_have_equivalent_lifecycle(self):
        for suffix, mission_class in TALKS:
            method_name = f'toggle_talk_{suffix}'
            method, created = _compiled_toggle(method_name, mission_class)
            obj = types.SimpleNamespace(**{
                f'talk_{suffix}': None,
                f'talk_{suffix}_active': False,
                'player': object(),
            })
            setattr(obj, method_name, types.MethodType(method, obj))
            toggle = getattr(obj, method_name)

            toggle()  # first open -> construct
            first = getattr(obj, f'talk_{suffix}')
            self.assertTrue(getattr(obj, f'talk_{suffix}_active'))
            self.assertEqual(len(created), 1)

            toggle()  # close -> keep
            self.assertFalse(getattr(obj, f'talk_{suffix}_active'))
            self.assertIs(getattr(obj, f'talk_{suffix}'), first)
            self.assertEqual(len(created), 1)

            toggle()  # reopen -> reuse
            self.assertTrue(getattr(obj, f'talk_{suffix}_active'))
            self.assertIs(getattr(obj, f'talk_{suffix}'), first)
            self.assertEqual(len(created), 1)


if __name__ == '__main__':
    unittest.main()
