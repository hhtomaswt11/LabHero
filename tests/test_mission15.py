"""Regression tests for Mission 15 objective conflict and viability audit.

Run from the project root with:
    python3 tests/test_mission15.py
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


class Mission15RegressionTests(unittest.TestCase):
    PRODUCT = {
        'objective': 'EX_succ_e',
        'primary': 13.905778,
        'biomass': 0.0,
        'EX_succ_e': 13.905778,
        'EX_ac_e': 5.664889,
        'EX_for_e': 0.0,
        'EX_etoh_e': 0.0,
        'EX_lac__D_e': 0.0,
        'total': 343.047111,
        'active': 36,
    }
    GROWTH = {
        'objective': 'BIOMASS_Ecoli_core_w_GAM',
        'primary': 0.211663,
        'biomass': 0.211663,
        'EX_succ_e': 0.0,
        'EX_ac_e': 8.503585,
        'EX_for_e': 17.804674,
        'EX_etoh_e': 8.279455,
        'EX_lac__D_e': 0.0,
        'total': 335.650617,
        'active': 47,
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION15_OXYGEN_REACTION)
        self.reactions[f'reaction_{oxygen_index}_lb'] = False

    @classmethod
    def _synthetic_visible(cls, run_type):
        values = cls.PRODUCT if run_type == 'product_optimal' else cls.GROWTH
        production = {
            'selected_ids': list(simulation.MISSION15_REQUIRED_TRACKED_FLUXES),
            'objective_raw': float(values['primary']),
            'biomass_raw': float(values['biomass']),
            'method_diagnostics': {
                'method': simulation.MISSION15_TARGET_METHOD,
                'objective_reaction': values['objective'],
                'primary_objective_flux': float(values['primary']),
                'method_score': float(values['total']),
                'method_score_name': simulation.MISSION15_EXPECTED_SECONDARY_CRITERION,
                'total_absolute_flux': float(values['total']),
                'active_reaction_count': int(values['active']),
            },
            'items': [
                {
                    'reaction_id': reaction_id,
                    'raw_flux': float(values[reaction_id]),
                    'production_flux': round(max(float(values[reaction_id]), 0.0), 3),
                }
                for reaction_id in simulation.MISSION15_REQUIRED_TRACKED_FLUXES
            ],
        }
        medium = {'items': [
            {
                'reaction_id': simulation.MISSION15_GLUCOSE_REACTION,
                'raw_flux': -10.0,
                'uptake_flux': 10.0,
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION15_OXYGEN_REACTION,
                'raw_flux': 0.0,
                'uptake_flux': 0.0,
                'secretion_flux': 0.0,
            },
        ]}
        return float(values['primary']), production, medium

    @classmethod
    def _mission14_report(cls):
        objective, production, _medium = cls._synthetic_visible('product_optimal')
        diagnostics = production['method_diagnostics']
        baseline = {
            'run_type': 'baseline',
            'source': 'mission13_visible_pfba_run',
            'method': simulation.MISSION15_TARGET_METHOD,
            'objective': simulation.MISSION15_PRODUCT_OBJECTIVE,
            'primary_objective_flux': objective,
            'method_score': diagnostics['method_score'],
            'method_score_name': diagnostics['method_score_name'],
            'total_absolute_flux': diagnostics['total_absolute_flux'],
            'active_reaction_count': diagnostics['active_reaction_count'],
            'tracked_flux_values': {
                item['reaction_id']: item['raw_flux'] for item in production['items']
            },
            'biomass_flux': 0.0,
            'glucose_uptake': 10.0,
            'oxygen_uptake': 0.0,
            'knocked_out_genes': [],
        }
        return {
            'mission_id': '14',
            'check_version': simulation.MISSION14_CHECK_VERSION,
            'evidence_ready': True,
            'baseline': baseline,
        }

    @classmethod
    def _imported_product_run(cls):
        with patch.object(simulation, 'load_mission14_reduction_check', return_value=cls._mission14_report()):
            run, available = simulation._mission15_import_mission14_product_run()
        assert available and run
        return run

    def _record(
        self,
        run_type,
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
        import_product=True,
    ):
        expected_objective = (
            simulation.MISSION15_PRODUCT_OBJECTIVE
            if run_type == 'product_optimal'
            else simulation.MISSION15_GROWTH_OBJECTIVE
        )
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes = self._synthetic_visible(run_type)
        imported = self._imported_product_run() if import_product else None
        with patch.object(simulation, 'save_mission15_diagnostic_report_check'), \
                patch.object(
                    simulation,
                    '_mission15_import_mission14_product_run',
                    return_value=(imported, bool(import_product)),
                ):
            return simulation._build_mission15_data(
                method or simulation.MISSION15_TARGET_METHOD,
                objective or expected_objective,
                objective_result,
                dict(genes or self.genes),
                dict(reactions or self.reactions),
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
                objective_error=objective_error,
                selected_fluxes=(
                    list(simulation.MISSION15_REQUIRED_TRACKED_FLUXES)
                    if selected_fluxes is None else selected_fluxes
                ),
            )

    def _complete(self, order=('product_optimal', 'growth_optimal'), import_product=False):
        report = None
        for run_type in order:
            report = self._record(run_type, report=report, import_product=import_product)
        return report

    def test_progression_constants_and_learning_design(self):
        self.assertFalse(simulation.is_mission15_unlocked([]))
        self.assertFalse(simulation.is_mission15_unlocked(['13']))
        self.assertTrue(simulation.is_mission15_unlocked(['14']))
        self.assertEqual(simulation.MISSION15_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION15_TARGET_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION15_PRODUCT_OBJECTIVE, 'EX_succ_e')
        self.assertEqual(simulation.MISSION15_GROWTH_OBJECTIVE, 'BIOMASS_Ecoli_core_w_GAM')
        self.assertEqual(simulation.MISSION15_EXPECTED_RELATIONSHIP, 'objective_conflict')
        self.assertEqual(
            simulation.MISSION15_REQUIRED_TRACKED_FLUXES,
            ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e'],
        )

    def test_environment_validator_accepts_explicit_and_legacy_keys(self):
        self.assertEqual(simulation._mission15_environment_status(self.reactions), (True, []))
        legacy = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        self.assertEqual(simulation._mission15_environment_status(legacy), (True, []))
        default = simulation._build_default_reactions_data()
        closed, issues = simulation._mission15_environment_status(default)
        self.assertFalse(closed)
        self.assertEqual(issues, [])

    def test_mission14_product_run_is_imported_without_solver_call(self):
        report14 = self._mission14_report()
        with patch.object(simulation, 'load_mission14_reduction_check', return_value=report14), \
                patch.object(simulation, 'save_mission15_diagnostic_report_check'):
            state = simulation.initialise_mission15_viability_audit()
        self.assertTrue(state['mission14_product_run_available'])
        self.assertTrue(state['mission14_product_run_imported'])
        self.assertEqual(state['product_optimal_run']['source'], 'mission14_visible_product_run')
        self.assertIsNone(state['growth_optimal_run'])
        self.assertFalse(state['evidence_ready'])
        source = inspect.getsource(simulation._mission15_import_mission14_product_run)
        self.assertNotIn('.simulate(', source)
        self.assertNotIn('_simulate_', source)

    def test_old_or_incomplete_mission14_report_is_not_imported(self):
        for report in (
            None,
            {'mission_id': '14', 'check_version': 1, 'evidence_ready': True},
            {'mission_id': '14', 'check_version': 2, 'evidence_ready': False},
            {'mission_id': '14', 'check_version': 2, 'evidence_ready': True, 'baseline': {}},
        ):
            with patch.object(simulation, 'load_mission14_reduction_check', return_value=report):
                run, available = simulation._mission15_import_mission14_product_run()
            self.assertIsNone(run)
            if report and report.get('check_version') == 2 and report.get('evidence_ready'):
                self.assertTrue(available)

    def test_product_run_is_recorded_but_does_not_complete_comparison(self):
        report = self._record('product_optimal', import_product=False)
        self.assertTrue(report['current_run_valid'])
        self.assertTrue(report['current_run_recorded'])
        self.assertIsNotNone(report['product_optimal_run'])
        self.assertIsNone(report['growth_optimal_run'])
        self.assertFalse(report['evidence_ready'])

    def test_growth_run_with_imported_product_completes_evidence(self):
        report = self._record('growth_optimal', import_product=True)
        self.assertTrue(report['current_run_valid'])
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['same_controlled_setup'])
        self.assertEqual(report['relationship_classification'], 'objective_conflict')
        self.assertTrue(report['objective_conflict_supported'])
        self.assertTrue(report['evidence_ready'])

    def test_two_manual_runs_work_in_either_order(self):
        for order in (
            ('product_optimal', 'growth_optimal'),
            ('growth_optimal', 'product_optimal'),
        ):
            report = self._complete(order=order, import_product=False)
            self.assertTrue(report['evidence_ready'], order)
            self.assertEqual(report['relationship_classification'], 'objective_conflict')

    def test_expected_cross_objective_values_drive_relationship(self):
        report = self._complete(import_product=False)
        product = report['product_optimal_run']
        growth = report['growth_optimal_run']
        self.assertAlmostEqual(product['primary_objective_flux'], 13.905778, delta=1e-6)
        self.assertAlmostEqual(product['biomass_flux'], 0.0, delta=1e-6)
        self.assertAlmostEqual(growth['primary_objective_flux'], 0.211663, delta=1e-6)
        self.assertAlmostEqual(growth['tracked_flux_values']['EX_succ_e'], 0.0, delta=1e-6)
        self.assertEqual(simulation._mission15_relationship(product, growth), 'objective_conflict')

    def test_method_objective_gene_and_environment_controls_are_required(self):
        wrong_method = self._record('growth_optimal', method='FBA')
        self.assertFalse(wrong_method['current_run_valid'])
        self.assertTrue(any('pFBA' in issue for issue in wrong_method['current_issues']))

        wrong_objective = self._record('growth_optimal', objective='EX_etoh_e')
        self.assertFalse(wrong_objective['current_run_valid'])
        self.assertTrue(any('either' in issue.lower() for issue in wrong_objective['current_issues']))

        genes = dict(self.genes)
        genes['b1241'] = False
        knockout = self._record('growth_optimal', genes=genes)
        self.assertFalse(knockout['current_run_valid'])
        self.assertTrue(any('every gene active' in issue.lower() for issue in knockout['current_issues']))

        aerobic = simulation._build_default_reactions_data()
        wrong_environment = self._record('growth_optimal', reactions=aerobic)
        self.assertFalse(wrong_environment['current_run_valid'])
        self.assertTrue(any('oxygen' in issue.lower() for issue in wrong_environment['current_issues']))

    def test_complete_panel_must_be_selected_and_numerically_measured(self):
        objective, production, medium = self._synthetic_visible('growth_optimal')
        selected = simulation.MISSION15_REQUIRED_TRACKED_FLUXES[:-1]
        report = self._record(
            'growth_optimal',
            selected_fluxes=selected,
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('EX_lac__D_e', report['missing_selected_fluxes'])

        production = dict(production)
        production['items'] = [
            item for item in production['items'] if item['reaction_id'] != 'EX_ac_e'
        ]
        report = self._record(
            'growth_optimal',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('EX_ac_e', report['missing_measured_fluxes'])

    def test_visible_biomass_medium_and_pfba_diagnostics_are_required(self):
        objective, production, medium = self._synthetic_visible('growth_optimal')
        no_biomass = dict(production)
        no_biomass.pop('biomass_raw')
        report = self._record(
            'growth_optimal', objective_result=objective,
            production_fluxes=no_biomass, medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('growth' in issue.lower() for issue in report['current_issues']))

        report = self._record(
            'growth_optimal', objective_result=objective,
            production_fluxes=production, medium_fluxes={'items': []},
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('glucose' in issue.lower() for issue in report['current_issues']))

        no_diagnostics = dict(production)
        no_diagnostics.pop('method_diagnostics')
        report = self._record(
            'growth_optimal', objective_result=objective,
            production_fluxes=no_diagnostics, medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('primary objective' in issue.lower() for issue in report['current_issues']))

    def test_primary_objective_must_match_the_relevant_visible_flux(self):
        objective, production, medium = self._synthetic_visible('product_optimal')
        altered = dict(production)
        altered['items'] = [dict(item) for item in production['items']]
        for item in altered['items']:
            if item['reaction_id'] == 'EX_succ_e':
                item['raw_flux'] = 12.0
                item['production_flux'] = 12.0
        report = self._record(
            'product_optimal', import_product=False,
            objective_result=objective, production_fluxes=altered, medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('tracked succinate' in issue.lower() for issue in report['current_issues']))

        objective, production, medium = self._synthetic_visible('growth_optimal')
        altered = dict(production)
        altered['biomass_raw'] = 0.15
        report = self._record(
            'growth_optimal', objective_result=objective,
            production_fluxes=altered, medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('predicted growth rate' in issue.lower() for issue in report['current_issues']))

    def test_repeated_run_updates_without_creating_extra_state(self):
        report = self._record('growth_optimal', import_product=True)
        first = json.dumps(report['growth_optimal_run'], sort_keys=True)
        report = self._record('growth_optimal', report=report, import_product=True)
        second = json.dumps(report['growth_optimal_run'], sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(set(report).issuperset({'product_optimal_run', 'growth_optimal_run'}), True)

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete(import_product=False)
        invalid = self._record('growth_optimal', report=complete, method='FBA', import_product=False)
        self.assertFalse(invalid['current_run_valid'])
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['product_optimal_run'], complete['product_optimal_run'])
        self.assertEqual(invalid['growth_optimal_run'], complete['growth_optimal_run'])
        self.assertTrue(invalid['evidence_ready'])
        self.assertEqual(invalid['relationship_classification'], 'objective_conflict')

    def test_answer_requires_complete_evidence_and_accepts_supported_aliases(self):
        incomplete = self._record('product_optimal', import_product=False)
        self.assertFalse(simulation.mission15_answer_matches('objective conflict', incomplete))
        complete = self._complete(import_product=False)
        for answer in (
            'objective conflict',
            'growth-production conflict',
            'not growth coupled',
            'not growth compatible',
            'conflito de objetivos',
            'não está acoplado ao crescimento',
        ):
            self.assertTrue(simulation.mission15_answer_matches(answer, complete), answer)
        for answer in ('b1241', 'succinate', 'total flux', 'compatible'):
            self.assertFalse(simulation.mission15_answer_matches(answer, complete), answer)

    def test_free_text_accepts_natural_english_conclusions(self):
        complete = self._complete(import_product=False)
        accepted = (
            'There is a trade-off between growth and succinate production.',
            'When succinate is maximised biomass is zero, and when growth is maximised succinate is zero.',
            'Growth and maximum succinate production conflict under these conditions.',
            'Maximum succinate production is not growth-coupled under these conditions.',
            'The product and growth objectives are incompatible under these conditions.',
        )
        for answer in accepted:
            self.assertTrue(simulation.mission15_answer_matches(answer, complete), answer)

    def test_free_text_rejects_opposite_or_incomplete_conclusions(self):
        complete = self._complete(import_product=False)
        rejected = (
            'Growth and succinate are compatible.',
            'There is no conflict between growth and succinate production.',
            'Succinate is zero.',
            'Growth is maximized.',
            'The values are different.',
        )
        for answer in rejected:
            self.assertFalse(simulation.mission15_answer_matches(answer, complete), answer)

    def test_relationship_is_derived_instead_of_hardcoded(self):
        complete = self._complete(import_product=False)
        coexistence = json.loads(json.dumps(complete))
        coexistence['product_optimal_run']['biomass_flux'] = 0.1
        coexistence['growth_optimal_run']['tracked_flux_values']['EX_succ_e'] = 1.0
        self.assertEqual(
            simulation._mission15_relationship(
                coexistence['product_optimal_run'], coexistence['growth_optimal_run']
            ),
            'coexistence',
        )

    def test_old_report_is_rejected_safely(self):
        old = {
            'mission_id': '15',
            'check_version': 1,
            'ready_to_deliver': True,
            'target_gene': 'b1241',
        }
        report = self._record('growth_optimal', report=old, import_product=True)
        self.assertEqual(report['check_version'], simulation.MISSION15_CHECK_VERSION)
        self.assertNotIn('target_gene', report)
        self.assertTrue(report['mission14_product_run_imported'])
        self.assertFalse(simulation.mission15_answer_matches('objective conflict', old))

    def test_report_contains_complete_evidence_without_printing_answer(self):
        report = self._complete(import_product=False)
        text = simulation.build_mission15_viability_report_text(report)
        self.assertIn('Product-priority optimum', text)
        self.assertIn('Growth-priority optimum', text)
        self.assertIn('Predicted growth rate in the product-priority optimum: 0.000 h^-1', text)
        self.assertIn('Succinate in the growth-priority optimum: 0.000', text)
        self.assertIn('Evidence complete', text)
        self.assertIn('Submit the relationship supported by both controlled optima', text)
        self.assertIn('No hidden simulation is used', text)
        lowered = text.lower()
        self.assertNotIn('objective conflict', lowered)
        self.assertNotIn('not growth coupled', lowered)
        self.assertNotIn('não está acoplado', lowered)

    def test_invalid_attempt_message_preserves_previous_evidence(self):
        complete = self._complete(import_product=False)
        invalid = self._record('growth_optimal', report=complete, method='FBA', import_product=False)
        text = simulation.build_mission15_viability_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 15 evidence remains available', text)
        self.assertIn('Evidence complete', text)

    def test_remote_wrapper_parity_no_hidden_requests_and_json_state(self):
        complete = self._complete(import_product=False)
        json.dumps(complete)
        source = inspect.getsource(simulation.run_mission15_diagnostic_report_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission15_diagnostic_report_check(simulation_results)', source)
        build_source = inspect.getsource(simulation._build_mission15_data)
        self.assertNotIn('.simulate(', build_source)
        self.assertNotIn('_simulate_', build_source)

    def test_ui_has_progression_guard_idempotent_activation_and_written_answer(self):
        source = (CODE_DIR / 'mission15.py').read_text(encoding='utf-8')
        self.assertIn('is_mission15_unlocked', source)
        self.assertIn('initialise_mission15_viability_audit()', source)
        self.assertIn("if '15' in self.missions_activated", source)
        self.assertIn('Evidence-based conclusion:', source)
        self.assertIn('mission15_answer_matches', source)
        self.assertNotIn('one useful knockout', source)
        self.assertNotIn('b1241', source)
        window_source = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission15_diagnostic_report_check_remote', window_source)
        self.assertIn('build_mission15_viability_report_text', window_source)
        self.assertIn('The secondary value is not the selected primary objective flux.', window_source)
        self.assertNotIn('The secondary value is not the succinate objective flux.', window_source)

    def test_dr_almeida_dialogue_and_documentation_match_redesign(self):
        dialogue = (CODE_DIR / 'mission11.py').read_text(encoding='utf-8')
        self.assertIn('cross-objective biomass and product fluxes', dialogue)
        self.assertNotIn('Use method choice, one knockout', dialogue)
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission15.md').read_text(encoding='utf-8')
        self.assertIn('Product–Growth Viability Audit', mission_doc)
        self.assertIn('BIOMASS_Ecoli_core_w_GAM', mission_doc)
        overview = (PROJECT_ROOT / 'MISSION_PROGRESS_OVERVIEW.md').read_text(encoding='utf-8')
        self.assertIn('Mission 15 — Product–Growth Viability Audit', overview)

    def test_real_pfba_values_for_both_objectives(self):
        expected_by_objective = {
            simulation.MISSION15_PRODUCT_OBJECTIVE: self.PRODUCT,
            simulation.MISSION15_GROWTH_OBJECTIVE: self.GROWTH,
        }
        for objective_name, expected in expected_by_objective.items():
            result, production, medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION15_TARGET_METHOD,
                objective_name,
                dict(self.genes),
                dict(self.reactions),
                list(simulation.MISSION15_REQUIRED_TRACKED_FLUXES),
            )
            self.assertAlmostEqual(float(result), expected['primary'], delta=1e-3, msg=objective_name)
            self.assertAlmostEqual(float(production['biomass_raw']), expected['biomass'], delta=1e-3, msg=objective_name)
            values = simulation._production_flux_value_map(production)
            for reaction_id in simulation.MISSION15_REQUIRED_TRACKED_FLUXES:
                self.assertAlmostEqual(values[reaction_id], expected[reaction_id], delta=1e-3, msg=f'{objective_name}:{reaction_id}')
            diagnostics = production['method_diagnostics']
            self.assertEqual(diagnostics['method_score_name'], 'total_absolute_flux')
            self.assertAlmostEqual(diagnostics['total_absolute_flux'], expected['total'], delta=1e-2)
            self.assertEqual(diagnostics['active_reaction_count'], expected['active'])
            _, uptake, _ = simulation._medium_flux_maps(medium)
            self.assertAlmostEqual(uptake['EX_glc__D_e'], 10.0, delta=1e-3)
            self.assertAlmostEqual(uptake['EX_o2_e'], 0.0, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
