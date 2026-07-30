"""Regression tests for Mission 11 anaerobic secretion fingerprint.

Run from the project root with:
    python3 tests/test_mission11.py
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


class Mission11RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION11_OXYGEN_REACTION)
        self.reactions[f'reaction_{oxygen_index}_lb'] = False

    def _simulate(self, genes=None, reactions=None, method=None, objective=None, tracked=None):
        genes = genes or dict(self.genes)
        reactions = reactions or dict(self.reactions)
        simul, constraints = simulation._build_local_constraints(genes, reactions)
        objective = objective or simulation.MISSION11_GROWTH_OBJECTIVE
        simul.objective = objective
        result = simul.simulate(method=method or simulation.MISSION11_METHOD, constraints=constraints)
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        tracked = tracked or list(simulation.MISSION11_REQUIRED_TRACKED_FLUXES)
        production = simulation._build_production_flux_data(tracked, flux_getter=flux_getter)
        objective_raw = simulation._as_float_or_none(simulation._extract_flux(result, objective))
        if objective_raw is not None:
            production['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION11_GROWTH_OBJECTIVE)
        )
        if biomass_raw is not None:
            production['biomass_raw'] = biomass_raw
        medium = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production, medium

    @staticmethod
    def _synthetic_flux_data(
        growth=0.211663,
        formate=17.804674,
        acetate=8.503585,
        ethanol=8.279455,
        lactate=0.0,
        succinate=0.0,
        glucose=10.0,
        oxygen=0.0,
    ):
        values = {
            'EX_for_e': formate,
            'EX_ac_e': acetate,
            'EX_etoh_e': ethanol,
            'EX_lac__D_e': lactate,
            'EX_succ_e': succinate,
        }
        production = {
            'selected_ids': list(simulation.MISSION11_REQUIRED_TRACKED_FLUXES),
            'objective_raw': float(growth),
            'biomass_raw': float(growth),
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
                'reaction_id': simulation.MISSION11_GLUCOSE_REACTION,
                'raw_flux': -float(glucose),
                'uptake_flux': float(glucose),
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION11_OXYGEN_REACTION,
                'raw_flux': -float(oxygen),
                'uptake_flux': float(oxygen),
                'secretion_flux': 0.0,
            },
        ]}
        return production, medium

    def _record(
        self,
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
        genes = genes or dict(self.genes)
        reactions = reactions or dict(self.reactions)
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes = self._simulate(
                genes=genes,
                reactions=reactions,
                method=method,
                objective=objective,
            )
        if selected_fluxes is None:
            selected_fluxes = list(simulation.MISSION11_REQUIRED_TRACKED_FLUXES)
        with patch.object(simulation, 'save_mission11_flux_fingerprint_check'):
            return simulation._build_mission11_data(
                method or simulation.MISSION11_METHOD,
                objective or simulation.MISSION11_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
                objective_error=objective_error,
                selected_fluxes=selected_fluxes,
            )

    def test_progression_requires_mission10(self):
        self.assertFalse(simulation.is_mission11_unlocked([]))
        self.assertFalse(simulation.is_mission11_unlocked(['09']))
        self.assertTrue(simulation.is_mission11_unlocked(['10']))

    def test_constants_define_complete_progressive_fingerprint(self):
        self.assertEqual(simulation.MISSION11_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION11_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION11_TARGET_CONTEXT, 'anaerobic biomass-optimal growth')
        self.assertEqual(
            simulation.MISSION11_REQUIRED_TRACKED_FLUXES,
            ['EX_for_e', 'EX_ac_e', 'EX_etoh_e', 'EX_lac__D_e', 'EX_succ_e'],
        )
        self.assertEqual(simulation.MISSION11_EXPECTED_DOMINANT_FLUX, 'EX_for_e')
        self.assertLess(simulation.MISSION11_MIN_GROWTH, 0.211663)

    def test_environment_validator_accepts_explicit_and_legacy_widget_keys(self):
        self.assertEqual(simulation._mission11_environment_status(self.reactions), (True, True, []))
        legacy = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        self.assertEqual(simulation._mission11_environment_status(legacy), (True, True, []))
        explicit_constraints = simulation._build_envconditions_from_reactions(self.reactions, simulation.REACTIONS)
        legacy_constraints = simulation._build_envconditions_from_reactions(legacy, simulation.REACTIONS)
        self.assertEqual(explicit_constraints, legacy_constraints)
        self.assertEqual(explicit_constraints[simulation.MISSION11_GLUCOSE_REACTION][0], -10.0)
        self.assertEqual(explicit_constraints[simulation.MISSION11_OXYGEN_REACTION][0], 0.0)

    def test_scientific_fingerprint_values_and_dominant_product(self):
        report = self._record()
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['fingerprint_complete'])
        run = report['fingerprint_run']
        self.assertAlmostEqual(run['growth'], 0.211663, places=3)
        expected = {
            'EX_for_e': 17.804674,
            'EX_ac_e': 8.503585,
            'EX_etoh_e': 8.279455,
            'EX_lac__D_e': 0.0,
            'EX_succ_e': 0.0,
        }
        for reaction_id, value in expected.items():
            self.assertAlmostEqual(run['tracked_flux_values'][reaction_id], value, places=3)
        self.assertEqual(run['positive_products'], ['EX_for_e', 'EX_ac_e', 'EX_etoh_e'])
        self.assertEqual(run['zero_products'], ['EX_lac__D_e', 'EX_succ_e'])
        self.assertEqual(run['dominant_product'], 'EX_for_e')
        self.assertAlmostEqual(run['glucose_uptake'], 10.0, places=3)
        self.assertAlmostEqual(run['oxygen_uptake'], 0.0, places=3)

    def test_negative_zero_is_normalised_in_state_and_report(self):
        production, medium = self._synthetic_flux_data(oxygen=-1e-12)
        report = self._record(
            objective_result=0.211663,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertEqual(report['fingerprint_run']['oxygen_uptake'], 0.0)
        self.assertEqual(report['current_oxygen_uptake'], 0.0)
        text = simulation.build_mission11_fingerprint_report_text(report)
        self.assertIn('Oxygen uptake: 0.000', text)
        self.assertNotIn('Oxygen uptake: -0.000', text)

    def test_full_profile_not_merely_two_positive_products_is_required(self):
        production, medium = self._synthetic_flux_data(formate=0.0)
        report = self._record(
            objective_result=0.211663,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('formate' in issue.lower() for issue in report['current_issues']))
        self.assertFalse(report['fingerprint_complete'])

    def test_zero_products_must_really_be_zero(self):
        production, medium = self._synthetic_flux_data(lactate=0.5)
        report = self._record(objective_result=0.211663, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(any('D-lactate' in issue for issue in report['current_issues']))

    def test_all_five_fluxes_must_be_selected_and_measured(self):
        production, medium = self._synthetic_flux_data()
        missing_selection = self._record(
            objective_result=0.211663,
            production_fluxes=production,
            medium_fluxes=medium,
            selected_fluxes=simulation.MISSION11_REQUIRED_TRACKED_FLUXES[:-1],
        )
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('EX_succ_e', missing_selection['missing_selected_fluxes'])

        production, medium = self._synthetic_flux_data()
        production['items'] = [item for item in production['items'] if item['reaction_id'] != 'EX_succ_e']
        missing_measurement = self._record(
            objective_result=0.211663,
            production_fluxes=production,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_measurement['current_run_valid'])
        self.assertIn('EX_succ_e', missing_measurement['missing_measured_fluxes'])

    def test_dominant_product_is_calculated_only_inside_required_panel(self):
        production, medium = self._synthetic_flux_data()
        production['items'].append({
            'reaction_id': 'EX_h_e',
            'raw_flux': 999.0,
            'production_flux': 999.0,
        })
        report = self._record(
            objective_result=0.211663,
            production_fluxes=production,
            medium_fluxes=medium,
            selected_fluxes=list(simulation.MISSION11_REQUIRED_TRACKED_FLUXES) + ['EX_h_e'],
        )
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertEqual(report['fingerprint_run']['dominant_product'], 'EX_for_e')
        self.assertNotIn('EX_h_e', report['fingerprint_run']['tracked_flux_values'])

    def test_invalid_runs_preserve_previously_valid_fingerprint(self):
        valid = self._record()
        stored = dict(valid['fingerprint_run'])
        production, medium = self._synthetic_flux_data()

        extra_environment = dict(self.reactions)
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION11_GLUCOSE_REACTION)
        extra_environment[f'reaction_{glucose_index}_lb'] = False
        knockout_genes = dict(self.genes)
        knockout_genes['b1241'] = False

        cases = [
            dict(method='pFBA', expected='Use FBA'),
            dict(objective='EX_for_e', expected='BIOMASS'),
            dict(reactions=simulation._build_default_reactions_data(), expected='Disable oxygen'),
            dict(reactions=extra_environment, expected='every other environmental bound'),
            dict(genes=knockout_genes, expected='all genes active'),
            dict(selected_fluxes=simulation.MISSION11_REQUIRED_TRACKED_FLUXES[:-1], expected='full fingerprint panel'),
        ]
        for case in cases:
            candidate = self._record(
                report=valid,
                method=case.get('method'),
                objective=case.get('objective'),
                genes=case.get('genes'),
                reactions=case.get('reactions'),
                selected_fluxes=case.get('selected_fluxes'),
                objective_result=0.211663,
                production_fluxes=production,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['fingerprint_run'], stored)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['expected'] in issue for issue in candidate['current_issues']))

    def test_visible_medium_and_growth_evidence_are_required(self):
        production, medium = self._synthetic_flux_data()
        production.pop('objective_raw')
        production.pop('biomass_raw')
        missing_growth = self._record(
            objective_result='not numeric', production_fluxes=production, medium_fluxes=medium
        )
        self.assertFalse(missing_growth['current_run_valid'])
        self.assertTrue(any('biomass flux' in issue for issue in missing_growth['current_issues']))

        production, medium = self._synthetic_flux_data()
        medium['items'] = [item for item in medium['items'] if item['reaction_id'] != simulation.MISSION11_OXYGEN_REACTION]
        missing_oxygen = self._record(objective_result=0.211663, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen-uptake evidence' in issue for issue in missing_oxygen['current_issues']))

    def test_answer_requires_evidence_and_accepts_name_or_reaction_id(self):
        empty = {}
        self.assertFalse(simulation.mission11_answer_matches('formate', empty))
        report = self._record()
        for answer in ('formate', 'Formate', 'EX_for_e', 'ex for e', 'formic acid'):
            self.assertTrue(simulation.mission11_answer_matches(answer, report), answer)
        for answer in ('ethanol', 'EX_ac_e', 'succinate'):
            self.assertFalse(simulation.mission11_answer_matches(answer, report), answer)

    def test_old_version1_report_is_rejected(self):
        stale = {
            'mission_id': '11',
            'check_version': 1,
            'ready_to_deliver': True,
            'dominant_product': 'EX_for_e',
        }
        self.assertFalse(simulation.mission11_answer_matches('formate', stale))
        text = simulation.build_mission11_fingerprint_report_text(stale)
        self.assertIn('Build one controlled anaerobic', text)
        self.assertNotIn('Evidence complete', text)

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = self._record()
        with patch.object(simulation, 'load_mission11_flux_fingerprint_check', return_value=completed) as loader:
            text = simulation.build_mission11_fingerprint_report_text({})
            matched = simulation.mission11_answer_matches('formate', {})
        loader.assert_not_called()
        self.assertFalse(matched)
        self.assertIn('Build one controlled anaerobic', text)

    def test_report_uses_careful_scientific_language(self):
        report = self._record()
        text = simulation.build_mission11_fingerprint_report_text(report)
        self.assertIn('positive exchange flux represents secretion predicted', text)
        self.assertIn('does not mean that E. coli can never produce', text)
        self.assertIn('model predicts positive growth', text)
        self.assertIn('same visible solution', text)
        self.assertNotIn('strain is viable', text.lower())

    def test_report_requires_player_to_infer_the_dominant_product(self):
        report = self._record()
        text = simulation.build_mission11_fingerprint_report_text(report)
        self.assertIn('formate (EX_for_e): 17.805', text)
        self.assertIn('acetate (EX_ac_e): 8.504', text)
        self.assertIn('ethanol (EX_etoh_e): 8.279', text)
        self.assertIn('greatest numeric secretion value', text)
        self.assertNotIn('Dominant tracked product:', text)
        self.assertNotIn('dominant product within the required panel should be', text.lower())

    def test_remote_wrapper_reuses_visible_result_without_hidden_requests(self):
        visible = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission11_flux_fingerprint_check', return_value=expected) as runner:
            observed = simulation.run_mission11_flux_fingerprint_check_remote('unused-url', visible)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible)

    def test_local_checker_contains_no_hidden_simulation_calls(self):
        source = inspect.getsource(simulation.run_mission11_flux_fingerprint_check)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_simulate_flux', source)
        self.assertIn('simulation_results', source)
        self.assertIn('medium_fluxes', source)

    def test_mission_ui_has_progression_guard_clear_report_and_answer_input(self):
        source = (CODE_DIR / 'mission11.py').read_text(encoding='utf-8')
        self.assertIn('is_mission11_unlocked', source)
        self.assertIn('clear_mission11_flux_fingerprint_check()', source)
        self.assertIn("text_input(\n                'Dominant tracked product: '", source)
        self.assertIn('build_mission11_fingerprint_report_text', source)
        self.assertIn('mission11_answer_matches', source)

    def test_five_fluxes_are_fixed_at_maximum_growth(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        model = simulation.model.copy()
        model.reactions.get_by_id(simulation.MISSION11_OXYGEN_REACTION).lower_bound = 0.0
        model.objective = simulation.MISSION11_GROWTH_OBJECTIVE
        solution = model.optimize()
        self.assertEqual(solution.status, 'optimal')
        self.assertAlmostEqual(float(solution.objective_value), 0.211663, delta=1e-3)
        expected = {
            'EX_for_e': 17.804674,
            'EX_ac_e': 8.503585,
            'EX_etoh_e': 8.279455,
            'EX_lac__D_e': 0.0,
            'EX_succ_e': 0.0,
        }
        fva = flux_variability_analysis(
            model,
            reaction_list=list(simulation.MISSION11_REQUIRED_TRACKED_FLUXES),
            fraction_of_optimum=1.0,
        )
        for reaction_id, expected_value in expected.items():
            minimum = float(fva.loc[reaction_id, 'minimum'])
            maximum = float(fva.loc[reaction_id, 'maximum'])
            self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=reaction_id)
            self.assertAlmostEqual(minimum, expected_value, delta=1e-3, msg=reaction_id)


if __name__ == '__main__':
    unittest.main()
