"""Cross-mission robustness tests for bounds and mission lifecycle guards."""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


MISSION_CLEAR_CALLS = {
    '03': 'clear_mission03_gene_screen_check',
    '04': 'clear_mission04_production_check',
    '05': 'clear_mission05_production_check',
    '06': 'clear_challenge_score',
    '07': 'clear_mission07_objective_check',
    '08': 'clear_mission08_constraint_check',
    '09': 'clear_mission09_design_check',
    '10': 'clear_mission10_robust_design_check',
    '11': 'clear_mission11_flux_fingerprint_check',
    '12': 'clear_mission12_byproduct_check',
    '13': 'clear_mission13_method_check',
    '14': 'clear_mission14_reduction_check',
}


class RobustBoundReaderTests(unittest.TestCase):
    def setUp(self):
        self.default = simulation._build_default_reactions_data()

    @staticmethod
    def _reversed(mapping):
        return dict(reversed(list(mapping.items())))

    def _set_lower(self, reactions, reaction_id, is_open):
        index = list(simulation.REACTIONS.index).index(reaction_id)
        reactions[f'reaction_{index}_lb'] = bool(is_open)

    def test_default_environment_is_order_independent(self):
        self.assertFalse(simulation._environment_has_changes(self.default))
        self.assertFalse(
            simulation._environment_has_changes(self._reversed(self.default))
        )

    def test_oxygen_constrained_environment_is_order_independent(self):
        reactions = dict(self.default)
        self._set_lower(reactions, simulation.MISSION08_OXYGEN_REACTION, False)
        reordered = self._reversed(reactions)

        self.assertEqual(
            simulation._mission08_environment_status(reordered),
            ('oxygen_constrained', True, []),
        )
        self.assertEqual(
            simulation._mission05_environment_status(reordered),
            (True, []),
        )
        self.assertTrue(simulation._environment_has_changes(reordered))

    def test_mission02_substitution_is_order_independent(self):
        reactions = dict(self.default)
        self._set_lower(reactions, simulation.MISSION02_BLOCKED_CARBON_SOURCE, False)
        source = 'EX_fru_e'
        self._set_lower(reactions, source, True)
        reordered = self._reversed(reactions)

        glucose_closed, sources, issues = simulation._mission02_environment_status(
            reordered
        )
        self.assertTrue(glucose_closed)
        self.assertEqual(sources, [source])
        self.assertEqual(issues, [])
        self.assertEqual(
            simulation._mission02_source_lower_bound(source, reordered),
            simulation.MISSION02_COMMON_UPTAKE_BOUND,
        )

    def test_explicit_payload_with_missing_bound_is_rejected_conservatively(self):
        reactions = dict(self.default)
        missing_key = next(key for key in reactions if key.endswith('_ub'))
        reactions.pop(missing_key)

        self.assertTrue(simulation._environment_has_changes(reactions))
        _kind, _oxygen_closed, issues = simulation._mission08_environment_status(
            reactions
        )
        self.assertTrue(any('bounds unavailable' in issue for issue in issues))

    def test_legacy_positional_payload_remains_supported(self):
        legacy = {
            f'legacy_widget_{index}': value
            for index, value in enumerate(self.default.values())
        }
        self.assertFalse(simulation._environment_has_changes(legacy))
        oxygen_index = list(simulation.REACTIONS.index).index(
            simulation.MISSION08_OXYGEN_REACTION
        )
        legacy[f'legacy_widget_{oxygen_index * 2}'] = False
        self.assertEqual(
            simulation._mission08_environment_status(legacy),
            ('oxygen_constrained', True, []),
        )


class MissionLifecycleSourceTests(unittest.TestCase):
    @staticmethod
    def _method_node(source, method_name):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                return node
        raise AssertionError(f'Method {method_name} not found')

    @staticmethod
    def _segment(source, node):
        lines = source.splitlines()
        end = getattr(node, 'end_lineno', node.lineno)
        return '\n'.join(lines[node.lineno - 1:end])

    def test_missions03_to14_activation_is_idempotent_before_clear(self):
        failures = []
        for mission_id, clear_call in MISSION_CLEAR_CALLS.items():
            source = (CODE_DIR / f'mission{mission_id}.py').read_text(encoding='utf-8')
            node = self._method_node(source, f'activate_mission{mission_id}')
            segment = self._segment(source, node)
            completed = f"if '{mission_id}' in self.missions_completed:"
            active = f"if '{mission_id}' in self.missions_activated:"
            clear = f'{clear_call}()'
            try:
                if not (segment.index(completed) < segment.index(active) < segment.index(clear)):
                    failures.append(f'Mission {mission_id}: guard order is unsafe')
            except ValueError as exc:
                failures.append(f'Mission {mission_id}: missing lifecycle element: {exc}')
        self.assertEqual([], failures, '\n'.join(failures))

    def test_missions03_to14_delivery_requires_unlock_and_activation(self):
        failures = []
        for mission_id in MISSION_CLEAR_CALLS:
            source = (CODE_DIR / f'mission{mission_id}.py').read_text(encoding='utf-8')
            node = self._method_node(source, 'deliver_results')
            segment = self._segment(source, node)
            unlock = f"if not self.player.is_mission_unlocked('{mission_id}'):"
            active = f"if '{mission_id}' not in self.missions_activated:"
            # Both guards must precede any load of mission evidence.
            load_positions = [
                segment.find(token)
                for token in ('load_mission', 'load_challenge_score')
                if segment.find(token) >= 0
            ]
            first_load = min(load_positions) if load_positions else len(segment)
            try:
                if not (segment.index(unlock) < segment.index(active) < first_load):
                    failures.append(f'Mission {mission_id}: delivery guard order is unsafe')
            except ValueError as exc:
                failures.append(f'Mission {mission_id}: missing delivery guard: {exc}')
        self.assertEqual([], failures, '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
