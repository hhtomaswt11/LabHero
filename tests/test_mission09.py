"""Regression tests for Mission 09 integrated L-malate/formate design.

Run from the project root with:
    python3 tests/test_mission09.py
"""
from __future__ import annotations

import inspect
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


class Mission09RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION09_BLOCKED_CARBON_SOURCE)
        malate_index = list(simulation.REACTIONS.index).index(simulation.MISSION09_REPLACEMENT_CARBON_SOURCE)
        self.reactions[f'reaction_{glucose_index}_lb'] = False
        self.reactions[f'reaction_{malate_index}_lb'] = True

    def _simulate(self, knocked_out=None, method=None, objective=None, reactions=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False
        reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, reactions)
        objective = objective or simulation.MISSION09_GROWTH_OBJECTIVE
        simul.objective = objective
        result = simul.simulate(method=method or simulation.MISSION09_METHOD, constraints=constraints)
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        production = simulation._build_production_flux_data(
            [simulation.MISSION09_TARGET_FLUX], flux_getter=flux_getter
        )
        objective_raw = simulation._as_float_or_none(simulation._extract_flux(result, objective))
        if objective_raw is not None:
            production['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION09_GROWTH_OBJECTIVE)
        )
        if biomass_raw is not None:
            production['biomass_raw'] = biomass_raw
        medium = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production, medium, genes, constraints

    def _record(
        self,
        knocked_out=None,
        report=None,
        method=None,
        objective=None,
        reactions=None,
        tracked=True,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
    ):
        reactions = reactions or self.reactions
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes, genes, _constraints = self._simulate(
                knocked_out, method=method, objective=objective, reactions=reactions
            )
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False
        selected = [simulation.MISSION09_TARGET_FLUX] if tracked else []
        with (
            patch.object(simulation, 'save_mission09_design_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected),
        ):
            return simulation._build_mission09_data(
                method or simulation.MISSION09_METHOD,
                objective or simulation.MISSION09_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(growth=0.3, formate=2.0, glucose=0.0, malate=10.0, oxygen=10.0):
        production = {
            'selected_ids': [simulation.MISSION09_TARGET_FLUX],
            'objective_raw': float(growth),
            'biomass_raw': float(growth),
            'items': [{
                'reaction_id': simulation.MISSION09_TARGET_FLUX,
                'raw_flux': float(formate),
                'production_flux': round(max(float(formate), 0.0), 3),
            }],
        }
        medium = {'items': [
            {'reaction_id': simulation.MISSION09_BLOCKED_CARBON_SOURCE, 'raw_flux': -float(glucose), 'uptake_flux': float(glucose), 'secretion_flux': 0.0},
            {'reaction_id': simulation.MISSION09_REPLACEMENT_CARBON_SOURCE, 'raw_flux': -float(malate), 'uptake_flux': float(malate), 'secretion_flux': 0.0},
            {'reaction_id': simulation.MISSION09_OXYGEN_REACTION, 'raw_flux': -float(oxygen), 'uptake_flux': float(oxygen), 'secretion_flux': 0.0},
        ]}
        return production, medium

    def _complete_report(self):
        report = self._record([])
        for gene_id in simulation.MISSION09_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)
        return report

    def test_progression_requires_mission08(self):
        self.assertFalse(simulation.is_mission09_unlocked([]))
        self.assertFalse(simulation.is_mission09_unlocked(['07']))
        self.assertTrue(simulation.is_mission09_unlocked(['08']))

    def test_mission_constants_and_candidate_names(self):
        self.assertEqual(simulation.MISSION09_CHECK_VERSION, 4)
        self.assertEqual(simulation.MISSION09_TARGET_PRODUCT, 'formate')
        self.assertEqual(simulation.MISSION09_TARGET_FLUX, 'EX_for_e')
        self.assertEqual(simulation.MISSION09_REPLACEMENT_CARBON_SOURCE, 'EX_mal__L_e')
        self.assertEqual(simulation.MISSION09_EXPECTED_WINNER, 'b0115')
        self.assertEqual(simulation.MISSION09_CANDIDATE_GENES, ['b1479', 'b0721', 'b0116', 'b0115'])
        self.assertEqual(simulation.MISSION09_GENE_NAMES['b1479'], 'maeA')
        self.assertEqual(simulation.MISSION09_GENE_NAMES['b0115'], 'aceF')

    def test_environment_validator_accepts_explicit_and_legacy_positional_keys(self):
        explicit_status = simulation._mission09_environment_status(self.reactions)
        self.assertEqual(explicit_status, (True, True, True, []))

        legacy_reactions = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        legacy_status = simulation._mission09_environment_status(legacy_reactions)
        self.assertEqual(legacy_status, (True, True, True, []))

        explicit_constraints = simulation._build_envconditions_from_reactions(
            self.reactions, simulation.REACTIONS
        )
        legacy_constraints = simulation._build_envconditions_from_reactions(
            legacy_reactions, simulation.REACTIONS
        )
        self.assertEqual(explicit_constraints, legacy_constraints)
        self.assertEqual(
            explicit_constraints[simulation.MISSION09_BLOCKED_CARBON_SOURCE][0],
            0.0,
        )
        self.assertEqual(
            explicit_constraints[simulation.MISSION09_REPLACEMENT_CARBON_SOURCE][0],
            -10.0,
        )

    def test_environment_menu_uses_explicit_reaction_bound_ids(self):
        window_source = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn("toggleswitch_id=f'reaction_{i}_lb'", window_source)
        self.assertIn("toggleswitch_id=f'reaction_{i}_ub'", window_source)

    def test_controlled_l_malate_reference(self):
        report = self._record([])
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['baseline_recorded'])
        self.assertAlmostEqual(report['baseline_growth'], 0.370741, places=3)
        self.assertAlmostEqual(report['baseline_production'], 0.0, places=3)
        self.assertAlmostEqual(report['baseline']['glucose_uptake'], 0.0, places=3)
        self.assertAlmostEqual(report['baseline']['malate_uptake'], 10.0, places=3)
        self.assertGreater(report['baseline']['oxygen_uptake'], 1.0)

    def test_candidate_screen_values_and_unique_winner(self):
        report = self._record([])
        expected = {
            'b1479': (0.370741, 0.0),
            'b0721': (0.306213, 0.0),
            'b0116': (0.292310, 1.410892),
            'b0115': (0.316705, 6.715199),
        }
        for gene_id, (growth, formate) in expected.items():
            report = self._record([gene_id], report=report)
            trial = report['trials'][gene_id]
            self.assertAlmostEqual(trial['growth'], growth, places=3, msg=gene_id)
            self.assertAlmostEqual(trial['production'], formate, places=3, msg=gene_id)
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['winner_unique'])
        self.assertEqual(report['winning_gene'], 'b0115')
        self.assertTrue(report['expected_winner_confirmed'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['trials']['b0115']['eligible_design'])
        self.assertFalse(report['trials']['b0116']['viable'])
        self.assertFalse(report['trials']['b0721']['production_improved'])
        self.assertTrue(report['trials']['b1479']['viable'])
        self.assertFalse(report['trials']['b1479']['production_improved'])

    def test_gpr_reaction_effects_are_correct(self):
        model = simulation.model
        expected = {
            'b1479': {'ME1'},
            'b0721': {'SUCDi'},
            'b0116': {'AKGDH', 'PDH'},
            'b0115': {'PDH'},
        }
        for gene_id, reactions in expected.items():
            self.assertEqual(set(disabled_reaction_ids(model, {gene_id})), reactions)

    def test_candidate_trials_can_precede_baseline(self):
        report = self._record(['b0115'])
        self.assertFalse(report['baseline_recorded'])
        self.assertIn('b0115', report['trials'])
        report = self._record([], report=report)
        self.assertTrue(report['baseline_recorded'])
        self.assertAlmostEqual(report['trials']['b0115']['growth_percent'], 85.4, places=1)

    def test_repeated_candidate_updates_without_duplicate_count(self):
        report = self._record([])
        report = self._record(['b0115'], report=report)
        report = self._record(['b0115'], report=report)
        self.assertEqual(report['valid_trial_count'], 1)
        self.assertEqual(set(report['trials']), {'b0115'})

    def test_invalid_runs_preserve_complete_evidence(self):
        report = self._complete_report()
        baseline = dict(report['baseline'])
        trials = {key: dict(value) for key, value in report['trials'].items()}
        production, medium = self._synthetic_flux_data()

        default_env = simulation._build_default_reactions_data()
        extra_env = dict(self.reactions)
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION09_OXYGEN_REACTION)
        extra_env[f'reaction_{oxygen_index}_lb'] = False

        cases = [
            dict(method='pFBA', message='Use FBA'),
            dict(objective=simulation.MISSION09_TARGET_FLUX, message='biomass objective'),
            dict(reactions=default_env, message='replace glucose'),
            dict(reactions=extra_env, message='every other environmental bound'),
            dict(knocked_out=['b0115', 'b0721'], message='exactly one'),
            dict(knocked_out=['b2297'], message='not one of'),
            dict(tracked=False, message='Track EX_for_e'),
        ]
        for case in cases:
            candidate = self._record(
                knocked_out=case.get('knocked_out', ['b0115']),
                report=report,
                method=case.get('method'),
                objective=case.get('objective'),
                reactions=case.get('reactions', self.reactions),
                tracked=case.get('tracked', True),
                objective_result=0.3,
                production_fluxes=production,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['baseline'], baseline)
            self.assertEqual(candidate['trials'], trials)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['message'] in issue for issue in candidate['current_issues']))

    def test_visible_solution_must_include_product_and_medium_evidence(self):
        production, medium = self._synthetic_flux_data()
        production['items'] = []
        missing_product = self._record([], objective_result=0.37, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_product['current_run_valid'])
        self.assertTrue(any('EX_for_e' in issue for issue in missing_product['current_issues']))

        production, medium = self._synthetic_flux_data()
        medium['items'] = [item for item in medium['items'] if item['reaction_id'] != simulation.MISSION09_OXYGEN_REACTION]
        missing_oxygen = self._record([], objective_result=0.37, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen' in issue.lower() for issue in missing_oxygen['current_issues']))

    def test_answer_requires_complete_evidence_and_accepts_aliases(self):
        incomplete = self._record([])
        self.assertFalse(simulation.mission09_answer_matches('b0115', incomplete))
        complete = self._complete_report()
        for answer in ('b0115', 'B0115', 'aceF', 'ACEF', 'b0115 (aceF)', 'b0115/aceF'):
            self.assertTrue(simulation.mission09_answer_matches(answer, complete), answer)
        self.assertFalse(simulation.mission09_answer_matches('b0116', complete))

    def test_version3_report_migrates_valid_evidence_and_drops_b0720(self):
        current = self._complete_report()
        legacy = dict(current)
        legacy['check_version'] = 3
        legacy['candidate_genes'] = ['b0721', 'b0116', 'b0720', 'b0115']
        legacy_trials = {key: dict(value) for key, value in current['trials'].items() if key != 'b1479'}
        legacy_trials['b0720'] = {
            'gene_id': 'b0720', 'gene_name': 'gltA',
            'growth': 0.0, 'production': 4.195,
            'growth_percent': 0.0, 'production_change': 4.195,
            'viable': False, 'production_improved': True,
            'eligible_design': False,
            'assessment': 'formate increases, but growth retention is below the mission criterion',
        }
        legacy['trials'] = legacy_trials
        legacy['winning_gene'] = 'b0115'
        legacy['evidence_ready'] = True
        legacy['ready_to_deliver'] = True

        self.assertFalse(simulation.mission09_answer_matches('b0115', legacy))
        stale_text = simulation.build_mission09_evidence_report_text(legacy)
        self.assertIn('b1479 (maeA): pending', stale_text)
        self.assertIn('b0721 (sdhC): predicted growth rate', stale_text)
        self.assertNotIn('b0720 (', stale_text)

        migrated = self._record(['b1479'], report=legacy)
        self.assertEqual(migrated['check_version'], 4)
        self.assertNotIn('b0720', migrated['trials'])
        self.assertEqual(set(migrated['trials']), {'b1479', 'b0721', 'b0116', 'b0115'})
        self.assertEqual(migrated['candidate_genes'], ['b1479', 'b0721', 'b0116', 'b0115'])
        self.assertTrue(migrated['evidence_ready'])
        self.assertEqual(migrated['winning_gene'], 'b0115')

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = self._complete_report()
        with patch.object(simulation, 'load_mission09_design_check', return_value=completed) as loader:
            text = simulation.build_mission09_evidence_report_text({})
            self.assertFalse(simulation.mission09_answer_matches('b0115', {}))
        loader.assert_not_called()
        self.assertIn('Build a controlled L-malate', text)
        self.assertNotIn('Evidence complete', text)

    def test_remote_wrapper_reuses_visible_result_without_hidden_requests(self):
        visible = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission09_design_check', return_value=expected) as runner:
            observed = simulation.run_mission09_design_check_remote('unused-url', visible)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible)

    def test_local_checker_contains_no_hidden_simulation_calls(self):
        source = inspect.getsource(simulation.run_mission09_design_check)
        self.assertNotIn('_simulate_flux_in_biomass_solution', source)
        self.assertNotIn('simulate(', source)
        self.assertIn('simulation_results', source)

    def test_formate_is_fixed_at_maximum_growth_for_all_candidates(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')
        expected = {
            'b1479': 0.0,
            'b0721': 0.0,
            'b0116': 1.410892,
            'b0115': 6.715199,
        }
        for gene_id, expected_formate in expected.items():
            model = simulation.model.copy()
            model.reactions.get_by_id(simulation.MISSION09_BLOCKED_CARBON_SOURCE).lower_bound = 0.0
            model.reactions.get_by_id(simulation.MISSION09_REPLACEMENT_CARBON_SOURCE).lower_bound = -10.0
            for reaction_id in disabled_reaction_ids(model, {gene_id}):
                model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
            model.objective = simulation.MISSION09_GROWTH_OBJECTIVE
            solution = model.optimize()
            self.assertEqual(solution.status, 'optimal', gene_id)
            fva = flux_variability_analysis(
                model,
                reaction_list=[simulation.MISSION09_TARGET_FLUX],
                fraction_of_optimum=1.0,
            )
            minimum = float(fva.loc[simulation.MISSION09_TARGET_FLUX, 'minimum'])
            maximum = float(fva.loc[simulation.MISSION09_TARGET_FLUX, 'maximum'])
            self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=gene_id)
            self.assertAlmostEqual(minimum, expected_formate, delta=1e-3, msg=gene_id)


if __name__ == '__main__':
    unittest.main()
