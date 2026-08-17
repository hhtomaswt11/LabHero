import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIALOGUES_PATH = ROOT / 'code' / 'dialogues.py'
PLAYER_PATH = ROOT / 'code' / 'player.py'

GENERIC_CHARACTERS = (
    'Sequeira', 'Pacheco', 'Nuno', 'Fernanda', 'Emanuel',
    'Alexandre', 'Capela', 'Marta', 'Oscar', 'Miguel',
)


def _tree():
    return ast.parse(DIALOGUES_PATH.read_text(encoding='utf-8'))


def _dialogues_class():
    return next(node for node in _tree().body if isinstance(node, ast.ClassDef) and node.name == 'Dialogues')


def _method(name):
    return next(
        node for node in _dialogues_class().body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _compile_choosing_character(path_calls, text_calls):
    node = _method('choosing_character')
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)

    def fake_path(path):
        path_calls.append(path)
        return f'/fake/{path}'

    def fake_text(font, text, antialias=True, color='black'):
        text_calls.append((font, text, antialias, color))
        return ('surface', text)

    namespace = {
        'get_resource_path': fake_path,
        'get_dialogue_text_surface': fake_text,
    }
    exec(compile(module, str(DIALOGUES_PATH), 'exec'), namespace)
    return namespace['choosing_character']


def _fake_dialogue():
    return types.SimpleNamespace(
        character=None,
        _prepared_character=object(),
        font_nome=object(),
        message=None,
        imagem_path=None,
        nome=None,
    )


class TestCheckpointD4EGenericDialogueCache(unittest.TestCase):
    def test_dialogues_init_uses_dedicated_prepared_character_sentinel(self):
        init = _method('__init__')
        assignments = [
            node for node in ast.walk(init)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == 'self'
                and target.attr == '_prepared_character'
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)
        self.assertIsInstance(assignments[0].value, ast.Call)
        self.assertIsInstance(assignments[0].value.func, ast.Name)
        self.assertEqual(assignments[0].value.func.id, 'object')

    def test_same_character_is_prepared_only_once(self):
        path_calls, text_calls = [], []
        method = _compile_choosing_character(path_calls, text_calls)
        obj = _fake_dialogue()

        method(obj, 'Sequeira')
        first_message = obj.message
        first_path = obj.imagem_path
        first_name = obj.nome
        method(obj, 'Sequeira')

        self.assertIs(obj.message, first_message)
        self.assertIs(obj.imagem_path, first_path)
        self.assertIs(obj.nome, first_name)
        self.assertEqual(path_calls, ['graphics/dialogues/Sequeira.jpg'])
        self.assertEqual([call[1] for call in text_calls], ['Dr. Sequeira'])

    def test_switching_character_prepares_the_new_dialogue(self):
        path_calls, text_calls = [], []
        method = _compile_choosing_character(path_calls, text_calls)
        obj = _fake_dialogue()

        method(obj, 'Sequeira')
        method(obj, 'Nuno')

        self.assertEqual(obj.character, 'Nuno')
        self.assertEqual(obj._prepared_character, 'Nuno')
        self.assertEqual(
            path_calls,
            ['graphics/dialogues/Sequeira.jpg', 'graphics/dialogues/Nuno.jpg'],
        )
        self.assertEqual([call[1] for call in text_calls], ['Dr. Sequeira', 'Dr. Alves'])

    def test_none_on_first_call_still_prepares_the_legacy_fallback(self):
        path_calls, text_calls = [], []
        method = _compile_choosing_character(path_calls, text_calls)
        obj = _fake_dialogue()

        method(obj, None)

        self.assertEqual(obj.character, None)
        self.assertEqual(obj.message, ['Hello there! Are you enjoying LabHero so far?'])
        self.assertEqual(obj.imagem_path, '/fake/graphics/dialogues/carter.jpg')
        self.assertEqual(obj.nome, ('surface', 'Dr.'))
        self.assertEqual(len(path_calls), 1)
        self.assertEqual(len(text_calls), 1)

    def test_choosing_character_no_longer_calls_font_render_directly(self):
        choosing = _method('choosing_character')
        render_calls = [
            node for node in ast.walk(choosing)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'render'
        ]
        self.assertEqual(render_calls, [])

    def test_all_generic_name_surfaces_use_existing_dialogue_text_cache(self):
        choosing = _method('choosing_character')
        helper_calls = [
            node for node in ast.walk(choosing)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'get_dialogue_text_surface'
        ]
        # Ten named generic NPCs plus the legacy fallback label.
        self.assertEqual(len(helper_calls), 11)

    def test_generic_npc_set_in_player_interaction_is_unchanged(self):
        source = PLAYER_PATH.read_text(encoding='utf-8')
        for name in GENERIC_CHARACTERS:
            self.assertIn(repr(name), source)
        self.assertIn('self.character = sprite.name', source)
        self.assertIn('self.dialogues()', source)

    def test_level_can_keep_calling_choosing_character_each_frame_safely(self):
        level_source = (ROOT / 'code' / 'level.py').read_text(encoding='utf-8')
        self.assertIn('self.dialogues.choosing_character(self.player.character)', level_source)
        self.assertIn('self.dialogues.update()', level_source)


if __name__ == '__main__':
    unittest.main()
