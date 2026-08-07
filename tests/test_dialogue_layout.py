"""Visual-safety regression tests for the fixed 1280x720 dialogue panel."""
from __future__ import annotations

import ast
import importlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import pygame  # noqa: E402
from utils import (  # noqa: E402
    DIALOGUE_PLAYER_NAME_MAX_CHARS,
    compact_dialogue_player_name,
    prepare_dialogue_text,
)


DIALOGUE_MODULES = (
    'mission01', 'mission02', 'mission03', 'mission04', 'mission05',
    'mission06', 'mission07', 'mission11', 'mission16', 'mission21',
    'mission23', 'mission25', 'mission26', 'mission32', 'mission34', 'mission35',
)
MAX_SAFE_LINE_WIDTH = 1040
MAX_LINES_WITH_BUTTONS = 3
MAX_LINES_WITHOUT_BUTTONS = 5
LONG_PLAYER_NAME = 'W' * 100


class DialogueLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        cls.font = pygame.font.Font(str(PROJECT_ROOT / 'font' / 'LycheeSoda.ttf'), 30)

    @staticmethod
    def _assignment_key(target):
        if isinstance(target, ast.Name):
            return target.id
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == 'self'
        ):
            return target.attr
        return None

    @staticmethod
    def _call_key(argument):
        return DialogueLayoutTests._assignment_key(argument)

    @staticmethod
    def _evaluate_list(module, list_node):
        fake_self = SimpleNamespace(
            player=SimpleNamespace(player_name=LONG_PLAYER_NAME)
        )
        expression = ast.Expression(body=list_node)
        ast.fix_missing_locations(expression)
        return eval(
            compile(expression, str(Path(module.__file__)), 'eval'),
            module.__dict__,
            {'self': fake_self},
        )

    def test_all_mission_dialogue_lines_fit_and_buttons_remain_visible(self):
        violations = []
        for module_name in DIALOGUE_MODULES:
            module = importlib.import_module(module_name)
            source_path = Path(module.__file__)
            tree = ast.parse(source_path.read_text(encoding='utf-8'))

            for class_node in (n for n in tree.body if isinstance(n, ast.ClassDef)):
                for update_node in (
                    n for n in class_node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == 'update'
                ):
                    assignments = {}
                    calls = []
                    for node in ast.walk(update_node):
                        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
                            for target in node.targets:
                                key = self._assignment_key(target)
                                if key:
                                    assignments[key] = node.value
                        if (
                            isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)
                            and node.func.attr == 'menu_message'
                            and node.args
                        ):
                            key = self._call_key(node.args[0])
                            if not key:
                                continue
                            buttons = True
                            for keyword in node.keywords:
                                if (
                                    keyword.arg == 'buttons'
                                    and isinstance(keyword.value, ast.Constant)
                                ):
                                    buttons = bool(keyword.value.value)
                            calls.append((key, buttons, node.lineno))

                    checked = set()
                    for key, buttons, call_line in calls:
                        marker = (key, buttons)
                        if marker in checked or key not in assignments:
                            continue
                        checked.add(marker)
                        messages = self._evaluate_list(module, assignments[key])
                        max_lines = (
                            MAX_LINES_WITH_BUTTONS if buttons
                            else MAX_LINES_WITHOUT_BUTTONS
                        )
                        if len(messages) > max_lines:
                            violations.append(
                                f'{module_name}.{class_node.name}.{key}: '
                                f'{len(messages)} lines, maximum {max_lines} '
                                f'(menu call line {call_line})'
                            )
                        for index, message in enumerate(messages, start=1):
                            rendered = prepare_dialogue_text(message, LONG_PLAYER_NAME)
                            width = self.font.size(rendered)[0]
                            if width > MAX_SAFE_LINE_WIDTH:
                                violations.append(
                                    f'{module_name}.{class_node.name}.{key} line {index}: '
                                    f'{width}px > {MAX_SAFE_LINE_WIDTH}px: {rendered!r}'
                                )

        self.assertEqual([], violations, '\n'.join(violations))

    def test_secondary_npc_dialogues_fit_without_buttons(self):
        module = importlib.import_module('dialogues')
        source_path = Path(module.__file__)
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        violations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
                continue
            if not any(
                isinstance(target, ast.Attribute) and target.attr == 'message'
                for target in node.targets
            ):
                continue
            messages = self._evaluate_list(module, node.value)
            if len(messages) > MAX_LINES_WITHOUT_BUTTONS:
                violations.append(
                    f'dialogues.py line {node.lineno}: {len(messages)} lines '
                    f'> {MAX_LINES_WITHOUT_BUTTONS}'
                )
            for index, message in enumerate(messages, start=1):
                width = self.font.size(str(message))[0]
                if width > MAX_SAFE_LINE_WIDTH:
                    violations.append(
                        f'dialogues.py line {node.lineno}, message {index}: '
                        f'{width}px > {MAX_SAFE_LINE_WIDTH}px: {message!r}'
                    )

        self.assertEqual([], violations, '\n'.join(violations))

    def test_long_player_name_is_compacted_only_for_dialogue_display(self):
        compact = compact_dialogue_player_name(LONG_PLAYER_NAME)
        self.assertLessEqual(len(compact.replace('...', '')), DIALOGUE_PLAYER_NAME_MAX_CHARS)
        self.assertTrue(compact.endswith('...'))

        original = f'Welcome, {LONG_PLAYER_NAME}.'
        rendered = prepare_dialogue_text(original, LONG_PLAYER_NAME)
        self.assertIn(compact, rendered)
        self.assertNotIn(LONG_PLAYER_NAME, rendered)
        self.assertEqual(LONG_PLAYER_NAME, 'W' * 100)  # the stored value is untouched
        self.assertLessEqual(self.font.size(rendered)[0], MAX_SAFE_LINE_WIDTH)


if __name__ == '__main__':
    unittest.main()
