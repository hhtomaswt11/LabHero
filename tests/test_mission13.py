"""Regression tests for Mission 13 primary objective and flux parsimony.

Run from the project root with:
    python3 tests/test_mission13.py
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


class Mission13RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION13_OXYGEN_REACTION)
        self.reactions[f'reaction_{oxygen_index}_lb'] = False

    @staticmethod
    def _synthetic_visible(method='FBA', total_flux=343.047111, active=36):
        target = 13.905778
        values = {
            'EX_succ_e': target,
            'EX_ac_e': 5.664889,
            'EX_for_e': 0.0,
            'EX_etoh_e': 0.0,
            'EX_lac__D_e': 0.0,
        }
        method_score = target if method == 'FBA' else total_flux
        production = {
            'selected_ids': list(simulation.MISSION13_REQUIRED_TRACKED_FLUXES),
            'objective_raw': target,
            'biomass_raw': 0.0,
            'method_diagnostics': {
                'method': method,
                'objective_reaction': simulation.MISSION13_TARGET_OBJECTIVE,
                'primary_objective_flux': target,
                'method_score': method_score,
                'method_score_name': (
                    'total_absolute_flux' if method == 'pFBA'
                    else 'primary_objective_flux'
                ),
                'total_absolute_flux': total_flux,
                'active_reaction_count': active,
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
                'reaction_id': simulation.MISSION13_GLUCOSE_REACTION,
                'raw_flux': -10.0,
                'uptake_flux': 10.0,
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION13_OXYGEN_REACTION,
                'raw_flux': 0.0,
                'uptake_flux': 0.0,
                'secretion_flux': 0.0,
            },
        ]}
        return target, production, medium

    def _record(
        self,
        method='FBA',
        report=None,
        total_flux=343.047111,
        active=36,
        objective=None,
        genes=None,
        reactions=None,
        selected_fluxes=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
        objective_error=None,
        imported_baseline=None,
        basic_baseline=False,
    ):
        genes = genes or dict(self.genes)
        reactions = reactions or dict(self.reactions)
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes = self._synthetic_visible(
                method=method, total_flux=total_flux, active=active
            )
        if selected_fluxes is None:
            selected_fluxes = list(simulation.MISSION13_REQUIRED_TRACKED_FLUXES)
        with patch.object(simulation, 'save_mission13_method_check'), \
                patch.object(
                    simulation,
                    '_mission13_import_mission12_baseline',
                    return_value=(imported_baseline, basic_baseline),
                ):
            return simulation._build_mission13_data(
                method,
                objective or simulation.MISSION13_TARGET_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
                objective_error=objective_error,
                selected_fluxes=selected_fluxes,
            )

    def _complete(self, reverse=False, fba_total=343.047111, pfba_total=343.047111):
        order = ('pFBA', 'FBA') if reverse else ('FBA', 'pFBA')
        report = None
        for method in order:
            total = fba_total if method == 'FBA' else pfba_total
            report = self._record(method=method, report=report, total_flux=total)
        return report

    def test_progression_and_constants(self):
        self.assertFalse(simulation.is_mission13_unlocked([]))
        self.assertFalse(simulation.is_mission13_unlocked(['11']))
        self.assertTrue(simulation.is_mission13_unlocked(['12']))
        self.assertEqual(simulation.MISSION13_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION13_BASELINE_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION13_TARGET_METHOD, 'pFBA')
        self.assertEqual(
            simulation.MISSION13_REQUIRED_TRACKED_FLUXES,
            ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e'],
        )

    def test_environment_validator_accepts_explicit_and_legacy_constrained_state(self):
        self.assertEqual(simulation._mission13_environment_status(self.reactions), (True, []))
        legacy = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        self.assertEqual(simulation._mission13_environment_status(legacy), (True, []))
        default = simulation._build_default_reactions_data()
        closed, issues = simulation._mission13_environment_status(default)
        self.assertFalse(closed)
        self.assertEqual(issues, [])

    def test_real_fba_and_pfba_values_and_score_separation(self):
        selected = list(simulation.MISSION13_REQUIRED_TRACKED_FLUXES)
        fba_result, fba_production, fba_medium = simulation._simulate_local_objective_with_production_fluxes(
            'FBA', simulation.MISSION13_TARGET_OBJECTIVE,
            dict(self.genes), dict(self.reactions), selected,
        )
        pfba_result, pfba_production, pfba_medium = simulation._simulate_local_objective_with_production_fluxes(
            'pFBA', simulation.MISSION13_TARGET_OBJECTIVE,
            dict(self.genes), dict(self.reactions), selected,
        )
        self.assertAlmostEqual(float(fba_result), 13.905778, delta=1e-3)
        self.assertAlmostEqual(float(pfba_result), 13.905778, delta=1e-3)
        fba_diag = fba_production['method_diagnostics']
        pfba_diag = pfba_production['method_diagnostics']
        self.assertAlmostEqual(fba_diag['primary_objective_flux'], 13.905778, delta=1e-3)
        self.assertAlmostEqual(pfba_diag['primary_objective_flux'], 13.905778, delta=1e-3)
        self.assertEqual(pfba_diag['method_score_name'], 'total_absolute_flux')
        self.assertAlmostEqual(pfba_diag['method_score'], 343.047111, delta=1e-2)
        self.assertAlmostEqual(pfba_diag['total_absolute_flux'], 343.047111, delta=1e-2)
        self.assertEqual(pfba_diag['active_reaction_count'], 36)
        self.assertAlmostEqual(
            simulation._production_flux_value_map(fba_production)['EX_ac_e'],
            5.664889, delta=1e-3,
        )
        self.assertAlmostEqual(
            simulation._production_flux_value_map(pfba_production)['EX_ac_e'],
            5.664889, delta=1e-3,
        )
        _, fba_uptake, _ = simulation._medium_flux_maps(fba_medium)
        _, pfba_uptake, _ = simulation._medium_flux_maps(pfba_medium)
        self.assertAlmostEqual(fba_uptake['EX_glc__D_e'], 10.0, delta=1e-3)
        self.assertAlmostEqual(pfba_uptake['EX_glc__D_e'], 10.0, delta=1e-3)
        self.assertAlmostEqual(fba_uptake['EX_o2_e'], 0.0, delta=1e-4)
        self.assertAlmostEqual(pfba_uptake['EX_o2_e'], 0.0, delta=1e-4)

    def test_new_results_displays_primary_flux_not_pfba_score(self):
        import window
        objective, production, medium = self._synthetic_visible('pFBA')
        text = window._build_simulation_results_text(
            (simulation.MISSION13_TARGET_OBJECTIVE, objective, production, medium)
        )
        self.assertIn('Primary objective flux', text)
        self.assertIn('EX_succ_e: 13.905778', text)
        self.assertIn('Total absolute flux: 343.047', text)
        self.assertNotIn('EX_succ_e: 343.047', text)

    def test_one_run_is_insufficient_and_order_is_irrelevant(self):
        pfba_only = self._record(method='pFBA')
        self.assertIsNone(pfba_only['fba_run'])
        self.assertFalse(pfba_only['comparison_complete'])
        self.assertFalse(pfba_only['evidence_ready'])
        normal = self._complete(reverse=False)
        reverse = self._complete(reverse=True)
        self.assertTrue(normal['evidence_ready'], normal['comparison_issues'])
        self.assertTrue(reverse['evidence_ready'], reverse['comparison_issues'])
        self.assertEqual(normal['fba_run'], reverse['fba_run'])
        self.assertEqual(normal['pfba_run'], reverse['pfba_run'])

    def test_complete_panel_must_be_selected_and_measured(self):
        objective, production, medium = self._synthetic_visible('FBA')
        selected = simulation.MISSION13_REQUIRED_TRACKED_FLUXES[:-1]
        missing_selection = self._record(
            method='FBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
            selected_fluxes=selected,
        )
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('EX_lac__D_e', missing_selection['missing_selected_fluxes'])
        production['items'] = [
            item for item in production['items']
            if item['reaction_id'] != 'EX_ac_e'
        ]
        missing_measurement = self._record(
            method='FBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(missing_measurement['current_run_valid'])
        self.assertIn('EX_ac_e', missing_measurement['missing_measured_fluxes'])

    def test_method_objective_genes_and_environment_are_controlled(self):
        objective, production, medium = self._synthetic_visible('FBA')
        knocked = dict(self.genes)
        knocked['b1241'] = False
        extra = dict(self.reactions)
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION13_GLUCOSE_REACTION)
        extra[f'reaction_{glucose_index}_lb'] = False
        cases = [
            dict(method='ROOM', expected='FBA for the reference'),
            dict(objective='EX_ac_e', expected='EX_succ_e'),
            dict(genes=knocked, expected='all genes active'),
            dict(reactions=extra, expected='model-default state'),
        ]
        for case in cases:
            report = self._record(
                method=case.get('method', 'FBA'),
                objective=case.get('objective'), genes=case.get('genes'),
                reactions=case.get('reactions'), objective_result=objective,
                production_fluxes=production, medium_fluxes=medium,
            )
            self.assertFalse(report['current_run_valid'])
            self.assertTrue(any(case['expected'] in issue for issue in report['current_issues']))

    def test_visible_biomass_medium_and_diagnostics_are_required(self):
        objective, production, medium = self._synthetic_visible('pFBA')
        production.pop('biomass_raw')
        missing_biomass = self._record(
            method='pFBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(missing_biomass['current_run_valid'])
        self.assertTrue(any('biomass' in issue.lower() for issue in missing_biomass['current_issues']))

        objective, production, medium = self._synthetic_visible('pFBA')
        medium['items'] = [
            item for item in medium['items']
            if item['reaction_id'] != simulation.MISSION13_OXYGEN_REACTION
        ]
        missing_oxygen = self._record(
            method='pFBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen-uptake' in issue for issue in missing_oxygen['current_issues']))

        objective, production, medium = self._synthetic_visible('pFBA')
        production.pop('method_diagnostics')
        missing_diagnostics = self._record(
            method='pFBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(missing_diagnostics['current_run_valid'])
        self.assertTrue(any('total absolute flux' in issue for issue in missing_diagnostics['current_issues']))

    def test_primary_objective_and_tracked_target_must_match(self):
        objective, production, medium = self._synthetic_visible('pFBA')
        production['items'][0]['raw_flux'] = 10.0
        production['items'][0]['production_flux'] = 10.0
        report = self._record(
            method='pFBA', objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('does not match' in issue for issue in report['current_issues']))

    def test_equal_total_flux_is_valid(self):
        report = self._complete(fba_total=343.047111, pfba_total=343.047111)
        self.assertTrue(report['primary_objective_preserved'])
        self.assertTrue(report['external_fingerprint_preserved'])
        self.assertTrue(report['pfba_not_less_parsimonious'])
        self.assertEqual(report['parsimony_classification'], 'equal_fba_already_parsimonious')
        self.assertTrue(report['evidence_ready'], report['comparison_issues'])

    def test_reduced_total_flux_is_valid(self):
        report = self._complete(fba_total=350.0, pfba_total=343.047111)
        self.assertTrue(report['pfba_not_less_parsimonious'])
        self.assertEqual(report['parsimony_classification'], 'reduced_total_flux')
        self.assertTrue(report['evidence_ready'], report['comparison_issues'])

    def test_pfba_total_flux_increase_is_rejected(self):
        report = self._complete(fba_total=343.047111, pfba_total=350.0)
        self.assertFalse(report['pfba_not_less_parsimonious'])
        self.assertFalse(report['evidence_ready'])
        self.assertTrue(any('cannot use more total absolute flux' in issue for issue in report['comparison_issues']))

    def test_invalid_attempt_does_not_erase_valid_evidence(self):
        complete = self._complete()
        stored_fba = dict(complete['fba_run'])
        stored_pfba = dict(complete['pfba_run'])
        objective, production, medium = self._synthetic_visible('pFBA')
        invalid = self._record(
            method='ROOM', report=complete, objective_result=objective,
            production_fluxes=production, medium_fluxes=medium,
        )
        self.assertFalse(invalid['current_run_valid'])
        self.assertEqual(invalid['fba_run'], stored_fba)
        self.assertEqual(invalid['pfba_run'], stored_pfba)
        self.assertTrue(invalid['evidence_ready'])

    def test_repeated_run_updates_without_duplicates(self):
        complete = self._complete()
        repeated = self._record(method='pFBA', report=complete)
        self.assertTrue(repeated['evidence_ready'])
        self.assertIsInstance(repeated['fba_run'], dict)
        self.assertIsInstance(repeated['pfba_run'], dict)
        self.assertNotIn('runs', repeated)

    def test_answer_requires_evidence_and_accepts_aliases(self):
        self.assertFalse(simulation.mission13_answer_matches('total flux', {}))
        report = self._complete()
        accepted = (
            'total flux', 'total absolute flux', 'sum of absolute fluxes',
            'flux sum', 'fluxo total', 'soma dos fluxos absolutos',
        )
        for answer in accepted:
            self.assertTrue(simulation.mission13_answer_matches(answer, report), answer)
        for answer in ('succinate', 'acetate', 'EX_succ_e', 'active reactions'):
            self.assertFalse(simulation.mission13_answer_matches(answer, report), answer)

    def test_old_report_is_rejected_and_empty_report_is_isolated(self):
        stale = {'mission_id': '13', 'check_version': 1, 'ready_to_deliver': True}
        self.assertFalse(simulation.mission13_answer_matches('total flux', stale))
        text = simulation.build_mission13_parsimony_report_text(stale)
        self.assertIn('Build a controlled FBA-versus-pFBA', text)
        complete = self._complete()
        with patch.object(simulation, 'load_mission13_method_check', return_value=complete) as loader:
            empty_text = simulation.build_mission13_parsimony_report_text({})
            match = simulation.mission13_answer_matches('total flux', {})
        loader.assert_not_called()
        self.assertFalse(match)
        self.assertIn('Build a controlled FBA-versus-pFBA', empty_text)

    def test_report_explains_primary_and_secondary_values(self):
        report = self._complete()
        text = simulation.build_mission13_parsimony_report_text(report)
        self.assertIn('Primary objective preserved: yes', text)
        self.assertIn('External fingerprint preserved: yes', text)
        self.assertIn('pFBA did not maximise hundreds of units of succinate', text)
        self.assertIn('minimises total absolute flux', text)
        self.assertIn('FBA solver had already returned', text)
        self.assertNotIn('-0.000', text)

    def test_state_is_json_serialisable(self):
        report = self._complete()
        decoded = json.loads(json.dumps(report))
        self.assertTrue(decoded['evidence_ready'])
        self.assertEqual(decoded['parsimony_classification'], 'equal_fba_already_parsimonious')

    def test_remote_wrapper_reuses_visible_result(self):
        visible = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission13_method_check', return_value=expected) as runner:
            observed = simulation.run_mission13_method_check_remote('unused-url', visible)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible)

    def test_checker_has_no_hidden_simulations(self):
        source = inspect.getsource(simulation.run_mission13_method_check)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_simulate_remote', source)
        self.assertIn('simulation_results', source)
        self.assertIn('medium_fluxes', source)
        self.assertIn('existing_report', source)

    def test_mission12_baseline_import_requires_diagnostics(self):
        objective, production, medium = self._synthetic_visible('FBA')
        run = {
            'target_flux': objective,
            'tracked_flux_values': simulation._production_flux_value_map(production),
            'biomass_flux': 0.0,
            'glucose_uptake': 10.0,
            'oxygen_uptake': 0.0,
            'method_score': objective,
            'method_score_name': 'primary_objective_flux',
            'total_absolute_flux': 343.047111,
            'active_reaction_count': 36,
        }
        mission12 = {
            'mission_id': '12',
            'check_version': simulation.MISSION12_CHECK_VERSION,
            'evidence_ready': True,
            'oxygen_constrained_run': run,
        }
        with patch.object(simulation, 'load_mission12_byproduct_check', return_value=mission12):
            imported, basic = simulation._mission13_import_mission12_baseline()
        self.assertTrue(basic)
        self.assertIsNotNone(imported)
        self.assertEqual(imported['source'], 'mission12_visible_run')

        old_run = dict(run)
        old_run.pop('total_absolute_flux')
        mission12['oxygen_constrained_run'] = old_run
        with patch.object(simulation, 'load_mission12_byproduct_check', return_value=mission12):
            imported, basic = simulation._mission13_import_mission12_baseline()
        self.assertTrue(basic)
        self.assertIsNone(imported)

    def test_backend_contract_separates_primary_flux_and_method_score(self):
        schema_source = (PROJECT_ROOT / 'backend/app/schemas.py').read_text(encoding='utf-8')
        simulator_source = (PROJECT_ROOT / 'backend/app/simulator.py').read_text(encoding='utf-8')
        for field in (
            'primary_objective_flux', 'method_score', 'method_score_name',
            'total_absolute_flux', 'active_reaction_count',
        ):
            self.assertIn(field, schema_source)
            self.assertIn(field, simulator_source)
        self.assertIn('def _clean_numeric', simulator_source)
        self.assertIn('result=_clean_numeric(primary_objective_flux, 3)', simulator_source)

    def test_ui_has_progression_guard_report_and_answer_input(self):
        source = (CODE_DIR / 'mission13.py').read_text(encoding='utf-8')
        self.assertIn('is_mission13_unlocked', source)
        self.assertIn('clear_mission13_method_check()', source)
        self.assertIn('pFBA secondary criterion minimises:', source)
        self.assertIn('build_mission13_parsimony_report_text', source)
        self.assertIn('mission13_answer_matches', source)
        window_source = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission13_method_check_remote', window_source)

    def test_fva_internal_cycle_and_pfba_solution(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis, pfba
        except Exception as exc:
            self.skipTest(f'COBRApy FVA/pFBA unavailable: {exc}')

        model = simulation.model.copy()
        model.reactions.get_by_id(simulation.MISSION13_OXYGEN_REACTION).lower_bound = 0.0
        model.objective = simulation.MISSION13_TARGET_OBJECTIVE
        solution = model.optimize()
        self.assertEqual(solution.status, 'optimal')
        self.assertAlmostEqual(float(solution.objective_value), 13.905778, delta=1e-3)
        fva = flux_variability_analysis(
            model, reaction_list=['FRD7', 'SUCDi'], fraction_of_optimum=1.0
        )
        self.assertAlmostEqual(float(fva.loc['FRD7', 'minimum']), 13.476444, delta=1e-3)
        self.assertGreater(float(fva.loc['FRD7', 'maximum']), 999.0)
        self.assertAlmostEqual(float(fva.loc['SUCDi', 'minimum']), 0.0, delta=1e-4)
        self.assertGreater(float(fva.loc['SUCDi', 'maximum']), 986.0)
        parsimonious = pfba(model)
        self.assertAlmostEqual(float(parsimonious.fluxes['EX_succ_e']), 13.905778, delta=1e-3)
        self.assertAlmostEqual(float(parsimonious.fluxes['SUCDi']), 0.0, delta=1e-4)


if __name__ == '__main__':
    unittest.main()
