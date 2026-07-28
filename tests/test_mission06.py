"""Regression tests for Mission 06 controlled multi-knockout challenge.

Run from the project root with:
    python3 -m unittest discover -s tests -p "test_mission06.py"
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


class Mission06RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()

    def _simulate(self, knocked_out=None, method=None, objective=None, reactions=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False

        active_reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, active_reactions)
        selected_objective = objective or simulation.MISSION06_GROWTH_OBJECTIVE
        simul.objective = selected_objective
        result = simul.simulate(
            method=method or simulation.MISSION06_METHOD,
            constraints=constraints,
        )
        objective_result = simulation._normalise_result(result)
        production_fluxes = simulation._build_production_flux_data(
            [simulation.MISSION06_TARGET_FLUX],
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        objective_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, selected_objective)
        )
        if objective_raw is not None:
            production_fluxes['objective_raw'] = objective_raw
        medium_fluxes = simulation._build_medium_flux_data(
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        return objective_result, production_fluxes, medium_fluxes, genes, constraints, result

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
        active_reactions = reactions or self.reactions
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            (
                objective_result,
                production_fluxes,
                medium_fluxes,
                genes,
                _constraints,
                _result,
            ) = self._simulate(
                knocked_out,
                method=method,
                objective=objective,
                reactions=active_reactions,
            )
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False

        selected_fluxes = [simulation.MISSION06_TARGET_FLUX] if tracked else []
        with (
            patch.object(simulation, 'save_challenge_score'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected_fluxes),
        ):
            return simulation._build_mission06_challenge_data(
                method or simulation.MISSION06_METHOD,
                objective or simulation.MISSION06_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                active_reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(growth=0.2, ethanol=10.0, oxygen_uptake=1.0):
        production_fluxes = {
            'selected_ids': [simulation.MISSION06_TARGET_FLUX],
            'objective_raw': float(growth),
            'items': [{
                'reaction_id': simulation.MISSION06_TARGET_FLUX,
                'production_flux': round(float(ethanol), 3),
                'raw_flux': float(ethanol),
            }],
        }
        medium_fluxes = {
            'items': [{
                'reaction_id': 'EX_o2_e',
                'raw_flux': -float(oxygen_uptake),
                'uptake_flux': float(oxygen_uptake),
                'secretion_flux': 0.0,
            }],
        }
        return production_fluxes, medium_fluxes

    def test_progression_requires_mission05(self):
        self.assertFalse(simulation.is_mission06_unlocked([]))
        self.assertFalse(simulation.is_mission06_unlocked(['04']))
        self.assertTrue(simulation.is_mission06_unlocked(['05']))

    def test_old_target_b2297_remains_redundant_and_scores_zero(self):
        growth, production, _medium, _genes, constraints, _result = self._simulate(['b2297'])
        self.assertNotEqual(constraints.get('PTAr'), (0.0, 0.0))
        self.assertAlmostEqual(float(growth), 0.873922, places=3)
        self.assertAlmostEqual(
            simulation._mission06_target_flux(production),
            0.0,
            places=3,
        )

    def test_backend_and_desktop_disable_the_same_reactions(self):
        backend_path = PROJECT_ROOT / 'backend' / 'app' / 'gpr.py'
        spec = importlib.util.spec_from_file_location('labhero_backend_gpr_m06', backend_path)
        backend_gpr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_gpr)

        for knockouts in (
            {'b2278'}, {'b3736'}, {'b1602'}, {'b0728'}, {'b2278', 'b3736'}, {'b2297'}
        ):
            self.assertEqual(
                set(disabled_reaction_ids(simulation.model, knockouts)),
                set(backend_gpr.disabled_reaction_ids(simulation.model, knockouts)),
            )

    def test_reference_and_expected_design_scores(self):
        report = self._record([])
        self.assertTrue(report['baseline_recorded'])
        self.assertAlmostEqual(report['baseline']['growth'], 0.873922, places=3)
        self.assertAlmostEqual(report['baseline']['production'], 0.0, places=3)
        self.assertGreater(report['baseline']['oxygen_uptake'], 1.0)

        expected = {
            ('b2278',): (0.211663, 8.279455, 1.752),
            ('b2278', 'b1602'): (0.207557, 9.795662, 2.033),
            ('b2278', 'b3736'): (0.202612, 14.196175, 2.876),
        }
        for genes, (growth, ethanol, score) in expected.items():
            report = self._record(list(genes), report=report)
            self.assertTrue(report['current_run_valid'], report['current_issues'])
            attempt = report['current_attempt']
            self.assertAlmostEqual(attempt['growth'], growth, places=3)
            self.assertAlmostEqual(attempt['production'], ethanol, places=3)
            self.assertAlmostEqual(attempt['score'], score, places=3)

        self.assertTrue(report['win'])
        self.assertEqual(
            tuple(report['best_attempt']['knocked_out_genes']),
            ('b2278', 'b3736'),
        )
        self.assertGreater(report['best_score'], simulation.MISSION06_VILLAIN_SCORE)

    def test_single_or_weaker_design_does_not_win(self):
        report = self._record([])
        for genes in (['b2278'], ['b2278', 'b1602']):
            report = self._record(genes, report=report)
            self.assertFalse(report['current_attempt']['win'])
            self.assertLessEqual(report['current_attempt']['score'], simulation.MISSION06_VILLAIN_SCORE)
        self.assertFalse(report['win'])

    def test_worse_valid_attempt_does_not_erase_winning_best(self):
        report = self._record([])
        report = self._record(['b2278', 'b3736'], report=report)
        winning_score = report['best_score']
        winning_genes = list(report['best_attempt']['knocked_out_genes'])

        report = self._record(['b2278'], report=report)
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['best_score'], winning_score)
        self.assertEqual(report['best_attempt']['knocked_out_genes'], winning_genes)
        self.assertTrue(report['win'])

    def test_invalid_attempts_preserve_best_design(self):
        report = self._record([])
        report = self._record(['b2278', 'b3736'], report=report)
        expected_best = dict(report['best_attempt'])
        expected_history = list(report['attempt_history'])

        changed_environment = dict(self.reactions)
        oxygen_index = list(simulation.REACTIONS.index).index('EX_o2_e')
        changed_environment[f'reaction_{oxygen_index}_lb'] = False
        production, medium = self._synthetic_flux_data(growth=0.20, ethanol=14.0, oxygen_uptake=0.0)

        invalid_cases = [
            (['b2278', 'b3736', 'b1602'], simulation.MISSION06_METHOD, simulation.MISSION06_GROWTH_OBJECTIVE, self.reactions, True, 'at most 2'),
            (['b2297'], simulation.MISSION06_METHOD, simulation.MISSION06_GROWTH_OBJECTIVE, self.reactions, True, 'highlighted'),
            (['b2278'], 'pFBA', simulation.MISSION06_GROWTH_OBJECTIVE, self.reactions, True, 'Use FBA'),
            (['b2278'], simulation.MISSION06_METHOD, simulation.MISSION06_TARGET_FLUX, self.reactions, True, 'biomass objective'),
            (['b2278'], simulation.MISSION06_METHOD, simulation.MISSION06_GROWTH_OBJECTIVE, changed_environment, True, 'default aerobic medium'),
            (['b2278'], simulation.MISSION06_METHOD, simulation.MISSION06_GROWTH_OBJECTIVE, self.reactions, False, 'Track EX_etoh_e'),
        ]

        for knockouts, method, objective, reactions, tracked, message in invalid_cases:
            candidate = self._record(
                knockouts,
                report=report,
                method=method,
                objective=objective,
                reactions=reactions,
                objective_result=0.2,
                production_fluxes=production,
                medium_fluxes=medium,
                tracked=tracked,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertFalse(candidate['current_run_recorded'])
            self.assertEqual(candidate['best_attempt'], expected_best)
            self.assertEqual(candidate['attempt_history'], expected_history)
            self.assertTrue(any(message in issue for issue in candidate['current_issues']), candidate['current_issues'])

    def test_growth_below_operational_threshold_is_rejected(self):
        report = self._record([])
        production, medium = self._synthetic_flux_data(growth=0.10, ethanol=50.0, oxygen_uptake=0.0)
        candidate = self._record(
            ['b2278', 'b3736'],
            report=report,
            objective_result=0.1,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(candidate['current_run_valid'])
        self.assertTrue(any('less than 20%' in issue for issue in candidate['current_issues']))
        self.assertFalse(candidate['best_attempt'])

    def test_score_uses_unrounded_visible_objective_and_raw_ethanol(self):
        report = self._record([])
        production, medium = self._synthetic_flux_data(
            growth=0.202612,
            ethanol=14.196175,
            oxygen_uptake=0.0,
        )
        candidate = self._record(
            ['b2278', 'b3736'],
            report=report,
            objective_result=0.203,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertTrue(candidate['current_run_valid'], candidate['current_issues'])
        self.assertAlmostEqual(candidate['current_attempt']['growth'], 0.202612, places=6)
        self.assertAlmostEqual(candidate['current_attempt']['production'], 14.196175, places=6)
        self.assertAlmostEqual(candidate['current_attempt']['score'], 2.8763154091, places=8)
        self.assertNotAlmostEqual(candidate['current_attempt']['score'], 0.203 * 14.196175, places=5)

    def test_old_artifact_is_discarded(self):
        legacy = {
            'mission_id': '06',
            'check_version': 2,
            'growth': 31.864,
            'production': 469.574,
            'score': 14962.474,
            'win': True,
        }
        report = self._record([], report=legacy)
        self.assertEqual(report['check_version'], 3)
        self.assertTrue(report['baseline_recorded'])
        self.assertFalse(report['best_attempt'])
        self.assertFalse(report['win'])

    def test_explicit_empty_report_text_does_not_load_saved_score(self):
        stored = {
            'mission_id': '06',
            'check_version': 3,
            'baseline': {'growth': 0.874, 'production': 0.0, 'oxygen_uptake': 21.799},
            'best_attempt': {'score': 2.9, 'knocked_out_genes': ['b2278', 'b3736']},
            'win': True,
        }
        with patch.object(simulation, 'load_challenge_score', return_value=stored):
            text = simulation.build_mission06_challenge_report_text({})
        self.assertIn('Record an all-genes-active reference', text)
        self.assertNotIn('rival beaten', text)

    def test_remote_wrapper_reuses_visible_result_without_hidden_request(self):
        visible_result = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_challenge_score', return_value=expected) as runner:
            observed = simulation.run_challenge_score_remote('unused-url', visible_result)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible_result)

    def test_history_is_bounded(self):
        baseline = {'growth': 0.874, 'production': 0.0, 'oxygen_uptake': 21.799}
        history = [
            {'knocked_out_genes': ['b2278'], 'growth': 0.212, 'production': 8.279, 'score': 1.75}
            for _ in range(simulation.MISSION06_HISTORY_LIMIT + 4)
        ]
        report = {
            'mission_id': '06',
            'check_version': 3,
            'baseline': baseline,
            'attempt_history': history,
            'design_best': {},
        }
        production, medium = self._synthetic_flux_data(growth=0.212, ethanol=8.279, oxygen_uptake=0.0)
        candidate = self._record(
            ['b2278'],
            report=report,
            objective_result=0.212,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertEqual(len(candidate['attempt_history']), simulation.MISSION06_HISTORY_LIMIT)

    def test_winning_ethanol_flux_is_fixed_at_maximum_growth(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:  # pragma: no cover - dependency expected in project env
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        model = simulation.model.copy()
        for reaction_id in disabled_reaction_ids(model, {'b2278', 'b3736'}):
            model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
        model.objective = simulation.MISSION06_GROWTH_OBJECTIVE
        solution = model.optimize()
        self.assertEqual(solution.status, 'optimal')
        fva = flux_variability_analysis(
            model,
            reaction_list=[simulation.MISSION06_TARGET_FLUX],
            fraction_of_optimum=1.0,
        )
        minimum = float(fva.loc[simulation.MISSION06_TARGET_FLUX, 'minimum'])
        maximum = float(fva.loc[simulation.MISSION06_TARGET_FLUX, 'maximum'])
        self.assertAlmostEqual(minimum, maximum, delta=1e-4)
        self.assertAlmostEqual(minimum, 14.196175, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
