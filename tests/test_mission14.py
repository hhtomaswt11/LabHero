"""Regression tests for Mission 14 byproduct trade-off screening.

Run from the project root with:
    python3 tests/test_mission14.py
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
from gpr import disabled_reaction_ids  # noqa: E402


class Mission14RegressionTests(unittest.TestCase):
    EXPECTED = {
        None: {
            'EX_succ_e': 13.905778,
            'EX_ac_e': 5.664889,
            'EX_for_e': 0.0,
            'EX_etoh_e': 0.0,
            'EX_lac__D_e': 0.0,
            'total': 343.047111,
            'active': 36,
        },
        'b1241': {
            'EX_succ_e': 13.905778,
            'EX_ac_e': 5.664889,
            'EX_for_e': 0.0,
            'EX_etoh_e': 0.0,
            'EX_lac__D_e': 0.0,
            'total': 343.047111,
            'active': 36,
        },
        'b0115': {
            'EX_succ_e': 13.312727,
            'EX_ac_e': 4.478788,
            'EX_for_e': 8.895758,
            'EX_etoh_e': 0.0,
            'EX_lac__D_e': 0.0,
            'total': 356.687273,
            'active': 38,
        },
        'b0474': {
            'EX_succ_e': 12.915200,
            'EX_ac_e': 2.712000,
            'EX_for_e': 10.000000,
            'EX_etoh_e': 1.457600,
            'EX_lac__D_e': 0.0,
            'total': 348.339200,
            'active': 40,
        },
        'b4151': {
            'EX_succ_e': 4.000000,
            'EX_ac_e': 0.000000,
            'EX_for_e': 20.000000,
            'EX_etoh_e': 12.000000,
            'EX_lac__D_e': 0.0,
            'total': 350.000000,
            'active': 32,
        },
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION14_OXYGEN_REACTION)
        self.reactions[f'reaction_{oxygen_index}_lb'] = False

    @classmethod
    def _synthetic_visible(cls, gene_id=None):
        values = cls.EXPECTED[gene_id]
        target = float(values['EX_succ_e'])
        production = {
            'selected_ids': list(simulation.MISSION14_REQUIRED_TRACKED_FLUXES),
            'objective_raw': target,
            'biomass_raw': 0.0,
            'method_diagnostics': {
                'method': simulation.MISSION14_TARGET_METHOD,
                'objective_reaction': simulation.MISSION14_TARGET_OBJECTIVE,
                'primary_objective_flux': target,
                'method_score': float(values['total']),
                'method_score_name': simulation.MISSION14_EXPECTED_SECONDARY_CRITERION,
                'total_absolute_flux': float(values['total']),
                'active_reaction_count': int(values['active']),
            },
            'items': [
                {
                    'reaction_id': reaction_id,
                    'raw_flux': float(values[reaction_id]),
                    'production_flux': round(max(float(values[reaction_id]), 0.0), 3),
                }
                for reaction_id in simulation.MISSION14_REQUIRED_TRACKED_FLUXES
            ],
        }
        medium = {'items': [
            {
                'reaction_id': simulation.MISSION14_GLUCOSE_REACTION,
                'raw_flux': -10.0,
                'uptake_flux': 10.0,
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION14_OXYGEN_REACTION,
                'raw_flux': 0.0,
                'uptake_flux': 0.0,
                'secretion_flux': 0.0,
            },
        ]}
        return target, production, medium

    @classmethod
    def _baseline_run(cls):
        objective, production, medium = cls._synthetic_visible(None)
        diagnostics = production['method_diagnostics']
        return {
            'run_type': 'baseline',
            'source': 'mission13_visible_pfba_run',
            'method': simulation.MISSION14_TARGET_METHOD,
            'objective': simulation.MISSION14_TARGET_OBJECTIVE,
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

    def _record(
        self,
        gene_id=None,
        report=None,
        method=None,
        objective=None,
        reactions=None,
        selected_fluxes=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
        objective_error=None,
        import_baseline=True,
        genes=None,
    ):
        genes = dict(genes or self.genes)
        if gene_id:
            genes[gene_id] = False
        reactions = dict(reactions or self.reactions)
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            synthetic_gene = gene_id if gene_id in self.EXPECTED else None
            objective_result, production_fluxes, medium_fluxes = self._synthetic_visible(synthetic_gene)
        if selected_fluxes is None:
            selected_fluxes = list(simulation.MISSION14_REQUIRED_TRACKED_FLUXES)
        imported = self._baseline_run() if import_baseline else None
        with patch.object(simulation, 'save_mission14_reduction_check'), \
                patch.object(
                    simulation,
                    '_mission14_import_mission13_baseline',
                    return_value=(imported, bool(import_baseline)),
                ):
            return simulation._build_mission14_data(
                method or simulation.MISSION14_TARGET_METHOD,
                objective or simulation.MISSION14_TARGET_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
                objective_error=objective_error,
                selected_fluxes=selected_fluxes,
            )

    def _complete(self, order=None, import_baseline=True):
        report = None
        for gene_id in order or simulation.MISSION14_CANDIDATE_GENES:
            report = self._record(gene_id, report=report, import_baseline=import_baseline)
        return report

    def test_progression_constants_and_candidate_design(self):
        self.assertFalse(simulation.is_mission14_unlocked([]))
        self.assertFalse(simulation.is_mission14_unlocked(['12']))
        self.assertTrue(simulation.is_mission14_unlocked(['13']))
        self.assertEqual(simulation.MISSION14_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION14_TARGET_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION14_TARGET_OBJECTIVE, 'EX_succ_e')
        self.assertEqual(
            simulation.MISSION14_CANDIDATE_GENES,
            ['b1241', 'b0115', 'b0474', 'b4151'],
        )
        self.assertEqual(
            simulation.MISSION14_REQUIRED_TRACKED_FLUXES,
            ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e'],
        )
        self.assertEqual(simulation.MISSION14_EXPECTED_CONCLUSION, 'none')

    def test_environment_validator_accepts_explicit_and_legacy_keys(self):
        self.assertEqual(simulation._mission14_environment_status(self.reactions), (True, []))
        legacy = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        self.assertEqual(simulation._mission14_environment_status(legacy), (True, []))
        default = simulation._build_default_reactions_data()
        closed, issues = simulation._mission14_environment_status(default)
        self.assertFalse(closed)
        self.assertEqual(issues, [])

    def test_real_pfba_values_for_reference_and_all_candidates(self):
        for gene_id, expected in self.EXPECTED.items():
            genes = dict(self.genes)
            if gene_id:
                genes[gene_id] = False
            result, production, medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION14_TARGET_METHOD,
                simulation.MISSION14_TARGET_OBJECTIVE,
                genes,
                dict(self.reactions),
                list(simulation.MISSION14_REQUIRED_TRACKED_FLUXES),
            )
            self.assertAlmostEqual(float(result), expected['EX_succ_e'], delta=1e-3, msg=gene_id)
            values = simulation._production_flux_value_map(production)
            for reaction_id in simulation.MISSION14_REQUIRED_TRACKED_FLUXES:
                self.assertAlmostEqual(values[reaction_id], expected[reaction_id], delta=1e-3, msg=f'{gene_id}:{reaction_id}')
            diagnostics = production['method_diagnostics']
            self.assertEqual(diagnostics['method_score_name'], 'total_absolute_flux')
            self.assertAlmostEqual(diagnostics['method_score'], expected['total'], delta=1e-2, msg=gene_id)
            self.assertAlmostEqual(diagnostics['total_absolute_flux'], expected['total'], delta=1e-2, msg=gene_id)
            self.assertEqual(diagnostics['active_reaction_count'], expected['active'], msg=gene_id)
            self.assertAlmostEqual(float(production['biomass_raw']), 0.0, delta=1e-4, msg=gene_id)
            _, uptake, _ = simulation._medium_flux_maps(medium)
            self.assertAlmostEqual(uptake['EX_glc__D_e'], 10.0, delta=1e-3, msg=gene_id)
            self.assertAlmostEqual(uptake['EX_o2_e'], 0.0, delta=1e-4, msg=gene_id)

    def test_gpr_disabled_reactions_are_scientifically_correct(self):
        expected = simulation.MISSION14_EXPECTED_DISABLED_REACTIONS
        for gene_id in simulation.MISSION14_CANDIDATE_GENES:
            disabled = disabled_reaction_ids(simulation.model, [gene_id])
            self.assertEqual(sorted(disabled), sorted(expected[gene_id]), gene_id)
        self.assertEqual(expected['b1241'], [])
        self.assertEqual(expected['b0115'], ['PDH'])
        self.assertEqual(expected['b0474'], ['ADK1'])
        self.assertEqual(expected['b4151'], ['FRD7'])

    def test_mission13_pfba_baseline_is_imported_without_a_hidden_simulation(self):
        baseline = self._baseline_run()
        mission13_report = {
            'mission_id': '13',
            'check_version': simulation.MISSION13_CHECK_VERSION,
            'evidence_ready': True,
            'pfba_run': {
                key: value for key, value in baseline.items()
                if key not in {'run_type', 'knocked_out_genes'}
            },
        }
        with patch.object(simulation, 'load_mission13_method_check', return_value=mission13_report):
            imported, available = simulation._mission14_import_mission13_baseline()
        self.assertTrue(available)
        self.assertIsNotNone(imported)
        self.assertEqual(imported['source'], 'mission13_visible_pfba_run')
        self.assertAlmostEqual(imported['primary_objective_flux'], 13.905778, delta=1e-6)
        self.assertAlmostEqual(imported['tracked_flux_values']['EX_ac_e'], 5.664889, delta=1e-6)

    def test_activation_initialises_current_state_from_persisted_visible_baseline(self):
        baseline = self._baseline_run()
        with patch.object(
            simulation,
            '_mission14_import_mission13_baseline',
            return_value=(baseline, True),
        ), patch.object(simulation, 'save_mission14_reduction_check') as save_mock:
            state = simulation.initialise_mission14_tradeoff_screening()
        self.assertTrue(state['baseline_recorded'])
        self.assertTrue(state['mission13_baseline_imported'])
        self.assertEqual(state['valid_trial_count'], 0)
        self.assertEqual(state['missing_candidates'], simulation.MISSION14_CANDIDATE_GENES)
        self.assertFalse(state['evidence_ready'])
        save_mock.assert_called_once()
        source = inspect.getsource(simulation.initialise_mission14_tradeoff_screening)
        self.assertNotIn('.simulate(', source)

    def test_reference_and_four_trials_are_required_but_order_is_irrelevant(self):
        one = self._record('b1241')
        self.assertTrue(one['baseline_recorded'])
        self.assertEqual(one['valid_trial_count'], 1)
        self.assertFalse(one['comparison_complete'])
        self.assertFalse(one['evidence_ready'])
        normal = self._complete()
        reverse = self._complete(order=list(reversed(simulation.MISSION14_CANDIDATE_GENES)))
        self.assertTrue(normal['evidence_ready'])
        self.assertTrue(reverse['evidence_ready'])
        self.assertEqual(normal['trials'], reverse['trials'])
        self.assertEqual(normal['conclusion'], 'none')
        self.assertEqual(reverse['conclusion'], 'none')

    def test_candidates_can_be_recorded_before_manual_reference(self):
        report = None
        for gene_id in simulation.MISSION14_CANDIDATE_GENES:
            report = self._record(gene_id, report=report, import_baseline=False)
        self.assertFalse(report['baseline_recorded'])
        self.assertEqual(report['valid_trial_count'], 4)
        self.assertFalse(report['evidence_ready'])
        report = self._record(None, report=report, import_baseline=False)
        self.assertTrue(report['baseline_recorded'])
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['conclusion'], 'none')

    def test_candidate_assessments_and_negative_conclusion_are_derived_from_evidence(self):
        report = self._complete()
        trials = report['trials']
        self.assertFalse(trials['b1241']['acetate_reduced'])
        self.assertTrue(trials['b1241']['target_retained'])
        self.assertEqual(trials['b1241']['new_positive_byproducts'], [])
        self.assertAlmostEqual(trials['b0115']['target_retention_percent'], 95.7, delta=0.1)
        self.assertGreater(trials['b0115']['acetate_reduction'], 1.0)
        self.assertEqual(trials['b0115']['new_positive_byproducts'], ['EX_for_e'])
        self.assertAlmostEqual(trials['b0474']['target_retention_percent'], 92.9, delta=0.1)
        self.assertEqual(trials['b0474']['new_positive_byproducts'], ['EX_for_e', 'EX_etoh_e'])
        self.assertLess(trials['b4151']['target_retention_percent'], 30.0)
        self.assertEqual(trials['b4151']['new_positive_byproducts'], ['EX_for_e', 'EX_etoh_e'])
        self.assertTrue(report['no_clean_candidate'])
        self.assertEqual(report['clean_candidates'], [])
        self.assertEqual(report['clean_candidate_count'], 0)
        self.assertEqual(report['conclusion'], 'none')
        self.assertTrue(report['expected_conclusion_confirmed'])

    def test_method_objective_environment_and_gene_controls_are_required(self):
        wrong_method = self._record('b1241', method='FBA')
        self.assertFalse(wrong_method['current_run_valid'])
        self.assertTrue(any('pFBA' in issue for issue in wrong_method['current_issues']))
        wrong_objective = self._record('b1241', objective='BIOMASS_Ecoli_core_w_GAM')
        self.assertFalse(wrong_objective['current_run_valid'])
        self.assertTrue(any('EX_succ_e' in issue for issue in wrong_objective['current_issues']))
        default_reactions = simulation._build_default_reactions_data()
        wrong_environment = self._record('b1241', reactions=default_reactions)
        self.assertFalse(wrong_environment['current_run_valid'])
        self.assertTrue(any('oxygen' in issue.lower() for issue in wrong_environment['current_issues']))
        genes = dict(self.genes)
        genes['b1241'] = False
        genes['b0115'] = False
        two_knockouts = self._record(
            objective_result=self._synthetic_visible('b1241')[0],
            production_fluxes=self._synthetic_visible('b1241')[1],
            medium_fluxes=self._synthetic_visible('b1241')[2],
            genes=genes,
        )
        self.assertFalse(two_knockouts['current_run_valid'])
        self.assertTrue(any('exactly one' in issue.lower() for issue in two_knockouts['current_issues']))
        outside = self._record('b0728')
        self.assertFalse(outside['current_run_valid'])
        self.assertTrue(any('candidate list' in issue.lower() for issue in outside['current_issues']))

    def test_complete_panel_must_be_selected_and_measured(self):
        objective, production, medium = self._synthetic_visible('b1241')
        selected = simulation.MISSION14_REQUIRED_TRACKED_FLUXES[:-1]
        missing_selection = self._record(
            'b1241',
            selected_fluxes=selected,
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('EX_lac__D_e', missing_selection['missing_selected_fluxes'])
        production = dict(production)
        production['items'] = [
            item for item in production['items']
            if item['reaction_id'] != 'EX_ac_e'
        ]
        missing_measurement = self._record(
            'b1241',
            objective_result=objective,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_measurement['current_run_valid'])
        self.assertIn('EX_ac_e', missing_measurement['missing_measured_fluxes'])

    def test_visible_biomass_medium_and_pfba_diagnostics_are_required(self):
        objective, production, medium = self._synthetic_visible('b1241')
        no_biomass = dict(production)
        no_biomass.pop('biomass_raw')
        report = self._record('b1241', objective_result=objective, production_fluxes=no_biomass, medium_fluxes=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('biomass' in issue.lower() for issue in report['current_issues']))
        no_medium = self._record('b1241', objective_result=objective, production_fluxes=production, medium_fluxes={'items': []})
        self.assertFalse(no_medium['current_run_valid'])
        self.assertTrue(any('glucose' in issue.lower() for issue in no_medium['current_issues']))
        no_diagnostics = dict(production)
        no_diagnostics.pop('method_diagnostics')
        report = self._record('b1241', objective_result=objective, production_fluxes=no_diagnostics, medium_fluxes=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('total absolute flux' in issue.lower() or 'secondary' in issue.lower() for issue in report['current_issues']))

    def test_primary_objective_and_tracked_target_must_match(self):
        objective, production, medium = self._synthetic_visible('b1241')
        production = dict(production)
        production['items'] = [dict(item) for item in production['items']]
        for item in production['items']:
            if item['reaction_id'] == 'EX_succ_e':
                item['raw_flux'] = 12.0
                item['production_flux'] = 12.0
        report = self._record('b1241', objective_result=objective, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('does not match' in issue.lower() for issue in report['current_issues']))

    def test_repeated_candidate_updates_without_duplicate_count(self):
        report = self._record('b1241')
        self.assertEqual(report['valid_trial_count'], 1)
        report = self._record('b1241', report=report)
        self.assertEqual(report['valid_trial_count'], 1)
        self.assertEqual(list(report['trials']), ['b1241'])

    def test_invalid_attempt_preserves_completed_evidence(self):
        complete = self._complete()
        invalid = self._record('b1241', report=complete, method='FBA')
        self.assertFalse(invalid['current_run_valid'])
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['baseline'], complete['baseline'])
        self.assertEqual(invalid['trials'], complete['trials'])
        self.assertTrue(invalid['evidence_ready'])
        self.assertEqual(invalid['conclusion'], 'none')

    def test_answer_requires_complete_evidence_and_accepts_negative_result_aliases(self):
        incomplete = self._record('b1241')
        self.assertFalse(simulation.mission14_answer_matches('none', incomplete))
        complete = self._complete()
        for answer in ('none', 'no candidate', 'nenhum', 'nenhum candidato'):
            self.assertTrue(simulation.mission14_answer_matches(answer, complete), answer)
        for answer in ('b1241', 'adhE', 'b0115', 'aceF', 'acetate'):
            self.assertFalse(simulation.mission14_answer_matches(answer, complete), answer)

    def test_old_report_is_rejected_safely(self):
        old = {
            'mission_id': '14',
            'check_version': 1,
            'ready_to_deliver': True,
            'target_gene': 'b1241',
        }
        report = self._record('b1241', report=old)
        self.assertEqual(report['check_version'], simulation.MISSION14_CHECK_VERSION)
        self.assertEqual(report['valid_trial_count'], 1)
        self.assertNotIn('target_gene', report)
        self.assertFalse(simulation.mission14_answer_matches('none', old))

    def test_report_explains_tradeoffs_and_never_claims_false_ethanol_reduction(self):
        report = self._complete()
        text = simulation.build_mission14_tradeoff_report_text(report)
        self.assertIn('Evaluate all four candidates against the clean-improvement criteria', text)
        self.assertIn('Submit the conclusion supported by the complete target and co-product evidence', text)
        self.assertNotIn('Submit none / no candidate', text)
        self.assertIn('b1241 (adhE)', text)
        self.assertIn('formate (EX_for_e)', text)
        self.assertIn('new positive co-products', text)
        self.assertIn('approximately zero predicted biomass flux', text)
        self.assertIn('No hidden simulation is used', text)
        self.assertNotIn('ethanol route reduced', text.lower())
        self.assertNotIn('unwanted byproduct is sufficiently reduced', text.lower())

    def test_remote_wrapper_parity_no_hidden_requests_and_json_state(self):
        complete = self._complete()
        json.dumps(complete)
        source = inspect.getsource(simulation.run_mission14_reduction_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission14_reduction_check(simulation_results)', source)
        build_source = inspect.getsource(simulation._build_mission14_data)
        self.assertNotIn('.simulate(', build_source)
        self.assertNotIn('_simulate_', build_source)

    def test_ui_has_progression_guard_complete_report_and_written_answer(self):
        source = (CODE_DIR / 'mission14.py').read_text(encoding='utf-8')
        self.assertIn('is_mission14_unlocked', source)
        self.assertIn('clear_mission14_reduction_check()', source)
        self.assertIn('initialise_mission14_tradeoff_screening()', source)
        self.assertIn('build_mission14_tradeoff_report_text', source)
        self.assertIn('Screening conclusion:', source)
        self.assertIn('Enter the conclusion supported by the completed candidate screen.', source)
        self.assertNotIn('Clean improvement candidate (or none):', source)
        self.assertIn('mission14_answer_matches', source)
        window_source = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission14_reduction_check_remote', window_source)
        self.assertIn("('14', MISSION14_CANDIDATE_GENES)", window_source)

    def test_fva_fixes_the_external_fingerprint_for_every_candidate(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        reaction_list = list(simulation.MISSION14_REQUIRED_TRACKED_FLUXES) + [
            simulation.MISSION07_BIOMASS_OBJECTIVE,
        ]
        for gene_id, expected in self.EXPECTED.items():
            model = simulation.model.copy()
            model.reactions.get_by_id(simulation.MISSION14_OXYGEN_REACTION).lower_bound = 0.0
            if gene_id:
                for reaction_id in disabled_reaction_ids(model, [gene_id]):
                    model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
            model.objective = simulation.MISSION14_TARGET_OBJECTIVE
            solution = model.optimize()
            self.assertEqual(solution.status, 'optimal', gene_id)
            self.assertAlmostEqual(float(solution.objective_value), expected['EX_succ_e'], delta=1e-3, msg=gene_id)
            fva = flux_variability_analysis(
                model,
                reaction_list=reaction_list,
                fraction_of_optimum=1.0,
            )
            expected_values = {
                reaction_id: expected[reaction_id]
                for reaction_id in simulation.MISSION14_REQUIRED_TRACKED_FLUXES
            }
            expected_values[simulation.MISSION07_BIOMASS_OBJECTIVE] = 0.0
            for reaction_id, expected_value in expected_values.items():
                minimum = float(fva.loc[reaction_id, 'minimum'])
                maximum = float(fva.loc[reaction_id, 'maximum'])
                self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=f'{gene_id}:{reaction_id}')
                self.assertAlmostEqual(minimum, expected_value, delta=1e-3, msg=f'{gene_id}:{reaction_id}')


if __name__ == '__main__':
    unittest.main()
