"""Regression tests for Mission 12 constraint-driven succinate byproducts.

Run from the project root with:
    python3 tests/test_mission12.py
"""
from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission12RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.default_reactions = simulation._build_default_reactions_data()
        self.constrained_reactions = dict(self.default_reactions)
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION12_OXYGEN_REACTION)
        self.constrained_reactions[f'reaction_{oxygen_index}_lb'] = False

    def _simulate(self, reactions=None, genes=None, method=None, objective=None, tracked=None):
        reactions = reactions or dict(self.default_reactions)
        genes = genes or dict(self.genes)
        objective = objective or simulation.MISSION12_TARGET_OBJECTIVE
        tracked = tracked or list(simulation.MISSION12_REQUIRED_TRACKED_FLUXES)
        simul, constraints = simulation._build_local_constraints(genes, reactions)
        simul.objective = objective
        result = simul.simulate(method=method or simulation.MISSION12_METHOD, constraints=constraints)
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        production = simulation._build_production_flux_data(tracked, flux_getter=flux_getter)
        objective_raw = simulation._as_float_or_none(simulation._extract_flux(result, objective))
        if objective_raw is not None:
            production['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION07_BIOMASS_OBJECTIVE)
        )
        if biomass_raw is not None:
            production['biomass_raw'] = biomass_raw
        medium = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production, medium

    @staticmethod
    def _synthetic_data(run_type='default', objective_value=None, biomass=0.0):
        if run_type == 'default':
            target = 16.384167 if objective_value is None else objective_value
            values = {
                'EX_succ_e': target,
                'EX_ac_e': 0.0,
                'EX_for_e': 0.0,
                'EX_etoh_e': 0.0,
                'EX_lac__D_e': 0.0,
            }
            oxygen = 2.655417
        else:
            target = 13.905778 if objective_value is None else objective_value
            values = {
                'EX_succ_e': target,
                'EX_ac_e': 5.664889,
                'EX_for_e': 0.0,
                'EX_etoh_e': 0.0,
                'EX_lac__D_e': 0.0,
            }
            oxygen = 0.0
        production = {
            'selected_ids': list(simulation.MISSION12_REQUIRED_TRACKED_FLUXES),
            'objective_raw': float(target),
            'biomass_raw': float(biomass),
            'method_diagnostics': {
                'method': 'FBA',
                'objective_reaction': simulation.MISSION12_TARGET_OBJECTIVE,
                'primary_objective_flux': float(target),
                'method_score': float(target),
                'method_score_name': 'primary_objective_flux',
                'total_absolute_flux': 343.047111 if run_type != 'default' else 360.0,
                'active_reaction_count': 36,
            },
            'items': [
                {
                    'reaction_id': reaction_id,
                    'raw_flux': float(value),
                    'production_flux': round(max(float(value), 0.0), 3),
                }
                for reaction_id, value in values.items()
            ],
        }
        medium = {'items': [
            {
                'reaction_id': simulation.MISSION12_GLUCOSE_REACTION,
                'raw_flux': -10.0,
                'uptake_flux': 10.0,
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION12_OXYGEN_REACTION,
                'raw_flux': -float(oxygen),
                'uptake_flux': float(oxygen),
                'secretion_flux': 0.0,
            },
        ]}
        return float(target), production, medium

    def _record(
        self,
        run_type='default',
        report=None,
        method=None,
        objective=None,
        genes=None,
        reactions=None,
        selected_fluxes=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
        objective_error=None,
    ):
        if reactions is None:
            reactions = dict(self.default_reactions if run_type == 'default' else self.constrained_reactions)
        genes = genes or dict(self.genes)
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes = self._simulate(
                reactions=reactions,
                genes=genes,
                method=method,
                objective=objective,
            )
        if selected_fluxes is None:
            selected_fluxes = list(simulation.MISSION12_REQUIRED_TRACKED_FLUXES)
        with patch.object(simulation, 'save_mission12_byproduct_check'):
            return simulation._build_mission12_data(
                method or simulation.MISSION12_METHOD,
                objective or simulation.MISSION12_TARGET_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
                objective_error=objective_error,
                selected_fluxes=selected_fluxes,
            )

    def _complete_synthetic_report(self, reverse=False):
        order = ('oxygen_constrained', 'default') if reverse else ('default', 'oxygen_constrained')
        report = None
        for run_type in order:
            objective, production, medium = self._synthetic_data(run_type)
            report = self._record(
                run_type=run_type,
                report=report,
                objective_result=objective,
                production_fluxes=production,
                medium_fluxes=medium,
            )
        return report

    def test_progression_requires_mission11(self):
        self.assertFalse(simulation.is_mission12_unlocked([]))
        self.assertFalse(simulation.is_mission12_unlocked(['10']))
        self.assertTrue(simulation.is_mission12_unlocked(['11']))

    def test_constants_define_progressive_full_panel_comparison(self):
        self.assertEqual(simulation.MISSION12_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION12_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION12_TARGET_OBJECTIVE, 'EX_succ_e')
        self.assertEqual(
            simulation.MISSION12_REQUIRED_TRACKED_FLUXES,
            ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e'],
        )
        self.assertEqual(simulation.MISSION12_EXPECTED_NEW_BYPRODUCT, 'EX_ac_e')

    def test_environment_validator_accepts_default_constrained_and_legacy_keys(self):
        self.assertEqual(
            simulation._mission12_environment_status(self.default_reactions),
            ('default', False, []),
        )
        self.assertEqual(
            simulation._mission12_environment_status(self.constrained_reactions),
            ('oxygen_constrained', True, []),
        )
        legacy_default = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.default_reactions.values())
        }
        legacy_constrained = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.constrained_reactions.values())
        }
        self.assertEqual(simulation._mission12_environment_status(legacy_default), ('default', False, []))
        self.assertEqual(simulation._mission12_environment_status(legacy_constrained), ('oxygen_constrained', True, []))

    def test_scientific_default_medium_values(self):
        report = self._record(run_type='default')
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        run = report['default_run']
        self.assertAlmostEqual(run['target_flux'], 16.384167, delta=1e-3)
        self.assertAlmostEqual(run['oxygen_uptake'], 2.655417, delta=1e-3)
        self.assertAlmostEqual(run['glucose_uptake'], 10.0, delta=1e-3)
        self.assertAlmostEqual(run['biomass_flux'], 0.0, delta=1e-4)
        for reaction_id in simulation.MISSION12_COMPETING_FLUXES:
            self.assertAlmostEqual(run['tracked_flux_values'][reaction_id], 0.0, delta=1e-4)
        self.assertFalse(report['evidence_ready'])

    def test_scientific_oxygen_constrained_values_and_complete_comparison(self):
        default_report = self._record(run_type='default')
        constrained = self._record(run_type='oxygen_constrained', report=default_report)
        self.assertTrue(constrained['current_run_valid'], constrained['current_issues'])
        run = constrained['oxygen_constrained_run']
        self.assertAlmostEqual(run['target_flux'], 13.905778, delta=1e-3)
        self.assertAlmostEqual(run['tracked_flux_values']['EX_ac_e'], 5.664889, delta=1e-3)
        for reaction_id in simulation.MISSION12_EXPECTED_ZERO_BYPRODUCTS:
            self.assertAlmostEqual(run['tracked_flux_values'][reaction_id], 0.0, delta=1e-4)
        self.assertAlmostEqual(run['oxygen_uptake'], 0.0, delta=1e-4)
        self.assertAlmostEqual(run['biomass_flux'], 0.0, delta=1e-4)
        self.assertTrue(constrained['comparison_complete'])
        self.assertTrue(constrained['constraint_binding'])
        self.assertTrue(constrained['both_no_growth'])
        self.assertEqual(constrained['new_byproduct'], 'EX_ac_e')
        self.assertAlmostEqual(constrained['target_change'], -2.478389, delta=1e-3)
        self.assertAlmostEqual(constrained['acetate_change'], 5.664889, delta=1e-3)
        self.assertTrue(constrained['evidence_ready'], constrained['comparison_issues'])

    def test_runs_can_be_recorded_in_either_order(self):
        normal = self._complete_synthetic_report(reverse=False)
        reverse = self._complete_synthetic_report(reverse=True)
        self.assertTrue(normal['evidence_ready'])
        self.assertTrue(reverse['evidence_ready'])
        self.assertEqual(normal['default_run'], reverse['default_run'])
        self.assertEqual(normal['oxygen_constrained_run'], reverse['oxygen_constrained_run'])
        self.assertEqual(normal['new_byproduct'], reverse['new_byproduct'])

    def test_one_run_is_insufficient(self):
        objective, production, medium = self._synthetic_data('oxygen_constrained')
        report = self._record(
            run_type='oxygen_constrained',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertTrue(report['current_run_valid'])
        self.assertIsNone(report['default_run'])
        self.assertFalse(report['comparison_complete'])
        self.assertFalse(report['evidence_ready'])

    def test_full_panel_must_be_selected_and_numerically_measured(self):
        objective, production, medium = self._synthetic_data('default')
        missing_selection = self._record(
            run_type='default',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
            selected_fluxes=simulation.MISSION12_REQUIRED_TRACKED_FLUXES[:-1],
        )
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('EX_lac__D_e', missing_selection['missing_selected_fluxes'])

        production['items'] = [item for item in production['items'] if item['reaction_id'] != 'EX_ac_e']
        missing_measurement = self._record(
            run_type='default',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_measurement['current_run_valid'])
        self.assertIn('EX_ac_e', missing_measurement['missing_measured_fluxes'])

    def test_target_objective_and_tracked_flux_must_match(self):
        objective, production, medium = self._synthetic_data('default')
        production['items'][0]['raw_flux'] = 1.1
        production['items'][0]['production_flux'] = 1.1
        report = self._record(
            run_type='default',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('does not match' in issue for issue in report['current_issues']))

    def test_expected_profiles_and_visible_growth_medium_are_required(self):
        objective, production, medium = self._synthetic_data('default')
        production['items'][1]['raw_flux'] = 1.0
        production['items'][1]['production_flux'] = 1.0
        bad_default = self._record(
            run_type='default', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(bad_default['current_run_valid'])
        self.assertTrue(any('acetate' in issue.lower() for issue in bad_default['current_issues']))

        objective, production, medium = self._synthetic_data('oxygen_constrained')
        production['biomass_raw'] = 0.2
        no_zero_growth = self._record(
            run_type='oxygen_constrained', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(no_zero_growth['current_run_valid'])
        self.assertTrue(any('growth' in issue.lower() for issue in no_zero_growth['current_issues']))

        objective, production, medium = self._synthetic_data('default')
        medium['items'] = [item for item in medium['items'] if item['reaction_id'] != simulation.MISSION12_OXYGEN_REACTION]
        missing_oxygen = self._record(
            run_type='default', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen-uptake evidence' in issue for issue in missing_oxygen['current_issues']))

    def test_invalid_attempts_do_not_erase_valid_runs(self):
        completed = self._complete_synthetic_report()
        default_stored = dict(completed['default_run'])
        constrained_stored = dict(completed['oxygen_constrained_run'])
        objective, production, medium = self._synthetic_data('oxygen_constrained')

        extra_environment = dict(self.constrained_reactions)
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION12_GLUCOSE_REACTION)
        extra_environment[f'reaction_{glucose_index}_lb'] = False
        knockout_genes = dict(self.genes)
        knockout_genes['b1241'] = False

        cases = [
            dict(method='pFBA', expected='Use FBA'),
            dict(objective='EX_ac_e', expected='EX_succ_e'),
            dict(genes=knockout_genes, expected='all genes active'),
            dict(reactions=extra_environment, expected='model-default state'),
            dict(selected_fluxes=simulation.MISSION12_REQUIRED_TRACKED_FLUXES[:-1], expected='complete target/byproduct panel'),
        ]
        for case in cases:
            candidate = self._record(
                run_type='oxygen_constrained',
                report=completed,
                method=case.get('method'),
                objective=case.get('objective'),
                genes=case.get('genes'),
                reactions=case.get('reactions'),
                selected_fluxes=case.get('selected_fluxes'),
                objective_result=objective,
                production_fluxes=production,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['default_run'], default_stored)
            self.assertEqual(candidate['oxygen_constrained_run'], constrained_stored)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['expected'] in issue for issue in candidate['current_issues']))

    def test_repeated_valid_run_updates_without_creating_duplicate_evidence(self):
        report = self._complete_synthetic_report()
        objective, production, medium = self._synthetic_data('default')
        repeated = self._record(
            run_type='default', report=report,
            objective_result=objective, production_fluxes=production, medium_fluxes=medium,
        )
        self.assertTrue(repeated['evidence_ready'])
        self.assertIsInstance(repeated['default_run'], dict)
        self.assertIsInstance(repeated['oxygen_constrained_run'], dict)
        self.assertNotIn('runs', repeated)

    def test_answer_requires_evidence_and_accepts_name_or_reaction_id(self):
        self.assertFalse(simulation.mission12_answer_matches('acetate', {}))
        report = self._complete_synthetic_report()
        for answer in ('acetate', 'Acetate', 'EX_ac_e', 'ex ac e', 'acetic acid'):
            self.assertTrue(simulation.mission12_answer_matches(answer, report), answer)
        for answer in ('succinate', 'ethanol', 'EX_for_e'):
            self.assertFalse(simulation.mission12_answer_matches(answer, report), answer)

    def test_old_version1_report_is_rejected(self):
        stale = {
            'mission_id': '12',
            'check_version': 1,
            'ready_to_deliver': True,
            'new_byproduct': 'EX_ac_e',
        }
        self.assertFalse(simulation.mission12_answer_matches('acetate', stale))
        text = simulation.build_mission12_comparison_report_text(stale)
        self.assertIn('Build two controlled FBA', text)
        self.assertNotIn('Evidence complete', text)

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = self._complete_synthetic_report()
        with patch.object(simulation, 'load_mission12_byproduct_check', return_value=completed) as loader:
            text = simulation.build_mission12_comparison_report_text({})
            matched = simulation.mission12_answer_matches('acetate', {})
        loader.assert_not_called()
        self.assertFalse(matched)
        self.assertIn('Build two controlled FBA', text)

    def test_report_has_correct_scientific_interpretation_and_no_negative_zero(self):
        report = self._complete_synthetic_report()
        text = simulation.build_mission12_comparison_report_text(report)
        self.assertIn('reduces the theoretical succinate maximum', text)
        self.assertIn('changes the predicted co-product profile', text)
        self.assertIn('no predicted growth', text.lower())
        self.assertIn('same two visible solutions', text)
        self.assertNotIn('viable production strain', text.lower())
        self.assertNotIn('-0.000', text)

    def test_report_requires_player_to_compare_fingerprints_for_the_answer(self):
        report = self._complete_synthetic_report()
        text = simulation.build_mission12_comparison_report_text(report)
        self.assertIn('acetate (EX_ac_e): 0.000', text)
        self.assertIn('acetate (EX_ac_e): 5.665', text)
        self.assertIn('identify which co-product changes from approximately zero to positive secretion', text)
        self.assertNotIn('New positive co-product:', text)
        self.assertNotIn('Acetate change after disabling oxygen uptake:', text)
        self.assertNotIn('introduces acetate as a predicted co-product', text)
        self.assertNotIn('new positive anaerobic co-product should be acetate', text.lower())
        self.assertNotIn('acetate should increase from approximately zero', text.lower())

    def test_state_is_json_serialisable_for_future_web_client(self):
        report = self._complete_synthetic_report()
        encoded = json.dumps(report)
        decoded = json.loads(encoded)
        self.assertTrue(decoded['evidence_ready'])
        self.assertEqual(decoded['new_byproduct'], 'EX_ac_e')

    def test_remote_wrapper_reuses_visible_result_without_hidden_requests(self):
        visible = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission12_byproduct_check', return_value=expected) as runner:
            observed = simulation.run_mission12_byproduct_check_remote('unused-url', visible)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible)

    def test_local_checker_contains_no_hidden_simulation_calls(self):
        source = inspect.getsource(simulation.run_mission12_byproduct_check)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_simulate_flux', source)
        self.assertIn('simulation_results', source)
        self.assertIn('medium_fluxes', source)
        self.assertIn('existing_report', source)

    def test_mission_ui_has_progression_guard_report_and_answer_input(self):
        source = (CODE_DIR / 'mission12.py').read_text(encoding='utf-8')
        self.assertIn('is_mission12_unlocked', source)
        self.assertIn('clear_mission12_byproduct_check()', source)
        self.assertIn("'New anaerobic co-product: '", source)
        self.assertIn('build_mission12_comparison_report_text', source)
        self.assertIn('mission12_answer_matches', source)
        window_source = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission12_byproduct_check_remote', window_source)

    def test_mission13_imports_diagnostic_complete_fba_baseline_from_new_state(self):
        report = self._complete_synthetic_report()
        with patch.object(simulation, 'load_mission12_byproduct_check', return_value=report):
            imported, basic_available = simulation._mission13_import_mission12_baseline()
        self.assertTrue(basic_available)
        self.assertIsNotNone(imported)
        self.assertEqual(imported['method'], 'FBA')
        self.assertAlmostEqual(
            imported['primary_objective_flux'],
            report['oxygen_constrained_run']['target_flux'],
            delta=1e-6,
        )
        self.assertAlmostEqual(imported['total_absolute_flux'], 343.047111, delta=1e-6)
        self.assertEqual(imported['active_reaction_count'], 36)

    def test_fva_fixes_target_byproducts_biomass_and_oxygen_at_both_optima(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        cases = [
            (False, 16.384167, 0.0, 2.655417),
            (True, 13.905778, 5.664889, 0.0),
        ]
        reaction_list = list(simulation.MISSION12_REQUIRED_TRACKED_FLUXES) + [
            simulation.MISSION07_BIOMASS_OBJECTIVE,
            simulation.MISSION12_OXYGEN_REACTION,
        ]
        for oxygen_closed, expected_succinate, expected_acetate, expected_oxygen_raw in cases:
            model = simulation.model.copy()
            if oxygen_closed:
                model.reactions.get_by_id(simulation.MISSION12_OXYGEN_REACTION).lower_bound = 0.0
            model.objective = simulation.MISSION12_TARGET_OBJECTIVE
            solution = model.optimize()
            self.assertEqual(solution.status, 'optimal')
            self.assertAlmostEqual(float(solution.objective_value), expected_succinate, delta=1e-3)
            fva = flux_variability_analysis(model, reaction_list=reaction_list, fraction_of_optimum=1.0)
            expected = {
                'EX_succ_e': expected_succinate,
                'EX_ac_e': expected_acetate,
                'EX_for_e': 0.0,
                'EX_etoh_e': 0.0,
                'EX_lac__D_e': 0.0,
                simulation.MISSION07_BIOMASS_OBJECTIVE: 0.0,
                simulation.MISSION12_OXYGEN_REACTION: -expected_oxygen_raw,
            }
            for reaction_id, expected_value in expected.items():
                minimum = float(fva.loc[reaction_id, 'minimum'])
                maximum = float(fva.loc[reaction_id, 'maximum'])
                self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=reaction_id)
                self.assertAlmostEqual(minimum, expected_value, delta=1e-3, msg=reaction_id)


if __name__ == '__main__':
    unittest.main()
