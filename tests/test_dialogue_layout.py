"""Visual-safety regression tests for fixed-size dialogue/feedback renderers."""
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


MAX_SAFE_LINE_WIDTH = 1040
MAX_LINES_WITH_BUTTONS = 3
MAX_LINES_WITHOUT_BUTTONS = 5
# animation_text_save() renders one centered 30px line on a 1280px-wide screen.
# Keep a small margin rather than accepting text that only fits edge-to-edge.
MAX_SAFE_ANIMATION_TEXT_WIDTH = 1240
LONG_PLAYER_NAME = 'W' * 100


def _is_named_call(node, name):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Name) and func.id == name
    ) or (
        isinstance(func, ast.Attribute) and func.attr == name
    )


def _discover_dialogue_modules():
    """Discover every mission module that actually calls menu_message().

    This deliberately avoids a hand-maintained module list so future missions are
    covered automatically as soon as they introduce fixed-panel NPC dialogue.
    """
    modules = []
    for source_path in sorted(CODE_DIR.glob('mission[0-9][0-9].py')):
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'menu_message'
            for node in ast.walk(tree)
        ):
            modules.append(source_path.stem)
    return tuple(modules)


DIALOGUE_MODULES = _discover_dialogue_modules()


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
    def _evaluate_list(module, list_node, campaign_mode='easy'):
        fake_self = SimpleNamespace(
            player=SimpleNamespace(
                player_name=LONG_PLAYER_NAME,
                campaign_mode=campaign_mode,
            )
        )

        # Some current NPC dialogue is intentionally built from local runtime
        # values before assigning self.message (for example Dr. Alves'
        # campaign-specific key budget/current balance).  This AST-based layout
        # test evaluates only the list expression, so reproduce those locals
        # rather than forcing production dialogue back to hard-coded strings.
        locals_context = {'self': fake_self}
        if hasattr(module, 'initial_keys_for_campaign'):
            budget = module.initial_keys_for_campaign(campaign_mode)
            current = dict(budget)
            if hasattr(module, 'golden_egg_gold_reward_for_campaign'):
                current['gold'] += module.golden_egg_gold_reward_for_campaign(campaign_mode)
            locals_context.update({'budget': budget, 'current': current})

        expression = ast.Expression(body=list_node)
        ast.fix_missing_locations(expression)
        return eval(
            compile(expression, str(Path(module.__file__)), 'eval'),
            module.__dict__,
            locals_context,
        )

    def test_dialogue_discovery_includes_all_current_fixed_panel_missions(self):
        # These missions historically fell outside the old hand-maintained list.
        for module_name in ('mission27', 'mission29', 'mission36', 'mission37', 'mission38'):
            self.assertIn(module_name, DIALOGUE_MODULES)

    def test_all_mission_dialogue_lines_fit_and_buttons_remain_visible(self):
        violations = []
        for module_name in DIALOGUE_MODULES:
            module = importlib.import_module(module_name)
            source_path = Path(module.__file__)
            tree = ast.parse(source_path.read_text(encoding='utf-8'))

            for class_node in (n for n in tree.body if isinstance(n, ast.ClassDef)):
                methods = (
                    n for n in class_node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and any(
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'menu_message'
                        for call in ast.walk(n)
                    )
                )
                for method_node in methods:
                    assignments = {}
                    calls = []
                    for node in ast.walk(method_node):
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
            # Check both student campaign modes because Alves' message contains
            # campaign-specific key budgets. Static NPC text is harmlessly
            # evaluated twice, while dynamic text is now protected in both paths.
            for campaign_mode in ('normal', 'easy'):
                messages = self._evaluate_list(module, node.value, campaign_mode=campaign_mode)
                if len(messages) > MAX_LINES_WITHOUT_BUTTONS:
                    violations.append(
                        f'dialogues.py line {node.lineno} ({campaign_mode}): '
                        f'{len(messages)} lines > {MAX_LINES_WITHOUT_BUTTONS}'
                    )
                for index, message in enumerate(messages, start=1):
                    # Generic dialogues pass every line through prepare_dialogue_text()
                    # before rendering, so long student names are compacted at runtime.
                    rendered_message = prepare_dialogue_text(message, LONG_PLAYER_NAME)
                    width = self.font.size(str(rendered_message))[0]
                    if width > MAX_SAFE_LINE_WIDTH:
                        violations.append(
                            f'dialogues.py line {node.lineno} ({campaign_mode}), message {index}: '
                            f'{width}px > {MAX_SAFE_LINE_WIDTH}px: {rendered_message!r}'
                        )

        self.assertEqual([], violations, '\n'.join(violations))

    def test_static_animation_feedback_lines_fit_screen(self):
        """Guard every literal animation_text_save() message in code/."""
        violations = []
        for source_path in sorted(CODE_DIR.rglob('*.py')):
            tree = ast.parse(source_path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not _is_named_call(node, 'animation_text_save') or not node.args:
                    continue
                argument = node.args[0]
                if not (
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                ):
                    continue
                width = self.font.size(argument.value)[0]
                if width > MAX_SAFE_ANIMATION_TEXT_WIDTH:
                    violations.append(
                        f'{source_path.relative_to(PROJECT_ROOT)}:{node.lineno}: '
                        f'{width}px > {MAX_SAFE_ANIMATION_TEXT_WIDTH}px: '
                        f'{argument.value!r}'
                    )
        self.assertEqual([], violations, '\n'.join(violations))

    def test_mission07_and_08_issue_feedback_templates_fit_screen(self):
        """M7/M8 forward current_issues[0] into the one-line overlay.

        Inspect their validator issue templates automatically so a future edit
        cannot silently reintroduce an oversized error message.
        """
        simulation = importlib.import_module('simulation')
        source_path = Path(simulation.__file__)
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        target_builders = {'_build_mission07_data', '_build_mission08_data'}
        target_runners = {'run_mission07_objective_check', 'run_mission08_constraint_check'}
        messages = []

        for function_node in (
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            if function_node.name in target_builders:
                for node in ast.walk(function_node):
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == 'issues'
                        and node.func.attr == 'append'
                        and node.args
                    ):
                        continue
                    expression_node = node.args[0]
                    if not isinstance(expression_node, (ast.Constant, ast.JoinedStr)):
                        continue
                    expression = ast.Expression(body=expression_node)
                    ast.fix_missing_locations(expression)
                    try:
                        value = eval(
                            compile(expression, str(source_path), 'eval'),
                            simulation.__dict__,
                            {},
                        )
                    except Exception:
                        continue
                    if isinstance(value, str):
                        messages.append((function_node.name, node.lineno, value))

            if function_node.name in target_runners:
                for node in ast.walk(function_node):
                    if not isinstance(node, ast.Assign):
                        continue
                    if not any(
                        isinstance(target, ast.Name) and target.id == 'objective_error'
                        for target in node.targets
                    ):
                        continue
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        messages.append((function_node.name, node.lineno, node.value.value))

        self.assertTrue(messages)
        violations = []
        for function_name, line_no, message in messages:
            width = self.font.size(message)[0]
            if width > MAX_SAFE_ANIMATION_TEXT_WIDTH:
                violations.append(
                    f'{function_name}:{line_no}: {width}px > '
                    f'{MAX_SAFE_ANIMATION_TEXT_WIDTH}px: {message!r}'
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
