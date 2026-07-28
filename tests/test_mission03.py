"""Regression tests for Mission 03 and GPR-correct knockouts.

Run from the project root with:
    python -m unittest tests.test_mission03
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402
from gpr import evaluate_gpr_rule  # noqa: E402


class Mission03RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()

    def _simulate(self, knocked_out=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False
        simul, constraints = simulation._build_local_constraints(genes, self.reactions)
        simul.objective = simulation.MISSION03_GROWTH_OBJECTIVE
        result = simul.simulate(method=simulation.MISSION03_METHOD, constraints=constraints)
        growth = simulation._as_float_or_none(simulation._normalise_result(result))
        self.assertIsNotNone(growth)
        return float(growth), genes, constraints

    def _record(self, knocked_out=None, report=None, method=None, objective=None, reactions=None, growth=None):
        if growth is None:
            growth, genes, _constraints = self._simulate(knocked_out)
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False
        with patch.object(simulation, 'save_mission03_gene_screen_check'):
            return simulation._build_mission03_trial_data(
                method or simulation.MISSION03_METHOD,
                objective or simulation.MISSION03_GROWTH_OBJECTIVE,
                growth,
                genes,
                reactions or self.reactions,
                existing_report=report,
            )

    def test_backend_and_desktop_use_the_same_gpr_semantics(self):
        backend_path = PROJECT_ROOT / 'backend' / 'app' / 'gpr.py'
        spec = importlib.util.spec_from_file_location('labhero_backend_gpr', backend_path)
        backend_gpr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_gpr)

        rules = [
            ('b0351 or b1241', {'b1241'}),
            ('b0351 or b1241', {'b0351', 'b1241'}),
            ('b0728 and b0729', {'b0728'}),
            ('(b1 and b2) or b3', {'b1'}),
        ]
        for rule, knockouts in rules:
            self.assertEqual(
                evaluate_gpr_rule(rule, knockouts),
                backend_gpr.evaluate_gpr_rule(rule, knockouts),
            )

    def test_boolean_gpr_semantics(self):
        self.assertTrue(evaluate_gpr_rule('b0351 or b1241', {'b1241'}))
        self.assertFalse(evaluate_gpr_rule('b0351 or b1241', {'b0351', 'b1241'}))
        self.assertFalse(evaluate_gpr_rule('b0728 and b0729', {'b0728'}))
        self.assertTrue(evaluate_gpr_rule('(b1 and b2) or b3', {'b1'}))

    def test_constraints_respect_or_and_single_gene_rules(self):
        _growth, _genes, constraints = self._simulate(['b1241'])
        self.assertNotEqual(constraints.get('ACALD'), (0.0, 0.0))
        self.assertNotEqual(constraints.get('ALCD2x'), (0.0, 0.0))

        _growth, _genes, constraints = self._simulate(['b0728'])
        self.assertEqual(constraints.get('SUCOAS'), (0.0, 0.0))

        _growth, _genes, constraints = self._simulate(['b2926'])
        self.assertEqual(constraints.get('PGK'), (0.0, 0.0))

    def test_candidate_growth_pattern_and_complete_evidence(self):
        report = self._record([])
        baseline = report['baseline_growth']
        self.assertGreater(baseline, simulation.MISSION03_MIN_BASELINE_GROWTH)

        for gene_id in simulation.MISSION03_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)
            self.assertTrue(report['current_run_valid'], report['current_issues'])

        self.assertEqual(report['valid_trial_count'], 6)
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['essential_unique'])
        self.assertEqual(report['essential_gene'], 'b2926')
        self.assertTrue(report['evidence_ready'])

        trials = report['trials']
        self.assertGreaterEqual(trials['b1241']['growth_ratio'], 0.99)
        self.assertGreater(trials['b0728']['growth_ratio'], 0.90)
        self.assertGreater(trials['b3919']['growth_ratio'], 0.60)
        self.assertLessEqual(trials['b3919']['growth_ratio'], 0.90)
        self.assertGreater(trials['b3736']['growth_ratio'], 0.25)
        self.assertLessEqual(trials['b3736']['growth_ratio'], 0.60)
        self.assertGreater(trials['b2278']['growth_ratio'], 0.01)
        self.assertLessEqual(trials['b2278']['growth_ratio'], 0.25)
        self.assertLessEqual(trials['b2926']['growth_ratio'], 0.01)

    def test_delivery_requires_complete_evidence_and_accepts_aliases(self):
        self.assertFalse(simulation.mission03_answer_matches('b2926', {}))
        report = self._record([])
        for gene_id in simulation.MISSION03_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)

        for answer in ('b2926', 'B2926', 'pgk', 'PGK', 'b2926 (pgk)', 'b2926/pgk'):
            self.assertTrue(simulation.mission03_answer_matches(answer, report))
        self.assertFalse(simulation.mission03_answer_matches('b2278', report))

    def test_invalid_runs_do_not_increment_or_replace_evidence(self):
        report = self._record([])
        report = self._record(['b1241'], report=report)
        expected_trials = dict(report['trials'])

        changed_environment = dict(self.reactions)
        oxygen_index = list(simulation.REACTIONS.index).index('EX_o2_e')
        changed_environment[f'reaction_{oxygen_index}_lb'] = False

        invalid_cases = [
            (['b2926', 'b2278'], simulation.MISSION03_METHOD, simulation.MISSION03_GROWTH_OBJECTIVE, self.reactions, 'exactly one'),
            (['b0351'], simulation.MISSION03_METHOD, simulation.MISSION03_GROWTH_OBJECTIVE, self.reactions, 'not one of'),
            (['b2926'], 'pFBA', simulation.MISSION03_GROWTH_OBJECTIVE, self.reactions, 'same FBA'),
            (['b2926'], simulation.MISSION03_METHOD, 'EX_etoh_e', self.reactions, 'biomass objective'),
            (['b2926'], simulation.MISSION03_METHOD, simulation.MISSION03_GROWTH_OBJECTIVE, changed_environment, 'default environment'),
        ]

        for knockouts, method, objective, reactions, expected_issue in invalid_cases:
            # These cases are invalid because of their configuration, independently
            # of the solver result.  In particular, multiple knockouts can make the
            # LP infeasible and therefore return no numeric objective value.  Supply
            # a harmless numeric result here so this test isolates the validation
            # rule that it is intended to exercise.
            candidate = self._record(
                knockouts,
                report=report,
                method=method,
                objective=objective,
                reactions=reactions,
                growth=0.0,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertFalse(candidate['current_run_recorded'])
            self.assertEqual(candidate['valid_trial_count'], 1)
            self.assertEqual(candidate['trials'], expected_trials)
            self.assertTrue(any(expected_issue in issue for issue in candidate['current_issues']), candidate['current_issues'])

    def test_infeasible_or_missing_result_is_rejected_without_erasing_evidence(self):
        report = self._record([])
        report = self._record(['b1241'], report=report)
        expected_trials = dict(report['trials'])
        expected_baseline = report['baseline_growth']

        genes = dict(self.genes)
        genes['b2926'] = False
        genes['b2278'] = False

        with patch.object(simulation, 'save_mission03_gene_screen_check'):
            candidate = simulation._build_mission03_trial_data(
                simulation.MISSION03_METHOD,
                simulation.MISSION03_GROWTH_OBJECTIVE,
                None,
                genes,
                self.reactions,
                existing_report=report,
            )

        self.assertFalse(candidate['current_run_valid'])
        self.assertFalse(candidate['current_run_recorded'])
        self.assertEqual(candidate['valid_trial_count'], 1)
        self.assertEqual(candidate['trials'], expected_trials)
        self.assertEqual(candidate['baseline_growth'], expected_baseline)
        self.assertTrue(
            any('numeric biomass-growth result' in issue for issue in candidate['current_issues']),
            candidate['current_issues'],
        )
        self.assertTrue(
            any('exactly one gene knockout' in issue for issue in candidate['current_issues']),
            candidate['current_issues'],
        )

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = {
            'evidence_ready': True,
            'essential_gene': 'b2926',
            'trials': {'b2926': {'growth': 0.0}},
        }
        with patch.object(simulation, 'load_mission03_gene_screen_check', return_value=completed) as loader:
            text = simulation.build_mission03_evidence_report_text({})
            self.assertFalse(simulation.mission03_answer_matches('b2926', {}))
        loader.assert_not_called()
        self.assertIn('Build a controlled gene-essentiality comparison', text)
        self.assertNotIn('unchanged default environment', text)

    def test_progression_requires_mission02(self):
        self.assertFalse(simulation.is_mission03_unlocked([]))
        self.assertFalse(simulation.is_mission03_unlocked(['01']))
        self.assertTrue(simulation.is_mission03_unlocked(['02']))


if __name__ == '__main__':
    unittest.main()