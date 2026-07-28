"""Regression tests for Mission 04 growth-coupled ethanol evidence.

Run from the project root with:
    python3 -m unittest discover -s tests -p "test_mission04.py"
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
from gpr import disabled_reaction_ids  # noqa: E402


class Mission04RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()

    def _simulate(self, knocked_out=None, method=None, objective=None, reactions=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False

        active_reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, active_reactions)
        simul.objective = objective or simulation.MISSION04_GROWTH_OBJECTIVE
        result = simul.simulate(
            method=method or simulation.MISSION04_METHOD,
            constraints=constraints,
        )
        objective_result = simulation._normalise_result(result)
        production_fluxes = simulation._build_production_flux_data(
            [simulation.MISSION04_PRODUCTION_OBJECTIVE],
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        medium_fluxes = simulation._build_medium_flux_data(
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        return objective_result, production_fluxes, medium_fluxes, genes, constraints

    def _record(
        self,
        knocked_out=None,
        report=None,
        method=None,
        objective=None,
        reactions=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
        tracked=True,
    ):
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            (
                objective_result,
                production_fluxes,
                medium_fluxes,
                genes,
                _constraints,
            ) = self._simulate(
                knocked_out,
                method=method,
                objective=objective,
                reactions=reactions,
            )
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False

        selected_fluxes = (
            [simulation.MISSION04_PRODUCTION_OBJECTIVE]
            if tracked
            else []
        )
        with (
            patch.object(simulation, 'save_mission04_production_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected_fluxes),
        ):
            return simulation._build_mission04_trial_data(
                method or simulation.MISSION04_METHOD,
                objective or simulation.MISSION04_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                reactions or self.reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(ethanol=0.0, oxygen_uptake=1.0):
        production_fluxes = {
            'selected_ids': [simulation.MISSION04_PRODUCTION_OBJECTIVE],
            'items': [{
                'reaction_id': simulation.MISSION04_PRODUCTION_OBJECTIVE,
                'production_flux': float(ethanol),
                'raw_flux': float(ethanol),
            }],
        }
        medium_fluxes = {
            'items': [{
                'reaction_id': simulation.MISSION04_OXYGEN_REACTION,
                'raw_flux': -float(oxygen_uptake),
                'uptake_flux': float(oxygen_uptake),
                'secretion_flux': 0.0,
            }],
        }
        return production_fluxes, medium_fluxes

    def test_gpr_correction_invalidates_old_target_and_supports_new_target(self):
        _result, _prod, _medium, _genes, constraints = self._simulate(['b2297'])
        self.assertNotEqual(constraints.get('PTAr'), (0.0, 0.0))

        _result, _prod, _medium, _genes, constraints = self._simulate(['b2278'])
        self.assertEqual(constraints.get('NADH16'), (0.0, 0.0))

    def test_backend_and_desktop_disable_the_same_reactions(self):
        backend_path = PROJECT_ROOT / 'backend' / 'app' / 'gpr.py'
        spec = importlib.util.spec_from_file_location('labhero_backend_gpr_m04', backend_path)
        backend_gpr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_gpr)

        for knockouts in ({'b2297'}, {'b2278'}, {'b1241'}, {'b0728'}):
            self.assertEqual(
                set(disabled_reaction_ids(simulation.model, knockouts)),
                set(backend_gpr.disabled_reaction_ids(simulation.model, knockouts)),
            )

    def test_candidate_pattern_and_complete_evidence(self):
        report = self._record([])
        self.assertAlmostEqual(report['baseline_growth'], 0.873922, places=3)
        self.assertAlmostEqual(report['baseline_production'], 0.0, places=3)
        self.assertGreater(report['baseline_oxygen_uptake'], 1.0)

        for gene_id in simulation.MISSION04_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)
            self.assertTrue(report['current_run_valid'], report['current_issues'])

        self.assertEqual(report['valid_trial_count'], 4)
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['winner_unique'])
        self.assertEqual(report['winning_gene'], 'b2278')
        self.assertTrue(report['evidence_ready'])

        trials = report['trials']
        self.assertAlmostEqual(trials['b1241']['production'], 0.0, places=3)
        self.assertGreaterEqual(trials['b1241']['growth_ratio'], 0.99)
        self.assertAlmostEqual(trials['b0728']['production'], 0.0, places=3)
        self.assertGreater(trials['b0728']['growth_ratio'], 0.90)
        self.assertAlmostEqual(trials['b3736']['production'], 0.0, places=3)
        self.assertGreater(trials['b3736']['growth_ratio'], 0.10)
        self.assertAlmostEqual(trials['b2278']['growth'], 0.211663, places=3)
        self.assertAlmostEqual(trials['b2278']['production'], 8.279455, places=3)
        self.assertGreaterEqual(
            trials['b2278']['growth_ratio'],
            simulation.MISSION04_MIN_VIABLE_GROWTH_RATIO,
        )
        self.assertTrue(trials['b2278']['eligible_design'])
        self.assertLessEqual(trials['b2278']['oxygen_uptake'], simulation.MISSION04_FLUX_TOLERANCE)

    def test_old_target_b2297_does_not_create_ethanol(self):
        objective_result, production_fluxes, _medium, _genes, _constraints = self._simulate(['b2297'])
        values = simulation._production_flux_value_map(production_fluxes)
        self.assertAlmostEqual(float(objective_result), 0.873922, places=3)
        self.assertAlmostEqual(values[simulation.MISSION04_PRODUCTION_OBJECTIVE], 0.0, places=3)

    def test_delivery_requires_complete_evidence_and_accepts_aliases(self):
        self.assertFalse(simulation.mission04_answer_matches('b2278', {}))
        report = self._record([])
        for gene_id in simulation.MISSION04_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)

        for answer in ('b2278', 'B2278', 'nuoL', 'NUOL', 'b2278 (nuoL)', 'b2278/nuoL'):
            self.assertTrue(simulation.mission04_answer_matches(answer, report))
        self.assertFalse(simulation.mission04_answer_matches('b3736', report))
        self.assertFalse(simulation.mission04_answer_matches('b2297', report))

    def test_invalid_runs_do_not_increment_or_replace_evidence(self):
        report = self._record([])
        report = self._record(['b1241'], report=report)
        expected_trials = dict(report['trials'])
        expected_baseline = report['baseline_growth']

        changed_environment = dict(self.reactions)
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION04_OXYGEN_REACTION)
        changed_environment[f'reaction_{oxygen_index}_lb'] = False

        production_fluxes, medium_fluxes = self._synthetic_flux_data(8.0, 1.0)
        invalid_cases = [
            (['b1241', 'b0728'], simulation.MISSION04_METHOD, simulation.MISSION04_GROWTH_OBJECTIVE, self.reactions, True, 'exactly one'),
            (['b2297'], simulation.MISSION04_METHOD, simulation.MISSION04_GROWTH_OBJECTIVE, self.reactions, True, 'not one of'),
            (['b2278'], 'pFBA', simulation.MISSION04_GROWTH_OBJECTIVE, self.reactions, True, 'Use FBA'),
            (['b2278'], simulation.MISSION04_METHOD, simulation.MISSION04_PRODUCTION_OBJECTIVE, self.reactions, True, 'biomass objective'),
            (['b2278'], simulation.MISSION04_METHOD, simulation.MISSION04_GROWTH_OBJECTIVE, changed_environment, True, 'default aerobic environment'),
            (['b2278'], simulation.MISSION04_METHOD, simulation.MISSION04_GROWTH_OBJECTIVE, self.reactions, False, 'Track EX_etoh_e'),
        ]

        for knockouts, method, objective, reactions, tracked, expected_issue in invalid_cases:
            candidate = self._record(
                knockouts,
                report=report,
                method=method,
                objective=objective,
                reactions=reactions,
                objective_result=0.2,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                tracked=tracked,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertFalse(candidate['current_run_recorded'])
            self.assertEqual(candidate['valid_trial_count'], 1)
            self.assertEqual(candidate['trials'], expected_trials)
            self.assertEqual(candidate['baseline_growth'], expected_baseline)
            self.assertTrue(
                any(expected_issue in issue for issue in candidate['current_issues']),
                candidate['current_issues'],
            )

    def test_missing_or_infeasible_result_preserves_evidence(self):
        report = self._record([])
        report = self._record(['b1241'], report=report)
        expected_trials = dict(report['trials'])
        expected_baseline = report['baseline_growth']

        genes = dict(self.genes)
        genes['b2278'] = False
        with (
            patch.object(simulation, 'save_mission04_production_check'),
            patch.object(
                simulation,
                '_read_selected_production_fluxes',
                return_value=[simulation.MISSION04_PRODUCTION_OBJECTIVE],
            ),
        ):
            candidate = simulation._build_mission04_trial_data(
                simulation.MISSION04_METHOD,
                simulation.MISSION04_GROWTH_OBJECTIVE,
                None,
                genes,
                self.reactions,
                production_fluxes={'error': 'infeasible'},
                medium_fluxes={'error': 'infeasible'},
                existing_report=report,
            )

        self.assertFalse(candidate['current_run_valid'])
        self.assertFalse(candidate['current_run_recorded'])
        self.assertEqual(candidate['trials'], expected_trials)
        self.assertEqual(candidate['baseline_growth'], expected_baseline)
        self.assertTrue(any('numeric biomass-growth' in issue for issue in candidate['current_issues']))
        self.assertTrue(any('numeric EX_etoh_e' in issue for issue in candidate['current_issues']))

    def test_repeated_candidate_replaces_instead_of_incrementing(self):
        report = self._record([])
        report = self._record(['b1241'], report=report)
        self.assertEqual(report['valid_trial_count'], 1)
        repeated = self._record(['b1241'], report=report)
        self.assertEqual(repeated['valid_trial_count'], 1)
        self.assertEqual(set(repeated['trials']), {'b1241'})

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = {
            'mission_id': '04',
            'check_version': 2,
            'evidence_ready': True,
            'winning_gene': 'b2278',
            'trials': {'b2278': {'growth': 0.2, 'production': 8.0}},
        }
        with patch.object(simulation, 'load_mission04_production_check', return_value=completed) as loader:
            text = simulation.build_mission04_evidence_report_text({})
            self.assertFalse(simulation.mission04_answer_matches('b2278', {}))
        loader.assert_not_called()
        self.assertIn('Build a controlled production-knockout comparison', text)
        self.assertNotIn('unchanged default aerobic environment', text)

    def test_legacy_report_is_not_mixed_with_new_evidence(self):
        legacy = {
            'target_gene': 'b2297',
            'baseline_growth': 34.0,
            'baseline_production': 296.0,
            'current_growth': 31.0,
            'current_production': 469.0,
        }
        production_fluxes, medium_fluxes = self._synthetic_flux_data(0.0, 21.0)
        report = self._record(
            [],
            report=legacy,
            objective_result=0.874,
            production_fluxes=production_fluxes,
            medium_fluxes=medium_fluxes,
        )
        self.assertAlmostEqual(report['baseline_growth'], 0.874, places=3)
        self.assertAlmostEqual(report['baseline_production'], 0.0, places=3)
        self.assertNotIn('target_gene', report)

    def test_progression_requires_mission03(self):
        self.assertFalse(simulation.is_mission04_unlocked([]))
        self.assertFalse(simulation.is_mission04_unlocked(['02']))
        self.assertTrue(simulation.is_mission04_unlocked(['03']))

    def test_b2278_ethanol_flux_is_fixed_at_maximum_growth(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:  # pragma: no cover - dependency is expected in the project env
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        model = simulation.model.copy()
        for reaction_id in disabled_reaction_ids(model, {'b2278'}):
            model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
        model.objective = simulation.MISSION04_GROWTH_OBJECTIVE
        solution = model.optimize()
        self.assertEqual(solution.status, 'optimal')
        fva = flux_variability_analysis(
            model,
            reaction_list=[simulation.MISSION04_PRODUCTION_OBJECTIVE],
            fraction_of_optimum=1.0,
        )
        minimum = float(fva.loc[simulation.MISSION04_PRODUCTION_OBJECTIVE, 'minimum'])
        maximum = float(fva.loc[simulation.MISSION04_PRODUCTION_OBJECTIVE, 'maximum'])
        self.assertAlmostEqual(minimum, maximum, delta=1e-4)
        self.assertAlmostEqual(minimum, 8.279455, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
